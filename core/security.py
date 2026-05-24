# ============================
# WOLLOYEWA STORE BOT - SECURITY
# ============================
"""Security utilities for authentication, encryption, and password handling."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet
from passlib.context import CryptContext
from jose import jwt, JWTError

from core.config import settings
from core.logger import logger

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": settings.PROJECT_NAME,
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string to verify
        
    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.PROJECT_NAME,
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


def generate_otp(length: int = 6) -> str:
    """
    Generate a one-time password (OTP).
    
    Args:
        length: Length of OTP (default 6)
        
    Returns:
        OTP string
    """
    return ''.join(str(secrets.randbelow(10)) for _ in range(length))


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: Token length in bytes
        
    Returns:
        URL-safe base64 encoded token
    """
    return secrets.token_urlsafe(length)


def get_encryption_key() -> bytes:
    """
    Get or generate encryption key for Fernet.
    
    Returns:
        Fernet encryption key
    """
    if settings.ENCRYPTION_KEY:
        return settings.ENCRYPTION_KEY.encode()
    
    # Generate a new key (should be saved to settings in production)
    key = Fernet.generate_key()
    logger.warning("Using temporary encryption key. Set ENCRYPTION_KEY in production!")
    return key


def encrypt_data(data: str) -> str:
    """
    Encrypt sensitive data using Fernet.
    
    Args:
        data: String data to encrypt
        
    Returns:
        Encrypted data as base64 string
    """
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(data.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise ValueError(f"Failed to encrypt data: {e}")


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt previously encrypted data.
    
    Args:
        encrypted_data: Encrypted data string
        
    Returns:
        Decrypted original data
    """
    try:
        key = get_encryption_key()
        f = Fernet(key)
        decrypted = f.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError(f"Failed to decrypt data: {e}")


def hash_telegram_id(telegram_id: int) -> str:
    """
    Hash a Telegram ID for privacy.
    
    Args:
        telegram_id: User's Telegram ID
        
    Returns:
        SHA-256 hash of the ID
    """
    return hashlib.sha256(str(telegram_id).encode()).hexdigest()


def verify_telegram_webhook(data: Dict[str, Any], token: str) -> bool:
    """
    Verify Telegram webhook authenticity.
    
    Args:
        data: Webhook data received from Telegram
        token: Expected webhook secret token
        
    Returns:
        True if webhook is authentic, False otherwise
    """
    received_token = data.get("secret_token")
    if not received_token:
        return False
    
    return hmac.compare_digest(received_token, token)


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.
    
    Args:
        text: User input text
        
    Returns:
        Sanitized text
    """
    # Remove potentially dangerous characters
    dangerous_chars = ["<", ">", "&", "'", '"', "script", "javascript"]
    sanitized = text
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")
    
    return sanitized.strip()


def validate_phone_number(phone: str) -> bool:
    """
    Validate Ethiopian phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if valid Ethiopian phone number, False otherwise
    """
    import re
    pattern = re.compile(r"^(09|07)\d{8}$")
    return bool(pattern.match(phone))


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format, False otherwise
    """
    import re
    pattern = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    return bool(pattern.match(email))


def mask_sensitive_data(data: str, visible_start: int = 2, visible_end: int = 2) -> str:
    """
    Mask sensitive data like phone numbers, emails, etc.
    
    Args:
        data: Original string
        visible_start: Number of characters to show at start
        visible_end: Number of characters to show at end
        
    Returns:
        Masked string
    """
    if len(data) <= visible_start + visible_end:
        return "*" * len(data)
    
    masked = (
        data[:visible_start] +
        "*" * (len(data) - visible_start - visible_end) +
        data[-visible_end:]
    )
    
    return masked


def generate_csrf_token() -> str:
    """
    Generate CSRF protection token.
    
    Returns:
        CSRF token string
    """
    return generate_secure_token(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    """
    Verify CSRF token.
    
    Args:
        token: Token to verify
        stored_token: Stored token to compare against
        
    Returns:
        True if tokens match, False otherwise
    """
    return hmac.compare_digest(token, stored_token)


class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get standard security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }


# Export commonly used functions
__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "verify_token",
    "generate_otp",
    "generate_secure_token",
    "encrypt_data",
    "decrypt_data",
    "hash_telegram_id",
    "verify_telegram_webhook",
    "sanitize_input",
    "validate_phone_number",
    "validate_email",
    "mask_sensitive_data",
    "generate_csrf_token",
    "verify_csrf_token",
    "SecurityHeaders",
]