import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, chat
from app.chatbot.initializer import initialize_chatbot
from app.chatbot.memory import ConversationMemory
from app.config import get_settings
from app.core.inference import initialize_inference
from app.errors import RHCPError
from app.infra.logging import (
    clear_request_context,
    get_logger,
    set_request_context,
    setup_logging,
)

# Global settings
settings = get_settings()

# Global chatbot instances
chatbot_processor = None
memory_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global chatbot_processor, memory_manager

    # Setup logging
    setup_logging(
        level=settings.log_level, format_type=settings.log_format, debug=settings.debug
    )

    logger = get_logger(__name__)
    logger.info("Starting RHCP Chatbot application")

    try:
        # Initialize chatbot processor
        chatbot_processor = await initialize_chatbot()

        # Initialize memory manager
        memory_manager = ConversationMemory(max_sessions=100, session_timeout_hours=24)

        # Initialize inference pipeline
        initialize_inference(chatbot_processor, memory_manager)

        # Store in app state
        app.state.chatbot_processor = chatbot_processor
        app.state.memory_manager = memory_manager

        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down RHCP Chatbot application")
    if memory_manager:
        memory_manager.cleanup_expired_sessions()


# Create FastAPI app
app = FastAPI(
    title="RHCP Chatbot API",
    description="A chatbot for Red Hot Chili Peppers information",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware to log requests and add request context."""
    request_id_val = str(uuid.uuid4())

    # Set request context
    set_request_context(request_id_val=request_id_val)

    # Log request start
    logger = get_logger(__name__)
    logger.info(f"Request started: {request.method} {request.url.path}")

    # Process request and measure latency
    import time

    start_time = time.time()

    try:
        response = await call_next(request)

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Log request completion
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={"latency_ms": latency_ms},
        )

        return response

    except Exception as e:
        # Log request error
        latency_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Request failed: {request.method} {request.url.path} - {str(e)}",
            extra={"latency_ms": latency_ms},
        )
        raise
    finally:
        # Clear request context
        clear_request_context()


# Exception handlers
@app.exception_handler(RHCPError)
async def rhcp_exception_handler(request: Request, exc: RHCPError):
    """Handle RHCP-specific exceptions."""
    logger = get_logger(__name__)
    logger.warning(f"RHCP error: {exc.message}", extra=exc.details)

    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "remedy": exc.details.get("remedy", "Please try again"),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger = get_logger(__name__)
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "remedy": "Please try again later"},
    )


# Health check endpoints
@app.get("/healthz")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/readyz")
async def readiness_check():
    """Readiness check endpoint."""
    # Get fresh settings to pick up environment variable changes
    from app.config import get_settings

    current_settings = get_settings(reload=True)

    ready = True
    details = {}

    # Check chatbot processor
    if not chatbot_processor:
        ready = False
        details["chatbot_processor"] = "not initialized"
    else:
        details["chatbot_processor"] = "ready"

    # Check memory manager
    if not memory_manager:
        ready = False
        details["memory_manager"] = "not initialized"
    else:
        details["memory_manager"] = "ready"

    # Check model file
    model_path = current_settings.model_path
    if not os.path.exists(model_path):
        ready = False
        details["model_file"] = f"not found: {model_path}"
    elif not os.access(model_path, os.R_OK):
        ready = False
        details["model_file"] = f"not readable: {model_path}"
    else:
        # Check file size > 0
        try:
            file_size = os.path.getsize(model_path)
            if file_size == 0:
                ready = False
                details["model_file"] = f"empty file: {model_path} (size: {file_size})"
            else:
                details["model_file"] = f"ready: {model_path} (size: {file_size} bytes)"
        except OSError as e:
            ready = False
            details["model_file"] = f"error checking file: {model_path} - {str(e)}"

    # Check static data files
    band_info_path = current_settings.band_info_path
    discography_path = current_settings.discography_path

    if not os.path.exists(band_info_path):
        ready = False
        details["band_info"] = f"not found: {band_info_path}"
    else:
        details["band_info"] = "exists"

    if not os.path.exists(discography_path):
        ready = False
        details["discography"] = f"not found: {discography_path}"
    else:
        details["discography"] = "exists"

    # Return appropriate status code
    if ready:
        return JSONResponse(content={"ready": True, "details": details})
    else:
        return JSONResponse(
            status_code=503, content={"ready": False, "details": details}
        )


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


def start():
    """Start the application."""
    import uvicorn

    uvicorn.run(
        "app.main:app", host=settings.host, port=settings.port, reload=settings.debug
    )


if __name__ == "__main__":
    start()
