from core.utils.currency import (
    format_currency,
    calculate_tax,
    calculate_discount,
    CurrencyConverter,
)
from core.utils.validators import (
    validate_phone,
    validate_email,
    validate_ethiopian_tin,
    validate_business_license,
    validate_password_strength,
    sanitize_string,
    is_valid_uuid,
)
from core.utils.pagination import (
    PaginationResult,
    Paginator,
    paginate_list as paginate,
)
from core.utils.string_utils import (
    slugify,
    truncate_string,
    generate_random_string,
    strip_html,
    extract_mentions,
)


def convert_currency(amount, from_currency: str = "ETB", to_currency: str = "ETB", rate: float = 1.0):
    from decimal import Decimal
    return Decimal(str(amount)) * Decimal(str(rate))


def format_date(dt=None, locale: str = "am") -> str:
    from datetime import datetime
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_date(date_str: str):
    from datetime import datetime
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def get_current_ethiopian_date():
    from datetime import datetime
    now = datetime.utcnow()
    return now.year, now.month, now.day


def convert_to_ethiopian_calendar(gregorian_date):
    return gregorian_date


class DateHelper:
    @staticmethod
    def format(dt=None):
        return format_date(dt)


__all__ = [
    "format_currency",
    "convert_currency",
    "calculate_tax",
    "calculate_discount",
    "CurrencyConverter",
    "validate_phone",
    "validate_email",
    "validate_ethiopian_tin",
    "validate_business_license",
    "validate_password_strength",
    "sanitize_string",
    "is_valid_uuid",
    "paginate",
    "PaginationResult",
    "Paginator",
    "format_date",
    "parse_date",
    "get_current_ethiopian_date",
    "convert_to_ethiopian_calendar",
    "DateHelper",
    "slugify",
    "truncate_string",
    "generate_random_string",
    "strip_html",
    "extract_mentions",
]
