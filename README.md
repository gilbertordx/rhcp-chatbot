# rhcp-chatbot

Python chatbot for Red Hot Chili Peppers trivia. Early learning project exploring NLP, intent classification, and entity recognition. Rough around the edges, but functional.

## What It Does

- **Intent Classification**: Logistic Regression-based intent detection on user queries
- **Entity Recognition**: Extracts band members, albums, and songs from text
- **SQLite FTS**: Full-text search for factual retrieval
- **FastAPI Server**: REST API with CLI alternative
- **Testing**: 38 test cases covering core functionality

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start API server
uvicorn app.main:app --reload
# or use CLI
python cli.py --message "Tell me about Anthony Kiedis"
```

## Running Tests

```bash
pytest
pytest --cov=app
```

## Docker

```bash
docker build -t rhcp-chatbot .
docker run -p 8000:80 rhcp-chatbot
```

## Notes

First project with all the mistakes that come with learning. Code and architecture will likely change significantly as understanding improves. Useful reference for understanding how chatbots handle NLP at a basic level. 