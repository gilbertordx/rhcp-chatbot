# RHCP Chatbot Component Documentation

## Overview

This document provides comprehensive documentation for all public classes, functions, and components in the RHCP Chatbot system, covering both Node.js and Python implementations.

---

## Node.js Components

### Classes

#### RHCPChatbot Class

**File**: `src/app.js`

Main chatbot application class that handles initialization and setup.

```javascript
class RHCPChatbot {
    constructor()
    async initialize()
}
```

**Constructor**
- **Description**: Creates a new RHCPChatbot instance
- **Parameters**: None
- **Properties**:
  - `trainingData`: Stores training corpus data
  - `staticData`: Stores band information and discography
  - `classifier`: Natural language classifier instance
  - `chatbotProcessor`: ChatbotProcessor instance

**Methods**

##### `async initialize()`
- **Description**: Initializes the chatbot by loading data and training the classifier
- **Parameters**: None
- **Returns**: `Promise<void>`
- **Throws**: Error if initialization fails
- **Example**:
```javascript
const chatbot = new RHCPChatbot();
await chatbot.initialize();
```

#### ChatbotProcessor Class

**File**: `src/chatbotProcessor.js`

Core chatbot processing engine that handles message understanding and response generation.

```javascript
class ChatbotProcessor {
    constructor(classifier, trainingData, staticData)
    async processMessage(message)
}
```

**Constructor**
- **Description**: Creates a new ChatbotProcessor instance
- **Parameters**:
  - `classifier` (Object): Trained Natural language classifier
  - `trainingData` (Object): Training corpus data with base and RHCP-specific data
  - `staticData` (Object): Static band information and discography data
- **Properties**:
  - `knownMembers`: Array of known band member names (lowercase)
  - `knownAlbums`: Array of known album names (lowercase)
  - `knownSongs`: Array of known songs with album information

**Methods**

##### `async processMessage(message)`
- **Description**: Processes a user message and returns a chatbot response
- **Parameters**:
  - `message` (string): User's input message
- **Returns**: `Promise<Object>` with the following structure:
```javascript
{
  message: string,        // Response message
  intent: string,         // Detected intent
  confidence: number,     // Confidence score (0.0-1.0)
  entities: Array,        // Extracted entities
  classifications: Array  // All classifications with scores
}
```
- **Example**:
```javascript
const processor = new ChatbotProcessor(classifier, trainingData, staticData);
const response = await processor.processMessage("Tell me about Flea");
console.log(response.message); // "Flea: Flea is the bassist and co-founding member..."
```

### Functions

#### initializeChatbot()

**File**: `src/initializer.js`

Initializes and returns a cached ChatbotProcessor instance.

```javascript
async function initializeChatbot()
```

- **Description**: Loads or trains NLU classifier and creates ChatbotProcessor instance
- **Parameters**: None
- **Returns**: `Promise<ChatbotProcessor>` - Initialized ChatbotProcessor instance
- **Caching**: Returns cached instance on subsequent calls
- **Example**:
```javascript
const { initializeChatbot } = require('./initializer');
const processor = await initializeChatbot();
```

#### processChatMessage()

**File**: `src/http/controllers/chatController.js`

Controller function for processing chat messages via HTTP API.

```javascript
async function processChatMessage(chatbotProcessor, userMessage)
```

- **Description**: Processes a chat message using the provided processor
- **Parameters**:
  - `chatbotProcessor` (ChatbotProcessor): Initialized processor instance
  - `userMessage` (string): User's message
- **Returns**: `Promise<Object>` - Chatbot response object
- **Throws**: 
  - Error if chatbotProcessor is null/undefined
  - Error if userMessage is empty/null
- **Example**:
```javascript
const { processChatMessage } = require('./http/controllers/chatController');
const response = await processChatMessage(processor, "Hello");
```

#### createChatRouter()

**File**: `src/http/routes/chatRoutes.js`

Creates Express router for chat-related endpoints.

```javascript
function createChatRouter(chatbotProcessor, chatController)
```

- **Description**: Sets up chat routes with the provided processor and controller
- **Parameters**:
  - `chatbotProcessor` (ChatbotProcessor): Initialized processor instance
  - `chatController` (Function): Controller function for processing messages
- **Returns**: `express.Router` - Configured Express router
- **Routes**:
  - `POST /` - Process chat message
- **Example**:
```javascript
const createChatRouter = require('./http/routes/chatRoutes');
const router = createChatRouter(processor, processChatMessage);
app.use('/api/chat', router);
```

### Utility Functions

#### startServer()

**File**: `src/app.js`

Starts the Express server with initialized chatbot.

```javascript
async function startServer()
```

- **Description**: Initializes chatbot and starts HTTP server
- **Parameters**: None
- **Returns**: `Promise<void>`
- **Environment Variables**:
  - `PORT`: Server port (default: 3000)
- **Example**:
```javascript
// Called automatically when running the application
startServer();
```

---

## Python Components

### Classes

#### ChatbotProcessor Class

**File**: `rhcp-chatbot-py/app/chatbot/processor.py`

Python implementation of the chatbot processing engine.

```python
class ChatbotProcessor:
    def __init__(self, classifier, training_data, static_data)
    def get_classifications(self, message)
    def process_message(self, message)
```

**Constructor**
- **Description**: Creates a new ChatbotProcessor instance
- **Parameters**:
  - `classifier`: Trained scikit-learn classifier pipeline
  - `training_data` (dict): Training corpus data
  - `static_data` (dict): Static band information and discography
- **Properties**:
  - `known_members`: List of known band member names (lowercase)
  - `known_albums`: List of known album names (lowercase)
  - `known_songs`: List of known songs with album information

**Methods**

##### `get_classifications(message)`
- **Description**: Returns intent classifications for a message
- **Parameters**:
  - `message` (str): Input message
- **Returns**: `List[Dict]` - Classifications sorted by confidence
```python
[
    {"label": "intent_name", "value": 0.85},
    {"label": "other_intent", "value": 0.15}
]
```
- **Example**:
```python
processor = ChatbotProcessor(classifier, training_data, static_data)
classifications = processor.get_classifications("Hello")
```

##### `process_message(message)`
- **Description**: Processes a user message and returns response
- **Parameters**:
  - `message` (str): User's input message
- **Returns**: `Dict` with response structure:
```python
{
    "message": str,        # Response message
    "intent": str,         # Detected intent
    "confidence": float,   # Confidence score (0.0-1.0)
    "entities": list      # Extracted entities
}
```
- **Example**:
```python
response = processor.process_message("Tell me about John Frusciante")
print(response["message"])  # Biography information
```

### Functions

#### initialize_chatbot()

**File**: `rhcp-chatbot-py/app/chatbot/initializer.py`

Async function to initialize the chatbot processor.

```python
async def initialize_chatbot()
```

- **Description**: Loads or trains classifier and creates ChatbotProcessor
- **Parameters**: None
- **Returns**: `ChatbotProcessor` - Initialized processor instance
- **Caching**: Returns cached instance on subsequent calls
- **Model Storage**: Saves/loads trained models using joblib
- **Example**:
```python
from app.chatbot.initializer import initialize_chatbot
processor = await initialize_chatbot()
```

#### train_classifier()

**File**: `rhcp-chatbot-py/app/chatbot/initializer.py`

Trains a new NLU classifier from training data.

```python
def train_classifier(training_files)
```

- **Description**: Trains LogisticRegression classifier with TF-IDF features
- **Parameters**:
  - `training_files` (List[str]): Paths to training corpus JSON files
- **Returns**: `sklearn.pipeline.Pipeline` - Trained classifier pipeline
- **Features**: Uses TF-IDF with n-grams (1-3) and stemming
- **Example**:
```python
files = ['base-corpus.json', 'rhcp-corpus.json']
classifier = train_classifier(files)
```

#### Utility Functions

##### `load_json_file(file_path)`
- **Description**: Loads JSON data from file
- **Parameters**: `file_path` (str): Path to JSON file
- **Returns**: `Dict` - Parsed JSON data

##### `stem_tokens(tokens)`
- **Description**: Applies Porter stemming to tokens
- **Parameters**: `tokens` (List[str]): List of tokens
- **Returns**: `List[str]` - Stemmed tokens

##### `tokenize(text)`
- **Description**: Tokenizes and stems text
- **Parameters**: `text` (str): Input text
- **Returns**: `List[str]` - Tokenized and stemmed words

### FastAPI Components

#### ChatMessage Model

**File**: `rhcp-chatbot-py/app/api/routes/chat.py`

Pydantic model for chat message requests.

```python
class ChatMessage(BaseModel):
    message: str
```

- **Description**: Request model for chat endpoints
- **Fields**:
  - `message` (str): Required user message
- **Validation**: Automatic validation via Pydantic

#### API Endpoints

##### `process_chat_message()`

**File**: `rhcp-chatbot-py/app/api/routes/chat.py`

FastAPI endpoint for processing chat messages.

```python
@router.post("/")
async def process_chat_message(chat_message: ChatMessage, request: Request)
```

- **Description**: Processes chat message and returns response
- **Parameters**:
  - `chat_message` (ChatMessage): Pydantic model with user message
  - `request` (Request): FastAPI request object
- **Returns**: `Dict` - Chatbot response with classifications
- **Exceptions**:
  - `HTTPException(400)`: Missing message
  - `HTTPException(503)`: Processor not initialized
  - `HTTPException(500)`: Processing error

##### `read_root()`

**File**: `rhcp-chatbot-py/app/main.py`

Health check endpoint.

```python
@app.get("/")
def read_root()
```

- **Description**: Returns health status
- **Returns**: `{"message": "RHCP Chatbot is running"}`

---

## Configuration

### Node.js Configuration

#### Environment Variables
- `NODE_ENV`: Environment mode (development/production/test)
- `PORT`: Server port (default: 3000)

#### Constants
- `CONFIDENCE_THRESHOLD`: Intent confidence threshold (default: 0.0005)

### Python Configuration

**File**: `rhcp-chatbot-py/app/core/config.py`

```python
PORT = int(os.getenv("PORT", 3000))
```

#### Environment Variables
- `PORT`: Server port (default: 3000)

#### Constants
- `CONFIDENCE_THRESHOLD`: Intent confidence threshold (default: 0.5)

---

## Data Models

### Training Data Structure

```json
{
  "data": [
    {
      "intent": "string",
      "utterances": ["string", "..."],
      "answers": ["string", "..."]
    }
  ]
}
```

### Static Data Structure

#### Band Info
```json
{
  "name": "Red Hot Chili Peppers",
  "formed": 1983,
  "location": "Los Angeles, California",
  "currentMembers": [...],
  "formerMembers": [...]
}
```

#### Discography
```json
{
  "studioAlbums": [...],
  "compilationAlbums": [...],
  "liveAlbums": [...]
}
```

---

## Usage Examples

### Node.js Integration

```javascript
const { initializeChatbot } = require('./src/initializer');
const { processChatMessage } = require('./src/http/controllers/chatController');

async function example() {
  // Initialize chatbot
  const processor = await initializeChatbot();
  
  // Process a message
  const response = await processChatMessage(processor, "Hello!");
  console.log(response);
}
```

### Python Integration

```python
from app.chatbot.initializer import initialize_chatbot

async def example():
    # Initialize chatbot
    processor = await initialize_chatbot()
    
    # Process a message
    response = processor.process_message("Hello!")
    print(response)
```

### Express.js Server Setup

```javascript
const express = require('express');
const { initializeChatbot } = require('./src/initializer');
const createChatRouter = require('./src/http/routes/chatRoutes');
const { processChatMessage } = require('./src/http/controllers/chatController');

const app = express();
app.use(express.json());

async function setupServer() {
  const processor = await initializeChatbot();
  app.use('/api/chat', createChatRouter(processor, processChatMessage));
  
  app.listen(3000, () => {
    console.log('Server running on port 3000');
  });
}

setupServer();
```

### FastAPI Server Setup

```python
from fastapi import FastAPI
from app.api.routes import chat
from app.chatbot.initializer import initialize_chatbot

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    processor = await initialize_chatbot()
    app.state.chatbot_processor = processor

app.include_router(chat.router, prefix="/api/chat")
```