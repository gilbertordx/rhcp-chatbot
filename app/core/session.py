import uuid

from fastapi import Request


def get_session_id(request: Request) -> str:
    """
    Get session ID from request headers or create a new one.

    Args:
        request: FastAPI request object

    Returns:
        Session ID string
    """
    # Try to get session ID from headers
    session_id = request.headers.get("X-Session-ID")

    if not session_id:
        # Generate new session ID if not provided
        session_id = str(uuid.uuid4())

    return session_id
