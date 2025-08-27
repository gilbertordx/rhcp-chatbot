# ============================================================================
# RHCP CHATBOT MODEL TRAINING - NOTEBOOK CELL
# Copy and paste this entire cell into your Jupyter notebook
# ============================================================================

import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

# Add project root to path for notebook execution
project_root = Path.cwd()
sys.path.append(str(project_root))

# Import required libraries
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    f1_score,
    make_scorer,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

print("RHCP Chatbot Model Training Pipeline (Notebook Version)")
print("=" * 60)


# Simple logger for notebook
class SimpleLogger:
    def info(self, msg):
        print(f"{msg}")

    def warning(self, msg):
        print(f"WARNING: {msg}")

    def error(self, msg):
        print(f"ERROR: {msg}")

    def debug(self, msg):
        print(f"DEBUG: {msg}")


logger = SimpleLogger()

# Load training data
logger.info("Loading training data...")


def find_project_root():
    """Find the project root directory by looking for key files."""
    current = Path.cwd()

    # Look for project root by checking for key files/directories
    for path in [current, current.parent, current.parent.parent]:
        if (
            path / "app" / "chatbot" / "data" / "training" / "base-corpus.json"
        ).exists():
            return path

    # If not found, try common locations
    common_paths = [
        Path("/home/gilberto/Documents/rhcp-chatbot"),
        Path.cwd() / "rhcp-chatbot",
        Path.cwd().parent / "rhcp-chatbot",
    ]

    for path in common_paths:
        if (
            path / "app" / "chatbot" / "data" / "training" / "base-corpus.json"
        ).exists():
            return path

    return current


def load_json_file(file_path):
    """Load JSON file safely with multiple path attempts."""
    # Try multiple possible paths
    possible_paths = [
        file_path,
        Path.cwd() / file_path,
        find_project_root() / file_path,
    ]

    for path in possible_paths:
        try:
            with open(path, encoding="utf-8") as f:
                logger.info(f"Successfully loaded: {path}")
                return json.load(f)
        except FileNotFoundError:
            continue

    logger.error(f"File not found in any of these locations: {possible_paths}")
    return None


# Find project root and update paths
project_root = find_project_root()
logger.info(f"Project root found: {project_root}")

# Load corpora with robust path resolution
base_corpus = load_json_file("app/chatbot/data/training/base-corpus.json")
rhcp_corpus = load_json_file("app/chatbot/data/training/rhcp-corpus.json")

if not base_corpus or not rhcp_corpus:
    raise FileNotFoundError(
        "Training data files not found. Please ensure you're running from the project root directory."
    )

# Extract texts and intents
texts = []
intents = []

for corpus in [base_corpus, rhcp_corpus]:
    for item in corpus["data"]:
        intent = item["intent"]
        for utterance in item["utterances"]:
            texts.append(utterance)
            intents.append(intent)

df = pd.DataFrame({"text": texts, "intent": intents})
logger.info(f"Loaded {len(df)} training samples with {df['intent'].nunique()} intents")

# Enhance minority classes
logger.info("Enhancing minority classes...")

class_counts = df["intent"].value_counts()
total_samples = len(df)
minority_threshold = max(10, total_samples * 0.02)
minority_classes = class_counts[class_counts < minority_threshold].index.tolist()

if minority_classes:
    logger.info(f"Found {len(minority_classes)} minority classes")

    # Enhancement templates
    enhancement_templates = {
        "agent.acquaintance": [
            "tell me about yourself",
            "what are you like",
            "describe yourself",
            "who are you exactly",
            "what kind of assistant are you",
        ],
        "agent.annoying": [
            "you are bothering me",
            "stop being annoying",
            "you are getting on my nerves",
            "this is irritating",
            "you are frustrating me",
        ],
        "agent.bad": [
            "you are terrible",
            "you are not good",
            "you are awful",
            "you are disappointing",
            "you are not helpful",
        ],
        "agent.beautiful": [
            "you are gorgeous",
            "you are stunning",
            "you look amazing",
            "you are attractive",
            "you are lovely",
        ],
        "agent.beclever": [
            "try to be smarter",
            "think harder",
            "use your brain",
            "be more intelligent",
            "improve your thinking",
        ],
        "user.angry": [
            "I am furious",
            "this makes me mad",
            "I am really upset",
            "I am enraged",
            "this is infuriating",
        ],
        "user.back": [
            "I have returned",
            "I am here again",
            "I came back",
            "I am back now",
            "I have come back",
        ],
        "user.bored": [
            "this is boring",
            "I am so bored",
            "this is dull",
            "I need something interesting",
            "entertain me",
        ],
        "user.busy": [
            "I am swamped",
            "I have no time",
            "I am overwhelmed",
            "I am tied up",
            "I cannot talk now",
        ],
    }

    enhanced_data = []
    for intent in minority_classes:
        if intent in enhancement_templates:
            examples = enhancement_templates[intent]
            for example in examples:
                enhanced_data.append({"text": example, "intent": intent})

    if enhanced_data:
        enhanced_df = pd.DataFrame(enhanced_data)
        df = pd.concat([df, enhanced_df], ignore_index=True)
        logger.info(f"Added {len(enhanced_data)} examples for minority classes")

# Split data
logger.info("Splitting data...")
X_train, X_test, y_train, y_test = train_test_split(
    df["text"], df["intent"], test_size=0.2, random_state=42, stratify=df["intent"]
)

logger.info(f"Data split: {len(X_train)} train, {len(X_test)} test samples")

# Create and train pipeline
logger.info("Creating and training model...")


def tokenize(text):
    """Simple tokenization function."""
    import re

    return re.findall(r"\b\w+\b", text.lower())


pipeline = Pipeline(
    [
        (
            "tfidf",
            TfidfVectorizer(
                tokenizer=tokenize, ngram_range=(1, 3), stop_words="english"
            ),
        ),
        (
            "clf",
            LogisticRegression(
                random_state=42,
                solver="lbfgs",
                multi_class="multinomial",
                class_weight="balanced",
            ),
        ),
    ]
)

pipeline.fit(X_train, y_train)
logger.info("Model training completed")

# Evaluate model
logger.info("Evaluating model...")
y_pred = pipeline.predict(X_test)

test_results = {
    "accuracy": (y_pred == y_test).mean(),
    "macro_f1": f1_score(y_test, y_pred, average="macro"),
    "weighted_f1": f1_score(y_test, y_pred, average="weighted"),
    "n_test_samples": len(y_test),
}

# Cross-validation
logger.info("Running cross-validation...")
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scoring = {
    "accuracy": "accuracy",
    "macro_f1": make_scorer(f1_score, average="macro"),
    "weighted_f1": make_scorer(f1_score, average="weighted"),
}

cv_results = {}
for metric_name, scorer in scoring.items():
    scores = cross_val_score(
        pipeline, df["text"], df["intent"], cv=skf, scoring=scorer, n_jobs=-1
    )
    cv_results[metric_name] = {
        "mean": scores.mean(),
        "std": scores.std(),
        "scores": scores.tolist(),
    }

# Generate confusion matrix
logger.info("Generating confusion matrix...")
plt.figure(figsize=(15, 12))
ConfusionMatrixDisplay.from_estimator(
    pipeline, X_test, y_test, xticks_rotation=45, normalize="true", values_format=".2f"
)
plt.title("Confusion Matrix - RHCP Chatbot Model\n(Normalized by True Class)")
plt.tight_layout()
plt.show()

# Print classification report
print("\nDetailed Classification Report:")
print(classification_report(y_test, y_pred))

# Save model and results
logger.info("Saving model and results...")

# Create output directories
os.makedirs("app/models", exist_ok=True)
os.makedirs("training_results", exist_ok=True)

# Save model
model_path = "app/models/logistic_regression_classifier_notebook.joblib"
joblib.dump(pipeline, model_path)

# Create metadata
metadata = {
    "model_type": "LogisticRegression_Notebook",
    "created_at": datetime.now().isoformat(),
    "total_samples": len(df),
    "unique_intents": df["intent"].nunique(),
    "class_distribution": df["intent"].value_counts().to_dict(),
    "test_results": test_results,
    "cross_validation": cv_results,
    "configuration": {
        "class_weight": "balanced",
        "multi_class": "multinomial",
        "solver": "lbfgs",
    },
}

# Save metadata
metadata_path = "app/models/model_metadata_notebook.json"
with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)

# Save detailed results
results_path = "training_results/training_results_notebook.json"
with open(results_path, "w") as f:
    json.dump(metadata, f, indent=2)

logger.info(f"Model saved: {model_path}")
logger.info(f"Metadata saved: {metadata_path}")
logger.info(f"Results saved: {results_path}")

# Print final summary
print("\nTRAINING COMPLETED SUCCESSFULLY!")
print("\nPERFORMANCE SUMMARY:")
print(f"  Test Accuracy: {test_results['accuracy']:.4f}")
print(f"  Test Macro F1: {test_results['macro_f1']:.4f}")
print(
    f"  CV Accuracy: {cv_results['accuracy']['mean']:.4f} ± {cv_results['accuracy']['std']:.4f}"
)
print(
    f"  CV Macro F1: {cv_results['macro_f1']['mean']:.4f} ± {cv_results['macro_f1']['std']:.4f}"
)

print(f"\nModel saved to: {model_path}")
print("Model is ready for deployment!")

# Test some predictions
test_cases = [
    "are you a bot",
    "bye for now",
    "Hello",
    "Who are the members of the band?",
    "Tell me about quantum physics",
]

print("\nTEST PREDICTIONS:")
predictions = pipeline.predict(test_cases)
probabilities = pipeline.predict_proba(test_cases)

for i, (query, pred) in enumerate(zip(test_cases, predictions, strict=False)):
    confidence = np.max(probabilities[i])
    print(f"'{query}' -> '{pred}' (confidence: {confidence:.3f})")

print("\nRHCP Chatbot model training complete!")
