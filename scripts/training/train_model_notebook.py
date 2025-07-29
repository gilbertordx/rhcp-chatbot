#!/usr/bin/env python3
"""
Notebook-Compatible Model Training Script for RHCP Chatbot ML Pipeline.

This version is designed to run in Jupyter notebooks without __file__ issues.
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add project root to path for notebook execution
project_root = Path.cwd()
sys.path.append(str(project_root))

# Import required libraries
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, f1_score, make_scorer
from sklearn.utils.class_weight import compute_class_weight
import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import ConfusionMatrixDisplay

print("RHCP Chatbot Model Training Pipeline (Notebook Version)")
print("=" * 60)


class NotebookModelTrainer:
    """Notebook-compatible model trainer."""
    
    def __init__(self):
        """Initialize the trainer."""
        self.logger = self._setup_simple_logger()
        self.logger.info("Notebook model trainer initialized")
    
    def _setup_simple_logger(self):
        """Simple logger for notebook environment."""
        class SimpleLogger:
            def info(self, msg): print(f"{msg}")
            def warning(self, msg): print(f"WARNING: {msg}")
            def error(self, msg): print(f"ERROR: {msg}")
            def debug(self, msg): print(f"DEBUG: {msg}")
        return SimpleLogger()
    
    def load_training_data(self):
        """Load training data from JSON files."""
        self.logger.info("Loading training data...")
        
        def load_json_file(file_path):
            """Load JSON file safely."""
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except FileNotFoundError:
                self.logger.error(f"File not found: {file_path}")
                return None
        
        # Load corpora
        base_corpus = load_json_file('app/chatbot/data/training/base-corpus.json')
        rhcp_corpus = load_json_file('app/chatbot/data/training/rhcp-corpus.json')
        
        if not base_corpus or not rhcp_corpus:
            raise FileNotFoundError("Training data files not found")
        
        # Extract texts and intents
        texts = []
        intents = []
        
        for corpus in [base_corpus, rhcp_corpus]:
            for item in corpus['data']:
                intent = item['intent']
                for utterance in item['utterances']:
                    texts.append(utterance)
                    intents.append(intent)
        
        df = pd.DataFrame({'text': texts, 'intent': intents})
        self.logger.info(f"Loaded {len(df)} training samples with {df['intent'].nunique()} intents")
        
        return df
    
    def enhance_minority_classes(self, df):
        """Enhance minority classes with additional examples."""
        self.logger.info("Enhancing minority classes...")
        
        class_counts = df['intent'].value_counts()
        total_samples = len(df)
        minority_threshold = max(10, total_samples * 0.02)
        minority_classes = class_counts[class_counts < minority_threshold].index.tolist()
        
        if not minority_classes:
            self.logger.info("No minority classes found")
            return df
        
        # Enhancement templates
        enhancement_templates = {
            'agent.acquaintance': [
                'tell me about yourself', 'what are you like', 'describe yourself',
                'who are you exactly', 'what kind of assistant are you'
            ],
            'agent.annoying': [
                'you are bothering me', 'stop being annoying', 'you are getting on my nerves',
                'this is irritating', 'you are frustrating me'
            ],
            'agent.bad': [
                'you are terrible', 'you are not good', 'you are awful',
                'you are disappointing', 'you are not helpful'
            ],
            'agent.beautiful': [
                'you are gorgeous', 'you are stunning', 'you look amazing',
                'you are attractive', 'you are lovely'
            ],
            'agent.beclever': [
                'try to be smarter', 'think harder', 'use your brain',
                'be more intelligent', 'improve your thinking'
            ],
            'user.angry': [
                'I am furious', 'this makes me mad', 'I am really upset',
                'I am enraged', 'this is infuriating'
            ],
            'user.back': [
                'I have returned', 'I am here again', 'I came back',
                'I am back now', 'I have come back'
            ],
            'user.bored': [
                'this is boring', 'I am so bored', 'this is dull',
                'I need something interesting', 'entertain me'
            ],
            'user.busy': [
                'I am swamped', 'I have no time', 'I am overwhelmed',
                'I am tied up', 'I cannot talk now'
            ]
        }
        
        enhanced_data = []
        for intent in minority_classes:
            if intent in enhancement_templates:
                examples = enhancement_templates[intent]
                for example in examples:
                    enhanced_data.append({'text': example, 'intent': intent})
        
        if enhanced_data:
            enhanced_df = pd.DataFrame(enhanced_data)
            df_enhanced = pd.concat([df, enhanced_df], ignore_index=True)
            self.logger.info(f"Added {len(enhanced_data)} examples for minority classes")
            return df_enhanced
        
        return df
    
    def create_pipeline(self):
        """Create the ML pipeline."""
        def tokenize(text):
            """Simple tokenization function."""
            import re
            return re.findall(r'\b\w+\b', text.lower())
        
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                tokenizer=tokenize, 
                ngram_range=(1, 3), 
                stop_words='english'
            )),
            ('clf', LogisticRegression(
                random_state=42, 
                solver='lbfgs', 
                multi_class='multinomial',
                class_weight='balanced'
            ))
        ])
        
        return pipeline
    
    def train_model(self, pipeline, X_train, y_train):
        """Train the model."""
        self.logger.info("Training model...")
        pipeline.fit(X_train, y_train)
        self.logger.info("Model training completed")
        return pipeline
    
    def evaluate_model(self, pipeline, X_test, y_test):
        """Evaluate model performance."""
        self.logger.info("Evaluating model...")
        
        y_pred = pipeline.predict(X_test)
        
        results = {
            'accuracy': (y_pred == y_test).mean(),
            'macro_f1': f1_score(y_test, y_pred, average='macro'),
            'weighted_f1': f1_score(y_test, y_pred, average='weighted'),
            'n_test_samples': len(y_test)
        }
        
        return results
    
    def cross_validate_model(self, pipeline, X, y):
        """Perform cross-validation."""
        self.logger.info("Running cross-validation...")
        
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scoring = {
            'accuracy': 'accuracy',
            'macro_f1': make_scorer(f1_score, average='macro'),
            'weighted_f1': make_scorer(f1_score, average='weighted')
        }
        
        cv_results = {}
        for metric_name, scorer in scoring.items():
            scores = cross_val_score(pipeline, X, y, cv=skf, scoring=scorer, n_jobs=-1)
            cv_results[metric_name] = {
                'mean': scores.mean(),
                'std': scores.std(),
                'scores': scores.tolist()
            }
        
        return cv_results
    
    def generate_confusion_matrix(self, pipeline, X_test, y_test):
        """Generate confusion matrix."""
        self.logger.info("Generating confusion matrix...")
        
        plt.figure(figsize=(15, 12))
        ConfusionMatrixDisplay.from_estimator(
            pipeline, X_test, y_test, 
            xticks_rotation=45,
            normalize='true',
            values_format='.2f'
        )
        plt.title('Confusion Matrix - RHCP Chatbot Model\n(Normalized by True Class)')
        plt.tight_layout()
        plt.show()
        
        # Print classification report
        y_pred = pipeline.predict(X_test)
        print("\nDetailed Classification Report:")
        print(classification_report(y_test, y_pred))
    
    def save_model(self, pipeline, results, cv_results, df):
        """Save model and results."""
        self.logger.info("Saving model and results...")
        
        # Create output directories
        os.makedirs('app/models', exist_ok=True)
        os.makedirs('training_results', exist_ok=True)
        
        # Save model
        model_path = 'app/models/logistic_regression_classifier_notebook.joblib'
        joblib.dump(pipeline, model_path)
        
        # Create metadata
        metadata = {
            'model_type': 'LogisticRegression_Notebook',
            'created_at': datetime.now().isoformat(),
            'total_samples': len(df),
            'unique_intents': df['intent'].nunique(),
            'class_distribution': df['intent'].value_counts().to_dict(),
            'test_results': results,
            'cross_validation': cv_results,
            'configuration': {
                'class_weight': 'balanced',
                'multi_class': 'multinomial',
                'solver': 'lbfgs'
            }
        }
        
        # Save metadata
        metadata_path = 'app/models/model_metadata_notebook.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save detailed results
        results_path = 'training_results/training_results_notebook.json'
        with open(results_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.logger.info(f"Model saved: {model_path}")
        self.logger.info(f"Metadata saved: {metadata_path}")
        self.logger.info(f"Results saved: {results_path}")
        
        return model_path
    
    def run_training_pipeline(self):
        """Run the complete training pipeline."""
        self.logger.info("=== STARTING NOTEBOOK TRAINING PIPELINE ===")
        
        try:
            # Step 1: Load data
            df = self.load_training_data()
            
            # Step 2: Enhance minority classes
            df = self.enhance_minority_classes(df)
            
            # Step 3: Split data
            X_train, X_test, y_train, y_test = train_test_split(
                df['text'], df['intent'],
                test_size=0.2,
                random_state=42,
                stratify=df['intent']
            )
            
            self.logger.info(f"Data split: {len(X_train)} train, {len(X_test)} test samples")
            
            # Step 4: Create and train model
            pipeline = self.create_pipeline()
            trained_pipeline = self.train_model(pipeline, X_train, y_train)
            
            # Step 5: Evaluate model
            test_results = self.evaluate_model(trained_pipeline, X_test, y_test)
            cv_results = self.cross_validate_model(trained_pipeline, df['text'], df['intent'])
            
            # Step 6: Generate confusion matrix
            self.generate_confusion_matrix(trained_pipeline, X_test, y_test)
            
            # Step 7: Save model and results
            model_path = self.save_model(trained_pipeline, test_results, cv_results, df)
            
            self.logger.info("=== NOTEBOOK TRAINING PIPELINE COMPLETED SUCCESSFULLY ===")
            return trained_pipeline, test_results, cv_results, model_path
            
        except Exception as e:
            self.logger.error(f"Training pipeline failed: {e}")
            raise


def main():
    """Main function for notebook execution."""
    try:
        # Initialize and run trainer
        trainer = NotebookModelTrainer()
        pipeline, test_results, cv_results, model_path = trainer.run_training_pipeline()
        
        # Print summary
        print(f"\nTRAINING COMPLETED SUCCESSFULLY!")
        print(f"\nPERFORMANCE SUMMARY:")
        print(f"  Test Accuracy: {test_results['accuracy']:.4f}")
        print(f"  Test Macro F1: {test_results['macro_f1']:.4f}")
        print(f"  CV Accuracy: {cv_results['accuracy']['mean']:.4f} ± {cv_results['accuracy']['std']:.4f}")
        print(f"  CV Macro F1: {cv_results['macro_f1']['mean']:.4f} ± {cv_results['macro_f1']['std']:.4f}")
        
        print(f"\nModel saved to: {model_path}")
        print(f"Model is ready for deployment!")
        
        return pipeline, test_results, cv_results
        
    except Exception as e:
        print(f"\nTRAINING FAILED: {e}")
        raise


if __name__ == "__main__":
    main() 