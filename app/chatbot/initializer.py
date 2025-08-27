import json
import os

import joblib
import nltk
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.chatbot.memory import ConversationMemory
from app.chatbot.processor import ChatbotProcessor

# --- File Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(
    BASE_DIR, "..", "models", "logistic_regression_classifier.joblib"
)
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DATA_DIR = os.path.join(DATA_DIR, "static")
TRAINING_DATA_DIR = os.path.join(DATA_DIR, "training")

# --- Global Cache ---
chatbot_processor_instance = None

# --- Stemming and Tokenization ---
stemmer = PorterStemmer()


def stem_tokens(tokens):
    return [stemmer.stem(item) for item in tokens]


def tokenize(text):
    """Custom tokenization function with stemming."""
    stemmer = PorterStemmer()
    tokens = word_tokenize(text.lower())
    return [stemmer.stem(token) for token in tokens]


def load_json_file(file_path):
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


async def initialize_chatbot():
    """Initialize the chatbot with NLU classifier and data."""
    print("Initializing chatbot...")

    # Download required NLTK data
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        print("Downloading NLTK punkt tokenizer...")
        nltk.download("punkt")

    try:
        nltk.data.find("corpora/wordnet")
    except LookupError:
        print("Downloading NLTK wordnet...")
        nltk.download("wordnet")

    try:
        nltk.data.find("corpora/omw-1.4")
    except LookupError:
        print("Downloading NLTK omw-1.4...")
        nltk.download("omw-1.4")

    # Load training data
    training_data = {}
    training_files = [
        (os.path.join(TRAINING_DATA_DIR, "base-corpus.json"), "base"),
        (os.path.join(TRAINING_DATA_DIR, "rhcp-corpus-v2.json"), "rhcp"),
    ]

    for file_path, corpus_key in training_files:
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as f:
                training_data[corpus_key] = json.load(f)
        else:
            print(f"Warning: Training file {file_path} not found")

    # Load static data
    static_data = {}
    static_files = [
        (os.path.join(STATIC_DATA_DIR, "band-info.json"), "bandInfo"),
        (os.path.join(STATIC_DATA_DIR, "discography.json"), "discography"),
    ]

    missing_files = []
    for file_path, data_key in static_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, encoding="utf-8") as f:
                    static_data[data_key] = json.load(f)
                print(f"Loaded static data: {data_key}")
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                missing_files.append(file_path)
        else:
            print(f"Warning: Static data file {file_path} not found")
            missing_files.append(file_path)

    if missing_files:
        print(f"Missing static data files: {missing_files}")
        print("Chatbot will operate with limited functionality")

    # Check if pre-trained model exists
    model_path = MODEL_FILE

    if os.path.exists(model_path):
        print(f"Loading NLU classifier from {model_path}...")
        try:
            classifier = joblib.load(model_path)
            print("NLU classifier loaded successfully.")
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Training new model...")
            classifier = train_new_model(training_data)
    else:
        print("No pre-trained model found. Training new model...")
        classifier = train_new_model(training_data)

    # Create memory manager
    memory_manager = ConversationMemory(max_sessions=100, session_timeout_hours=24)

    # Create chatbot processor with memory manager
    processor = ChatbotProcessor(classifier, training_data, static_data, memory_manager)

    # Validate static data and report any issues
    validation_issues = processor.validate_static_data()
    if validation_issues:
        print("Static data validation issues:")
        for issue in validation_issues:
            print(f"  - {issue}")
        print("Chatbot will operate with limited functionality")
    else:
        print("Static data validation passed")

    print("Chatbot initialized successfully.")
    return processor


def train_new_model(training_data):
    """Train a new NLU classifier."""
    texts = []
    intents = []

    for _corpus_name, corpus_data in training_data.items():
        for item in corpus_data["data"]:
            if item["intent"] != "None":
                for utterance in item["utterances"]:
                    texts.append(utterance)
                    intents.append(item["intent"])

    print(f"Training on {len(texts)} samples...")

    # Create pipeline with TF-IDF vectorization and logistic regression
    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    tokenizer=tokenize,
                    ngram_range=(1, 3),  # unigrams, bigrams, trigrams
                    max_features=5000,
                    min_df=1,
                    max_df=0.95,
                ),
            ),
            ("classifier", LogisticRegression(random_state=42, max_iter=1000, C=1.0)),
        ]
    )

    # Train the model
    pipeline.fit(texts, intents)

    # Save the model
    os.makedirs(os.path.dirname(MODEL_FILE), exist_ok=True)
    model_path = MODEL_FILE
    joblib.dump(pipeline, model_path)
    print(f"Model saved to {model_path}")

    return pipeline
