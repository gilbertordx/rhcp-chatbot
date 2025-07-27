from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes import chat, auth
from app.core.config import PORT
from app.core.database import create_tables
from app.chatbot.initializer import initialize_chatbot
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_tables()
    print("Database tables created/verified.")
    
    chatbot_processor = await initialize_chatbot()
    app.state.chatbot_processor = chatbot_processor
    print("Chatbot initialized successfully.")
    
    yield
    
    # Shutdown
    print("Shutting down RHCP Chatbot...")

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

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "RHCP Chatbot"}

def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True) 