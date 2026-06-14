# ============================
# WOLLOYEWA STORE BOT - VALIDATORS
# ============================
"""Data validation utilities for Ethiopian-specific formats."""

import re
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from email_validator import validate_email as validate_email_lib, EmailNotValidError

from core.constants import PHONE_PATTERN, TIN_PATTERN, LICENSE_PATTERN, EMAIL_PATTERN


def validate_phone(phone: str, normalize: bool = True) -> tuple[bool, Optional[str]]:
    """
    Validate Ethiopian phone number.
    
    Args:
        phone: Phone number to validate
        normalize: Whether to return normalized phone number
        
    Returns:
        Tuple of (is_valid, normalized_phone)
    """
    if not phone:
        return False, None
    
    # Remove any non-digit characters
    cleaned = re.sub(r'\D', '', phone)
    
    # Check if it's a valid Ethiopian number
    pattern = re.compile(PHONE_PATTERN)
    
    if not pattern.match(cleaned):
        return False, None
    
    if normalize:
        return True, cleaned
    
    return True, None


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, normalized_email)
    """
    if not email:
        return False, None
    
    try:
        validated = validate_email_lib(email)
        return True, validated.normalized
    except EmailNotValidError:
        return False, None


def validate_ethiopian_tin(tin: str) -> bool:
    """
    Validate Ethiopian Tax Identification Number (TIN).
    
    Args:
        tin: TIN number to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not tin:
        return False
    
    # Remove spaces
    tin = tin.strip()
    
    # Check format (10 digits)
    pattern = re.compile(TIN_PATTERN)
    return bool(pattern.match(tin))


def validate_business_license(license_number: str) -> bool:
    """
    Validate Ethiopian business license number.
    
    Args:
        license_number: License number to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not license_number:
        return False
    
    license_number = license_number.strip().upper()
    pattern = re.compile(LICENSE_PATTERN)
    return bool(pattern.match(license_number))


def validate_password_strength(
    password: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digits: bool = True,
    require_special: bool = True,
) -> tuple[bool, List[str]]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        min_length: Minimum length required
        require_uppercase: Require uppercase letters
        require_lowercase: Require lowercase letters
        require_digits: Require digits
        require_special: Require special characters
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    if not password:
        issues.append("Password is required")
        return False, issues
    
    if len(password) < min_length:
        issues.append(f"Password must be at least {min_length} characters")
    
    if require_uppercase and not re.search(r'[A-Z]', password):
        issues.append("Password must contain at least one uppercase letter")
    
    if require_lowercase and not re.search(r'[a-z]', password):
        issues.append("Password must contain at least one lowercase letter")
    
    if require_digits and not re.search(r'\d', password):
        issues.append("Password must contain at least one digit")
    
    if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        issues.append("Password must contain at least one special character")
    
    return len(issues) == 0, issues


def sanitize_string(text: str, allow_spaces: bool = True, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent injection attacks.
    
    Args:
        text: Input string
        allow_spaces: Whether to allow spaces
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not text:
        return ""
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove JavaScript events
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    
    # Remove script tags
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove potentially dangerous characters
    dangerous = ['&', '<', '>', "'", '"', '`', ';', '%', '\\', '/']
    for char in dangerous:
        text = text.replace(char, '')
    
    if not allow_spaces:
        text = re.sub(r'\s+', '', text)
    else:
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def is_valid_uuid(value: str, version: int = 4) -> bool:
    """
    Check if string is a valid UUID.
    
    Args:
        value: String to check
        version: UUID version (1, 3, 4, 5)
        
    Returns:
        True if valid UUID, False otherwise
    """
    try:
        u = uuid.UUID(value, version=version)
        return str(u) == value
    except (ValueError, AttributeError, TypeError):
        return False


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    if not url:
        return False
    
    pattern = re.compile(
        r'^(?:http|https)://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return bool(pattern.match(url))


def validate_amount(amount: Union[int, float, str]) -> bool:
    """
    Validate monetary amount.
    
    Args:
        amount: Amount to validate
        
    Returns:
        True if valid amount, False otherwise
    """
    try:
        value = float(amount)
        return value >= 0 and value <= 999999999.99
    except (ValueError, TypeError):
        return False


def validate_quantity(quantity: int) -> bool:
    """
    Validate product quantity.
    
    Args:
        quantity: Quantity to validate
        
    Returns:
        True if valid quantity, False otherwise
    """
    try:
        qty = int(quantity)
        return qty > 0 and qty <= 99999
    except (ValueError, TypeError):
        return False


def validate_rating(rating: Union[int, float]) -> bool:
    """
    Validate rating value (1-5).
    
    Args:
        rating: Rating to validate
        
    Returns:
        True if valid rating, False otherwise
    """
    try:
        value = float(rating)
        return 1 <= value <= 5
    except (ValueError, TypeError):
        return False


def validate_date_range(start_date: str, end_date: str) -> tuple[bool, Optional[str]]:
    """
    Validate date range (start date must be before end date).
    
    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    from datetime import datetime
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start > end:
            return False, "Start date must be before end date"
        
        return True, None
    except ValueError as e:
        return False, f"Invalid date format: {e}"


def validate_page_number(page: int, max_page: int = 1000) -> bool:
    """
    Validate pagination page number.
    
    Args:
        page: Page number to validate
        max_page: Maximum allowed page number
        
    Returns:
        True if valid page number, False otherwise
    """
    try:
        p = int(page)
        return p >= 1 and p <= max_page
    except (ValueError, TypeError):
        return False


def validate_page_size(size: int, max_size: int = 100, min_size: int = 1) -> bool:
    """
    Validate pagination page size.
    
    Args:
        size: Page size to validate
        max_size: Maximum allowed size
        min_size: Minimum allowed size
        
    Returns:
        True if valid page size, False otherwise
    """
    try:
        s = int(size)
        return min_size <= s <= max_size
    except (ValueError, TypeError):
        return False


class Validator:
    """Collection of static validation methods."""
    
    @staticmethod
    def phone(phone: str, normalize: bool = True) -> Optional[str]:
        """Validate and normalize phone number."""
        is_valid, normalized = validate_phone(phone, normalize)
        if not is_valid:
            raise ValueError(f"Invalid phone number: {phone}")
        return normalized
    
    @staticmethod
    def email(email: str) -> str:
        """Validate and normalize email address."""
        is_valid, normalized = validate_email(email)
        if not is_valid:
            raise ValueError(f"Invalid email address: {email}")
        return normalized
    
    @staticmethod
    def tin(tin: str) -> str:
        """Validate Ethiopian TIN."""
        if not validate_ethiopian_tin(tin):
            raise ValueError(f"Invalid TIN number: {tin}")
        return tin.strip()
    
    @staticmethod
    def password(password: str) -> str:
        """Validate password strength."""
        is_valid, issues = validate_password_strength(password)
        if not is_valid:
            raise ValueError(f"Weak password: {', '.join(issues)}")
        return password
    
    @staticmethod
    def amount(value: Union[int, float, str]) -> Decimal:
        """Validate and convert amount."""
        if not validate_amount(value):
            raise ValueError(f"Invalid amount: {value}")
        from core.utils.currency import to_decimal
        return to_decimal(value)


__all__ = [
    "validate_phone",
    "validate_email",
    "validate_ethiopian_tin",
    "validate_business_license",
    "validate_password_strength",
    "sanitize_string",
    "is_valid_uuid",
    "validate_url",
    "validate_amount",
    "validate_quantity",
    "validate_rating",
    "validate_date_range",
    "validate_page_number",
    "validate_page_size",
    "Validator",
]