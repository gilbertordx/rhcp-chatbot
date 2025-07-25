# RHCP Chatbot (Python Version)

This is a Python-based chatbot for Red Hot Chili Peppers fans, refactored from the original Node.js version.

## Features

-   Responds to questions about the band, albums, songs, and members.
-   Uses a machine learning model (Logistic Regression) for intent classification.
-   Simple entity recognition for members, albums, and songs.
-   API built with FastAPI.

## Project Structure

```
rhcp-chatbot-py/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app setup
│   │   ├── __init__.py
│   │   ├── processor.py      # Core chatbot logic
│   │   ├── initializer.py    # Logic to load/train the model
│   │   └── data/             # Static and training data
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py         # Configuration and env variables
│   ├── models/
│   │   └── logistic_regression_classifier.joblib # Trained model file
│   └── api/
│       ├── __init__.py
│       └── routes/
│           ├── __init__.py
│           └── chat.py         # Chat API endpoint
├── tests/
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

-   Python 3.8+
-   `pip` for package management

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd rhcp-chatbot-py
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    This will also download necessary NLTK data (`punkt`).

### Running the Application

1.  **Start the FastAPI server:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The server will be running at `http://127.0.0.1:8000`.

2.  **First time run:**
    The very first time you start the server, it will train the NLU model. This might take a minute or two. The trained model will be saved to `app/models/logistic_regression_classifier.joblib`. Subsequent startups will be much faster as they will load the pre-trained model.

### Using the API

You can interact with the chatbot by sending a POST request to the `/api/chat` endpoint.

**Request:**
-   **URL:** `http://127.0.0.1:8000/api/chat`
-   **Method:** `POST`
-   **Headers:** `Content-Type: application/json`
-   **Body:**
    ```json
    {
        "message": "tell me about john frusciante"
    }
    ```

**Example using `curl`:**
```bash
curl -X POST "http://127.0.0.1:8000/api/chat" \
-H "Content-Type: application/json" \
-d '{"message": "tell me about the album californication"}'
```

**Response:**
You will get a JSON response with the chatbot's message, the detected intent, and other details.

## Running with Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t rhcp-chatbot-py .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 8000:80 rhcp-chatbot-py
    ```
    The application will be accessible at `http://localhost:8000`.

## Testing

To run the tests, use `pytest`:
```bash
pytest
```
(Note: Test files need to be created). 