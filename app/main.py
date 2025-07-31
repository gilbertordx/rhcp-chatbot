import time
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.api.routes import chat, auth
from app.core.database import create_tables
from app.chatbot.initializer import initialize_chatbot
from app.config import get_settings
from app.infra.logging import setup_logging, get_logger, set_request_context, clear_request_context
from app.errors import RHCPError, ConfigError, ProcessingError
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    setup_logging(
        level=settings.log_level,
        format_type=settings.log_format,
        debug=settings.debug
    )
    logger = get_logger(__name__)
    
    logger.info("Starting RHCP Chatbot", extra={"version": "2.0.0"})
    
    try:
        create_tables()
        logger.info("Database tables created/verified")
        
        chatbot_processor = await initialize_chatbot()
        app.state.chatbot_processor = chatbot_processor
        logger.info("Chatbot initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down RHCP Chatbot")

app = FastAPI(
    title="RHCP Chatbot",
    description="A Red Hot Chili Peppers chatbot with authentication and conversation memory",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log request/response with timing and request ID."""
    request_id = str(uuid.uuid4())
    set_request_context(request_id_val=request_id)
    
    logger = get_logger(__name__)
    start_time = time.time()
    
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={"request_id": request_id}
    )
    
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"Request completed: {response.status_code}",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "latency_ms": round(process_time, 2)
            }
        )
        
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(
            f"Request failed: {str(e)}",
            extra={
                "request_id": request_id,
                "latency_ms": round(process_time, 2)
            }
        )
        raise
    finally:
        clear_request_context()

# Add exception handlers
@app.exception_handler(RHCPError)
async def rhcp_exception_handler(request: Request, exc: RHCPError):
    """Handle RHCP-specific exceptions."""
    logger = get_logger(__name__)
    logger.error(f"RHCP Error: {exc.message}", extra={"details": exc.details})
    
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "remedy": "Check input and try again"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger = get_logger(__name__)
    logger.error(f"Unexpected error: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "remedy": "Contact support if problem persists"
        }
    )

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/")
def read_root():
    return {
        "message": "RHCP Chatbot is running",
        "version": "2.0.0",
        "features": [
            "Conversation memory with context",
            "User authentication",
            "Session management",
            "Entity recognition",
            "Intent classification"
        ],
        "endpoints": {
            "auth": "/api/auth",
            "chat": "/api/chat",
            "docs": "/docs"
        }
    }

@app.get("/healthz")
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/readyz")
async def readiness_check():
    """Readiness check endpoint - verifies critical dependencies."""
    logger = get_logger(__name__)
    
    details = {}
    ready = True
    
    # Check database
    try:
        from app.core.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        details["database"] = "ok"
    except Exception as e:
        details["database"] = f"error: {str(e)}"
        ready = False
    
    # Check model files
    settings = get_settings()
    import os
    
    if os.path.exists(settings.model_path):
        details["model"] = "ok"
    else:
        details["model"] = "error: model file not found"
        ready = False
    
    if os.path.exists(settings.band_info_path):
        details["band_info"] = "ok"
    else:
        details["band_info"] = "error: band info file not found"
        ready = False
    
    if os.path.exists(settings.discography_path):
        details["discography"] = "ok"
    else:
        details["discography"] = "error: discography file not found"
        ready = False
    
    # Check chatbot processor
    try:
        if hasattr(app.state, 'chatbot_processor') and app.state.chatbot_processor:
            details["chatbot_processor"] = "ok"
        else:
            details["chatbot_processor"] = "error: not initialized"
            ready = False
    except Exception as e:
        details["chatbot_processor"] = f"error: {str(e)}"
        ready = False
    
    logger.info(f"Readiness check: {ready}", extra={"details": details})
    
    if ready:
        return {"ready": ready, "details": details}
    else:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"ready": ready, "details": details}
        )

def start():
    """Launched with `poetry run start` at root level"""
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True) 