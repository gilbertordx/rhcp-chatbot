from fastapi import APIRouter, Depends, HTTPException

from app.core.inference import run_inference
from app.core.session import get_session_id
from app.errors import InvalidInputError, ProcessingError
from app.infra.logging import get_logger
from app.schemas import ChatRequest, ChatResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def process_chat_message(
    request: ChatRequest, session_id: str = Depends(get_session_id)
) -> ChatResponse:
    """
    Process a chat message and return a structured response.

    Args:
        request: Chat request containing the message
        session_id: Session identifier for conversation context

    Returns:
        ChatResponse with validated inference results
    """
    try:
        logger.info(
            f"Processing chat message: {request.message[:50]}{'...' if len(request.message) > 50 else ''}"
        )

        # Run unified inference pipeline
        response = run_inference(request.message, session_id)

        # Return structured response
        return ChatResponse(response=response, session_id=session_id)

    except InvalidInputError as e:
        logger.warning(f"Invalid input: {e.message}")
        raise HTTPException(
            status_code=400,
            detail={"error": e.message, "remedy": "Please provide a valid message"},
        ) from e

    except ProcessingError as e:
        logger.error(f"Processing error: {e.message}")
        raise HTTPException(
            status_code=500,
            detail={"error": e.message, "remedy": "Please try again later"},
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error processing message: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "remedy": "Please try again later",
            },
        ) from e
