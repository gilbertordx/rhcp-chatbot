#!/usr/bin/env python3
"""
Data Loading Script for RHCP Chatbot ML Pipeline.

Handles loading and initial processing of training data from JSON corpus files.
"""

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

from scripts.utils.config_manager import ConfigManager
from scripts.utils.data_utils import DataUtils
from scripts.utils.logger_setup import setup_data_logger


class DataLoader:
    """Handles loading and initial processing of training data."""

    def __init__(self, config_manager: ConfigManager = None):
        """Initialize the data loader."""
        self.config_manager = config_manager or ConfigManager()
        self.data_config = self.config_manager.get_data_config()
        self.training_config = self.config_manager.get_training_config()
        self.logger = setup_data_logger(self.data_config)

        # Create necessary directories
        self.config_manager.create_directories("data_config")

    def load_training_data(self) -> pd.DataFrame:
        """
        Load training data from configured corpus files.

        Returns:
            DataFrame containing text and intent columns
        """
        self.logger.info("Starting data loading process...")

        # Get training files from configuration
        training_files = self.training_config["data"]["training_files"]
        self.logger.info(
            f"Loading data from {len(training_files)} files: {training_files}"
        )

        # Load corpus data
        texts, intents = DataUtils.load_corpus(training_files)

        # Create DataFrame
        df = DataUtils.create_dataframe(texts, intents)

        self.logger.info(
            f"Loaded {len(df)} samples with {df['intent'].nunique()} unique intents"
        )

        # Analyze class balance
        balance_analysis = DataUtils.analyze_class_balance(df)
        self.logger.info("Class balance analysis:")
        self.logger.info(
            f"  Most common class: {balance_analysis['most_common_class']} ({balance_analysis['max_samples']} samples)"
        )
        self.logger.info(
            f"  Least common class: {balance_analysis['least_common_class']} ({balance_analysis['min_samples']} samples)"
        )
        self.logger.info(
            f"  Imbalance ratio: {balance_analysis['imbalance_ratio']:.2f}:1"
        )

        return df

    def load_raw_data(self) -> dict:
        """
        Load raw data files (band info, discography).

        Returns:
            Dictionary containing raw data
        """
        self.logger.info("Loading raw data files...")

        raw_data = {}
        raw_data_config = self.data_config["raw_data"]

        for data_type, file_path in raw_data_config.items():
            try:
                data = DataUtils.load_json_file(file_path)
                raw_data[data_type] = data
                self.logger.info(f"Loaded {data_type} from {file_path}")
            except FileNotFoundError:
                self.logger.warning(f"Raw data file not found: {file_path}")
                raw_data[data_type] = None

        return raw_data

    def get_data_summary(self, df: pd.DataFrame) -> dict:
        """
        Get a comprehensive summary of the loaded data.

        Args:
            df: DataFrame containing the data

        Returns:
            Dictionary containing data summary
        """
        summary = {
            "total_samples": len(df),
            "unique_intents": df["intent"].nunique(),
            "intent_distribution": df["intent"].value_counts().to_dict(),
            "sample_texts": df["text"].head(10).tolist(),
            "intent_examples": {},
        }

        # Add examples for each intent
        for intent in df["intent"].unique()[:10]:  # Limit to first 10 intents
            examples = df[df["intent"] == intent]["text"].head(3).tolist()
            summary["intent_examples"][intent] = examples

        return summary

    def create_data_backup(self) -> str:
        """
        Create backup of current training data.

        Returns:
            Path to backup directory
        """
        self.logger.info("Creating data backup...")

        training_files = self.training_config["data"]["training_files"]
        backup_dir = DataUtils.create_backup(training_files)

        self.logger.info(f"Backup created at: {backup_dir}")
        return backup_dir


def main():
    """Main function for standalone execution."""
    try:
        # Initialize data loader
        loader = DataLoader()

        # Load training data
        df = loader.load_training_data()

        # Get data summary
        summary = loader.get_data_summary(df)

        # Print summary
        print("\n=== DATA LOADING SUMMARY ===")
        print(f"Total samples: {summary['total_samples']}")
        print(f"Unique intents: {summary['unique_intents']}")
        print("\nTop 10 intents by frequency:")
        for intent, count in list(summary["intent_distribution"].items())[:10]:
            print(f"  {intent}: {count} samples")

        print("\nSample texts:")
        for i, text in enumerate(summary["sample_texts"][:5], 1):
            print(f"  {i}. {text}")

        # Create backup
        backup_dir = loader.create_data_backup()
        print(f"\nBackup created: {backup_dir}")

        print("\nData loading completed successfully!")

    except Exception as e:
        print(f"Error during data loading: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
