# ============================
# WOLLOYEWA STORE BOT - LOGGING CONFIGURATION
# ============================
"""Structured logging setup with JSON formatting and context tracking."""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

import pythonjsonlogger.jsonlogger as jsonlogger
from pythonjsonlogger.jsonlogger import JsonFormatter

from core.config import settings

# Context variables for request/transaction tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[int]] = ContextVar("user_id", default=None)
telegram_id_var: ContextVar[Optional[int]] = ContextVar("telegram_id", default=None)
transaction_id_var: ContextVar[Optional[str]] = ContextVar("transaction_id", default=None)


class CustomJsonFormatter(JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(self, log_record: Dict, record: logging.LogRecord, message_dict: Dict) -> None:
        """Add custom fields to log records."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get("timestamp"):
            log_record["timestamp"] = datetime.utcnow().isoformat()
        
        # Add log level
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        
        # Add context variables
        request_id = request_id_var.get()
        if request_id:
            log_record["request_id"] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_record["user_id"] = user_id
        
        telegram_id = telegram_id_var.get()
        if telegram_id:
            log_record["telegram_id"] = telegram_id
        
        transaction_id = transaction_id_var.get()
        if transaction_id:
            log_record["transaction_id"] = transaction_id
        
        # Add environment
        log_record["environment"] = settings.ENVIRONMENT
        log_record["service"] = settings.PROJECT_NAME


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output in development."""
    
    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
        "RESET": "\033[0m",
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        log_message = super().format(record)
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        return f"{color}{log_message}{self.COLORS['RESET']}"


def setup_logging() -> None:
    """
    Configure logging for the entire application.
    
    Sets up different formatters based on environment (JSON for production,
    colored for development) and configures appropriate handlers.
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Choose formatter based on environment
    if settings.LOG_FORMAT == "json" and settings.ENVIRONMENT == "production":
        formatter = CustomJsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            json_ensure_ascii=False,
        )
    else:
        # Development: colored console output
        formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for errors (always enabled)
    if settings.LOG_FILE_PATH:
        try:
            file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
            file_handler.setLevel(logging.ERROR)
            file_formatter = CustomJsonFormatter(
                fmt="%(timestamp)s %(level)s %(name)s %(message)s",
                json_ensure_ascii=False,
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"Could not create log file handler: {e}")
    
    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    
    root_logger.info(f"Logging initialized | Level: {settings.LOG_LEVEL} | Format: {settings.LOG_FORMAT}")


class LoggerContext:
    """Context manager for setting logging context variables."""
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None,
        telegram_id: Optional[int] = None,
        transaction_id: Optional[str] = None,
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.telegram_id = telegram_id
        self.transaction_id = transaction_id
        self.reset_tokens = []
    
    def __enter__(self):
        """Set context variables."""
        if self.request_id:
            self.reset_tokens.append((request_id_var, request_id_var.set(self.request_id)))
        if self.user_id:
            self.reset_tokens.append((user_id_var, user_id_var.set(self.user_id)))
        if self.telegram_id:
            self.reset_tokens.append((telegram_id_var, telegram_id_var.set(self.telegram_id)))
        if self.transaction_id:
            self.reset_tokens.append((transaction_id_var, transaction_id_var.set(self.transaction_id)))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Reset context variables."""
        for var, token in self.reset_tokens:
            var.reset(token)
        self.reset_tokens.clear()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Create module logger
logger = get_logger(__name__)


# Convenience functions for context logging
def log_with_context(
    logger_obj: logging.Logger,
    level: str,
    message: str,
    **kwargs,
) -> None:
    """
    Log a message with additional context.
    
    Args:
        logger_obj: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **kwargs: Additional context to include
    """
    log_func = getattr(logger_obj, level.lower())
    if kwargs:
        message = f"{message} | {kwargs}"
    log_func(message)


__all__ = [
    "setup_logging",
    "get_logger",
    "LoggerContext",
    "logger",
    "request_id_var",
    "user_id_var",
    "telegram_id_var",
    "transaction_id_var",
    "log_with_context",
]