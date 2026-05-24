# ============================
# WOLLOYEWA STORE BOT - UTILITY TESTS
# ============================
"""Unit tests for utility functions."""

import pytest
from decimal import Decimal
from datetime import datetime, date


@pytest.mark.unit
class TestCurrencyUtils:
    """Tests for currency utilities."""
    
    def test_format_currency(self):
        """Test currency formatting."""
        from core.utils.currency import format_currency, format_etb
        
        result = format_currency(1000.50, symbol="ብር")
        assert "1000.50" in result
        assert "ብር" in result
        
        result = format_etb(1500.75)
        assert "1500.75" in result
    
    def test_calculate_tax(self):
        """Test tax calculation."""
        from core.utils.currency import calculate_tax, add_tax
        
        tax = calculate_tax(Decimal("100.00"))
        assert tax == Decimal("13.04")  # 100 - (100/1.15)
        
        total = add_tax(Decimal("100.00"))
        assert total == Decimal("115.00")
    
    def test_calculate_discount(self):
        """Test discount calculation."""
        from core.utils.currency import calculate_discount, calculate_discount_percent
        
        discounted = calculate_discount(Decimal("100.00"), discount_percent=10)
        assert discounted == Decimal("90.00")
        
        discounted = calculate_discount(Decimal("100.00"), discount_amount=Decimal("15.00"))
        assert discounted == Decimal("85.00")
        
        percent = calculate_discount_percent(Decimal("100.00"), Decimal("80.00"))
        assert percent == Decimal("20.00")
    
    def test_calculate_subtotal(self):
        """Test subtotal calculation."""
        from core.utils.currency import calculate_subtotal
        
        items = [
            {"price": 100, "quantity": 2},
            {"price": 50, "quantity": 3},
        ]
        subtotal = calculate_subtotal(items)
        assert subtotal == Decimal("350.00")
    
    def test_currency_converter(self):
        """Test currency conversion."""
        from core.utils.currency import CurrencyConverter
        
        converter = CurrencyConverter()
        # Test rate exists
        rate = converter.get_rate("ETB", "USD")
        assert rate is not None
        
        # Test conversion
        converted = converter.convert(Decimal("100"), "USD", "ETB")
        assert converted >= Decimal("0")


@pytest.mark.unit
class TestStringUtils:
    """Tests for string utilities."""
    
    def test_slugify(self):
        """Test slug generation."""
        from core.utils.string_utils import slugify
        
        result = slugify("Hello World!")
        assert result == "hello-world"
        
        result = slugify("ሰላም ሰላም")
        assert result == "" or result is not None
    
    def test_truncate_string(self):
        """Test string truncation."""
        from core.utils.string_utils import truncate_string
        
        result = truncate_string("This is a very long string", 10)
        assert len(result) <= 13  # 10 + 3 for "..."
        assert result.endswith("...")
    
    def test_generate_random_string(self):
        """Test random string generation."""
        from core.utils.string_utils import generate_random_string
        
        result = generate_random_string(10)
        assert len(result) == 10
        
        result = generate_random_string(8, include_digits=True, uppercase=True, lowercase=False)
        assert result.isupper() or any(c.isdigit() for c in result)
    
    def test_generate_order_number(self):
        """Test order number generation."""
        from core.utils.string_utils import generate_order_number
        
        result = generate_order_number()
        assert result.startswith("ORD-")
        assert len(result) > 10
    
    def test_strip_html(self):
        """Test HTML stripping."""
        from core.utils.string_utils import strip_html
        
        result = strip_html("<p>Hello <strong>World</strong></p>")
        assert result == "Hello World"
    
    def test_extract_mentions(self):
        """Test mention extraction."""
        from core.utils.string_utils import extract_mentions
        
        result = extract_mentions("Hello @user1 and @user2")
        assert result == ["user1", "user2"]
    
    def test_mask_email(self):
        """Test email masking."""
        from core.utils.string_utils import mask_email
        
        result = mask_email("testuser@example.com")
        assert "@" in result
        assert "testuser" not in result
    
    def test_mask_phone(self):
        """Test phone number masking."""
        from core.utils.string_utils import mask_phone
        
        result = mask_phone("0912345678")
        assert result != "0912345678"
        assert "******" in result


@pytest.mark.unit
class TestValidators:
    """Tests for validator functions."""
    
    def test_validate_phone(self):
        """Test phone number validation."""
        from core.utils.validators import validate_phone
        
        is_valid, _ = validate_phone("0912345678")
        assert is_valid is True
        
        is_valid, _ = validate_phone("12345678")
        assert is_valid is False
    
    def test_validate_email(self):
        """Test email validation."""
        from core.utils.validators import validate_email
        
        is_valid, _ = validate_email("test@example.com")
        assert is_valid is True
        
        is_valid, _ = validate_email("invalid-email")
        assert is_valid is False
    
    def test_validate_ethiopian_tin(self):
        """Test Ethiopian TIN validation."""
        from core.utils.validators import validate_ethiopian_tin
        
        is_valid = validate_ethiopian_tin("1234567890")
        assert is_valid is True
        
        is_valid = validate_ethiopian_tin("12345")
        assert is_valid is False
    
    def test_validate_password_strength(self):
        """Test password strength validation."""
        from core.utils.validators import validate_password_strength
        
        is_valid, issues = validate_password_strength("Weak")
        assert is_valid is False
        assert len(issues) > 0
        
        is_valid, issues = validate_password_strength("StrongP@ss123")
        assert is_valid is True
    
    def test_sanitize_string(self):
        """Test string sanitization."""
        from core.utils.validators import sanitize_string
        
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
    
    def test_is_valid_uuid(self):
        """Test UUID validation."""
        from core.utils.validators import is_valid_uuid
        
        import uuid
        valid_uuid = str(uuid.uuid4())
        assert is_valid_uuid(valid_uuid) is True
        
        assert is_valid_uuid("not-a-uuid") is False


@pytest.mark.unit
class TestDateHelpers:
    """Tests for date helper functions."""
    
    def test_format_date(self):
        """Test date formatting."""
        from core.utils.date_helpers import format_date
        
        result = format_date(datetime(2024, 1, 15))
        assert result is not None
    
    def test_time_ago(self):
        """Test time ago calculation."""
        from core.utils.date_helpers import time_ago
        from datetime import datetime, timedelta
        
        past_time = datetime.utcnow() - timedelta(hours=2)
        result = time_ago(past_time)
        assert "2" in result
    
    def test_days_between(self):
        """Test days between calculation."""
        from core.utils.date_helpers import DateHelper
        
        start = date(2024, 1, 1)
        end = date(2024, 1, 10)
        days = DateHelper.days_between(start, end)
        assert days == 9


__all__ = [
    "TestCurrencyUtils",
    "TestStringUtils",
    "TestValidators",
    "TestDateHelpers",
]