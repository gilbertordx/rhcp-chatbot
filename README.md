# RHCP Chatbot

A Python-based conversational AI chatbot that provides comprehensive information about the Red Hot Chili Peppers band, including details about members, albums, songs, and band history.

## Features

- **Intent Classification**: Uses machine learning (Logistic Regression) to understand user queries
- **Enhanced Entity Recognition**: Extracts band members, albums, and songs with fuzzy matching
- **Dynamic Responses**: Generates contextual responses based on classified intents
- **REST API**: FastAPI-based API with authentication and session management
- **Conversation Memory**: Maintains context across conversation sessions
- **CLI Tool**: Command-line interface for easy interaction
- **Performance Monitoring**: Built-in performance testing and benchmarking
- **Comprehensive Testing**: 38 test cases covering all functionality
- **Pre-trained Model**: Includes a trained model ready for immediate use

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd rhcp-chatbot
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup NLTK data:**
   ```bash
   python app/scripts/setup_nltk.py
   ```

5. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

The server will start at `http://127.0.0.1:8000`

### Alternative: Use CLI Tool

For quick testing without starting the server:

```bash
# Single message
python cli.py --message "Tell me about Anthony Kiedis"

# Interactive mode
python cli.py

# API mode (requires server running)
python cli.py --api --username your_username --password your_password
```

## API Usage

### Chat Endpoint

**POST** `/api/chat`

**Request:**
```json
{
    "message": "tell me about john frusciante"
}
```

**Response:**
```json
{
    "message": "John Frusciante is the guitarist of the Red Hot Chili Peppers...",
    "intent": "member.biography",
    "confidence": 0.85,
    "entities": [
        {
            "type": "member",
            "value": {
                "name": "John Frusciante",
                "role": "Guitar",
                "biography": "..."
            }
        }
    ]
}
```

### Example with curl

```bash
curl -X POST "http://127.0.0.1:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "when was RHCP formed"}'
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test categories
pytest tests/test_auth.py
pytest tests/test_chatbot.py
```

### Performance Testing

Run comprehensive performance benchmarks:

```bash
python scripts/performance_test.py
```

This will test response times, accuracy, and throughput across different query types.

### Model Training

To retrain the model with updated data:

1. Update training data in `data/processed/`
2. Run the training notebook: `model_training.ipynb`
3. The model will be saved to `data/models/`

### Debugging

Use the debug utility to test model performance:

```bash
python debug_model.py
```

## Docker

### Build and Run

```bash
docker build -t rhcp-chatbot .
docker run -p 8000:80 rhcp-chatbot
```

## Documentation

For detailed technical documentation, see [docs/README.md](docs/README.md)

## Performance

Recent performance test results:
- **Average Response Time**: 3.26ms
- **Success Rate**: 100%
- **Accuracy**: 69.57%
- **Test Coverage**: 38 test cases

## Recent Improvements

- Fixed all failing tests (38/38 passing)
- Updated to FastAPI lifespan events (removed deprecation warnings)
- Fixed datetime deprecation warnings
- Added comprehensive test suite with edge cases
- Created CLI tool for easy interaction
- Added performance testing and benchmarking
- Enhanced API documentation
- Improved error handling and validation

## 🛠 Hardening Pass #1

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION HARDENING                     │
│                     RHCP Chatbot v2.0                       │
└─────────────────────────────────────────────────────────────┘
```

### New Production Features

**🔧 Structured Logging**
- JSON-formatted logs with correlation IDs
- Request tracking with latency measurement
- Debug mode with human-readable output
- Context-aware logging for chatbot operations

**⚙️ Environment Configuration**
- Environment-based settings with validation
- Support for `.env` files (optional)
- Immutable configuration after initialization
- Comprehensive validation with actionable errors

**✅ Input Validation & Error Handling**
- Typed exceptions with detailed context
- API request validation with Pydantic
- CLI input sanitization and length limits
- Consistent error responses with remedies

**🏥 Health & Readiness Endpoints**
- `/healthz` - Basic health check
- `/readyz` - Dependency readiness check
- Database, model, and file system validation
- Proper HTTP status codes (200/503)

### Quick Setup

```bash
# Environment variables (optional)
export RHCP_DEBUG=true
export RHCP_LOG_LEVEL=DEBUG
export RHCP_PORT=3000

# Start with debug logging
python cli.py --message "Hello" --debug

# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 3000

# Check health
curl http://localhost:3000/healthz
curl http://localhost:3000/readyz
```

### Sample JSON Logs

```json
{"ts": "2025-07-31T00:23:01.571249Z", "level": "INFO", "msg": "Application started", "module": "main", "function": "startup", "line": 25, "request_id": "req-456", "correlation_id": "corr-789"}
{"ts": "2025-07-31T00:23:01.572127Z", "level": "INFO", "msg": "Message processed", "module": "chat", "function": "process_chat_message", "line": 65, "request_id": "req-456", "intent": "greetings.hello", "confidence": 0.85, "latency_ms": 12.3}
```

### Troubleshooting

| Issue | Symptom | Remedy |
|-------|---------|--------|
| Environment not loaded | Default values used | Check `.env` file or set `RHCP_*` vars |
| Invalid input | 422/400 errors | Check message length (max 2000 chars) |
| Service not ready | 503 from `/readyz` | Check database, model files, dependencies |
| Debug logs not showing | JSON format still used | Ensure `--debug` flag or `RHCP_DEBUG=true` |

## License

This project is licensed under the MIT License. 