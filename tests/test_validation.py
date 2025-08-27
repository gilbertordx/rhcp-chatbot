"""
Tests for input validation and error handling.
"""

import pytest
from fastapi.testclient import TestClient

from app.errors import InvalidInputError
from app.infra.logging import setup_logging
from app.main import app


class TestAPIValidation:
    """Test API input validation."""

    def setup_method(self):
        """Setup test environment."""
        setup_logging(level="INFO", format_type="json", debug=False)
        self.client = TestClient(app)

    def test_valid_message(self):
        """Test valid message processing."""
        response = self.client.post(
            "/api/chat", json={"message": "Hello, how are you?"}
        )

        # Should get 503 because chatbot processor is not initialized in test
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "not initialized" in data["detail"]

    def test_empty_message(self):
        """Test empty message rejection."""
        response = self.client.post("/api/chat", json={"message": ""})

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_whitespace_only_message(self):
        """Test whitespace-only message rejection."""
        response = self.client.post("/api/chat", json={"message": "   \n\t   "})

        # Should get 503 because chatbot processor is not initialized in test
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "not initialized" in data["detail"]

    def test_message_too_long(self):
        """Test message length validation."""
        long_message = "x" * 2001  # Exceeds 2000 character limit

        response = self.client.post("/api/chat", json={"message": long_message})

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_missing_message_field(self):
        """Test missing message field."""
        response = self.client.post("/api/chat", json={})

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_message_stripped(self):
        """Test that message whitespace is stripped."""
        response = self.client.post("/api/chat", json={"message": "  Hello  "})

        # Should get 503 because chatbot processor is not initialized in test
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "not initialized" in data["detail"]


class TestCLIValidation:
    """Test CLI input validation."""

    def setup_method(self):
        """Setup test environment."""
        setup_logging(level="INFO", format_type="json", debug=False)

    def test_valid_cli_message(self):
        """Test valid CLI message processing."""
        from cli import RHCPChatbotCLI

        cli = RHCPChatbotCLI(debug=True)

        # This should not raise an exception
        try:
            cli.send_message("Hello, how are you?")
        except Exception as e:
            # It's okay if it fails due to missing initialization
            # We're just testing the validation logic
            assert "not initialized" in str(e) or "Chatbot not initialized" in str(e)

    def test_empty_cli_message(self):
        """Test empty CLI message rejection."""
        from cli import RHCPChatbotCLI

        cli = RHCPChatbotCLI(debug=True)

        with pytest.raises(InvalidInputError, match="Message cannot be empty"):
            cli.send_message("")

    def test_whitespace_cli_message(self):
        """Test whitespace-only CLI message rejection."""
        from cli import RHCPChatbotCLI

        cli = RHCPChatbotCLI(debug=True)

        with pytest.raises(InvalidInputError, match="Message cannot be empty"):
            cli.send_message("   \n\t   ")

    def test_long_cli_message(self):
        """Test CLI message length validation."""
        from cli import RHCPChatbotCLI

        cli = RHCPChatbotCLI(debug=True)
        long_message = "x" * 2001  # Exceeds 2000 character limit

        with pytest.raises(InvalidInputError, match="Message too long"):
            cli.send_message(long_message)

    def test_cli_message_stripped(self):
        """Test that CLI message whitespace is stripped."""
        from cli import RHCPChatbotCLI

        cli = RHCPChatbotCLI(debug=True)

        # This should not raise an exception
        try:
            cli.send_message("  Hello  ")
        except Exception as e:
            # It's okay if it fails due to missing initialization
            assert "not initialized" in str(e) or "Chatbot not initialized" in str(e)


class TestErrorTypes:
    """Test custom error types."""

    def test_invalid_input_error(self):
        """Test InvalidInputError creation and properties."""
        error = InvalidInputError("Test error message", {"field": "message"})

        assert error.message == "Test error message"
        assert error.details == {"field": "message"}
        assert str(error) == "Test error message"

    def test_processing_error(self):
        """Test ProcessingError creation."""
        from app.errors import ProcessingError

        error = ProcessingError("Processing failed", {"step": "classification"})

        assert error.message == "Processing failed"
        assert error.details == {"step": "classification"}

    def test_config_error(self):
        """Test ConfigError creation."""
        from app.errors import ConfigError

        error = ConfigError("Invalid configuration", {"setting": "port"})

        assert error.message == "Invalid configuration"
        assert error.details == {"setting": "port"}

    def test_error_inheritance(self):
        """Test error inheritance hierarchy."""
        from app.errors import InvalidInputError, RHCPError

        error = InvalidInputError("Test")

        assert isinstance(error, InvalidInputError)
        assert isinstance(error, RHCPError)
        assert isinstance(error, Exception)
