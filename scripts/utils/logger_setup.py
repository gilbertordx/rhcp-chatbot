"""
Logger Setup Utility for RHCP Chatbot ML Pipeline.

Provides consistent logging configuration across all modules.
"""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str,
    log_file: str | None = None,
    level: str = "INFO",
    format_string: str | None = None,
    console: bool = True,
) -> logging.Logger:
    """
    Set up a logger with file and console handlers.

    Args:
        name: Name of the logger
        log_file: Path to log file (optional)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (optional)
        console: Whether to log to console

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    # Default format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def setup_training_logger(config: dict) -> logging.Logger:
    """
    Set up logger for training pipeline using configuration.

    Args:
        config: Configuration dictionary containing logging settings

    Returns:
        Configured logger for training
    """
    logging_config = config.get("logging", {})

    return setup_logger(
        name="training",
        log_file=logging_config.get("file"),
        level=logging_config.get("level", "INFO"),
        format_string=logging_config.get("format"),
        console=logging_config.get("console", True),
    )


def setup_data_logger(config: dict) -> logging.Logger:
    """
    Set up logger for data processing using configuration.

    Args:
        config: Configuration dictionary containing logging settings

    Returns:
        Configured logger for data processing
    """
    # Use logs path from config if available
    log_path = config.get("paths", {}).get("logs", "logs")
    log_file = f"{log_path}/data_processing.log"

    return setup_logger(
        name="data_processing", log_file=log_file, level="INFO", console=True
    )


def setup_evaluation_logger(config: dict) -> logging.Logger:
    """
    Set up logger for evaluation using configuration.

    Args:
        config: Configuration dictionary containing logging settings

    Returns:
        Configured logger for evaluation
    """
    # Use logs path from config if available
    log_path = config.get("paths", {}).get("logs", "logs")
    log_file = f"{log_path}/evaluation.log"

    return setup_logger(
        name="evaluation", log_file=log_file, level="INFO", console=True
    )


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)

    def setup_class_logger(self, log_file: str | None = None, level: str = "INFO"):
        """Set up logger for the class instance."""
        self.logger = setup_logger(
            name=self.__class__.__name__, log_file=log_file, level=level
        )
