#!/usr/bin/env python3
"""
Model Training Script for RHCP Chatbot ML Pipeline.

Main training script that coordinates data loading, model training, and evaluation.
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Add parent directories to path for imports - notebook compatible
try:
    # For script execution
    script_dir = Path(__file__).parent
except NameError:
    # For notebook execution
    script_dir = Path.cwd() / 'scripts' / 'training'

# Add project root to path
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

from scripts.utils.config_manager import ConfigManager
from scripts.utils.logger_setup import setup_training_logger
from scripts.utils.model_utils import ModelUtils
from scripts.data.load_data import DataLoader
from scripts.data.enhance_data import DataEnhancer
from scripts.evaluation.evaluate_model import ModelEvaluator

from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np


class ModelTrainer:
    """Main class for coordinating the training pipeline."""
    
    def __init__(self):
        """Initialize the trainer."""
        self.config_manager = ConfigManager()
        self.training_config = self.config_manager.get_training_config()
        self.data_config = self.config_manager.get_data_config()
        
        # Set up logging
        self.logger = setup_training_logger(self.training_config)
        
        # Initialize components
        self.data_loader = DataLoader(self.config_manager)
        self.data_enhancer = DataEnhancer(self.config_manager)
        self.evaluator = ModelEvaluator(self.config_manager)
        
        self.logger.info("Model trainer initialized")
    
    def run_training_pipeline(self):
        """Run the complete training pipeline."""
        self.logger.info("=== STARTING TRAINING PIPELINE ===")
        
        try:
            # Step 1: Load and validate data
            self.logger.info("Step 1: Loading training data...")
            df = self.data_loader.load_training_data()
            
            # Step 2: Enhance data if configured
            enhancement_config = self.training_config.get('enhancement', {})
            if enhancement_config.get('enable_minority_class_enhancement', False):
                self.logger.info("Step 2: Enhancing minority classes...")
                df = self.data_enhancer.enhance_minority_classes(df)
            else:
                self.logger.info("Step 2: Skipping data enhancement (disabled in config)")
            
            # Step 3: Split data
            self.logger.info("Step 3: Splitting data into train/test sets...")
            X_train, X_test, y_train, y_test = self._split_data(df)
            
            # Step 4: Create and train model
            self.logger.info("Step 4: Creating and training model...")
            pipeline = ModelUtils.create_pipeline(self.training_config)
            
            # Set random seed for reproducibility
            self._set_random_seed()
            
            # Train the model
            trained_pipeline = ModelUtils.train_model(
                pipeline, X_train, y_train, self.training_config, self.logger
            )
            
            # Step 5: Evaluate model
            self.logger.info("Step 5: Evaluating model performance...")
            
            # Test set evaluation
            test_results = ModelUtils.evaluate_model(
                trained_pipeline, X_test, y_test, self.training_config, self.logger
            )
            
            # Cross-validation
            cv_results = ModelUtils.cross_validate_model(
                trained_pipeline, df['text'], df['intent'], self.training_config, self.logger
            )
            
            # Test on specific cases
            test_cases = self.training_config.get('evaluation', {}).get('test_cases', [])
            prediction_results = ModelUtils.test_model_predictions(
                trained_pipeline, test_cases, self.logger
            )
            
            # Step 6: Save model and results
            self.logger.info("Step 6: Saving model and results...")
            self._save_training_artifacts(
                trained_pipeline, test_results, cv_results, prediction_results, df
            )
            
            # Step 7: Generate comprehensive evaluation
            self.logger.info("Step 7: Generating evaluation report...")
            self.evaluator.generate_evaluation_report(
                trained_pipeline, X_test, y_test, test_results, cv_results
            )
            
            self.logger.info("=== TRAINING PIPELINE COMPLETED SUCCESSFULLY ===")
            return trained_pipeline, test_results, cv_results
            
        except Exception as e:
            self.logger.error(f"Training pipeline failed: {e}")
            raise
    
    def _split_data(self, df: pd.DataFrame):
        """Split data into training and test sets."""
        training_config = self.training_config['training']
        
        X = df['text']
        y = df['intent']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=training_config['test_size'],
            random_state=training_config['random_state'],
            stratify=y if training_config['stratify'] else None
        )
        
        self.logger.info(f"Data split: {len(X_train)} train, {len(X_test)} test samples")
        return X_train, X_test, y_train, y_test
    
    def _set_random_seed(self):
        """Set random seeds for reproducibility."""
        reproducibility_config = self.training_config.get('reproducibility', {})
        
        if reproducibility_config.get('set_global_seed', True):
            seed = reproducibility_config.get('seed', 42)
            np.random.seed(seed)
            
            # Set other random seeds if needed
            import random
            random.seed(seed)
            
            self.logger.info(f"Random seed set to: {seed}")
    
    def _save_training_artifacts(self, pipeline, test_results, cv_results, 
                               prediction_results, df):
        """Save all training artifacts."""
        output_config = self.training_config['output']
        models_path = self.data_config['paths']['models']
        results_path = self.data_config['paths']['results']
        
        # Create paths
        Path(models_path).mkdir(parents=True, exist_ok=True)
        Path(results_path).mkdir(parents=True, exist_ok=True)
        
        # Model file path
        model_path = Path(models_path) / output_config['model_filename']
        
        # Create comprehensive metadata
        training_info = {
            'total_samples': len(df),
            'training_samples': test_results['n_test_samples'] * 4,  # Approximate
            'test_samples': test_results['n_test_samples'],
            'version': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'enhancement_applied': self.training_config.get('enhancement', {}).get('enable_minority_class_enhancement', False)
        }
        
        metadata = ModelUtils.create_model_metadata(
            pipeline, test_results, self.training_config, training_info
        )
        
        # Add cross-validation results to metadata
        metadata['cross_validation'] = cv_results
        metadata['test_predictions'] = prediction_results
        
        # Save model with metadata
        ModelUtils.save_model(
            pipeline, str(model_path), metadata, self.training_config, self.logger
        )
        
        # Save detailed results
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'model_path': str(model_path),
            'test_evaluation': test_results,
            'cross_validation': cv_results,
            'test_predictions': prediction_results,
            'data_summary': {
                'total_samples': len(df),
                'unique_intents': df['intent'].nunique(),
                'class_distribution': df['intent'].value_counts().to_dict()
            },
            'configuration': self.training_config
        }
        
        results_file = Path(results_path) / output_config['results_filename']
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Training artifacts saved:")
        self.logger.info(f"  Model: {model_path}")
        self.logger.info(f"  Results: {results_file}")
        
        # Create backup if configured
        if output_config.get('create_backup', True):
            training_files = self.training_config['data']['training_files']
            backup_dir = self.data_loader.create_data_backup()
            self.logger.info(f"  Backup: {backup_dir}")


def main():
    """Main function for standalone execution."""
    print("🚀 RHCP Chatbot Model Training Pipeline")
    print("=" * 50)
    
    try:
        # Initialize and run trainer
        trainer = ModelTrainer()
        pipeline, test_results, cv_results = trainer.run_training_pipeline()
        
        # Print summary
        print(f"\n✅ TRAINING COMPLETED SUCCESSFULLY!")
        print(f"\n📊 PERFORMANCE SUMMARY:")
        print(f"  Test Accuracy: {test_results['accuracy']:.4f}")
        print(f"  Test Macro F1: {test_results['macro_f1']:.4f}")
        print(f"  CV Accuracy: {cv_results['accuracy']['mean']:.4f} ± {cv_results['accuracy']['std']:.4f}")
        print(f"  CV Macro F1: {cv_results['macro_f1']['mean']:.4f} ± {cv_results['macro_f1']['std']:.4f}")
        
        print(f"\n🎯 Model is ready for deployment!")
        
    except Exception as e:
        print(f"\n❌ TRAINING FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 