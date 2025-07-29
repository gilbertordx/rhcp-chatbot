"""
Model Utilities for RHCP Chatbot ML Pipeline.

Provides functions for model training, evaluation, and management.
"""

import json
import joblib
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.metrics import precision_recall_fscore_support, make_scorer, f1_score
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

import matplotlib.pyplot as plt
import seaborn as sns


def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj


class TextTokenizer:
    """Tokenizer class that can be pickled for model persistence."""
    
    def __init__(self, use_stemming: bool = True):
        """
        Initialize the tokenizer.
        
        Args:
            use_stemming: Whether to use stemming in tokenization
        """
        self.use_stemming = use_stemming
        if use_stemming:
            self.stemmer = PorterStemmer()
    
    def __call__(self, text: str) -> List[str]:
        """
        Tokenize and optionally stem the input text.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of tokens
        """
        tokens = word_tokenize(text.lower())
        
        if self.use_stemming:
            return [self.stemmer.stem(token) for token in tokens]
        else:
            return tokens


class ModelUtils:
    """Utility class for model operations."""
    
    @staticmethod
    def create_text_processor(config: Dict[str, Any]):
        """
        Create text processing function based on configuration.
        
        Args:
            config: Configuration dictionary with preprocessing settings
            
        Returns:
            Text processing function that can be pickled
        """
        preprocessing_config = config.get('training', {}).get('preprocessing', {})
        use_stemming = preprocessing_config.get('use_stemming', True)
        
        return TextTokenizer(use_stemming=use_stemming)
    
    @staticmethod
    def create_pipeline(config: Dict[str, Any]) -> Pipeline:
        """
        Create ML pipeline based on configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configured sklearn Pipeline
        """
        # Get configuration sections
        vectorizer_config = config['model']['vectorizer']
        classifier_config = config['model']['classifier']
        
        # Create text processor
        tokenizer = ModelUtils.create_text_processor(config)
        
        # Create vectorizer
        vectorizer = TfidfVectorizer(
            tokenizer=tokenizer,
            ngram_range=tuple(vectorizer_config['ngram_range']),
            stop_words=vectorizer_config['stop_words'],
            max_features=vectorizer_config.get('max_features'),
            min_df=vectorizer_config.get('min_df', 1),
            max_df=vectorizer_config.get('max_df', 1.0)
        )
        
        # Create classifier
        classifier = LogisticRegression(
            random_state=classifier_config['random_state'],
            solver=classifier_config['solver'],
            multi_class=classifier_config['multi_class'],
            class_weight=classifier_config['class_weight'],
            max_iter=classifier_config.get('max_iter', 1000),
            C=classifier_config.get('C', 1.0)
        )
        
        # Create and return pipeline
        pipeline = Pipeline([
            ('tfidf', vectorizer),
            ('clf', classifier)
        ])
        
        return pipeline
    
    @staticmethod
    def train_model(pipeline: Pipeline, X_train: pd.Series, y_train: pd.Series, 
                   config: Dict[str, Any], logger=None) -> Pipeline:
        """
        Train the model pipeline.
        
        Args:
            pipeline: sklearn Pipeline to train
            X_train: Training features
            y_train: Training labels
            config: Configuration dictionary
            logger: Logger instance
            
        Returns:
            Trained pipeline
        """
        if logger:
            logger.info("Starting model training...")
            logger.info(f"Training samples: {len(X_train)}")
            logger.info(f"Unique classes: {len(y_train.unique())}")
        
        # Set random seed for reproducibility
        if config.get('reproducibility', {}).get('set_global_seed', True):
            seed = config.get('reproducibility', {}).get('seed', 42)
            np.random.seed(seed)
        
        # Train the pipeline
        pipeline.fit(X_train, y_train)
        
        if logger:
            logger.info("Model training completed successfully")
        
        return pipeline
    
    @staticmethod
    def evaluate_model(pipeline: Pipeline, X_test: pd.Series, y_test: pd.Series,
                      config: Dict[str, Any], logger=None) -> Dict[str, Any]:
        """
        Evaluate the trained model.
        
        Args:
            pipeline: Trained pipeline
            X_test: Test features
            y_test: Test labels
            config: Configuration dictionary
            logger: Logger instance
            
        Returns:
            Dictionary containing evaluation results
        """
        if logger:
            logger.info("Starting model evaluation...")
        
        # Make predictions
        y_pred = pipeline.predict(X_test)
        y_pred_proba = pipeline.predict_proba(X_test)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, support = precision_recall_fscore_support(
            y_test, y_pred, average=None, labels=pipeline.classes_
        )
        
        # Overall metrics
        macro_f1 = f1_score(y_test, y_pred, average='macro')
        weighted_f1 = f1_score(y_test, y_pred, average='weighted')
        micro_f1 = f1_score(y_test, y_pred, average='micro')
        
        # Create detailed results
        results = {
            'accuracy': accuracy,
            'macro_f1': macro_f1,
            'weighted_f1': weighted_f1,
            'micro_f1': micro_f1,
            'n_test_samples': len(X_test),
            'n_classes': len(pipeline.classes_),
            'classes': pipeline.classes_.tolist(),
            'class_metrics': {
                cls: {
                    'precision': prec,
                    'recall': rec,
                    'f1_score': f1_val,
                    'support': sup
                }
                for cls, prec, rec, f1_val, sup in zip(
                    pipeline.classes_, precision, recall, f1, support
                )
            },
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }
        
        if logger:
            logger.info(f"Evaluation completed - Accuracy: {accuracy:.4f}, Macro F1: {macro_f1:.4f}")
        
        # Convert numpy types to Python native types for JSON serialization
        results = convert_numpy_types(results)
        
        return results
    
    @staticmethod
    def cross_validate_model(pipeline: Pipeline, X: pd.Series, y: pd.Series,
                           config: Dict[str, Any], logger=None) -> Dict[str, Any]:
        """
        Perform cross-validation on the model.
        
        Args:
            pipeline: Pipeline to evaluate
            X: Features
            y: Labels
            config: Configuration dictionary
            logger: Logger instance
            
        Returns:
            Dictionary containing cross-validation results
        """
        cv_config = config.get('training', {})
        cv_folds = cv_config.get('cv_folds', 5)
        cv_scoring = cv_config.get('cv_scoring', ['accuracy', 'macro_f1'])
        
        if logger:
            logger.info(f"Starting {cv_folds}-fold cross-validation...")
        
        # Create stratified k-fold
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        
        # Define scoring metrics
        scoring_funcs = {
            'accuracy': 'accuracy',
            'macro_f1': make_scorer(f1_score, average='macro'),
            'weighted_f1': make_scorer(f1_score, average='weighted'),
            'micro_f1': make_scorer(f1_score, average='micro')
        }
        
        cv_results = {}
        
        for metric_name in cv_scoring:
            if metric_name in scoring_funcs:
                scores = cross_val_score(
                    pipeline, X, y,
                    cv=skf,
                    scoring=scoring_funcs[metric_name],
                    n_jobs=-1
                )
                
                cv_results[metric_name] = {
                    'scores': scores.tolist(),
                    'mean': scores.mean(),
                    'std': scores.std(),
                    'min': scores.min(),
                    'max': scores.max(),
                    'confidence_interval_95': [
                        scores.mean() - 1.96 * scores.std(),
                        scores.mean() + 1.96 * scores.std()
                    ]
                }
        
        if logger:
            logger.info("Cross-validation completed")
            for metric, results in cv_results.items():
                logger.info(f"{metric}: {results['mean']:.4f} ± {results['std']:.4f}")
        
        # Convert numpy types to Python native types for JSON serialization
        cv_results = convert_numpy_types(cv_results)
        
        return cv_results
    
    @staticmethod
    def test_model_predictions(pipeline: Pipeline, test_cases: List[str],
                             logger=None) -> List[Dict[str, Any]]:
        """
        Test model on specific test cases.
        
        Args:
            pipeline: Trained pipeline
            test_cases: List of test sentences
            logger: Logger instance
            
        Returns:
            List of prediction results
        """
        if logger:
            logger.info(f"Testing model on {len(test_cases)} test cases...")
        
        predictions = pipeline.predict(test_cases)
        probabilities = pipeline.predict_proba(test_cases)
        
        results = []
        for i, (text, pred) in enumerate(zip(test_cases, predictions)):
            max_prob = np.max(probabilities[i])
            prob_dist = {
                cls: prob for cls, prob in zip(pipeline.classes_, probabilities[i])
            }
            
            results.append({
                'text': text,
                'predicted_intent': pred,
                'confidence': max_prob,
                'probability_distribution': prob_dist
            })
            
            if logger:
                logger.info(f"'{text}' -> '{pred}' (confidence: {max_prob:.3f})")
        
        # Convert numpy types to Python native types for JSON serialization
        results = convert_numpy_types(results)
        
        return results
    
    @staticmethod
    def save_model(pipeline: Pipeline, model_path: str, metadata: Dict[str, Any],
                  config: Dict[str, Any], logger=None) -> None:
        """
        Save trained model with metadata.
        
        Args:
            pipeline: Trained pipeline
            model_path: Path to save model
            metadata: Model metadata
            config: Configuration dictionary
            logger: Logger instance
        """
        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save model
        joblib.dump(pipeline, model_path)
        
        # Save metadata
        metadata_path = model_path.with_suffix('.json')
        # Convert numpy types to Python native types for JSON serialization
        metadata = convert_numpy_types(metadata)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        if logger:
            logger.info(f"Model saved to: {model_path}")
            logger.info(f"Metadata saved to: {metadata_path}")
    
    @staticmethod
    def load_model(model_path: str) -> Tuple[Pipeline, Dict[str, Any]]:
        """
        Load trained model with metadata.
        
        Args:
            model_path: Path to model file
            
        Returns:
            Tuple of (pipeline, metadata)
        """
        model_path = Path(model_path)
        
        # Load model
        pipeline = joblib.load(model_path)
        
        # Load metadata
        metadata_path = model_path.with_suffix('.json')
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        return pipeline, metadata
    
    @staticmethod
    def plot_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray,
                            classes: List[str], save_path: Optional[str] = None,
                            normalize: bool = True) -> None:
        """
        Plot confusion matrix.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            classes: List of class names
            save_path: Path to save plot (optional)
            normalize: Whether to normalize the matrix
        """
        # Calculate confusion matrix
        cm = confusion_matrix(y_true, y_pred, labels=classes)
        
        if normalize:
            cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            fmt = '.2f'
            title = 'Normalized Confusion Matrix'
        else:
            fmt = 'd'
            title = 'Confusion Matrix'
        
        # Create plot
        plt.figure(figsize=(12, 10))
        sns.heatmap(cm, annot=True, fmt=fmt, cmap='Blues',
                   xticklabels=classes, yticklabels=classes)
        plt.title(title)
        plt.xlabel('Predicted Label')
        plt.ylabel('True Label')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    @staticmethod
    def create_model_metadata(pipeline: Pipeline, results: Dict[str, Any],
                            config: Dict[str, Any], training_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create comprehensive model metadata.
        
        Args:
            pipeline: Trained pipeline
            results: Evaluation results
            config: Configuration used
            training_info: Additional training information
            
        Returns:
            Dictionary containing model metadata
        """
        metadata = {
            'model_info': {
                'type': config['model']['type'],
                'created_at': datetime.now().isoformat(),
                'version': training_info.get('version', '1.0'),
                'sklearn_version': '1.5',  # Could be dynamically obtained
            },
            'data_info': {
                'total_samples': training_info.get('total_samples', 0),
                'training_samples': training_info.get('training_samples', 0),
                'test_samples': training_info.get('test_samples', 0),
                'unique_classes': len(pipeline.classes_),
                'classes': pipeline.classes_.tolist(),
            },
            'performance': {
                'accuracy': results.get('accuracy', 0),
                'macro_f1': results.get('macro_f1', 0),
                'weighted_f1': results.get('weighted_f1', 0),
                'micro_f1': results.get('micro_f1', 0),
            },
            'configuration': config,
            'training_info': training_info,
            'feature_info': {
                'vectorizer_type': config['model']['vectorizer']['type'],
                'ngram_range': config['model']['vectorizer']['ngram_range'],
                'stop_words': config['model']['vectorizer']['stop_words'],
            }
        }
        
        return metadata 