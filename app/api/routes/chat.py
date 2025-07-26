from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    message: str
    intent: str
    confidence: float
    entities: list
    classifications: list
    context: Optional[dict] = None

router = APIRouter()

@router.post("/", response_model=SessionResponse)
async def process_chat_message(chat_message: ChatMessage, request: Request):
    user_message = chat_message.message
    session_id = chat_message.session_id
    
    if not user_message:
        raise HTTPException(status_code=400, detail="User message is required.")

    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")

    try:
        # Create new session if none provided
        if not session_id:
            session_id = chatbot_processor.memory_manager.create_session()
        
        # Check if session is valid
        if not chatbot_processor.memory_manager.is_session_valid(session_id):
            # Create new session if old one expired
            session_id = chatbot_processor.memory_manager.create_session()
        
        # Process message with session context
        response = chatbot_processor.process_message(user_message, session_id)
        
        # Get classifications
        classifications = chatbot_processor.get_classifications(user_message)
        
        # Get conversation context
        context = chatbot_processor.memory_manager.get_context(session_id)
        
        # Create complete response
        complete_response = {
            'message': response['message'],
            'intent': response['intent'],
            'confidence': response['confidence'],
            'entities': response['entities'],
            'classifications': classifications,
            'context': context,
            'session_id': session_id
        }
        

        
        return complete_response
    except Exception as e:
        # For debugging, it's helpful to see the error.
        print(f"Error processing message: {e}")
        # In a real app, you'd want more specific error handling and logging
        raise HTTPException(status_code=500, detail="An error occurred while processing your message.")

@router.get("/session/{session_id}/context")
async def get_session_context(session_id: str, request: Request):
    """Get conversation context for a specific session."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    if not chatbot_processor.memory_manager.is_session_valid(session_id):
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    
    context = chatbot_processor.memory_manager.get_context(session_id)
    history = chatbot_processor.memory_manager.get_conversation_history(session_id)
    
    return {
        "session_id": session_id,
        "context": context,
        "history": history
    }

@router.delete("/session/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Delete a conversation session."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    if session_id in chatbot_processor.memory_manager.sessions:
        del chatbot_processor.memory_manager.sessions[session_id]
        return {"message": "Session deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found.")

@router.get("/sessions/stats")
async def get_session_stats(request: Request):
    """Get statistics about active sessions."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    return chatbot_processor.memory_manager.get_session_stats() 