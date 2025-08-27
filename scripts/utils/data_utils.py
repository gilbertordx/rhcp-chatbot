"""
Data Utilities for RHCP Chatbot ML Pipeline.

Provides functions for loading, processing, and validating training data.
"""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


class DataUtils:
    """Utility class for data operations."""

    @staticmethod
    def load_json_file(file_path: str) -> dict[str, Any]:
        """
        Load a JSON file safely.

        Args:
            file_path: Path to the JSON file

        Returns:
            Dictionary containing JSON data

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is malformed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Error parsing JSON file {file_path}: {e}")

    @staticmethod
    def save_json_file(
        data: dict[str, Any], file_path: str, create_backup: bool = True
    ) -> None:
        """
        Save data to a JSON file safely.

        Args:
            data: Data to save
            file_path: Path to save the file
            create_backup: Whether to create a backup if file exists
        """
        file_path = Path(file_path)

        # Create backup if file exists and backup is requested
        if file_path.exists() and create_backup:
            backup_path = file_path.with_suffix(
                f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            shutil.copy2(file_path, backup_path)

        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_corpus(training_files: list[str]) -> tuple[list[str], list[str]]:
        """
        Load training corpus from multiple files.

        Args:
            training_files: List of paths to training files

        Returns:
            Tuple of (texts, intents)
        """
        texts = []
        intents = []

        for file_path in training_files:
            corpus = DataUtils.load_json_file(file_path)

            for item in corpus.get("data", []):
                if item.get("intent") and item.get("intent") != "None":
                    for utterance in item.get("utterances", []):
                        if utterance and utterance.strip():  # Skip empty utterances
                            texts.append(utterance.strip())
                            intents.append(item["intent"])

        return texts, intents

    @staticmethod
    def create_dataframe(texts: list[str], intents: list[str]) -> pd.DataFrame:
        """
        Create a pandas DataFrame from texts and intents.

        Args:
            texts: List of text utterances
            intents: List of corresponding intents

        Returns:
            DataFrame with 'text' and 'intent' columns
        """
        return pd.DataFrame({"text": texts, "intent": intents})

    @staticmethod
    def validate_corpus(
        corpus_data: dict[str, Any], config: dict[str, Any]
    ) -> list[str]:
        """
        Validate corpus data against configuration rules.

        Args:
            corpus_data: Corpus data to validate
            config: Validation configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        validation_rules = config.get("validation", {})

        # Check required fields
        required_fields = validation_rules.get("required_fields", [])
        if "data" not in corpus_data:
            errors.append("Missing 'data' field in corpus")
            return errors

        for idx, item in enumerate(corpus_data["data"]):
            for field in required_fields:
                if field not in item:
                    errors.append(f"Item {idx}: Missing required field '{field}'")

            # Validate intent naming
            intent = item.get("intent", "")
            intent_pattern = validation_rules.get("intent_naming", {}).get(
                "pattern", ""
            )
            if intent_pattern:
                import re

                if not re.match(intent_pattern, intent):
                    errors.append(
                        f"Item {idx}: Intent '{intent}' doesn't match pattern {intent_pattern}"
                    )

            # Validate utterances
            utterances = item.get("utterances", [])
            utterance_rules = validation_rules.get("utterance_rules", {})

            min_length = utterance_rules.get("min_length", 0)
            max_length = utterance_rules.get("max_length", 1000)
            min_per_intent = utterance_rules.get("min_per_intent", 1)
            max_per_intent = utterance_rules.get("max_per_intent", 1000)

            if len(utterances) < min_per_intent:
                errors.append(
                    f"Item {idx}: Too few utterances ({len(utterances)} < {min_per_intent})"
                )

            if len(utterances) > max_per_intent:
                errors.append(
                    f"Item {idx}: Too many utterances ({len(utterances)} > {max_per_intent})"
                )

            for u_idx, utterance in enumerate(utterances):
                if not isinstance(utterance, str):
                    errors.append(f"Item {idx}, utterance {u_idx}: Not a string")
                    continue

                if len(utterance.strip()) < min_length:
                    errors.append(
                        f"Item {idx}, utterance {u_idx}: Too short ({len(utterance)} < {min_length})"
                    )

                if len(utterance) > max_length:
                    errors.append(
                        f"Item {idx}, utterance {u_idx}: Too long ({len(utterance)} > {max_length})"
                    )

        return errors

    @staticmethod
    def analyze_class_balance(df: pd.DataFrame) -> dict[str, Any]:
        """
        Analyze class balance in the dataset.

        Args:
            df: DataFrame with 'intent' column

        Returns:
            Dictionary with balance analysis
        """
        class_counts = df["intent"].value_counts()
        total_samples = len(df)

        analysis = {
            "total_samples": total_samples,
            "unique_classes": len(class_counts),
            "class_counts": class_counts.to_dict(),
            "class_percentages": (class_counts / total_samples * 100).to_dict(),
            "most_common_class": class_counts.index[0],
            "least_common_class": class_counts.index[-1],
            "max_samples": class_counts.iloc[0],
            "min_samples": class_counts.iloc[-1],
            "imbalance_ratio": class_counts.iloc[0] / class_counts.iloc[-1],
            "median_samples": class_counts.median(),
            "mean_samples": class_counts.mean(),
            "std_samples": class_counts.std(),
        }

        return analysis

    @staticmethod
    def find_minority_classes(
        df: pd.DataFrame,
        threshold_percentage: float = 2.0,
        threshold_absolute: int = 10,
    ) -> list[str]:
        """
        Find minority classes based on thresholds.

        Args:
            df: DataFrame with 'intent' column
            threshold_percentage: Minimum percentage of total samples
            threshold_absolute: Minimum absolute number of samples

        Returns:
            List of minority class names
        """
        class_counts = df["intent"].value_counts()
        total_samples = len(df)

        min_samples = max(
            threshold_absolute, total_samples * threshold_percentage / 100
        )

        minority_classes = class_counts[class_counts < min_samples].index.tolist()
        return minority_classes

    @staticmethod
    def create_backup(file_paths: list[str], backup_dir: str | None = None) -> str:
        """
        Create backup copies of files.

        Args:
            file_paths: List of file paths to backup
            backup_dir: Directory to store backups (auto-generated if None)

        Returns:
            Path to backup directory
        """
        if backup_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"data/backups/backup_{timestamp}"

        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)

        for file_path in file_paths:
            source_path = Path(file_path)
            if source_path.exists():
                dest_path = backup_path / source_path.name
                shutil.copy2(source_path, dest_path)

        return str(backup_path)

    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = "md5") -> str:
        """
        Calculate hash of a file for integrity checking.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm (md5, sha256, etc.)

        Returns:
            Hex digest of the file hash
        """
        hash_obj = hashlib.new(algorithm)

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    @staticmethod
    def check_data_integrity(
        file_paths: list[str], expected_hashes: dict[str, str]
    ) -> bool:
        """
        Check data integrity using file hashes.

        Args:
            file_paths: List of file paths to check
            expected_hashes: Dictionary mapping file names to expected hashes

        Returns:
            True if all files match expected hashes
        """
        for file_path in file_paths:
            file_name = Path(file_path).name
            if file_name in expected_hashes:
                current_hash = DataUtils.calculate_file_hash(file_path)
                if current_hash != expected_hashes[file_name]:
                    return False

        return True

    @staticmethod
    def clean_text(text: str, config: dict[str, Any]) -> str:
        """
        Clean and normalize text according to configuration.

        Args:
            text: Text to clean
            config: Configuration with normalization settings

        Returns:
            Cleaned text
        """
        normalization_config = config.get("processing", {}).get("normalization", {})

        if normalization_config.get("lowercase", True):
            text = text.lower()

        if normalization_config.get("strip_whitespace", True):
            text = text.strip()

        if normalization_config.get("remove_extra_spaces", True):
            import re

            text = re.sub(r"\s+", " ", text)

        return text
