# ============================
# WOLLOYEWA STORE BOT - STRING UTILITIES
# ============================
"""String manipulation and text processing utilities."""

import re
import random
import string
import hashlib
import unicodedata
from typing import List, Optional, Set, Union
from html import escape
import json


def slugify(text: str, max_length: int = 100) -> str:
    """
    Convert text to URL-friendly slug.
    
    Args:
        text: Input text
        max_length: Maximum slug length
        
    Returns:
        URL-friendly slug string
    """
    if not text:
        return ""
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters (keep letters, numbers, spaces, hyphens)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    
    # Replace spaces with hyphens
    text = re.sub(r'[\s-]+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length].rsplit('-', 1)[0]
    
    return text


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated string
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length - len(suffix)]
    return truncated.rstrip() + suffix


def generate_random_string(
    length: int = 8,
    include_digits: bool = True,
    include_special: bool = False,
    uppercase: bool = True,
    lowercase: bool = True,
) -> str:
    """
    Generate random string.
    
    Args:
        length: Length of the string
        include_digits: Include digits (0-9)
        include_special: Include special characters
        uppercase: Include uppercase letters
        lowercase: Include lowercase letters
        
    Returns:
        Random string
    """
    characters = ""
    
    if uppercase:
        characters += string.ascii_uppercase
    if lowercase:
        characters += string.ascii_lowercase
    if include_digits:
        characters += string.digits
    if include_special:
        characters += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    if not characters:
        characters = string.ascii_letters
    
    return ''.join(random.choice(characters) for _ in range(length))


def generate_order_number(prefix: str = "ORD") -> str:
    """
    Generate unique order number.
    
    Args:
        prefix: Order prefix
        
    Returns:
        Order number like ORD-20241215-ABC123
    """
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    random_part = generate_random_string(6, include_digits=True, include_special=False)
    return f"{prefix}-{date_str}-{random_part}"


def generate_transaction_id(prefix: str = "TXN") -> str:
    """
    Generate unique transaction ID.
    
    Args:
        prefix: Transaction prefix
        
    Returns:
        Transaction ID
    """
    random_part = generate_random_string(12, include_digits=True, include_special=False)
    return f"{prefix}_{random_part}"


def strip_html(text: str) -> str:
    """
    Remove HTML tags from string.
    
    Args:
        text: HTML text
        
    Returns:
        Plain text without HTML
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove HTML entities
    text = re.sub(r'&[^;]+;', '', text)
    
    return text.strip()


def escape_html(text: str) -> str:
    """
    Escape HTML special characters.
    
    Args:
        text: Input text
        
    Returns:
        HTML-escaped text
    """
    return escape(str(text))


def extract_mentions(text: str) -> List[str]:
    """
    Extract Telegram mentions from text.
    
    Args:
        text: Input text
        
    Returns:
        List of usernames mentioned (without @)
    """
    if not text:
        return []
    
    # Match @username pattern
    pattern = r'@(\w+)'
    matches = re.findall(pattern, text)
    return matches


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text.
    
    Args:
        text: Input text
        
    Returns:
        List of hashtags (without #)
    """
    if not text:
        return []
    
    # Match #hashtag pattern
    pattern = r'#(\w+)'
    matches = re.findall(pattern, text)
    return matches


def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text.
    
    Args:
        text: Input text
        
    Returns:
        List of email addresses
    """
    if not text:
        return []
    
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(pattern, text)


def extract_phone_numbers(text: str) -> List[str]:
    """
    Extract Ethiopian phone numbers from text.
    
    Args:
        text: Input text
        
    Returns:
        List of phone numbers
    """
    if not text:
        return []
    
    pattern = r'(09|07)\d{8}'
    return re.findall(pattern, text)


def mask_string(text: str, visible_start: int = 2, visible_end: int = 2, mask_char: str = "*") -> str:
    """
    Mask part of a string.
    
    Args:
        text: Input text
        visible_start: Number of characters to show at start
        visible_end: Number of characters to show at end
        mask_char: Character to use for masking
        
    Returns:
        Masked string
    """
    if not text:
        return ""
    
    if len(text) <= visible_start + visible_end:
        return mask_char * len(text)
    
    masked = (
        text[:visible_start] +
        mask_char * (len(text) - visible_start - visible_end) +
        text[-visible_end:]
    )
    
    return masked


def mask_email(email: str) -> str:
    """
    Mask email address (e.g., u***r@example.com).
    
    Args:
        email: Email address
        
    Returns:
        Masked email
    """
    if not email or "@" not in email:
        return email
    
    local, domain = email.split("@", 1)
    
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """
    Mask phone number (e.g., 09******89).
    
    Args:
        phone: Phone number
        
    Returns:
        Masked phone number
    """
    if not phone:
        return phone
    
    # Remove non-digits
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) <= 6:
        return "*" * len(digits)
    
    return f"{digits[:2]}******{digits[-2:]}"


def capitalize_words(text: str) -> str:
    """
    Capitalize first letter of each word.
    
    Args:
        text: Input text
        
    Returns:
        Text with each word capitalized
    """
    if not text:
        return ""
    
    return ' '.join(word.capitalize() for word in text.split())


def remove_extra_whitespace(text: str) -> str:
    """
    Remove extra whitespace (multiple spaces, tabs, newlines).
    
    Args:
        text: Input text
        
    Returns:
        Text with normalized whitespace
    """
    if not text:
        return ""
    
    # Replace tabs and newlines with spaces
    text = re.sub(r'[\t\n\r]+', ' ', text)
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def is_valid_username(username: str) -> bool:
    """
    Check if username is valid (alphanumeric and underscore, 3-32 chars).
    
    Args:
        username: Username to validate
        
    Returns:
        True if valid username
    """
    if not username:
        return False
    
    pattern = r'^[a-zA-Z0-9_]{3,32}$'
    return bool(re.match(pattern, username))


def is_valid_telegram_username(username: str) -> bool:
    """
    Check if Telegram username is valid.
    
    Args:
        username: Telegram username (with or without @)
        
    Returns:
        True if valid
    """
    if not username:
        return False
    
    # Remove @ if present
    username = username.lstrip('@')
    
    # Telegram username rules: 5-32 chars, alphanumeric and underscore
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$'
    return bool(re.match(pattern, username))


def normalize_text(text: str, to_lower: bool = True, remove_punctuation: bool = False) -> str:
    """
    Normalize text for comparison or search.
    
    Args:
        text: Input text
        to_lower: Convert to lowercase
        remove_punctuation: Remove punctuation marks
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    if to_lower:
        text = text.lower()
    
    if remove_punctuation:
        text = re.sub(r'[^\w\s]', '', text)
    
    # Normalize unicode
    text = unicodedata.normalize('NFKC', text)
    
    return text.strip()


def create_text_preview(text: str, max_length: int = 100, strip_html_tags: bool = True) -> str:
    """
    Create text preview for display.
    
    Args:
        text: Input text
        max_length: Maximum preview length
        strip_html_tags: Whether to remove HTML tags
        
    Returns:
        Text preview
    """
    if not text:
        return ""
    
    if strip_html_tags:
        text = strip_html(text)
    
    return truncate_string(text, max_length)


def generate_hash(text: str, algorithm: str = "md5") -> str:
    """
    Generate hash of text.
    
    Args:
        text: Input text
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
        
    Returns:
        Hash string
    """
    text_bytes = text.encode('utf-8')
    
    if algorithm == "md5":
        return hashlib.md5(text_bytes).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(text_bytes).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(text_bytes).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(text_bytes).hexdigest()
    else:
        return hashlib.md5(text_bytes).hexdigest()


def to_camel_case(text: str) -> str:
    """
    Convert snake_case to camelCase.
    
    Args:
        text: snake_case string
        
    Returns:
        camelCase string
    """
    parts = text.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])


def to_snake_case(text: str) -> str:
    """
    Convert camelCase to snake_case.
    
    Args:
        text: camelCase string
        
    Returns:
        snake_case string
    """
    pattern = re.compile(r'(?<!^)(?=[A-Z])')
    return pattern.sub('_', text).lower()


def pluralize(word: str, count: int, language: str = "en") -> str:
    """
    Get plural form of word based on count.
    
    Args:
        word: Singular word
        count: Number of items
        language: Language code
        
    Returns:
        Pluralized word if count != 1
    """
    if count == 1:
        return word
    
    if language == "am":
        # Amharic pluralization (simple rule)
        if word.endswith('ዎች'):
            return word
        if word.endswith('ል'):
            return word + 'ሎች'
        return word + 'ዎች'
    
    # English pluralization (simple rule)
    if word.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return word + 'es'
    elif word.endswith('y') and word[-2] not in 'aeiou':
        return word[:-1] + 'ies'
    else:
        return word + 's'


__all__ = [
    "slugify",
    "truncate_string",
    "generate_random_string",
    "generate_order_number",
    "generate_transaction_id",
    "strip_html",
    "escape_html",
    "extract_mentions",
    "extract_hashtags",
    "extract_emails",
    "extract_phone_numbers",
    "mask_string",
    "mask_email",
    "mask_phone",
    "capitalize_words",
    "remove_extra_whitespace",
    "is_valid_username",
    "is_valid_telegram_username",
    "normalize_text",
    "create_text_preview",
    "generate_hash",
    "to_camel_case",
    "to_snake_case",
    "pluralize",
]