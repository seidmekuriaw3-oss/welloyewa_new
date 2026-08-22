# ============================
# WOLLOYEWA STORE BOT - COMPLIANCE MODULE
# ============================
"""Legal and regulatory compliance for Ethiopian market."""

from infrastructure.compliance.audit_log_retention import (
    AuditLogRetention,
    LogRetentionManager,
    RetentionPolicy,
    archive_audit_logs,
    delete_expired_logs,
    enforce_retention_policy,
)
from infrastructure.compliance.data_residency import (
    DataClassification,
    DataRegion,
    DataResidencyCompliance,
    DataResidencyManager,
    ensure_data_residency,
    get_data_location,
)
from infrastructure.compliance.invoice_legal_format import (
    InvoiceType,
    LegalInvoice,
    LegalInvoiceGenerator,
    ReceiptInvoice,
    TaxInvoice,
    generate_legal_invoice,
    validate_invoice_for_tax,
)
from infrastructure.compliance.privacy_policy_gen import (
    ConsentType,
    PrivacyCompliance,
    PrivacyPolicy,
    PrivacyPolicyGenerator,
    generate_privacy_policy,
    update_privacy_policy,
)
from infrastructure.compliance.tax_calculator import (
    TaxCalculator,
    TaxCategory,
    TaxRate,
    TaxResult,
    calculate_total_tax,
    calculate_turnover_tax,
    calculate_vat,
    calculate_withholding_tax,
)
from infrastructure.compliance.terms_checker import (
    TermsAcceptance,
    TermsChecker,
    TermsCompliance,
    TermsVersion,
    check_terms_acceptance,
    get_current_terms,
    record_terms_acceptance,
)

__all__ = [
    # Audit Log Retention
    "AuditLogRetention",
    "ConsentType",
    "DataClassification",
    "DataRegion",
    "DataResidencyCompliance",
    # Data Residency
    "DataResidencyManager",
    "InvoiceType",
    "LegalInvoice",
    # Legal Invoice
    "LegalInvoiceGenerator",
    "LogRetentionManager",
    "PrivacyCompliance",
    "PrivacyPolicy",
    # Privacy Policy
    "PrivacyPolicyGenerator",
    "ReceiptInvoice",
    "RetentionPolicy",
    # Tax Calculator
    "TaxCalculator",
    "TaxCategory",
    "TaxInvoice",
    "TaxRate",
    "TaxResult",
    "TermsAcceptance",
    # Terms Checker
    "TermsChecker",
    "TermsCompliance",
    "TermsVersion",
    "archive_audit_logs",
    "calculate_total_tax",
    "calculate_turnover_tax",
    "calculate_vat",
    "calculate_withholding_tax",
    "check_terms_acceptance",
    "delete_expired_logs",
    "enforce_retention_policy",
    "ensure_data_residency",
    "generate_legal_invoice",
    "generate_privacy_policy",
    "get_current_terms",
    "get_data_location",
    "record_terms_acceptance",
    "update_privacy_policy",
    "validate_invoice_for_tax",
]
