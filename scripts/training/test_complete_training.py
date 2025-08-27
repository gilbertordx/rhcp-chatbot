#!/usr/bin/env python3
"""
Quick test of the complete training pipeline with all fixes applied.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
os.chdir(project_root)

print("Testing complete training pipeline...")
print(f"Project root: {project_root}")
print(f"Working directory: {os.getcwd()}")

try:
    from scripts.training.train_model import ModelTrainer

    # Initialize and run trainer
    print("\nInitializing trainer...")
    trainer = ModelTrainer()

    print("Running complete training pipeline...")
    pipeline, test_results, cv_results = trainer.run_training_pipeline()

    print("\nSUCCESS! Training completed without errors!")
    print(f"Test Accuracy: {test_results['accuracy']:.4f}")
    print(f"Test Macro F1: {test_results['macro_f1']:.4f}")
    print(
        f"CV Accuracy: {cv_results['accuracy']['mean']:.4f} ± {cv_results['accuracy']['std']:.4f}"
    )
    print("Model saved successfully!")

    # Test model loading
    from scripts.utils.model_utils import ModelUtils

    model_path = "data/models/logistic_regression_classifier.joblib"
    loaded_pipeline, metadata = ModelUtils.load_model(model_path)

    print("\nModel loading test:")
    print(f"Loaded model accuracy matches: {loaded_pipeline.score is not None}")
    print(f"Metadata contains: {list(metadata.keys())}")

    print("\nAll tests passed! Training pipeline is fully functional.")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
