# ============================
# WOLLOYEWA STORE BOT - CUSTOM EXCEPTIONS
# ============================
"""Custom exception classes for the application."""

from typing import Any, Dict, Optional


class WolloyewaException(Exception):
    """Base exception for all application-specific exceptions."""
    
    def __init__(
        self,
        message: str,
        code: str = "ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


# ============================
# Database Exceptions
# ============================

class DatabaseError(WolloyewaException):
    """Base exception for database-related errors."""
    
    def __init__(self, message: str = "Database error occurred", **kwargs):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            **kwargs,
        )


class RecordNotFoundError(DatabaseError):
    """Exception raised when a database record is not found."""
    
    def __init__(self, model: str, identifier: Any):
        super().__init__(
            message=f"{model} with identifier '{identifier}' not found",
            code="RECORD_NOT_FOUND",
            status_code=404,
            details={"model": model, "identifier": str(identifier)},
        )


class DuplicateRecordError(DatabaseError):
    """Exception raised when attempting to create a duplicate record."""
    
    def __init__(self, model: str, field: str, value: Any):
        super().__init__(
            message=f"{model} with {field} '{value}' already exists",
            code="DUPLICATE_RECORD",
            status_code=409,
            details={"model": model, "field": field, "value": str(value)},
        )


# ============================
# Validation Exceptions
# ============================

class ValidationError(WolloyewaException):
    """Exception raised when data validation fails."""
    
    def __init__(self, message: str = "Validation failed", errors: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details={"errors": errors or {}},
        )


class PhoneNumberError(ValidationError):
    """Exception raised for invalid phone numbers."""
    
    def __init__(self, phone: str):
        super().__init__(
            message=f"Invalid phone number: {phone}. Must be an Ethiopian phone number (09XXXXXXXX or 07XXXXXXXX)",
            errors={"phone": ["Invalid format"]},
        )


class EmailError(ValidationError):
    """Exception raised for invalid email addresses."""
    
    def __init__(self, email: str):
        super().__init__(
            message=f"Invalid email address: {email}",
            errors={"email": ["Invalid format"]},
        )


class PasswordError(ValidationError):
    """Exception raised for invalid passwords."""
    
    def __init__(self, message: str = "Password must be at least 8 characters"):
        super().__init__(
            message=message,
            errors={"password": [message]},
        )


# ============================
# Authentication & Authorization
# ============================

class AuthenticationError(WolloyewaException):
    """Exception raised for authentication failures."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401,
        )


class InvalidTokenError(AuthenticationError):
    """Exception raised for invalid or expired tokens."""
    
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message)


class PermissionError(WolloyewaException):
    """Exception raised for permission/authorization failures."""
    
    def __init__(self, message: str = "You don't have permission to perform this action"):
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=403,
        )


class RoleRequiredError(PermissionError):
    """Exception raised when a specific role is required."""
    
    def __init__(self, required_role: str):
        super().__init__(
            message=f"Role '{required_role}' is required to perform this action",
            details={"required_role": required_role},
        )


# ============================
# Business Logic Exceptions
# ============================

class NotFoundError(WolloyewaException):
    """Exception raised when a resource is not found."""
    
    def __init__(self, resource: str, resource_id: Any = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with ID '{resource_id}' not found"
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
        )


class InsufficientStockError(WolloyewaException):
    """Exception raised when product stock is insufficient."""
    
    def __init__(self, product_name: str, requested: int, available: int):
        super().__init__(
            message=f"Insufficient stock for '{product_name}'. Requested: {requested}, Available: {available}",
            code="INSUFFICIENT_STOCK",
            status_code=400,
            details={
                "product_name": product_name,
                "requested": requested,
                "available": available,
            },
        )


class PaymentError(WolloyewaException):
    """Exception raised for payment-related errors."""
    
    def __init__(self, message: str = "Payment processing failed"):
        super().__init__(
            message=message,
            code="PAYMENT_ERROR",
            status_code=400,
        )


class PaymentVerificationError(PaymentError):
    """Exception raised when payment verification fails."""
    
    def __init__(self, transaction_id: str):
        super().__init__(
            message=f"Payment verification failed for transaction: {transaction_id}",
            details={"transaction_id": transaction_id},
        )


class OrderError(WolloyewaException):
    """Exception raised for order-related errors."""
    
    def __init__(self, message: str = "Order operation failed"):
        super().__init__(
            message=message,
            code="ORDER_ERROR",
            status_code=400,
        )


class OrderStatusError(OrderError):
    """Exception raised for invalid order status transitions."""
    
    def __init__(self, current_status: str, requested_status: str):
        super().__init__(
            message=f"Cannot change order status from '{current_status}' to '{requested_status}'",
            details={
                "current_status": current_status,
                "requested_status": requested_status,
            },
        )


# ============================
# Rate Limiting Exceptions
# ============================

class RateLimitError(WolloyewaException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Please try again in {retry_after} seconds.",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after},
        )


# ============================
# File & Storage Exceptions
# ============================

class FileUploadError(WolloyewaException):
    """Exception raised for file upload errors."""
    
    def __init__(self, message: str = "File upload failed"):
        super().__init__(
            message=message,
            code="FILE_UPLOAD_ERROR",
            status_code=400,
        )


class FileSizeExceededError(FileUploadError):
    """Exception raised when file size exceeds limit."""
    
    def __init__(self, max_size_mb: int):
        super().__init__(
            message=f"File size exceeds maximum allowed size of {max_size_mb}MB",
            details={"max_size_mb": max_size_mb},
        )


class UnsupportedFileTypeError(FileUploadError):
    """Exception raised for unsupported file types."""
    
    def __init__(self, file_type: str, allowed_types: list):
        super().__init__(
            message=f"Unsupported file type: {file_type}. Allowed: {', '.join(allowed_types)}",
            details={"file_type": file_type, "allowed_types": allowed_types},
        )


# ============================
# Cache Exceptions
# ============================

class CacheError(WolloyewaException):
    """Exception raised for cache-related errors."""
    
    def __init__(self, message: str = "Cache operation failed"):
        super().__init__(
            message=message,
            code="CACHE_ERROR",
            status_code=500,
        )


# ============================
# External Service Exceptions
# ============================

class ExternalServiceError(WolloyewaException):
    """Exception raised when an external service fails."""
    
    def __init__(self, service: str, message: str = "External service error"):
        super().__init__(
            message=f"{service}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service},
        )


class TelegramAPIError(ExternalServiceError):
    """Exception raised for Telegram API errors."""
    
    def __init__(self, message: str = "Telegram API error"):
        super().__init__(service="Telegram", message=message)


# ============================
# Configuration Exceptions
# ============================

class ConfigurationError(WolloyewaException):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str = "Configuration error"):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=500,
        )


# ============================
# Webhook Exceptions
# ============================

class WebhookError(WolloyewaException):
    """Exception raised for webhook processing errors."""
    
    def __init__(self, message: str = "Webhook processing failed"):
        super().__init__(
            message=message,
            code="WEBHOOK_ERROR",
            status_code=400,
        )


class WebhookVerificationError(WebhookError):
    """Exception raised when webhook verification fails."""
    
    def __init__(self):
        super().__init__(message="Webhook signature verification failed")