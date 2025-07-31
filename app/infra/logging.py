"""
Structured logging for RHCP chatbot.

Provides JSON formatter, correlation IDs, and debug mode support.
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional
from datetime import datetime

# Context variables for request tracking
request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'msg': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add request tracking if available
        if request_id.get():
            log_entry['request_id'] = request_id.get()
        if correlation_id.get():
            log_entry['correlation_id'] = correlation_id.get()
            
        # Add intent and confidence for chatbot-specific logs
        if hasattr(record, 'intent'):
            log_entry['intent'] = record.intent
        if hasattr(record, 'confidence'):
            log_entry['confidence'] = record.confidence
        if hasattr(record, 'latency_ms'):
            log_entry['latency_ms'] = record.latency_ms
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for debug mode."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human reading."""
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # Base format
        fmt = f"[{timestamp}] {record.levelname:8} {record.module}:{record.lineno} - {record.getMessage()}"
        
        # Add request tracking if available
        req_id = request_id.get()
        if req_id:
            fmt += f" [req:{req_id[:8]}]"
        corr_id = correlation_id.get()
        if corr_id:
            fmt += f" [corr:{corr_id[:8]}]"
            
        # Add intent/confidence for chatbot logs
        if hasattr(record, 'intent'):
            fmt += f" [intent:{record.intent}]"
        if hasattr(record, 'confidence'):
            fmt += f" [conf:{record.confidence:.3f}]"
        if hasattr(record, 'latency_ms'):
            fmt += f" [latency:{record.latency_ms}ms]"
            
        return fmt


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    debug: bool = False
) -> None:
    """Setup logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format ("json" or "human")
        debug: Enable debug mode (overrides level to DEBUG, format to human)
    """
    if debug:
        level = "DEBUG"
        format_type = "human"
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler()
    
    # Set formatter
    if format_type == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(HumanFormatter())
    logger.addHandler(handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


def set_request_context(request_id_val: Optional[str] = None, correlation_id_val: Optional[str] = None) -> None:
    """Set request context for logging."""
    if request_id_val:
        request_id.set(request_id_val)
    if correlation_id_val:
        correlation_id.set(correlation_id_val)


def clear_request_context() -> None:
    """Clear request context."""
    request_id.set(None)
    correlation_id.set(None)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    intent: Optional[str] = None,
    confidence: Optional[float] = None,
    latency_ms: Optional[float] = None,
    **kwargs: Any
) -> None:
    """Log message with additional context."""
    extra: Dict[str, Any] = {}
    if intent:
        extra['intent'] = intent
    if confidence is not None:
        extra['confidence'] = confidence
    if latency_ms is not None:
        extra['latency_ms'] = latency_ms
    extra.update(kwargs)
    
    log_method = getattr(logger, level.lower())
    log_method(message, extra=extra) 