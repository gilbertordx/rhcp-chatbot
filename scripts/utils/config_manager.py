"""
Configuration Manager for RHCP Chatbot ML Pipeline.

Handles loading and validation of YAML configuration files.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, Dict[str, Any]] = {}
        
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """
        Load a configuration file.
        
        Args:
            config_name: Name of the config file (without .yaml extension)
            
        Returns:
            Dictionary containing configuration data
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is malformed
        """
        if config_name in self._configs:
            return self._configs[config_name]
            
        config_path = self.config_dir / f"{config_name}.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            self._configs[config_name] = config_data
            return config_data
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing config file {config_path}: {e}")
    
    def get_training_config(self) -> Dict[str, Any]:
        """Load training configuration."""
        return self.load_config("training_config")
    
    def get_data_config(self) -> Dict[str, Any]:
        """Load data configuration."""
        return self.load_config("data_config")
    
    def get_nested_value(self, config_name: str, key_path: str, default: Any = None) -> Any:
        """
        Get a nested configuration value using dot notation.
        
        Args:
            config_name: Name of the configuration
            key_path: Dot-separated path to the value (e.g., "model.classifier.random_state")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        config = self.load_config(config_name)
        
        keys = key_path.split('.')
        value = config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def validate_config(self, config_name: str) -> bool:
        """
        Validate configuration structure and required fields.
        
        Args:
            config_name: Name of the configuration to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        config = self.load_config(config_name)
        
        if config_name == "training_config":
            return self._validate_training_config(config)
        elif config_name == "data_config":
            return self._validate_data_config(config)
        else:
            # Basic validation for unknown config types
            return isinstance(config, dict) and len(config) > 0
    
    def _validate_training_config(self, config: Dict[str, Any]) -> bool:
        """Validate training configuration structure."""
        required_sections = ["data", "model", "training", "evaluation"]
        
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required section in training config: {section}")
        
        # Validate data section
        if "training_files" not in config["data"]:
            raise ValueError("Missing 'training_files' in data configuration")
        
        # Validate model section
        if "type" not in config["model"]:
            raise ValueError("Missing 'type' in model configuration")
        
        return True
    
    def _validate_data_config(self, config: Dict[str, Any]) -> bool:
        """Validate data configuration structure."""
        required_sections = ["paths", "processed_data", "validation"]
        
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required section in data config: {section}")
        
        return True
    
    def create_directories(self, config_name: str) -> None:
        """
        Create directories specified in configuration.
        
        Args:
            config_name: Name of the configuration
        """
        config = self.load_config(config_name)
        
        # Create directories from paths section
        if "paths" in config:
            for path_name, path_value in config["paths"].items():
                Path(path_value).mkdir(parents=True, exist_ok=True)
        
        # Create data directories from data section
        if "data" in config:
            for key, value in config["data"].items():
                if key.endswith("_path") and isinstance(value, str):
                    Path(value).mkdir(parents=True, exist_ok=True)
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded configurations."""
        return self._configs.copy()
    
    def reload_config(self, config_name: str) -> Dict[str, Any]:
        """
        Reload a configuration file from disk.
        
        Args:
            config_name: Name of the config to reload
            
        Returns:
            Reloaded configuration data
        """
        if config_name in self._configs:
            del self._configs[config_name]
        
        return self.load_config(config_name) 