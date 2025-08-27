import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from app.models.user import User, UserSession


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> dict[str, Any]:
        """Create a new user account."""
        # Validate input
        if not self._validate_username(username):
            raise ValueError(
                "Username must be 3-20 characters and contain only letters, numbers, and underscores"
            )

        if not self._validate_email(email):
            raise ValueError("Invalid email format")

        if not self._validate_password(password):
            raise ValueError("Password must be at least 8 characters long")

        # Check if user already exists
        if self.db.query(User).filter(User.username == username).first():
            raise ValueError("Username already exists")

        if self.db.query(User).filter(User.email == email).first():
            raise ValueError("Email already exists")

        # Create new user
        user = User(
            username=username, email=email, first_name=first_name, last_name=last_name
        )
        user.set_password(password)

        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return {"success": True, "user": user.to_dict()}
        except IntegrityError:
            self.db.rollback()
            raise ValueError("User creation failed") from None

    def authenticate_user(self, username: str, password: str) -> User | None:
        """Authenticate a user with username and password."""
        user = self.db.query(User).filter(User.username == username).first()
        if not user or not user.check_password(password):
            return None
        if not user.is_active:
            return None
        return user

    def create_access_token(self, user: User) -> str:
        """Create a JWT access token for the user."""
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode = {
            "sub": str(user.id),
            "username": user.username,
            "is_admin": user.is_admin,
            "exp": expire,
        }
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def create_user_session(self, user: User) -> str:
        """Create a user session and return session ID."""
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        session = UserSession(
            user_id=user.id, session_id=session_id, expires_at=expires_at
        )

        self.db.add(session)
        self.db.commit()

        return session_id

    def get_user_by_token(self, token: str) -> User | None:
        """Get user from JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
            user = self.db.query(User).filter(User.id == user_id).first()
            return user if user and user.is_active else None
        except jwt.PyJWTError:
            return None

    def get_user_by_session(self, session_id: str) -> User | None:
        """Get user from session ID."""
        session = (
            self.db.query(UserSession)
            .filter(UserSession.session_id == session_id, UserSession.is_active)
            .first()
        )

        if not session or session.is_expired():
            return None

        user = self.db.query(User).filter(User.id == session.user_id).first()
        return user if user and user.is_active else None

    def update_last_login(self, user: User) -> None:
        """Update user's last login timestamp."""
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()

    def deactivate_session(self, session_id: str) -> bool:
        """Deactivate a user session."""
        session = (
            self.db.query(UserSession)
            .filter(UserSession.session_id == session_id)
            .first()
        )

        if session:
            session.is_active = False
            self.db.commit()
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count of cleaned sessions."""
        expired_sessions = (
            self.db.query(UserSession)
            .filter(UserSession.expires_at < datetime.now(timezone.utc))
            .all()
        )

        count = len(expired_sessions)
        for session in expired_sessions:
            self.db.delete(session)

        self.db.commit()
        return count

    def _validate_username(self, username: str) -> bool:
        """Validate username format."""
        if len(username) < 3 or len(username) > 20:
            return False
        return bool(re.match(r"^[a-zA-Z0-9_]+$", username))

    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def _validate_password(self, password: str) -> bool:
        """Validate password strength."""
        return len(password) >= 8
