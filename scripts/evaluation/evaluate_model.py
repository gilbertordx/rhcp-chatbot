#!/usr/bin/env python3
"""
Model Evaluation Script for RHCP Chatbot ML Pipeline.

Comprehensive evaluation including confusion matrix, classification reports, and visualizations.
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.utils.config_manager import ConfigManager
from scripts.utils.logger_setup import setup_evaluation_logger
from scripts.utils.model_utils import ModelUtils
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


class ModelEvaluator:
    """Comprehensive model evaluation and analysis."""
    
    def __init__(self, config_manager: ConfigManager = None):
        """Initialize the evaluator."""
        self.config_manager = config_manager or ConfigManager()
        self.training_config = self.config_manager.get_training_config()
        self.data_config = self.config_manager.get_data_config()
        self.logger = setup_evaluation_logger(self.data_config)
    
    def generate_evaluation_report(self, pipeline, X_test, y_test, 
                                 test_results, cv_results):
        """
        Generate comprehensive evaluation report.
        
        Args:
            pipeline: Trained model pipeline
            X_test: Test features
            y_test: Test labels
            test_results: Test evaluation results
            cv_results: Cross-validation results
        """
        self.logger.info("Generating comprehensive evaluation report...")
        
        results_path = Path(self.data_config['paths']['results'])
        results_path.mkdir(parents=True, exist_ok=True)
        
        # Generate confusion matrix
        self._generate_confusion_matrix(pipeline, X_test, y_test, results_path)
        
        # Generate performance plots
        self._generate_performance_plots(cv_results, results_path)
        
        # Generate detailed classification report
        self._generate_classification_report(test_results, results_path)
        
        # Generate model analysis
        self._generate_model_analysis(pipeline, test_results, cv_results, results_path)
        
        self.logger.info("Evaluation report generated successfully")
    
    def _generate_confusion_matrix(self, pipeline, X_test, y_test, results_path):
        """Generate and save confusion matrix visualization."""
        self.logger.info("Generating confusion matrix...")
        
        y_pred = pipeline.predict(X_test)
        classes = pipeline.classes_
        
        # Generate normalized confusion matrix plot
        plot_path = results_path / "confusion_matrix.png"
        ModelUtils.plot_confusion_matrix(
            y_test, y_pred, classes, save_path=str(plot_path), normalize=True
        )
        
        self.logger.info(f"Confusion matrix saved to: {plot_path}")
    
    def _generate_performance_plots(self, cv_results, results_path):
        """Generate performance visualization plots."""
        self.logger.info("Generating performance plots...")
        
        # Cross-validation scores plot
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        metrics = ['accuracy', 'macro_f1', 'weighted_f1', 'micro_f1']
        metric_names = ['Accuracy', 'Macro F1', 'Weighted F1', 'Micro F1']
        
        for i, (metric, name) in enumerate(zip(metrics, metric_names)):
            if metric in cv_results:
                ax = axes[i // 2, i % 2]
                scores = cv_results[metric]['scores']
                mean_score = cv_results[metric]['mean']
                std_score = cv_results[metric]['std']
                
                # Box plot
                ax.boxplot(scores)
                ax.set_title(f'{name}\nMean: {mean_score:.4f} ± {std_score:.4f}')
                ax.set_ylabel('Score')
                ax.set_xlabel('Cross-Validation')
                ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = results_path / "cv_performance.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Performance plots saved to: {plot_path}")
    
    def _generate_classification_report(self, test_results, results_path):
        """Generate detailed classification report."""
        self.logger.info("Generating detailed classification report...")
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'overall_metrics': {
                'accuracy': test_results['accuracy'],
                'macro_f1': test_results['macro_f1'],
                'weighted_f1': test_results['weighted_f1'],
                'micro_f1': test_results['micro_f1']
            },
            'class_metrics': test_results['class_metrics'],
            'confusion_matrix': test_results['confusion_matrix'],
            'detailed_report': test_results['classification_report']
        }
        
        report_path = results_path / "detailed_classification_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Detailed report saved to: {report_path}")
    
    def _generate_model_analysis(self, pipeline, test_results, cv_results, results_path):
        """Generate comprehensive model analysis."""
        self.logger.info("Generating model analysis...")
        
        # Analyze feature importance (for logistic regression)
        feature_analysis = self._analyze_features(pipeline)
        
        # Analyze prediction confidence
        confidence_analysis = self._analyze_prediction_confidence(test_results)
        
        # Compare test vs CV performance
        performance_comparison = self._compare_performance(test_results, cv_results)
        
        analysis_data = {
            'timestamp': datetime.now().isoformat(),
            'model_type': self.training_config['model']['type'],
            'feature_analysis': feature_analysis,
            'confidence_analysis': confidence_analysis,
            'performance_comparison': performance_comparison,
            'recommendations': self._generate_recommendations(test_results, cv_results)
        }
        
        analysis_path = results_path / "model_analysis.json"
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Model analysis saved to: {analysis_path}")
    
    def _analyze_features(self, pipeline):
        """Analyze feature importance for the model."""
        try:
            # Get the TF-IDF vectorizer and classifier
            vectorizer = pipeline.named_steps['tfidf']
            classifier = pipeline.named_steps['clf']
            
            # Get feature names
            feature_names = vectorizer.get_feature_names_out()
            
            # Get coefficients for each class
            coefficients = classifier.coef_
            classes = classifier.classes_
            
            # Find top features for each class
            top_features_per_class = {}
            
            for i, class_name in enumerate(classes):
                class_coef = coefficients[i]
                
                # Get top positive and negative features
                top_positive_idx = np.argsort(class_coef)[-10:][::-1]
                top_negative_idx = np.argsort(class_coef)[:10]
                
                top_features_per_class[class_name] = {
                    'top_positive': [
                        {
                            'feature': feature_names[idx],
                            'coefficient': float(class_coef[idx])
                        }
                        for idx in top_positive_idx
                    ],
                    'top_negative': [
                        {
                            'feature': feature_names[idx],
                            'coefficient': float(class_coef[idx])
                        }
                        for idx in top_negative_idx
                    ]
                }
            
            return {
                'total_features': len(feature_names),
                'top_features_per_class': top_features_per_class
            }
            
        except Exception as e:
            self.logger.warning(f"Could not analyze features: {e}")
            return {'error': str(e)}
    
    def _analyze_prediction_confidence(self, test_results):
        """Analyze prediction confidence patterns."""
        # This would typically require access to prediction probabilities
        # For now, return basic analysis based on available data
        
        class_metrics = test_results['class_metrics']
        
        # Find classes with low confidence (low precision/recall)
        low_confidence_classes = []
        high_confidence_classes = []
        
        for class_name, metrics in class_metrics.items():
            f1_score = metrics['f1_score']
            if f1_score < 0.5:
                low_confidence_classes.append({
                    'class': class_name,
                    'f1_score': f1_score,
                    'precision': metrics['precision'],
                    'recall': metrics['recall']
                })
            elif f1_score > 0.8:
                high_confidence_classes.append({
                    'class': class_name,
                    'f1_score': f1_score,
                    'precision': metrics['precision'],
                    'recall': metrics['recall']
                })
        
        return {
            'low_confidence_classes': low_confidence_classes,
            'high_confidence_classes': high_confidence_classes,
            'avg_f1_score': np.mean([m['f1_score'] for m in class_metrics.values()])
        }
    
    def _compare_performance(self, test_results, cv_results):
        """Compare test set performance with cross-validation results."""
        comparison = {}
        
        metrics = ['accuracy', 'macro_f1', 'weighted_f1', 'micro_f1']
        
        for metric in metrics:
            if metric in cv_results:
                test_score = test_results.get(metric, 0)
                cv_mean = cv_results[metric]['mean']
                cv_std = cv_results[metric]['std']
                
                # Check if test score is within 1 std of CV mean
                within_expected_range = abs(test_score - cv_mean) <= cv_std
                
                comparison[metric] = {
                    'test_score': test_score,
                    'cv_mean': cv_mean,
                    'cv_std': cv_std,
                    'difference': test_score - cv_mean,
                    'within_expected_range': within_expected_range
                }
        
        return comparison
    
    def _generate_recommendations(self, test_results, cv_results):
        """Generate recommendations based on evaluation results."""
        recommendations = []
        
        # Check overall performance
        accuracy = test_results.get('accuracy', 0)
        macro_f1 = test_results.get('macro_f1', 0)
        
        if accuracy < 0.7:
            recommendations.append({
                'type': 'performance',
                'issue': 'Low overall accuracy',
                'recommendation': 'Consider adding more training data or trying different algorithms'
            })
        
        if macro_f1 < 0.6:
            recommendations.append({
                'type': 'performance',
                'issue': 'Low macro F1 score indicates class imbalance issues',
                'recommendation': 'Enhance minority classes or adjust class weights'
            })
        
        # Check for overfitting/underfitting
        cv_accuracy = cv_results.get('accuracy', {}).get('mean', 0)
        if abs(accuracy - cv_accuracy) > 0.1:
            recommendations.append({
                'type': 'generalization',
                'issue': 'Large difference between test and CV performance',
                'recommendation': 'Check for overfitting or data leakage'
            })
        
        # Check class-specific issues
        class_metrics = test_results.get('class_metrics', {})
        problematic_classes = [
            cls for cls, metrics in class_metrics.items()
            if metrics['f1_score'] < 0.3
        ]
        
        if problematic_classes:
            recommendations.append({
                'type': 'class_specific',
                'issue': f'Poor performance on classes: {problematic_classes}',
                'recommendation': 'Add more training examples for these classes or review data quality'
            })
        
        return recommendations


def main():
    """Main function for standalone execution."""
    try:
        print("📊 RHCP Chatbot Model Evaluation")
        print("=" * 40)
        
        # This would typically load a trained model and test data
        print("⚠️  This script is typically called from the training pipeline")
        print("To run evaluation, use: python scripts/training/train_model.py")
        
    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 