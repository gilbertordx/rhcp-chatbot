from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

class ChatMessage(BaseModel):
    message: str

router = APIRouter()

@router.post("/")
async def process_chat_message(chat_message: ChatMessage, request: Request):
    user_message = chat_message.message
    if not user_message:
        raise HTTPException(status_code=400, detail="User message is required.")

    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")

    try:
        response = chatbot_processor.process_message(user_message)
        # The classifications are now part of the response from process_message in the JS version, 
        # but in our python version we have a separate method for it. Let's adjust.
        # In our python version, get_classifications is a separate method.
        # The original JS route returned classifications in the main JSON body.
        classifications = chatbot_processor.get_classifications(user_message)
        response['classifications'] = classifications # Add classifications to the response dict
        
        return response
    except Exception as e:
        # For debugging, it's helpful to see the error.
        print(f"Error processing message: {e}")
        # In a real app, you'd want more specific error handling and logging
        raise HTTPException(status_code=500, detail="An error occurred while processing your message.") 