# ============================
# WOLLOYEWA STORE BOT - CONSTANTS
# ============================
"""Application-wide constants and enums."""

from enum import Enum, IntEnum
from typing import Dict, List, Tuple


# ============================
# User Related Constants
# ============================

class UserRole(str, Enum):
    """User role enumeration."""
    CUSTOMER = "customer"
    VENDOR = "vendor"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"


class Gender(str, Enum):
    """User gender."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


# ============================
# Product Related Constants
# ============================

class ProductStatus(str, Enum):
    """Product status."""
    DRAFT = "draft"
    ACTIVE = "active"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class ProductCategory(str, Enum):
    """Product categories."""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    FOOD = "food"
    BOOKS = "books"
    BEAUTY = "beauty"
    HEALTH = "health"
    HOME = "home"
    SPORTS = "sports"
    TOYS = "toys"
    OTHER = "other"


# Category display names in Amharic
CATEGORY_NAMES_AMHARIC: Dict[ProductCategory, str] = {
    ProductCategory.ELECTRONICS: "ኤሌክትሮኒክስ",
    ProductCategory.CLOTHING: "አልባሳት",
    ProductCategory.FOOD: "ምግብ",
    ProductCategory.BOOKS: "መጽሐፍት",
    ProductCategory.BEAUTY: "ውበት",
    ProductCategory.HEALTH: "ጤና",
    ProductCategory.HOME: "ቤት",
    ProductCategory.SPORTS: "ስፖርት",
    ProductCategory.TOYS: "መጫወቻ",
    ProductCategory.OTHER: "ሌላ",
}


# ============================
# Order Related Constants
# ============================

class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIAL = "partial"


class PaymentMethod(str, Enum):
    """Payment methods."""
    CHAPA = "chapa"
    TELEBIRR = "telebirr"
    CBE_BIRR = "cbe_birr"
    CASH_ON_DELIVERY = "cash_on_delivery"


class ShippingMethod(str, Enum):
    """Shipping methods."""
    STANDARD = "standard"
    EXPRESS = "express"
    PICKUP = "pickup"


# Order status flow (valid transitions)
ORDER_STATUS_FLOW: Dict[OrderStatus, List[OrderStatus]] = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
    OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
    OrderStatus.DELIVERED: [OrderStatus.REFUNDED],
    OrderStatus.CANCELLED: [],
    OrderStatus.REFUNDED: [],
}


# ============================
# Notification Types
# ============================

class NotificationType(str, Enum):
    """Notification types."""
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    PUSH = "push"


class NotificationEvent(str, Enum):
    """Notification events."""
    ORDER_CREATED = "order_created"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    ORDER_CANCELLED = "order_cancelled"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    PRODUCT_BACK_IN_STOCK = "product_back_in_stock"
    PRICE_DROP = "price_drop"
    NEW_PRODUCT = "new_product"
    PROMOTION = "promotion"
    WELCOME = "welcome"
    VERIFICATION = "verification"


# ============================
# Cache Keys
# ============================

class CacheKey:
    """Redis cache key constants."""
    
    USER_PREFIX = "user:"
    PRODUCT_PREFIX = "product:"
    ORDER_PREFIX = "order:"
    VENDOR_PREFIX = "vendor:"
    SESSION_PREFIX = "session:"
    RATE_LIMIT_PREFIX = "rate_limit:"
    
    @classmethod
    def user(cls, user_id: int) -> str:
        return f"{cls.USER_PREFIX}{user_id}"
    
    @classmethod
    def user_by_telegram(cls, telegram_id: int) -> str:
        return f"{cls.USER_PREFIX}telegram:{telegram_id}"
    
    @classmethod
    def product(cls, product_id: int) -> str:
        return f"{cls.PRODUCT_PREFIX}{product_id}"
    
    @classmethod
    def order(cls, order_id: int) -> str:
        return f"{cls.ORDER_PREFIX}{order_id}"
    
    @classmethod
    def vendor(cls, vendor_id: int) -> str:
        return f"{cls.VENDOR_PREFIX}{vendor_id}"
    
    @classmethod
    def session(cls, session_id: str) -> str:
        return f"{cls.SESSION_PREFIX}{session_id}"
    
    @classmethod
    def rate_limit(cls, key: str) -> str:
        return f"{cls.RATE_LIMIT_PREFIX}{key}"


# ============================
# Pagination
# ============================

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100
DEFAULT_PAGE: int = 1


# ============================
# Ethiopian Calendar
# ============================

ETHIOPIAN_MONTHS: List[str] = [
    "መስከረም", "ጥቅምት", "ህዳር", "ታህሳስ", "ጥር", "የካቲት",
    "መጋቢት", "ሚያዝያ", "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜ"
]

ETHIOPIAN_WEEKDAYS: List[str] = [
    "እሑድ", "ሰኞ", "ማክሰኞ", "ረቡዕ", "ሐሙስ", "አርብ", "ቅዳሜ"
]


# ============================
# Currency
# ============================

CURRENCY_CODE: str = "ETB"
CURRENCY_SYMBOL: str = "ብር"
CURRENCY_SUBUNIT: str = "ሳንቲም"
CURRENCY_SUBUNIT_VALUE: int = 100


# ============================
# Timeouts & Limits
# ============================

CART_EXPIRY_HOURS: int = 24
ORDER_PENDING_TIMEOUT_MINUTES: int = 30
OTP_EXPIRY_MINUTES: int = 5
SESSION_TIMEOUT_MINUTES: int = 30
MAX_LOGIN_ATTEMPTS: int = 5
LOGIN_LOCKOUT_MINUTES: int = 15


# ============================
# File Upload Limits
# ============================

MAX_IMAGE_SIZE_MB: int = 5
MAX_IMAGE_SIZE_BYTES: int = MAX_IMAGE_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
MAX_PRODUCT_IMAGES: int = 10
MAX_REVIEW_IMAGES: int = 5


# ============================
# Regular Expressions
# ============================

# Ethiopian phone number pattern (09XXXXXXXX or 07XXXXXXXX)
PHONE_PATTERN: str = r"^(09|07)\d{8}$"

# Ethiopian TIN pattern (10 digits)
TIN_PATTERN: str = r"^\d{10}$"

# Business license pattern
LICENSE_PATTERN: str = r"^[A-Z0-9]{6,20}$"

# Email pattern
EMAIL_PATTERN: str = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


# ============================
# API Related
# ============================

API_VERSION: str = "v1"
API_PREFIX: str = f"/api/{API_VERSION}"

# Rate limiting defaults
RATE_LIMIT_DEFAULT: str = "60/minute"
RATE_LIMIT_STRICT: str = "10/minute"
RATE_LIMIT_LOGIN: str = "5/minute"
RATE_LIMIT_PAYMENT: str = "3/minute"


# ============================
# Ethiopia Specific
# ============================

ETHIOPIAN_REGIONS: List[str] = [
    "Addis Ababa",
    "Afar",
    "Amhara",
    "Benishangul-Gumuz",
    "Central Ethiopia",
    "Dire Dawa",
    "Gambela",
    "Harari",
    "Oromia",
    "Sidama",
    "Somali",
    "South Ethiopia",
    "South West Ethiopia",
    "Tigray",
]

ETHIOPIAN_REGIONS_AMHARIC: Dict[str, str] = {
    "Addis Ababa": "አዲስ አበባ",
    "Afar": "አፋር",
    "Amhara": "አማራ",
    "Benishangul-Gumuz": "ቤንሻንጉል-ጉሙዝ",
    "Dire Dawa": "ድሬ ዳዋ",
    "Gambela": "ጋምቤላ",
    "Harari": "ሐረሪ",
    "Oromia": "ኦሮሚያ",
    "Sidama": "ሲዳማ",
    "Somali": "ሶማሌ",
    "Tigray": "ትግራይ",
}


# ============================
# Message Templates
# ============================

class MessageTemplate:
    """Telegram message templates."""
    
    WELCOME = """
🌟 እንኳን ደህና መጡ ወደ *Wolloyewa Store*! 🌟

የኢትዮጵያ የመጀመሪያው ዘመናዊ የኢ-ኮሜርስ ቴሌግራም ቦት።

✨ ባህሪያት:
• 🛍️ ምርቶችን ይመልከቱ እና ይግዙ
• 💳 በቀላሉ ይክፈሉ (Chapa፣ Telebirr፣ CBE Birr)
• 📦 ትዕዛዞትን ይከታተሉ
• ⭐ ግምገማ ያስቀምጡ

ለመጀመር /menu ይጫኑ
    """
    
    PRODUCT_LIST = """
📦 *{category}* - {page}/{total_pages}

{products}

🔍 ለመፈለግ /search ይጫኑ
📖 ተጨማሪ ለማየት የታችኛውን ቁልፍ ይጫኑ
    """
    
    CART = """
🛒 *የግዢ ቅርጫትዎ*

{items}

─────────────────
💰 *ድምር*: {total} ብር

/checkout - ግዢውን ለማጠናቀቅ
/clear_cart - ቅርጫቱን ለማጥፋት
    """
    
    ORDER_CONFIRMATION = """
✅ *ትዕዛዝ ተረጋግጧል!*

🆔 ትዕዛዝ ቁጥር: `{order_number}`
💰 ጠቅላላ: {total} ብር
📦 አቅርቦት: {shipping_method}
💳 ክፍያ: {payment_method}

ትዕዛዝዎን ለመከታተል /my_orders ይጫኑ
    """