# ============================
# WOLLOYEWA STORE BOT - SECURITY TESTS
# ============================
"""Unit tests for security utilities."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


@pytest.mark.unit
class TestPasswordHashing:
    """Tests for password hashing utilities."""
    
    def test_hash_password(self):
        """Test password hashing."""
        from core.security import hash_password, verify_password
        
        password = "test_password123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 20
        
        # Verify correct password
        assert verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert verify_password("wrong_password", hashed) is False
    
    def test_verify_password_with_invalid_hash(self):
        """Test password verification with invalid hash."""
        from core.security import verify_password
        
        result = verify_password("password", "invalid_hash")
        assert result is False


@pytest.mark.unit
class TestJWTToken:
    """Tests for JWT token utilities."""
    
    def test_create_access_token(self):
        """Test JWT access token creation."""
        from core.security import create_access_token, verify_token
        
        data = {"sub": "123", "role": "customer"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 20
    
    def test_verify_valid_token(self):
        """Test JWT token verification with valid token."""
        from core.security import create_access_token, verify_token
        
        data = {"sub": "123", "role": "customer"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["role"] == "customer"
    
    def test_verify_invalid_token(self):
        """Test JWT token verification with invalid token."""
        from core.security import verify_token
        
        payload = verify_token("invalid_token")
        assert payload is None
    
    def test_verify_expired_token(self):
        """Test JWT token verification with expired token."""
        from core.security import create_access_token, verify_token
        from datetime import timedelta
        
        data = {"sub": "123"}
        # Create token with very short expiry
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        payload = verify_token(token)
        assert payload is None


@pytest.mark.unit
class TestOTPGeneration:
    """Tests for OTP generation."""
    
    def test_generate_otp(self):
        """Test OTP generation."""
        from core.security import generate_otp
        
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()
        
        otp = generate_otp(4)
        assert len(otp) == 4
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        from core.security import generate_secure_token
        
        token = generate_secure_token()
        assert len(token) >= 32
        
        token = generate_secure_token(16)
        assert len(token) >= 16


@pytest.mark.unit
class TestEncryption:
    """Tests for encryption utilities."""
    
    def test_encrypt_decrypt_data(self):
        """Test data encryption and decryption."""
        from core.security import encrypt_data, decrypt_data
        
        original = "sensitive_data_123"
        encrypted = encrypt_data(original)
        
        assert encrypted != original
        assert isinstance(encrypted, str)
        
        decrypted = decrypt_data(encrypted)
        assert decrypted == original
    
    def test_encrypt_invalid_data(self):
        """Test encryption with invalid data."""
        from core.security import encrypt_data
        
        with pytest.raises(Exception):
            encrypt_data(None)


@pytest.mark.unit
class TestInputSanitization:
    """Tests for input sanitization."""
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        from core.security import sanitize_input
        
        malicious = "<script>alert('xss')</script>"
        sanitized = sanitize_input(malicious)
        
        assert "<script>" not in sanitized
        assert "alert" not in sanitized
    
    def test_validate_phone_number(self):
        """Test phone number validation."""
        from core.security import validate_phone_number
        
        assert validate_phone_number("0912345678") is True
        assert validate_phone_number("0712345678") is True
        assert validate_phone_number("12345678") is False
        assert validate_phone_number("") is False
    
    def test_validate_email(self):
        """Test email validation."""
        from core.security import validate_email
        
        assert validate_email("test@example.com") is True
        assert validate_email("invalid-email") is False
        assert validate_email("") is False


@pytest.mark.unit
class TestDataMasking:
    """Tests for data masking utilities."""
    
    def test_mask_sensitive_data(self):
        """Test sensitive data masking."""
        from core.security import mask_sensitive_data
        
        result = mask_sensitive_data("1234567890", visible_start=2, visible_end=2)
        assert result == "12******90"
        
        result = mask_sensitive_data("abc", visible_start=1, visible_end=1)
        assert result == "a*c" or result == "***"
    
    def test_hash_telegram_id(self):
        """Test Telegram ID hashing."""
        from core.security import hash_telegram_id
        
        hashed = hash_telegram_id(123456789)
        assert len(hashed) == 64  # SHA-256 hex digest
        assert hashed.isalnum()


@pytest.mark.unit
class TestCSRFProtection:
    """Tests for CSRF protection utilities."""
    
    def test_generate_csrf_token(self):
        """Test CSRF token generation."""
        from core.security import generate_csrf_token
        
        token = generate_csrf_token()
        assert len(token) >= 32
    
    def test_verify_csrf_token(self):
        """Test CSRF token verification."""
        from core.security import generate_csrf_token, verify_csrf_token
        
        token = generate_csrf_token()
        assert verify_csrf_token(token, token) is True
        assert verify_csrf_token("invalid", token) is False


@pytest.mark.unit
class TestSecurityHeaders:
    """Tests for security headers."""
    
    def test_security_headers(self):
        """Test security headers generation."""
        from core.security import SecurityHeaders
        
        headers = SecurityHeaders.get_headers()
        
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"


@pytest.mark.unit
class TestWebhookVerification:
    """Tests for webhook verification."""
    
    def test_verify_telegram_webhook(self):
        """Test Telegram webhook verification."""
        from core.security import verify_telegram_webhook
        
        data = {"secret_token": "test_token"}
        assert verify_telegram_webhook(data, "test_token") is True
        assert verify_telegram_webhook(data, "wrong_token") is False
        assert verify_telegram_webhook({}, "test_token") is False


__all__ = [
    "TestPasswordHashing",
    "TestJWTToken",
    "TestOTPGeneration",
    "TestEncryption",
    "TestInputSanitization",
    "TestDataMasking",
    "TestCSRFProtection",
    "TestSecurityHeaders",
    "TestWebhookVerification",
]