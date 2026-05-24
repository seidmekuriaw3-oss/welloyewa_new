# ============================
# WOLLOYEWA STORE BOT - REQUEST VALIDATOR
# ============================
"""Request validation and sanitization for API gateway."""

import re
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

from core.logger import logger


class ValidationType(str, Enum):
    """Types of validation rules."""
    REQUIRED = "required"
    TYPE = "type"
    MIN = "min"
    MAX = "max"
    PATTERN = "pattern"
    LENGTH = "length"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    UUID = "uuid"
    ENUM = "enum"
    CUSTOM = "custom"


@dataclass
class ValidationRule:
    """Validation rule definition."""
    
    field: str
    rule_type: ValidationType
    value: Any = None
    message: Optional[str] = None
    condition: Optional[Callable] = None


class RequestValidator:
    """
    Request validator for API endpoints.
    
    Features:
    - Field validation rules
    - Type checking
    - Pattern matching
    - Custom validation functions
    - Detailed error reporting
    """
    
    def __init__(self):
        self._rules: Dict[str, List[ValidationRule]] = {}
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule."""
        if rule.field not in self._rules:
            self._rules[rule.field] = []
        self._rules[rule.field].append(rule)
    
    def add_rules(self, rules: List[ValidationRule]) -> None:
        """Add multiple validation rules."""
        for rule in rules:
            self.add_rule(rule)
    
    def validate(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Validate data against rules.
        
        Args:
            data: Data to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        for field, rules in self._rules.items():
            value = data.get(field)
            
            for rule in rules:
                error = self._validate_rule(field, value, rule)
                if error:
                    errors.append(error)
        
        return errors
    
    def _validate_rule(
        self,
        field: str,
        value: Any,
        rule: ValidationRule,
    ) -> Optional[Dict[str, str]]:
        """Validate a single rule."""
        message = rule.message or f"Validation failed for field '{field}'"
        
        if rule.rule_type == ValidationType.REQUIRED:
            if value is None or (isinstance(value, str) and not value.strip()):
                return {"field": field, "message": message}
        
        if value is None:
            return None
        
        if rule.rule_type == ValidationType.TYPE:
            expected_type = rule.value
            if not isinstance(value, expected_type):
                return {"field": field, "message": message}
        
        elif rule.rule_type == ValidationType.MIN:
            if isinstance(value, (int, float)):
                if value < rule.value:
                    return {"field": field, "message": message}
            elif isinstance(value, str):
                if len(value) < rule.value:
                    return {"field": field, "message": message}
            elif isinstance(value, list):
                if len(value) < rule.value:
                    return {"field": field, "message": message}
        
        elif rule.rule_type == ValidationType.MAX:
            if isinstance(value, (int, float)):
                if value > rule.value:
                    return {"field": field, "message": message}
            elif isinstance(value, str):
                if len(value) > rule.value:
                    return {"field": field, "message": message}
            elif isinstance(value, list):
                if len(value) > rule.value:
                    return {"field": field, "message": message}
        
        elif rule.rule_type == ValidationType.PATTERN:
            if not re.match(rule.value, str(value)):
                return {"field": field, "message": message}
        
        elif rule.rule_type == ValidationType.LENGTH:
            if len(str(value)) != rule.value:
                return {"field": field, "message": message}
        
        elif rule.rule_type == ValidationType.EMAIL:
            if not self._is_valid_email(str(value)):
                return {"field": field, "message": message}
        
        elif rule.rule_type == ValidationType.PHONE:
            if not self._is_valid_phone(str(value)):
                return {"field": field, "message": message}
        
        elif rule.rule_type == ValidationType.URL:
            if not self._is_valid_url(str(value)):
                return {"field": field, "message": message}
        
        elif rule.rule_type == ValidationType.UUID:
            if not self._is_valid_uuid(str(value)):
                return {"field": field, "message": message}
        
        elif rule.rule_type == ValidationType.ENUM:
            if value not in rule.value:
                return {"field": field, "message": message}
        
        elif rule.rule_type == ValidationType.CUSTOM:
            if rule.condition and not rule.condition(value):
                return {"field": field, "message": message}
        
        return None
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Validate Ethiopian phone number."""
        pattern = r'^(09|07)\d{8}$'
        return bool(re.match(pattern, re.sub(r'\D', '', phone)))
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        pattern = r'^(https?://)?([\da-z\.-]+)\.([a-z\.]{2,6})([/\w \.-]*)*/?$'
        return bool(re.match(pattern, url))
    
    def _is_valid_uuid(self, uuid_str: str) -> bool:
        """Validate UUID format."""
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(pattern, uuid_str.lower()))


def sanitize_request(data: Dict[str, Any], allowed_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Sanitize request data.
    
    Args:
        data: Request data
        allowed_fields: List of allowed fields (if None, all fields allowed)
        
    Returns:
        Sanitized data
    """
    sanitized = {}
    
    for key, value in data.items():
        # Check if field is allowed
        if allowed_fields and key not in allowed_fields:
            continue
        
        # Sanitize string values
        if isinstance(value, str):
            # Remove leading/trailing spaces
            value = value.strip()
            
            # Escape HTML
            value = value.replace('&', '&amp;')
            value = value.replace('<', '&lt;')
            value = value.replace('>', '&gt;')
            value = value.replace('"', '&quot;')
            value = value.replace("'", '&#39;')
        
        # Recursively sanitize nested structures
        elif isinstance(value, dict):
            value = sanitize_request(value, allowed_fields=None)
        
        elif isinstance(value, list):
            value = [sanitize_request(v, allowed_fields=None) if isinstance(v, dict) else v for v in value]
        
        sanitized[key] = value
    
    return sanitized


async def validate_request(data: Dict[str, Any], rules: List[ValidationRule]) -> tuple[bool, List[Dict[str, str]]]:
    """
    Validate request data against rules.
    
    Args:
        data: Request data
        rules: Validation rules
        
    Returns:
        Tuple of (is_valid, errors)
    """
    validator = RequestValidator()
    validator.add_rules(rules)
    errors = validator.validate(data)
    return len(errors) == 0, errors


__all__ = [
    "RequestValidator",
    "ValidationRule",
    "ValidationType",
    "sanitize_request",
    "validate_request",
]