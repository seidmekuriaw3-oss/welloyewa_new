from core.utils.currency import (
    CurrencyConverter,
    calculate_discount,
    calculate_tax,
    format_currency,
)
from core.utils.pagination import (
    PaginationResult,
    Paginator,
)
from core.utils.pagination import (
    paginate_list as paginate,
)
from core.utils.string_utils import (
    extract_mentions,
    generate_random_string,
    slugify,
    strip_html,
    truncate_string,
)
from core.utils.validators import (
    is_valid_uuid,
    sanitize_string,
    validate_business_license,
    validate_email,
    validate_ethiopian_tin,
    validate_password_strength,
    validate_phone,
)


def convert_currency(
    amount, from_currency: str = "ETB", to_currency: str = "ETB", rate: float = 1.0
):
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
    "CurrencyConverter",
    "DateHelper",
    "PaginationResult",
    "Paginator",
    "calculate_discount",
    "calculate_tax",
    "convert_currency",
    "convert_to_ethiopian_calendar",
    "extract_mentions",
    "format_currency",
    "format_date",
    "generate_random_string",
    "get_current_ethiopian_date",
    "is_valid_uuid",
    "paginate",
    "parse_date",
    "sanitize_string",
    "slugify",
    "strip_html",
    "truncate_string",
    "validate_business_license",
    "validate_email",
    "validate_ethiopian_tin",
    "validate_password_strength",
    "validate_phone",
]
