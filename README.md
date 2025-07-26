# RHCP Chatbot

A Python-based conversational AI chatbot that provides information about the Red Hot Chili Peppers band, including details about members, albums, songs, and band history.

## Features

- **Intent Classification**: Uses machine learning (Logistic Regression) to understand user queries
- **Enhanced Entity Recognition**: Extracts band members, albums, and songs with fuzzy matching
- **Dynamic Responses**: Generates contextual responses based on classified intents
- **REST API**: FastAPI-based API for easy integration
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
pytest
```

### Model Training

To retrain the model with updated data:

1. Update training data in `app/chatbot/data/training/`
2. Run the training notebook: `model_training.ipynb`
3. The model will be saved to `app/models/`

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

## License

This project is licensed under the MIT License. 