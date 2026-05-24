# ============================
# WOLLOYEWA STORE BOT - CORE MODULE
# ============================
"""Core module containing configuration, security, monitoring, and utilities."""

from core.config import settings
from core.logger import logger, setup_logging
from core.exceptions import (
    WolloyewaException,
    DatabaseError,
    ValidationError,
    NotFoundError,
    PermissionError,
    PaymentError,
    RateLimitError,
)
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    encrypt_data,
    decrypt_data,
)

__all__ = [
    # Config
    "settings",
    # Logging
    "logger",
    "setup_logging",
    # Exceptions
    "WolloyewaException",
    "DatabaseError",
    "ValidationError",
    "NotFoundError",
    "PermissionError",
    "PaymentError",
    "RateLimitError",
    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "verify_token",
    "encrypt_data",
    "decrypt_data",
]

__version__ = "1.0.0"
__author__ = "Wolloyewa Team"
__description__ = "Core functionality for Wolloyewa Store Bot"