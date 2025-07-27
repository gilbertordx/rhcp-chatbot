# RHCP Chatbot API Documentation

## Overview

The RHCP Chatbot API provides a comprehensive interface for interacting with a Red Hot Chili Peppers knowledge base. The API supports user authentication, conversation memory, and intelligent responses about band members, albums, songs, and band history.

## Base URL

```
http://localhost:8000
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Most endpoints require authentication except for registration and login.

### Authentication Flow

1. **Register** a new user account
2. **Login** to receive an access token
3. **Use the token** in the `Authorization` header for subsequent requests

### Headers

For authenticated requests, include:
```
Authorization: Bearer <your_access_token>
```

## Endpoints

### Authentication Endpoints

#### Register User

**POST** `/api/auth/register`

Create a new user account.

**Request Body:**
```json
{
    "username": "string",
    "email": "string",
    "password": "string",
    "first_name": "string (optional)",
    "last_name": "string (optional)"
}
```

**Response:**
```json
{
    "success": true,
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_active": true,
        "is_admin": false,
        "created_at": "2024-01-01T00:00:00",
        "last_login": null
    }
}
```

**Validation Rules:**
- Username: 3-20 characters, alphanumeric + underscore only
- Email: Valid email format
- Password: Minimum 8 characters

#### Login User

**POST** `/api/auth/login`

Authenticate user and receive access token.

**Request Body:**
```json
{
    "username": "string",
    "password": "string"
}
```

**Response:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "session_id": "uuid-string",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe"
    }
}
```

#### Get Current User

**GET** `/api/auth/me`

Get current user information.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "is_admin": false,
    "created_at": "2024-01-01T00:00:00",
    "last_login": "2024-01-01T12:00:00"
}
```

#### Update User Profile

**PUT** `/api/auth/profile`

Update user profile information.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
    "first_name": "string (optional)",
    "last_name": "string (optional)",
    "email": "string (optional)"
}
```

**Response:**
```json
{
    "success": true,
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "newemail@example.com",
        "first_name": "John",
        "last_name": "Smith"
    }
}
```

#### Logout User

**POST** `/api/auth/logout`

Logout user and invalidate session.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
    "success": true,
    "message": "Successfully logged out"
}
```

### Chat Endpoints

#### Send Message

**POST** `/api/chat`

Send a message to the chatbot and receive a response.

**Headers:** `Authorization: Bearer <token>` (optional)

**Request Body:**
```json
{
    "message": "string",
    "session_id": "string (optional)"
}
```

**Response:**
```json
{
    "message": "Anthony Kiedis is the lead vocalist and primary lyricist of RHCP...",
    "intent": "member.biography",
    "confidence": 0.85,
    "entities": [
        {
            "type": "member",
            "value": {
                "name": "Anthony Kiedis",
                "role": "Vocals",
                "memberSince": "1983",
                "biography": "..."
            }
        }
    ],
    "session_id": "uuid-string"
}
```

**Response Fields:**
- `message`: The chatbot's response text
- `intent`: The classified intent of the user's message
- `confidence`: Confidence score (0-1) for the intent classification
- `entities`: Extracted entities (members, albums, songs)
- `session_id`: Session ID for conversation memory

#### Get Conversation History

**GET** `/api/chat/history/{session_id}`

Get conversation history for a specific session.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
    "session_id": "uuid-string",
    "history": [
        {
            "timestamp": "2024-01-01T12:00:00",
            "user_message": "Tell me about Anthony Kiedis",
            "bot_response": {
                "message": "Anthony Kiedis is the lead vocalist...",
                "intent": "member.biography",
                "confidence": 0.85,
                "entities": [...]
            }
        }
    ]
}
```

## Intent Classification

The chatbot recognizes the following intents:

### Band Information
- `band.members` - Information about current band members
- `band.history` - Band formation and history
- `band.style` - Musical style and genre
- `band.awards` - Awards and recognition
- `band.tours` - Tour information
- `band.influence` - Band's influence on music
- `band.collaborations` - Collaborations with other artists

### Member Information
- `member.biography` - Individual member biographies
- `member.role` - Member roles and instruments

### Album Information
- `album.info` - General album information
- `album.specific` - Specific album details

### Song Information
- `song.info` - General song information
- `song.specific` - Specific song details
- `song.lyrics` - Song lyrics

### General Conversation
- `greetings.hello` - Greeting messages
- `greetings.bye` - Farewell messages
- `greetings.howareyou` - How are you questions
- `agent.chatbot` - Questions about the chatbot itself
- `intent.outofscope` - Out of scope queries

## Entity Recognition

The chatbot can extract the following entity types:

### Members
- Current members: Anthony Kiedis, Flea, John Frusciante, Chad Smith
- Former members: Hillel Slovak, Jack Irons, Josh Klinghoffer, Dave Navarro

### Albums
- Studio albums: Blood Sugar Sex Magik, Californication, By the Way, Stadium Arcadium, etc.
- Compilation albums
- Live albums

### Songs
- Popular songs: Under the Bridge, Californication, Scar Tissue, Otherside, etc.

## Error Responses

### Validation Errors

**Status:** 422 Unprocessable Entity

```json
{
    "detail": [
        {
            "loc": ["body", "username"],
            "msg": "Username must be 3-20 characters",
            "type": "value_error"
        }
    ]
}
```

### Authentication Errors

**Status:** 401 Unauthorized

```json
{
    "detail": "Not authenticated"
}
```

### Not Found Errors

**Status:** 404 Not Found

```json
{
    "detail": "User not found"
}
```

### Server Errors

**Status:** 500 Internal Server Error

```json
{
    "detail": "Internal server error"
}
```

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting for production use.

## Session Management

- Sessions are automatically created when a user sends their first message
- Sessions expire after 24 hours of inactivity
- Users can have multiple concurrent sessions
- Session data includes conversation history and context

## Examples

### Complete Conversation Flow

1. **Register a user:**
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
         "username": "rhcp_fan",
         "email": "fan@example.com",
         "password": "securepassword123",
         "first_name": "John",
         "last_name": "Fan"
     }'
```

2. **Login:**
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
         "username": "rhcp_fan",
         "password": "securepassword123"
     }'
```

3. **Send a message:**
```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <your_token>" \
     -d '{
         "message": "Tell me about Anthony Kiedis"
     }'
```

4. **Get conversation history:**
```bash
curl -X GET "http://localhost:8000/api/chat/history/<session_id>" \
     -H "Authorization: Bearer <your_token>"
```

## Development

### Running the API

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

### Environment Variables

Create a `.env` file with:

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./rhcp_chatbot.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Support

For issues and questions, please refer to the main README.md file or create an issue in the repository. 