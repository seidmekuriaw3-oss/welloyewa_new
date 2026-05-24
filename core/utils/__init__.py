# ============================
# WOLLOYEWA STORE BOT - CORE UTILITIES
# ============================
"""Utility modules for common operations."""

from core.utils.currency import (
    format_currency,
    convert_currency,
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
from core.utils.media_optimizer import (
    optimize_image,
    generate_thumbnail,
    get_image_dimensions,
    compress_image,
    MediaOptimizer,
)
from core.utils.pagination import (
    paginate,
    PaginationResult,
    Paginator,
)
from core.utils.date_helpers import (
    format_date,
    parse_date,
    get_current_ethiopian_date,
    convert_to_ethiopian_calendar,
    DateHelper,
)
from core.utils.string_utils import (
    slugify,
    truncate_string,
    generate_random_string,
    strip_html,
    extract_mentions,
)
from core.utils.ethiopian_calendar import (
    EthiopianCalendar,
    EthiopianDate,
    convert_to_gregorian,
    convert_to_ethiopian,
    get_ethiopian_holidays,
)

__all__ = [
    # Currency
    "format_currency",
    "convert_currency",
    "calculate_tax",
    "calculate_discount",
    "CurrencyConverter",
    # Validators
    "validate_phone",
    "validate_email",
    "validate_ethiopian_tin",
    "validate_business_license",
    "validate_password_strength",
    "sanitize_string",
    "is_valid_uuid",
    # Media
    "optimize_image",
    "generate_thumbnail",
    "get_image_dimensions",
    "compress_image",
    "MediaOptimizer",
    # Pagination
    "paginate",
    "PaginationResult",
    "Paginator",
    # Date Helpers
    "format_date",
    "parse_date",
    "get_current_ethiopian_date",
    "convert_to_ethiopian_calendar",
    "DateHelper",
    # String Utils
    "slugify",
    "truncate_string",
    "generate_random_string",
    "strip_html",
    "extract_mentions",
    # Ethiopian Calendar
    "EthiopianCalendar",
    "EthiopianDate",
    "convert_to_gregorian",
    "convert_to_ethiopian",
    "get_ethiopian_holidays",
]