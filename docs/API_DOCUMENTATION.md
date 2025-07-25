# RHCP Chatbot API Documentation

## Overview

The RHCP Chatbot provides two API implementations:
- **Node.js Express API** (Primary): RESTful API for chat interactions
- **Python FastAPI** (Alternative): FastAPI-based implementation with similar functionality

Both APIs provide the same core functionality for interacting with the Red Hot Chili Peppers chatbot.

## Base URLs

- **Node.js API**: `http://localhost:3000`
- **Python API**: `http://localhost:3000` (configurable via PORT environment variable)

## Authentication

Currently, the chat endpoints do not require authentication. Future versions may include JWT-based authentication for user management features.

## Content-Type

All API requests should use `Content-Type: application/json` for POST requests.

---

## Node.js Express API

### Chat Endpoints

#### POST /api/chat

Process a user message and get a chatbot response.

**Request Body:**
```json
{
  "message": "string" // Required: The user's message to the chatbot
}
```

**Response:**
```json
{
  "message": "string",           // The chatbot's response message
  "intent": "string",            // Detected intent (e.g., "member.biography", "album.specific")
  "confidence": 0.85,            // Confidence score (0.0 to 1.0)
  "entities": [                  // Extracted entities from the message
    {
      "type": "member|album|song", // Entity type
      "value": {                   // Entity details object
        "name": "string",
        // Additional fields vary by entity type
      }
    }
  ],
  "classifications": [            // All intent classifications sorted by confidence
    {
      "label": "string",          // Intent name
      "value": 0.85              // Confidence score
    }
  ]
}
```

**Example Request:**
```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about Anthony Kiedis"}'
```

**Example Response:**
```json
{
  "message": "Anthony Kiedis: Anthony Kiedis is the lead vocalist and primary lyricist of RHCP. He has been with the band since its inception in 1983.",
  "intent": "member.biography",
  "confidence": 0.92,
  "entities": [
    {
      "type": "member",
      "value": {
        "name": "Anthony Kiedis",
        "role": "Lead Vocals",
        "memberSince": 1983,
        "birthDate": "1962-11-01",
        "biography": "Anthony Kiedis is the lead vocalist and primary lyricist of RHCP. He has been with the band since its inception in 1983."
      }
    }
  ],
  "classifications": [
    {"label": "member.biography", "value": 0.92},
    {"label": "member.general", "value": 0.08}
  ]
}
```

**Error Responses:**

- **400 Bad Request**: Missing or empty message
```json
{
  "error": "User message is required."
}
```

- **503 Service Unavailable**: Chatbot not initialized
```json
{
  "error": "Chatbot processor is not initialized."
}
```

- **500 Internal Server Error**: Processing error
```json
{
  "error": "An error occurred while processing your message."
}
```

---

## Python FastAPI

### Chat Endpoints

#### POST /api/chat/

Process a user message and get a chatbot response (FastAPI implementation).

**Request Body:**
```json
{
  "message": "string" // Required: The user's message to the chatbot
}
```

**Response:**
```json
{
  "message": "string",           // The chatbot's response message
  "intent": "string",            // Detected intent
  "confidence": 0.85,            // Confidence score (0.0 to 1.0)
  "entities": [                  // Extracted entities from the message
    {
      "type": "member|album|song", // Entity type
      "value": {                   // Entity details object
        "name": "string",
        // Additional fields vary by entity type
      }
    }
  ],
  "classifications": [            // All intent classifications sorted by confidence
    {
      "label": "string",          // Intent name
      "value": 0.85              // Confidence score
    }
  ]
}
```

#### GET /

Health check endpoint.

**Response:**
```json
{
  "message": "RHCP Chatbot is running"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:3000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "What albums has the band released?"}'
```

**Example Response:**
```json
{
  "message": "The Red Hot Chili Peppers have released numerous studio albums including Blood Sugar Sex Magik, Californication, By the Way, and Stadium Arcadium, among others.",
  "intent": "album.general",
  "confidence": 0.78,
  "entities": [],
  "classifications": [
    {"label": "album.general", "value": 0.78},
    {"label": "discography.general", "value": 0.15}
  ]
}
```

---

## Intent Types

The chatbot recognizes several intent categories:

### Member Intents
- `member.biography` - Requests for member biographies
- `member.general` - General questions about band members

### Album Intents
- `album.specific` - Questions about specific albums
- `album.general` - General album-related questions

### Song Intents
- `song.specific` - Questions about specific songs
- `song.general` - General song-related questions

### General Intents
- `greeting` - Greeting messages
- `goodbye` - Farewell messages
- `thanks` - Thank you messages
- `unrecognized` - Unrecognized input

---

## Entity Types

### Member Entity
```json
{
  "type": "member",
  "value": {
    "name": "string",
    "role": "string",
    "memberSince": 1983,
    "birthDate": "1962-11-01",
    "biography": "string",
    "periods": ["1988-1992", "1998-2009"] // For former members
  }
}
```

### Album Entity
```json
{
  "type": "album",
  "value": {
    "name": "string",
    "releaseDate": "1991-09-24",
    "producer": "string",
    "tracks": ["track1", "track2", "..."]
  }
}
```

### Song Entity
```json
{
  "type": "song",
  "value": {
    "name": "string",
    "album": "string"
  }
}
```

---

## Error Handling

Both APIs use standard HTTP status codes:

- `200 OK` - Successful request
- `400 Bad Request` - Invalid request format or missing required fields
- `500 Internal Server Error` - Server processing error
- `503 Service Unavailable` - Service not ready or initialized

Error responses follow this format:
```json
{
  "error": "Error description",
  "detail": "Additional error details (FastAPI only)"
}
```

---

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting for production use.

---

## Examples

### Basic Chat Interaction
```bash
# Ask about a band member
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Who is Flea?"}'

# Ask about an album
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about Blood Sugar Sex Magik"}'

# Ask about a song
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What album is Under the Bridge from?"}'
```

### JavaScript/Node.js Client Example
```javascript
const axios = require('axios');

async function chatWithBot(message) {
  try {
    const response = await axios.post('http://localhost:3000/api/chat', {
      message: message
    });
    
    console.log('Bot response:', response.data.message);
    console.log('Intent:', response.data.intent);
    console.log('Confidence:', response.data.confidence);
    
    return response.data;
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

// Usage
chatWithBot("Tell me about John Frusciante");
```

### Python Client Example
```python
import requests
import json

def chat_with_bot(message):
    url = "http://localhost:3000/api/chat/"
    payload = {"message": message}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        print(f"Bot response: {data['message']}")
        print(f"Intent: {data['intent']}")
        print(f"Confidence: {data['confidence']}")
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

# Usage
chat_with_bot("What is the band's history?")
```