# ============================
# WOLLOYEWA STORE BOT - COMPLIANCE MODULE
# ============================
"""Legal and regulatory compliance for Ethiopian market."""

from infrastructure.compliance.tax_calculator import (
    TaxCalculator,
    TaxRate,
    TaxCategory,
    calculate_vat,
    calculate_withholding_tax,
    calculate_turnover_tax,
    calculate_total_tax,
    TaxResult,
)
from infrastructure.compliance.invoice_legal_format import (
    LegalInvoiceGenerator,
    LegalInvoice,
    InvoiceType,
    generate_legal_invoice,
    validate_invoice_for_tax,
    TaxInvoice,
    ReceiptInvoice,
)
from infrastructure.compliance.data_residency import (
    DataResidencyManager,
    DataRegion,
    DataClassification,
    ensure_data_residency,
    get_data_location,
    DataResidencyCompliance,
)
from infrastructure.compliance.privacy_policy_gen import (
    PrivacyPolicyGenerator,
    PrivacyPolicy,
    ConsentType,
    generate_privacy_policy,
    update_privacy_policy,
    PrivacyCompliance,
)
from infrastructure.compliance.terms_checker import (
    TermsChecker,
    TermsAcceptance,
    TermsVersion,
    check_terms_acceptance,
    record_terms_acceptance,
    get_current_terms,
    TermsCompliance,
)
from infrastructure.compliance.audit_log_retention import (
    AuditLogRetention,
    RetentionPolicy,
    LogRetentionManager,
    enforce_retention_policy,
    archive_audit_logs,
    delete_expired_logs,
)

__all__ = [
    # Tax Calculator
    "TaxCalculator",
    "TaxRate",
    "TaxCategory",
    "calculate_vat",
    "calculate_withholding_tax",
    "calculate_turnover_tax",
    "calculate_total_tax",
    "TaxResult",
    # Legal Invoice
    "LegalInvoiceGenerator",
    "LegalInvoice",
    "InvoiceType",
    "generate_legal_invoice",
    "validate_invoice_for_tax",
    "TaxInvoice",
    "ReceiptInvoice",
    # Data Residency
    "DataResidencyManager",
    "DataRegion",
    "DataClassification",
    "ensure_data_residency",
    "get_data_location",
    "DataResidencyCompliance",
    # Privacy Policy
    "PrivacyPolicyGenerator",
    "PrivacyPolicy",
    "ConsentType",
    "generate_privacy_policy",
    "update_privacy_policy",
    "PrivacyCompliance",
    # Terms Checker
    "TermsChecker",
    "TermsAcceptance",
    "TermsVersion",
    "check_terms_acceptance",
    "record_terms_acceptance",
    "get_current_terms",
    "TermsCompliance",
    # Audit Log Retention
    "AuditLogRetention",
    "RetentionPolicy",
    "LogRetentionManager",
    "enforce_retention_policy",
    "archive_audit_logs",
    "delete_expired_logs",
]