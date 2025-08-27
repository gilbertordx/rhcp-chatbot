import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.main import app
from app.models.user import Base

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=None
)
TestingSessionLocal = sessionmaker(autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create test client
    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_register_user_success(client):
    """Test successful user registration."""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User",
    }

    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] == True
    assert data["user"]["username"] == "testuser"
    assert data["user"]["email"] == "test@example.com"
    assert "password" not in data["user"]


def test_register_user_duplicate_username(client):
    """Test registration with duplicate username."""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    }

    # Register first user
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 200

    # Try to register with same username
    user_data["email"] = "test2@example.com"
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 400
    assert "Username already exists" in response.json()["detail"]


def test_register_user_invalid_email(client):
    """Test registration with invalid email."""
    user_data = {
        "username": "testuser",
        "email": "invalid-email",
        "password": "testpassword123",
    }

    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 400
    assert "Invalid email format" in response.json()["detail"]


def test_register_user_weak_password(client):
    """Test registration with weak password."""
    user_data = {"username": "testuser", "email": "test@example.com", "password": "123"}

    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 400
    assert "Password must be at least 8 characters long" in response.json()["detail"]


def test_login_user_success(client):
    """Test successful user login."""
    # Register user first
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    }
    client.post("/api/auth/register", json=user_data)

    # Login
    login_data = {"username": "testuser", "password": "testpassword123"}

    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "session_id" in data
    assert data["user"]["username"] == "testuser"


def test_login_user_invalid_credentials(client):
    """Test login with invalid credentials."""
    login_data = {"username": "nonexistent", "password": "wrongpassword"}

    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_get_current_user_info(client):
    """Test getting current user information."""
    # Register and login user
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    }
    client.post("/api/auth/register", json=user_data)

    login_data = {"username": "testuser", "password": "testpassword123"}
    login_response = client.post("/api/auth/login", json=login_data)
    token = login_response.json()["access_token"]

    # Get user info
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


def test_get_current_user_unauthorized(client):
    """Test getting user info without authentication."""
    response = client.get("/api/auth/me")
    assert response.status_code == 403


def test_update_user_profile(client):
    """Test updating user profile."""
    # Register and login user
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    }
    client.post("/api/auth/register", json=user_data)

    login_data = {"username": "testuser", "password": "testpassword123"}
    login_response = client.post("/api/auth/login", json=login_data)
    token = login_response.json()["access_token"]

    # Update profile
    headers = {"Authorization": f"Bearer {token}"}
    update_data = {"first_name": "Updated", "last_name": "Name"}
    response = client.put("/api/auth/me", headers=headers, params=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"


def test_logout_user(client):
    """Test user logout."""
    # Register and login user
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    }
    client.post("/api/auth/register", json=user_data)

    login_data = {"username": "testuser", "password": "testpassword123"}
    login_response = client.post("/api/auth/login", json=login_data)
    token = login_response.json()["access_token"]
    session_id = login_response.json()["session_id"]

    # Logout
    headers = {"Authorization": f"Bearer {token}", "X-Session-ID": session_id}
    response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 200
    assert "Successfully logged out" in response.json()["message"]


def test_chat_with_authentication(client):
    """Test chat functionality with authentication."""
    # Register and login user
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    }
    client.post("/api/auth/register", json=user_data)

    login_data = {"username": "testuser", "password": "testpassword123"}
    login_response = client.post("/api/auth/login", json=login_data)
    token = login_response.json()["access_token"]

    # Send chat message
    headers = {"Authorization": f"Bearer {token}"}
    chat_data = {"message": "Hello"}
    response = client.post("/api/chat/", json=chat_data, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert "intent" in data
    assert data["user_id"] is not None
    assert data["username"] == "testuser"


def test_chat_without_authentication(client):
    """Test chat functionality without authentication."""
    chat_data = {"message": "Hello"}
    response = client.post("/api/chat/", json=chat_data)
    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert "intent" in data
    assert data["user_id"] is None
    assert data["username"] is None
