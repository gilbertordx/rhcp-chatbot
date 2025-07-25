from fastapi import FastAPI
from app.api.routes import chat
from app.core.config import PORT
from app.chatbot.initializer import initialize_chatbot
import uvicorn

app = FastAPI(title="RHCP Chatbot")

@app.on_event("startup")
async def startup_event():
    chatbot_processor = await initialize_chatbot()
    app.state.chatbot_processor = chatbot_processor

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/")
def read_root():
    return {"message": "RHCP Chatbot is running"}

def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True) 