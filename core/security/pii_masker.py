# ============================
# WOLLOYEWA STORE BOT - PII MASKER
# ============================
"""Personally Identifiable Information (PII) detection and masking."""

import re
from enum import Enum
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

from core.logger import logger


class PIICategory(str, Enum):
    """Categories of Personally Identifiable Information."""
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    NAME = "name"
    ADDRESS = "address"
    TIN = "tin"  # Ethiopian Tax ID
    PASSPORT = "passport"
    BANK_ACCOUNT = "bank_account"
    CREDIT_CARD = "credit_card"
    NATIONAL_ID = "national_id"
    DRIVERS_LICENSE = "drivers_license"
    IP_ADDRESS = "ip_address"
    LOCATION = "location"
    DATE_OF_BIRTH = "date_of_birth"
    USERNAME = "username"
    PASSWORD = "password"


@dataclass
class PIIMatch:
    """Information about detected PII."""
    
    category: PIICategory
    value: str
    start_pos: int
    end_pos: int
    confidence: float  # 0-1 confidence score


class PIIMasker:
    """
    Detect and mask Personally Identifiable Information.
    
    Features:
    - Automatic detection of common PII types
    - Configurable masking strategies
    - Support for Ethiopian-specific identifiers
    """
    
    # Patterns for PII detection
    PATTERNS = {
        PIICategory.PHONE_NUMBER: re.compile(r'(09|07)\d{8}'),
        PIICategory.EMAIL: re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        PIICategory.TIN: re.compile(r'\b\d{10}\b'),  # Ethiopian TIN: 10 digits
        PIICategory.IP_ADDRESS: re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        PIICategory.CREDIT_CARD: re.compile(r'\b(?:\d[ -]*?){13,16}\b'),
        PIICategory.BANK_ACCOUNT: re.compile(r'\b\d{10,16}\b'),
        PIICategory.NATIONAL_ID: re.compile(r'\b[A-Z]{2}-\d{8}\b'),  # Ethiopian ID format
        PIICategory.DATE_OF_BIRTH: re.compile(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b|\b\d{4}-\d{2}-\d{2}\b'),
    }
    
    # Name patterns (simplified - detects common name patterns)
    NAME_PATTERN = re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b')
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._mask_char = "*"
        self._mask_length = 4  # Number of characters to keep visible at ends
    
    def detect(self, text: str) -> List[PIIMatch]:
        """
        Detect PII in text.
        
        Args:
            text: Text to scan for PII
            
        Returns:
            List of detected PII matches
        """
        if not self.enabled or not text:
            return []
        
        matches = []
        
        # Check each pattern
        for category, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                matches.append(PIIMatch(
                    category=category,
                    value=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.95,  # High confidence for pattern matches
                ))
        
        # Check for names (lower confidence)
        for match in self.NAME_PATTERN.finditer(text):
            # Skip if already matched as something else
            if not any(m.start_pos <= match.start() < m.end_pos for m in matches):
                matches.append(PIIMatch(
                    category=PIICategory.NAME,
                    value=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.7,  # Lower confidence for name detection
                ))
        
        # Sort by position
        matches.sort(key=lambda m: m.start_pos)
        
        # Merge overlapping matches
        merged = []
        for match in matches:
            if merged and match.start_pos <= merged[-1].end_pos:
                # Merge into previous match
                prev = merged[-1]
                if match.end_pos > prev.end_pos:
                    prev.end_pos = match.end_pos
                    prev.value = text[prev.start_pos:prev.end_pos]
            else:
                merged.append(match)
        
        return merged
    
    def mask(self, text: str, mask_char: str = "*", keep_ends: int = 2) -> str:
        """
        Mask PII in text.
        
        Args:
            text: Text containing PII
            mask_char: Character to use for masking
            keep_ends: Number of characters to keep visible at ends
            
        Returns:
            Text with PII masked
        """
        if not self.enabled or not text:
            return text
        
        self._mask_char = mask_char
        self._mask_length = keep_ends
        
        matches = self.detect(text)
        
        if not matches:
            return text
        
        # Build masked text from end to start to preserve indices
        result = text
        for match in reversed(matches):
            masked = self._mask_value(match.value, keep_ends, mask_char)
            result = result[:match.start_pos] + masked + result[match.end_pos:]
        
        return result
    
    def _mask_value(self, value: str, keep_ends: int, mask_char: str) -> str:
        """Mask a single PII value."""
        if len(value) <= keep_ends * 2:
            return mask_char * len(value)
        
        start = value[:keep_ends]
        end = value[-keep_ends:]
        middle_length = len(value) - (keep_ends * 2)
        
        return start + (mask_char * middle_length) + end
    
    def redact(self, text: str) -> str:
        """
        Completely redact PII (replace with [REDACTED]).
        
        Args:
            text: Text containing PII
            
        Returns:
            Text with PII redacted
        """
        if not self.enabled or not text:
            return text
        
        matches = self.detect(text)
        
        if not matches:
            return text
        
        result = text
        for match in reversed(matches):
            result = result[:match.start_pos] + "[REDACTED]" + result[match.end_pos:]
        
        return result
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for PII and return summary.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with PII analysis summary
        """
        matches = self.detect(text)
        
        categories = {}
        for match in matches:
            if match.category not in categories:
                categories[match.category] = 0
            categories[match.category] += 1
        
        return {
            "total_pii_found": len(matches),
            "categories": {k.value: v for k, v in categories.items()},
            "has_pii": len(matches) > 0,
            "text_length": len(text),
        }
    
    def is_safe_for_logging(self, text: str) -> bool:
        """Check if text is safe to log (contains no PII)."""
        matches = self.detect(text)
        return len(matches) == 0
    
    def get_log_safe_version(self, text: str) -> str:
        """Get version of text safe for logging (with PII masked)."""
        if self.is_safe_for_logging(text):
            return text
        return self.mask(text, keep_ends=1)


# Global PII masker instance
pii_masker = PIIMasker()


def mask_pii(text: str, keep_ends: int = 2) -> str:
    """Convenience function to mask PII in text."""
    return pii_masker.mask(text, keep_ends=keep_ends)


def detect_pii(text: str) -> List[PIIMatch]:
    """Convenience function to detect PII in text."""
    return pii_masker.detect(text)


def redact_pii(text: str) -> str:
    """Convenience function to redact PII from text."""
    return pii_masker.redact(text)


class PIIContextManager:
    """Context manager for temporarily handling PII."""
    
    def __init__(self, text: str, mask: bool = True):
        self.text = text
        self.mask = mask
        self._original = text
        self._processed = None
    
    def __enter__(self):
        if self.mask:
            self._processed = pii_masker.mask(self.text)
        else:
            self._processed = pii_masker.redact(self.text)
        return self._processed
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


__all__ = [
    "PIIMasker",
    "PIICategory",
    "PIIMatch",
    "pii_masker",
    "mask_pii",
    "detect_pii",
    "redact_pii",
    "PIIContextManager",
]