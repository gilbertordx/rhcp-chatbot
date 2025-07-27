from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.database import get_db
from app.core.auth import get_current_active_user, get_current_admin_user
from app.services.auth import AuthService
from app.models.user import User

router = APIRouter()

# Pydantic models for request/response
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: Optional[str] = None
    last_login: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    session_id: str
    user: UserResponse

@router.post("/register", response_model=dict)
async def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register a new user account."""
    auth_service = AuthService(db)
    
    try:
        result = auth_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        return {
            "success": True,
            "message": "User registered successfully",
            "user": result["user"]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=LoginResponse)
async def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Login user and return access token and session ID."""
    auth_service = AuthService(db)
    
    user = auth_service.authenticate_user(user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    auth_service.update_last_login(user)
    
    # Create access token and session
    access_token = auth_service.create_access_token(user)
    session_id = auth_service.create_user_session(user)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        session_id=session_id,
        user=UserResponse(**user.to_dict())
    )

@router.post("/logout")
async def logout_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Logout user and invalidate session."""
    auth_service = AuthService(db)
    
    # Get session ID from request headers or query params
    session_id = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
    
    if session_id:
        auth_service.deactivate_session(session_id)
    
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return UserResponse(**current_user.to_dict())

@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update current user profile."""
    if first_name is not None:
        current_user.first_name = first_name
    if last_name is not None:
        current_user.last_name = last_name
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse(**current_user.to_dict())

@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all users (admin only)."""
    users = db.query(User).all()
    return [UserResponse(**user.to_dict()) for user in users]

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get user by ID (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse(**user.to_dict())

@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Activate a user account (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.commit()
    
    return {"message": "User activated successfully"}

@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Deactivate a user account (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}

@router.post("/cleanup-sessions")
async def cleanup_expired_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Clean up expired sessions (admin only)."""
    auth_service = AuthService(db)
    count = auth_service.cleanup_expired_sessions()
    
    return {"message": f"Cleaned up {count} expired sessions"} 