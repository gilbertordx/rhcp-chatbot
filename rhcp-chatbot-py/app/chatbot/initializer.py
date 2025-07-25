import json
import joblib
import os
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

from .processor import ChatbotProcessor

# --- File Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(BASE_DIR, '..', 'models', 'logistic_regression_classifier.joblib')
DATA_DIR = os.path.join(BASE_DIR, 'data')
STATIC_DATA_DIR = os.path.join(DATA_DIR, 'static')
TRAINING_DATA_DIR = os.path.join(DATA_DIR, 'training')

# --- Global Cache ---
chatbot_processor_instance = None

# --- Stemming and Tokenization ---
stemmer = PorterStemmer()

def stem_tokens(tokens):
    return [stemmer.stem(item) for item in tokens]

def tokenize(text):
    return stem_tokens(word_tokenize(text.lower()))


def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def train_classifier(training_files):
    print("Training new NLU classifier (LogisticRegression with Tfidf)...")
    
    texts = []
    intents = []

    for file_path in training_files:
        corpus = load_json_file(file_path)
        for item in corpus['data']:
            if item['intent'] != 'None':
                for utterance in item['utterances']:
                    texts.append(utterance)
                    intents.append(item['intent'])

    # Create a scikit-learn pipeline
    # TfidfVectorizer will handle tokenization, n-grams, and TF-IDF weighting
    # LogisticRegression is the classifier
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(tokenizer=tokenize, ngram_range=(1, 3))),
        ('clf', LogisticRegression(random_state=42, solver='lbfgs', multi_class='auto'))
    ])

    print("Training the pipeline...")
    pipeline.fit(texts, intents)
    print("Training complete.")

    # Save the trained pipeline
    joblib.dump(pipeline, MODEL_FILE)
    print(f"Classifier saved to {MODEL_FILE}")

    return pipeline

async def initialize_chatbot():
    global chatbot_processor_instance
    if chatbot_processor_instance:
        print("Returning cached chatbot processor.")
        return chatbot_processor_instance

    classifier = None
    
    # 1. Try to load the classifier
    if os.path.exists(MODEL_FILE):
        print(f"Loading NLU classifier from {MODEL_FILE}...")
        try:
            classifier = joblib.load(MODEL_FILE)
            print("NLU classifier loaded successfully.")
        except Exception as e:
            print(f"Error loading model: {e}. Retraining...")
            classifier = None

    # 2. If loading failed, train a new one
    if not classifier:
        training_files = [
            os.path.join(TRAINING_DATA_DIR, 'base-corpus.json'),
            os.path.join(TRAINING_DATA_DIR, 'rhcp-corpus.json')
        ]
        classifier = train_classifier(training_files)

    # 3. Load static and training data for the processor
    band_info = load_json_file(os.path.join(STATIC_DATA_DIR, 'band-info.json'))
    discography = load_json_file(os.path.join(STATIC_DATA_DIR, 'discography.json'))
    
    base_corpus = load_json_file(os.path.join(TRAINING_DATA_DIR, 'base-corpus.json'))
    rhcp_corpus = load_json_file(os.path.join(TRAINING_DATA_DIR, 'rhcp-corpus.json'))

    training_data = {'base': base_corpus, 'rhcp': rhcp_corpus}
    static_data = {'bandInfo': band_info, 'discography': discography}

    # 4. Create the ChatbotProcessor instance
    chatbot_processor_instance = ChatbotProcessor(classifier, training_data, static_data)
    print("Chatbot initialized successfully.")
    
    return chatbot_processor_instance 