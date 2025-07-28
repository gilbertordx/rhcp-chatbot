#!/usr/bin/env python3
"""
Data Validation Script for RHCP Chatbot ML Pipeline.

Validates training data against configuration rules and quality standards.
"""

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.utils.config_manager import ConfigManager
from scripts.utils.logger_setup import setup_data_logger
from scripts.utils.data_utils import DataUtils


class DataValidator:
    """Validates training data quality and structure."""
    
    def __init__(self, config_manager: ConfigManager = None):
        """Initialize the data validator."""
        self.config_manager = config_manager or ConfigManager()
        self.data_config = self.config_manager.get_data_config()
        self.logger = setup_data_logger(self.data_config)
    
    def validate_corpus_files(self) -> bool:
        """
        Validate all corpus files against configuration rules.
        
        Returns:
            True if all files are valid
        """
        self.logger.info("Starting corpus file validation...")
        
        training_config = self.config_manager.get_training_config()
        training_files = training_config['data']['training_files']
        
        all_valid = True
        
        for file_path in training_files:
            self.logger.info(f"Validating file: {file_path}")
            
            try:
                # Load corpus data
                corpus_data = DataUtils.load_json_file(file_path)
                
                # Validate against rules
                errors = DataUtils.validate_corpus(corpus_data, self.data_config)
                
                if errors:
                    self.logger.error(f"Validation errors in {file_path}:")
                    for error in errors:
                        self.logger.error(f"  - {error}")
                    all_valid = False
                else:
                    self.logger.info(f"✅ {file_path} passed validation")
                    
            except Exception as e:
                self.logger.error(f"Error validating {file_path}: {e}")
                all_valid = False
        
        if all_valid:
            self.logger.info("✅ All corpus files passed validation")
        else:
            self.logger.error("❌ Some corpus files failed validation")
        
        return all_valid


def main():
    """Main function for standalone execution."""
    try:
        print("🔍 RHCP Chatbot Data Validation")
        print("=" * 40)
        
        # Initialize validator
        validator = DataValidator()
        
        # Validate corpus files
        is_valid = validator.validate_corpus_files()
        
        if is_valid:
            print("\n✅ All data validation checks passed!")
        else:
            print("\n❌ Data validation failed!")
            print("Check logs for detailed error information.")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 