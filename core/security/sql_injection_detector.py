# ============================
# WOLLOYEWA STORE BOT - SQL INJECTION DETECTOR
# ============================
"""SQL injection detection and prevention utilities."""

import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from core.logger import logger


class SQLInjectionRisk(str, Enum):
    """SQL injection risk levels."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SQLInjectionResult:
    """Result of SQL injection detection."""
    
    is_malicious: bool
    risk_level: SQLInjectionRisk
    patterns_detected: List[str]
    sanitized_input: str
    original_input: str


class SQLInjectionDetector:
    """
    SQL injection detection and prevention.
    
    Detects common SQL injection patterns and provides sanitization.
    """
    
    # Common SQL injection patterns
    SQL_PATTERNS = [
        # Basic SQL keywords
        (r'(?i)(\bSELECT\b.*\bFROM\b)', "SQL SELECT statement"),
        (r'(?i)(\bINSERT\b.*\bINTO\b)', "SQL INSERT statement"),
        (r'(?i)(\bUPDATE\b.*\bSET\b)', "SQL UPDATE statement"),
        (r'(?i)(\bDELETE\b.*\bFROM\b)', "SQL DELETE statement"),
        (r'(?i)(\bDROP\b.*\bTABLE\b)', "SQL DROP TABLE"),
        (r'(?i)(\bCREATE\b.*\bTABLE\b)', "SQL CREATE TABLE"),
        (r'(?i)(\bALTER\b.*\bTABLE\b)', "SQL ALTER TABLE"),
        (r'(?i)(\bTRUNCATE\b.*\bTABLE\b)', "SQL TRUNCATE TABLE"),
        
        # SQL operators
        (r'(?i)(\bOR\b.*=.*--)', "OR condition with comment"),
        (r'(?i)(\bAND\b.*=.*--)', "AND condition with comment"),
        (r'(?i)(\bUNION\b.*\bSELECT\b)', "UNION SELECT attack"),
        (r'(?i)(\bJOIN\b.*\bON\b)', "SQL JOIN with condition"),
        
        # Special characters and sequences
        (r"(';|;'|';|;'')", "Semicolon with quotes"),
        (r"(--|#|\/\*|\*\/)", "SQL comment markers"),
        (r"('.*\bor\b.*=.*')", "OR injection with quotes"),
        (r"('.*\band\b.*=.*')", "AND injection with quotes"),
        (r"(\b1=1\b|\b1=2\b|\btrue\b|\bfalse\b)", "Boolean injection"),
        (r"('.*\bunion\b.*\bselect\b.*')", "UNION injection with quotes"),
        
        # Function injection
        (r"(?i)(\bEXEC\b|\bEXECUTE\b)", "SQL EXEC execution"),
        (r"(?i)(\bxp_cmdshell\b)", "xp_cmdshell execution"),
        (r"(?i)(\bCAST\b|\bCONVERT\b)", "SQL type conversion"),
        (r"(?i)(\bWAITFOR\b.*\bDELAY\b)", "Time-based injection"),
        
        # Stacked queries
        (r"(;\s*\d+\s*;)", "Stacked query"),
        (r"('.*;.*')", "Stacked query with quotes"),
        
        # Authentication bypass
        (r"('.*\bor\b.*'='.*')", "Authentication bypass pattern 1"),
        (r"('.*\bor\b.*'.*'.*)", "Authentication bypass pattern 2"),
        (r"(\badmin\b.*\b--\b)", "Admin bypass with comment"),
    ]
    
    # Whitelist patterns that might look like SQL but are safe
    WHITELIST_PATTERNS = [
        r"^(SELECT|INSERT|UPDATE|DELETE)\s+\w+\s+FROM\s+\w+$",  # Simple SELECT statements for reports
        r"^\d{4}-\d{2}-\d{2}$",  # Date format
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",  # Email
        r"^09\d{8}$",  # Ethiopian phone
    ]
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._compiled_patterns = [
            (re.compile(pattern), description)
            for pattern, description in self.SQL_PATTERNS
        ]
        self._whitelist_compiled = [re.compile(p) for p in self.WHITELIST_PATTERNS]
    
    def detect(self, input_string: str) -> SQLInjectionResult:
        """
        Detect SQL injection in input string.
        
        Args:
            input_string: User input to check
            
        Returns:
            SQLInjectionResult with detection details
        """
        if not self.enabled or not input_string:
            return SQLInjectionResult(
                is_malicious=False,
                risk_level=SQLInjectionRisk.SAFE,
                patterns_detected=[],
                sanitized_input=input_string,
                original_input=input_string,
            )
        
        patterns_found = []
        risk_level = SQLInjectionRisk.SAFE
        
        # Check against whitelist first
        if self._is_whitelisted(input_string):
            return SQLInjectionResult(
                is_malicious=False,
                risk_level=SQLInjectionRisk.SAFE,
                patterns_detected=[],
                sanitized_input=input_string,
                original_input=input_string,
            )
        
        # Check for malicious patterns
        for pattern, description in self._compiled_patterns:
            if pattern.search(input_string):
                patterns_found.append(description)
                
                # Determine risk level
                if "DROP" in description or "DELETE" in description or "TRUNCATE" in description:
                    risk_level = max(risk_level, SQLInjectionRisk.CRITICAL)
                elif "SELECT" in description or "UNION" in description:
                    risk_level = max(risk_level, SQLInjectionRisk.HIGH)
                elif "OR" in description or "AND" in description:
                    risk_level = max(risk_level, SQLInjectionRisk.MEDIUM)
                else:
                    risk_level = max(risk_level, SQLInjectionRisk.LOW)
        
        is_malicious = len(patterns_found) > 0
        
        # Sanitize input
        sanitized = self.sanitize(input_string) if is_malicious else input_string
        
        if is_malicious:
            logger.warning(f"SQL injection detected: {patterns_found} in input: {input_string[:100]}")
        
        return SQLInjectionResult(
            is_malicious=is_malicious,
            risk_level=risk_level,
            patterns_detected=patterns_found,
            sanitized_input=sanitized,
            original_input=input_string,
        )
    
    def _is_whitelisted(self, input_string: str) -> bool:
        """Check if input matches whitelist patterns."""
        for pattern in self._whitelist_compiled:
            if pattern.match(input_string):
                return True
        return False
    
    def sanitize(self, input_string: str) -> str:
        """
        Sanitize input by escaping or removing dangerous characters.
        
        Args:
            input_string: Input to sanitize
            
        Returns:
            Sanitized string
        """
        if not input_string:
            return input_string
        
        # Remove common SQL injection patterns
        sanitized = input_string
        
        # Remove SQL comments
        sanitized = re.sub(r'--.*$', '', sanitized, flags=re.MULTILINE)
        sanitized = re.sub(r'#.*$', '', sanitized, flags=re.MULTILINE)
        sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)
        
        # Escape quotes
        sanitized = sanitized.replace("'", "''")
        sanitized = sanitized.replace('"', '""')
        
        # Remove semicolons (potential stacked queries)
        sanitized = sanitized.replace(';', '')
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    def validate_input(self, input_string: str, allow_sql: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate input and return if it's safe.
        
        Args:
            input_string: Input to validate
            allow_sql: Whether to allow SQL-like content
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not input_string:
            return True, None
        
        result = self.detect(input_string)
        
        if result.is_malicious and not allow_sql:
            return False, f"SQL injection detected: {', '.join(result.patterns_detected)}"
        
        return True, None


def detect_sql_injection(input_string: str) -> SQLInjectionResult:
    """Convenience function to detect SQL injection."""
    detector = SQLInjectionDetector()
    return detector.detect(input_string)


def sanitize_sql_input(input_string: str) -> str:
    """Convenience function to sanitize SQL input."""
    detector = SQLInjectionDetector()
    return detector.sanitize(input_string)


# Global detector instance
sql_injection_detector = SQLInjectionDetector()


__all__ = [
    "SQLInjectionDetector",
    "SQLInjectionResult",
    "SQLInjectionRisk",
    "detect_sql_injection",
    "sanitize_sql_input",
    "sql_injection_detector",
]