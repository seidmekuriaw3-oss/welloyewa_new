# ============================
# WOLLOYEWA STORE BOT - UTILITY TESTS
# ============================
"""Unit tests for utility functions."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest


@pytest.mark.unit
class TestCurrencyUtils:
    """Tests for currency utilities."""

    def test_format_currency(self):
        """Test currency formatting."""
        from core.utils.currency import format_currency, format_etb

        result = format_currency(1000.50, symbol="ብር")
        assert "1,000.50" in result
        assert "ብር" in result

        result = format_etb(1500.75)
        assert "1500.75" in result

    def test_calculate_tax(self):
        """Test tax calculation."""
        from core.utils.currency import add_tax, calculate_tax

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

    def test_string_extraction_and_formatting_helpers(self):
        """Test the remaining pure string transformation helpers."""
        from core.utils.string_utils import (
            capitalize_words,
            create_text_preview,
            escape_html,
            extract_emails,
            extract_hashtags,
            extract_phone_numbers,
            generate_hash,
            generate_transaction_id,
            mask_string,
            normalize_text,
            remove_extra_whitespace,
            to_camel_case,
            to_snake_case,
        )

        assert extract_hashtags("#shop #sale") == ["shop", "sale"]
        assert extract_emails("Contact a@example.com") == ["a@example.com"]
        assert extract_phone_numbers("Call 0912345678") == ["09"]
        assert mask_string("abcdefgh") == "ab****gh"
        assert escape_html('<b>"x"</b>') == "&lt;b&gt;&quot;x&quot;&lt;/b&gt;"
        assert capitalize_words("hello   world") == "Hello World"
        assert remove_extra_whitespace(" a\n\tb ") == "a b"
        assert normalize_text(" Hello, WORLD! ", remove_punctuation=True) == "hello world"
        assert create_text_preview("<b>Hello</b> world", 8) == "Hello..."
        assert generate_hash("hello", "sha256") == (
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )
        assert generate_transaction_id("PAY").startswith("PAY_")
        assert to_camel_case("hello_world") == "helloWorld"
        assert to_snake_case("helloWorld") == "hello_world"

    def test_string_validation_and_pluralization_helpers(self):
        """Test username, preview, and pluralization branches."""
        from core.utils.string_utils import (
            is_valid_telegram_username,
            is_valid_username,
            pluralize,
        )

        assert is_valid_username("shop_user") is True
        assert is_valid_username("x!") is False
        assert is_valid_telegram_username("@Store_1") is True
        assert is_valid_telegram_username("1store") is False
        assert pluralize("box", 2) == "boxes"
        assert pluralize("city", 2) == "cities"
        assert pluralize("item", 1) == "item"
        assert pluralize("ተማሪ", 2, language="am").endswith("ዎች")


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

        is_valid, normalized = validate_phone("+251 91 234 5678")
        assert is_valid is True
        assert normalized == "0912345678"

        is_valid, normalized = validate_phone("0912345678", normalize=False)
        assert is_valid is True
        assert normalized is None

    def test_validate_email(self):
        """Test email validation."""
        from core.utils.validators import validate_email

        is_valid, _ = validate_email("seidmekuriaw3@gmail.com")
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

    def test_validate_business_license_and_url(self):
        """Test business license and URL validation branches."""
        from core.utils.validators import validate_business_license, validate_url

        assert validate_business_license("ET123456") is True
        assert validate_business_license("bad") is False
        assert validate_url("https://example.com/path") is True
        assert validate_url("not a url") is False

        from core.utils.validators import validate_amount, validate_quantity

        assert validate_amount("12.50") is True
        assert validate_amount(-1) is False
        assert validate_quantity(3) is True
        assert validate_quantity(0) is False

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
        import uuid

        from core.utils.validators import is_valid_uuid

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
        from datetime import datetime, timedelta

        from core.utils.date_helpers import time_ago

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

    def test_parse_and_format_date_variants(self):
        """Test supported date and datetime input formats."""
        from core.utils.date_helpers import DateHelper, format_date, parse_date

        assert DateHelper.parse_date("2024-01-15") == date(2024, 1, 15)
        assert DateHelper.parse_date("15/01/2024") == date(2024, 1, 15)
        assert DateHelper.parse_date("invalid") is None
        assert DateHelper.parse_datetime("2024-01-15 12:30:00") == datetime(
            2024, 1, 15, 12, 30
        )
        assert DateHelper.parse_datetime("invalid") is None
        assert DateHelper.format_date(date(2024, 1, 15), locale="en") == "2024-01-15"
        assert format_date(date(2024, 1, 15), locale="en") == "2024-01-15"
        assert parse_date("2024-01-15") == date(2024, 1, 15)

    def test_timezone_conversion_for_naive_and_aware_values(self):
        """Test conversion of naive and timezone-aware datetimes."""
        import pytz

        from core.utils.date_helpers import DateHelper

        naive = datetime(2024, 1, 15, 9, 0)
        addis = DateHelper.to_addis(naive)
        utc = DateHelper.to_utc(naive)

        assert addis.tzinfo is not None
        assert utc.tzinfo == pytz.UTC
        assert addis.hour == 12
        assert utc.hour == 6

    def test_timedelta_and_period_boundaries(self):
        """Test human-readable durations and calendar period boundaries."""
        from core.utils.date_helpers import DateHelper

        assert "seconds" in DateHelper.format_timedelta(timedelta(seconds=5), "en")
        assert "minutes" in DateHelper.format_timedelta(timedelta(minutes=5), "en")
        assert "hours" in DateHelper.format_timedelta(timedelta(hours=5), "en")
        assert "days" in DateHelper.format_timedelta(timedelta(days=2), "en")

        value = date(2024, 5, 15)
        assert DateHelper.add_days(value, 3) == date(2024, 5, 18)
        assert DateHelper.start_of_day(value).hour == 0
        assert DateHelper.end_of_day(value).hour == 23
        assert DateHelper.start_of_week(value).date() == date(2024, 5, 13)
        assert DateHelper.start_of_month(value).date() == date(2024, 5, 1)
        assert DateHelper.start_of_year(value).date() == date(2024, 1, 1)

    def test_date_predicates_and_age(self, monkeypatch):
        """Test date predicates and age calculation against a fixed current date."""
        from core.utils.date_helpers import DateHelper

        fixed_today = date(2024, 5, 15)
        monkeypatch.setattr(DateHelper, "today", classmethod(lambda cls: fixed_today))

        assert DateHelper.is_today("2024-05-15") is True
        assert DateHelper.is_this_week("2024-05-13") is True
        assert DateHelper.is_this_month("2024-05-01") is True
        assert DateHelper.age("2000-06-01") == 23
        assert DateHelper.age("2000-05-01") == 24

    def test_invalid_date_type_raises(self):
        """Unsupported and unparseable date values should fail explicitly."""
        from core.utils.date_helpers import DateHelper

        with pytest.raises(ValueError):
            DateHelper.days_between("not-a-date", date.today())
        with pytest.raises(ValueError):
            DateHelper.days_between([], date.today())


@pytest.mark.unit
class TestEthiopianCalendar:
    """Tests for Ethiopian calendar conversion helpers."""

    def test_reference_conversion_and_date_properties(self):
        """The reference date should round-trip and expose calendar properties."""
        from core.utils.ethiopian_calendar import EthiopianDate, EthiopianCalendar

        reference = date(2007, 9, 11)
        et_date = EthiopianCalendar.from_gregorian(reference)

        assert et_date == EthiopianDate(2000, 1, 1)
        assert et_date.to_gregorian() == reference
        assert et_date.month_name
        assert et_date.is_pagume is False
        assert str(et_date).endswith("(ኢትዮጵያ)")
        assert "EthiopianDate" in repr(et_date)

    def test_leap_year_and_month_validation(self):
        """Leap Pagume dates are valid while invalid months and days are rejected."""
        from core.utils.ethiopian_calendar import EthiopianCalendar

        assert EthiopianCalendar.is_ethiopian_leap_year(2000) is True
        assert EthiopianCalendar.get_month_days(2000, 13) == 6
        assert EthiopianCalendar.get_month_days(2001, 13) == 5

        with pytest.raises(ValueError):
            EthiopianCalendar.get_month_days(2000, 14)
        with pytest.raises(ValueError):
            EthiopianCalendar.to_gregorian(2001, 13, 6)

    def test_calendar_arithmetic_and_holidays(self):
        """Test Ethiopian date arithmetic and holiday generation."""
        from core.utils.ethiopian_calendar import EthiopianCalendar, EthiopianDate

        value = EthiopianDate(2000, 12, 5)
        assert EthiopianCalendar.add_months(value, 1) == EthiopianDate(2000, 13, 5)
        assert EthiopianCalendar.add_months(value, 13) == EthiopianDate(2001, 12, 5)
        assert EthiopianCalendar.add_years(EthiopianDate(2000, 13, 6), 1) == EthiopianDate(
            2001, 13, 5
        )
        assert EthiopianCalendar.add_days(EthiopianDate(2000, 1, 1), 1) == EthiopianDate(
            2000, 1, 2
        )

        holidays = EthiopianCalendar.get_ethiopian_holidays(2017)
        assert holidays["Enkutatash (New Year)"] == EthiopianDate(2017, 1, 1)
        assert holidays["Fasika (Easter)"] == EthiopianDate(2017, 10, 15)

    def test_calendar_formatting_and_convenience_functions(self):
        """Convenience APIs should accept date, datetime, and ISO string inputs."""
        from core.utils.ethiopian_calendar import (
            EthiopianCalendar,
            EthiopianDate,
            convert_to_ethiopian,
            convert_to_gregorian,
            format_ethiopian_date,
            get_ethiopian_holidays,
        )

        expected = EthiopianDate(2000, 1, 1)
        assert convert_to_ethiopian("2007-09-11") == expected
        assert convert_to_ethiopian(datetime(2007, 9, 11)) == expected
        assert convert_to_gregorian(2000, 1, 1) == date(2007, 9, 11)
        assert format_ethiopian_date(expected).startswith("1 ")
        assert "፣" in EthiopianCalendar.format_ethiopian_date(expected, include_weekday=True)
        assert len(get_ethiopian_holidays(2017)) >= 10


__all__ = [
    "TestCurrencyUtils",
    "TestDateHelpers",
    "TestStringUtils",
    "TestValidators",
]
