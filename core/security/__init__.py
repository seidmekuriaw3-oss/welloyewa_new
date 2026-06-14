# ============================
# WOLLOYEWA STORE BOT - SECURITY MODULE
# ============================
"""Security utilities for encryption, audit, rate limiting, and compliance."""

import hashlib
import hmac
import secrets as _secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from passlib.context import CryptContext
from jose import jwt, JWTError

from core.config import settings
from core.logger import logger

# Password hashing context
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "iss": settings.PROJECT_NAME})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.PROJECT_NAME,
        )
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


def generate_otp(length: int = 6) -> str:
    return ''.join(str(_secrets.randbelow(10)) for _ in range(length))


def generate_secure_token(length: int = 32) -> str:
    return _secrets.token_urlsafe(length)


def sanitize_input(text: str) -> str:
    import re
    return re.sub(r'[<>&\'""]', '', text).strip()


def validate_phone_number(phone: str) -> bool:
    import re
    return bool(re.match(r'^(09|07)\d{8}$', phone))


def validate_email(email: str) -> bool:
    import re
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def mask_sensitive_data(data: str, visible_start: int = 2, visible_end: int = 2) -> str:
    if len(data) <= visible_start + visible_end:
        return '*' * len(data)
    return data[:visible_start] + '*' * (len(data) - visible_start - visible_end) + data[-visible_end:]


def hash_telegram_id(telegram_id: int) -> str:
    return hashlib.sha256(str(telegram_id).encode()).hexdigest()


def generate_csrf_token() -> str:
    return generate_secure_token(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    return hmac.compare_digest(token, stored_token)


def verify_telegram_webhook(data: dict, token: str) -> bool:
    received_token = data.get("secret_token")
    if not received_token:
        return False
    return hmac.compare_digest(received_token, token)


from core.security.encryption import (
    encrypt_data,
    decrypt_data,
    hash_data,
    verify_hash,
    EncryptionManager,
)
from core.security.audit_trail import (
    AuditLogger,
    audit_log,
    AuditEvent,
    get_audit_logs,
)
from core.security.rate_limiter_advanced import (
    AdvancedRateLimiter,
    rate_limit,
    RateLimitStrategy as AdvancedRateLimitStrategy,
)
from core.security.sql_injection_detector import (
    SQLInjectionDetector,
    detect_sql_injection,
    sanitize_sql_input,
)
from core.security.pii_masker import (
    PIICategory,
    PIIMasker,
    mask_pii,
    detect_pii,
    redact_pii,
)
from core.security.fraud_detection import (
    FraudDetector,
    FraudRule,
    FraudAlert,
    detect_fraud,
    FraudSeverity,
)
from core.security.gdpr_compliance import (
    GDPRCompliance,
    DataSubjectRequest,
    ConsentManager,
    gdpr_compliance,
    handle_data_request,
)

__all__ = [
    # Encryption
    "encrypt_data",
    "decrypt_data",
    "hash_data",
    "verify_hash",
    "EncryptionManager",
    # Audit Trail
    "AuditLogger",
    "audit_log",
    "AuditEvent",
    "get_audit_logs",
    # Rate Limiting
    "AdvancedRateLimiter",
    "rate_limit",
    "AdvancedRateLimitStrategy",
    # SQL Injection
    "SQLInjectionDetector",
    "detect_sql_injection",
    "sanitize_sql_input",
    # PII Masking
    "PIICategory",
    "PIIMasker",
    "mask_pii",
    "detect_pii",
    "redact_pii",
    # Fraud Detection
    "FraudDetector",
    "FraudRule",
    "FraudAlert",
    "detect_fraud",
    "FraudSeverity",
    # GDPR Compliance
    "GDPRCompliance",
    "DataSubjectRequest",
    "ConsentManager",
    "gdpr_compliance",
    "handle_data_request",
]