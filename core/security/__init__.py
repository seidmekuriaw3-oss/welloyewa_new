import secrets
import hashlib
import hmac
import json
import base64
from typing import Any, Dict, Optional

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
    AuditEntry,
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
    handle_data_request,
)
from core.security.middleware import SecurityHeadersMiddleware


def hash_password(password: str) -> str:
    try:
        from passlib.context import CryptContext
        _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return _pwd_context.hash(password)
    except Exception:
        return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        from passlib.context import CryptContext
        _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return hmac.compare_digest(
            hashlib.sha256(plain_password.encode()).hexdigest(),
            hashed_password,
        )


def create_access_token(data: Dict[str, Any], expires_delta=None) -> str:
    try:
        from datetime import datetime, timedelta
        from jose import jwt
        from core.config import settings
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRY_MINUTES))
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    except Exception:
        token_data = json.dumps({k: str(v) for k, v in data.items()})
        return base64.b64encode(token_data.encode()).decode()


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        from jose import jwt, JWTError
        from core.config import settings
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        try:
            data = json.loads(base64.b64decode(token.encode()).decode())
            return data
        except Exception:
            return None


def generate_otp(length: int = 6) -> str:
    return ''.join(str(secrets.randbelow(10)) for _ in range(length))


def generate_secure_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def verify_telegram_webhook(data: Dict[str, Any], token: str) -> bool:
    received_token = data.get("secret_token")
    if not received_token:
        return False
    return hmac.compare_digest(str(received_token), str(token))


def sanitize_input(text: str) -> str:
    import bleach
    return bleach.clean(text, tags=[], strip=True)


def validate_phone_number(phone: str) -> bool:
    import re
    pattern = r'^\+?[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone.replace(' ', '').replace('-', '')))


def validate_email(email: str) -> bool:
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def mask_sensitive_data(data: str, visible_start: int = 2, visible_end: int = 2) -> str:
    if len(data) <= visible_start + visible_end:
        return '*' * len(data)
    return data[:visible_start] + '*' * (len(data) - visible_start - visible_end) + data[-visible_end:]


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected: str) -> bool:
    return hmac.compare_digest(token, expected)


__all__ = [
    "encrypt_data",
    "decrypt_data",
    "hash_data",
    "verify_hash",
    "EncryptionManager",
    "AuditLogger",
    "audit_log",
    "AuditEntry",
    "get_audit_logs",
    "AdvancedRateLimiter",
    "rate_limit",
    "AdvancedRateLimitStrategy",
    "SQLInjectionDetector",
    "detect_sql_injection",
    "sanitize_sql_input",
    "PIICategory",
    "PIIMasker",
    "mask_pii",
    "detect_pii",
    "redact_pii",
    "FraudDetector",
    "FraudRule",
    "FraudAlert",
    "detect_fraud",
    "FraudSeverity",
    "GDPRCompliance",
    "DataSubjectRequest",
    "ConsentManager",
    "handle_data_request",
    "SecurityHeadersMiddleware",
    "hash_password",
    "verify_password",
    "create_access_token",
    "verify_token",
    "generate_otp",
    "generate_secure_token",
    "verify_telegram_webhook",
    "sanitize_input",
    "validate_phone_number",
    "validate_email",
    "mask_sensitive_data",
    "generate_csrf_token",
    "verify_csrf_token",
]
