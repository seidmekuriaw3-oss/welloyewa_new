# ============================
# WOLLOYEWA STORE BOT - SECURITY MODULE
# ============================
"""Security utilities for encryption, audit, rate limiting, and compliance."""

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