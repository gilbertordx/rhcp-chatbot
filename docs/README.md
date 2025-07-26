# RHCP Chatbot Documentation

## Overview

The RHCP Chatbot is a Python-based conversational AI designed to provide information about the Red Hot Chili Peppers band, including details about members, albums, songs, and band history.

## System Architecture

### Core Components

1. **Natural Language Understanding (NLU)**
   - Uses scikit-learn's LogisticRegression for intent classification
   - Trained on custom corpus data (base-corpus.json and rhcp-corpus.json)
   - Confidence threshold of 0.6 for intent recognition
   - Basic entity extraction for members, albums, and songs

2. **Response Generation**
   - Dynamic responses based on classified intents
   - Fallback to predefined answers from training corpus
   - Integration with static data for specific queries

3. **API Layer**
   - FastAPI-based REST API
   - Single `/api/chat` endpoint for message processing
   - JSON request/response format

4. **Data Sources**
   - Training data: `app/chatbot/data/training/`
   - Static data: `app/chatbot/data/static/`
   - Pre-trained model: `app/models/logistic_regression_classifier.joblib`

## Project Structure

```
rhcp-chatbot/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── chatbot/
│   │   ├── initializer.py      # Model initialization and training
│   │   ├── processor.py        # Core chatbot logic
│   │   └── data/               # Training and static data
│   ├── api/
│   │   └── routes/
│   │       └── chat.py         # Chat API endpoint
│   ├── core/
│   │   └── config.py           # Configuration settings
│   ├── models/                 # Trained ML models
│   ├── scripts/
│   │   └── setup_nltk.py       # NLTK data setup
│   └── services/               # Business logic services
├── tests/                      # Test files
├── notebooks/                  # Jupyter notebooks for development
├── debug_model.py              # Model debugging utility
├── model_training.ipynb        # Model training notebook
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
└── README.md                   # Main project documentation
```

## Development Guidelines

### Code Standards
- Follow PEP 8 Python style guidelines
- Use type hints where appropriate
- Write docstrings for functions and classes
- Maintain consistent naming conventions

### Testing
- Write unit tests for core functionality
- Use pytest for testing framework
- Aim for good test coverage

### Documentation
- Keep documentation concise and up-to-date
- Document API endpoints with examples
- Maintain clear README files

## API Usage

### Endpoint: `/api/chat`

**Request:**
```json
{
    "message": "tell me about john frusciante"
}
```

**Response:**
```json
{
    "message": "John Frusciante is the guitarist...",
    "intent": "member.biography",
    "confidence": 0.85,
    "entities": ["john frusciante"]
}
```

## Setup and Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup NLTK data:**
   ```bash
   python app/scripts/setup_nltk.py
   ```

3. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

## Model Training

The chatbot uses a Logistic Regression classifier trained on custom corpus data. To retrain the model:

1. Update training data in `app/chatbot/data/training/`
2. Run the training notebook: `model_training.ipynb`
3. The trained model is automatically saved to `app/models/`

## Future Enhancements

- Enhanced entity recognition
- Multi-turn conversation support
- Database integration for larger datasets
- Improved response generation
- Better error handling and logging 