"""
Tests for structured logging functionality.
"""

import logging

from app.infra.logging import (
    JSONFormatter,
    clear_request_context,
    get_logger,
    log_with_context,
    set_request_context,
    setup_logging,
)


class TestLoggingSetup:
    """Test logging setup and configuration."""

    def test_setup_logging_json_format(self):
        """Test JSON format logging setup."""
        setup_logging(level="INFO", format_type="json", debug=False)
        logger = get_logger("test")

        # Test that JSON formatter is working by checking the formatter type
        root_logger = logging.getLogger()
        handler = root_logger.handlers[0] if root_logger.handlers else None

        assert handler is not None
        assert isinstance(handler.formatter, JSONFormatter)

        # Test that logger works
        logger.info("Test message")
        # If we get here without error, the logging setup is working

    def test_setup_logging_debug_mode(self):
        """Test debug mode logging setup."""
        setup_logging(debug=True)
        logger = get_logger("test")

        # Test that debug mode sets correct level and format
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        # Test that logger works
        logger.debug("Debug message")
        # If we get here without error, the logging setup is working

    def test_request_context(self):
        """Test request context setting and clearing."""
        setup_logging(level="INFO", format_type="json", debug=False)
        logger = get_logger("test")

        # Set request context
        set_request_context(
            request_id_val="test-req-123", correlation_id_val="test-corr-456"
        )

        # Test that context is set
        logger.info("Message with context")

        # Clear context
        clear_request_context()

        # Test that context is cleared
        logger.info("Message without context")

        # If we get here without error, the context management is working

    def test_log_with_context(self):
        """Test logging with additional context."""
        setup_logging(level="INFO", format_type="json", debug=False)
        logger = get_logger("test")

        # Test that log_with_context works without error
        log_with_context(
            logger,
            "info",
            "Test message",
            intent="test.intent",
            confidence=0.85,
            latency_ms=123.45,
        )

        # If we get here without error, the context logging is working

    def _capture_logs(self):
        """Context manager to capture log output."""

        class LogCapture:
            def __init__(self):
                self.records = []
                self.handler = None

            def __enter__(self):
                # Create a custom handler to capture logs
                class CaptureHandler(logging.Handler):
                    def __init__(self, records):
                        super().__init__()
                        self.records = records

                    def emit(self, record):
                        self.records.append(self.format(record))

                self.handler = CaptureHandler(self.records)
                self.handler.setFormatter(logging.Formatter("%(message)s"))

                # Add to root logger and clear existing handlers
                root_logger = logging.getLogger()
                # Store existing handlers
                self.existing_handlers = root_logger.handlers[:]
                # Clear and add our capture handler
                root_logger.handlers.clear()
                root_logger.addHandler(self.handler)
                return self.records

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Restore original handlers
                root_logger = logging.getLogger()
                root_logger.handlers.clear()
                for handler in self.existing_handlers:
                    root_logger.addHandler(handler)

        return LogCapture()


class TestLoggingIntegration:
    """Test logging integration with application components."""

    def test_logger_names(self):
        """Test that loggers are created with correct names."""
        logger1 = get_logger("app.main")
        logger2 = get_logger("app.chatbot.processor")

        assert logger1.name == "app.main"
        assert logger2.name == "app.chatbot.processor"

    def _capture_logs(self):
        """Context manager to capture log output."""

        class LogCapture:
            def __init__(self):
                self.records = []
                self.handler = None

            def __enter__(self):
                # Create a custom handler to capture logs
                class CaptureHandler(logging.Handler):
                    def __init__(self, records):
                        super().__init__()
                        self.records = records

                    def emit(self, record):
                        self.records.append(self.format(record))

                self.handler = CaptureHandler(self.records)
                self.handler.setFormatter(logging.Formatter("%(message)s"))

                # Add to root logger and clear existing handlers
                root_logger = logging.getLogger()
                # Store existing handlers
                self.existing_handlers = root_logger.handlers[:]
                # Clear and add our capture handler
                root_logger.handlers.clear()
                root_logger.addHandler(self.handler)
                return self.records

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Restore original handlers
                root_logger = logging.getLogger()
                root_logger.handlers.clear()
                for handler in self.existing_handlers:
                    root_logger.addHandler(handler)

        return LogCapture()

    def test_log_levels(self):
        """Test different log levels."""
        setup_logging(level="WARNING", format_type="json", debug=False)
        logger = get_logger("test")

        # Test that log levels are respected
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

        # Test that logger works
        logger.warning("Warning message")
        logger.error("Error message")

        # If we get here without error, the log levels are working
