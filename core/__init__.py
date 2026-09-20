# ============================
# WOLLOYEWA STORE BOT - CORE MODULE
# ============================
"""Core module containing configuration, security, monitoring, and utilities."""

from core.config import settings
from core.exceptions import (
    DatabaseError,
    NotFoundError,
    PaymentError,
    PermissionError,
    RateLimitError,
    ValidationError,
    WolloyewaException,
)
from core.logger import logger, setup_logging
from core.security import (
    create_access_token,
    decrypt_data,
    encrypt_data,
    hash_password,
    verify_password,
    verify_token,
)

__all__ = [
    "DatabaseError",
    "NotFoundError",
    "PaymentError",
    "PermissionError",
    "RateLimitError",
    "ValidationError",
    # Exceptions
    "WolloyewaException",
    "create_access_token",
    "decrypt_data",
    "encrypt_data",
    # Security
    "hash_password",
    # Logging
    "logger",
    # Config
    "settings",
    "setup_logging",
    "verify_password",
    "verify_token",
]

__version__ = "1.0.0"
__author__ = "Wolloyewa Team"
__description__ = "Core functionality for Wolloyewa Store Bot"
