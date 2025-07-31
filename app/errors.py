"""
RHCP Chatbot Error Types

Typed exceptions for consistent error handling across API and CLI.
"""

from typing import Optional, Dict, Any


class RHCPError(Exception):
    """Base exception for all RHCP chatbot errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigError(RHCPError):
    """Configuration-related errors."""
    pass


class InvalidInputError(RHCPError):
    """Input validation errors."""
    pass


class ProcessingError(RHCPError):
    """Message processing errors."""
    pass


class AuthenticationError(RHCPError):
    """Authentication and authorization errors."""
    pass


class DatabaseError(RHCPError):
    """Database operation errors."""
    pass


class ModelError(RHCPError):
    """ML model loading or inference errors."""
    pass 