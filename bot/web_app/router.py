# ============================
# WOLLOYEWA STORE BOT - WEB APP ROUTER
# ============================
"""FastAPI router for the Telegram Mini App web interface."""

import asyncio
import json
import mimetypes
import os
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from pydantic import (
    ValidationError as PydanticValidationError,
)
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from telegram import Bot
from telegram.error import TelegramError

from apps.orders.services import OrderService
from apps.products.models import Product
from apps.products.services import ProductService
from apps.users.models import User, UserAddress, UserPreferences, Vendor, Wishlist
from apps.users.schemas import UserUpdate
from apps.users.services import UserService
from core.config import settings
from core.constants import ProductStatus
from core.dependencies import (
    get_current_admin,
    get_current_user,
    get_current_vendor,
    get_db_session,
    get_transaction_session,
)
from core.exceptions import InsufficientStockError, NotFoundError, ValidationError
from core.logger import logger
from core.security.telegram import verify_telegram_init_data
from core.utils.validators import Validator

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

web_app_router = APIRouter(prefix="/app", tags=["Web App"])
_telegram_bot_link_cache: str | None = None
_PROFILE_IMAGE_DIRECTORY = Path(__file__).parent / "private_uploads" / "profile_images"
_PROFILE_IMAGE_POINTER_PREFIX = "local-profile-image:"
_PROFILE_IMAGE_MAX_DIMENSION = 4096
_PROFILE_IMAGE_MAX_PIXELS = 16_777_216


def _profile_image_filename(profile_picture: str | None) -> str | None:
    if not isinstance(profile_picture, str) or not profile_picture.startswith(
        _PROFILE_IMAGE_POINTER_PREFIX
    ):
        return None

    filename = profile_picture.removeprefix(_PROFILE_IMAGE_POINTER_PREFIX)
    if (
        len(filename) != 37
        or not filename.endswith(".webp")
        or any(character not in "0123456789abcdef" for character in filename[:-5])
    ):
        return None
    return filename


def _profile_image_path(profile_picture: str | None) -> Path | None:
    filename = _profile_image_filename(profile_picture)
    if filename is None:
        return None

    directory = _PROFILE_IMAGE_DIRECTORY.resolve()
    path = directory / filename
    if path.parent.resolve() != directory:
        return None
    return path


def _write_private_profile_image(filename: str, image_data: bytes) -> Path:
    directory = _PROFILE_IMAGE_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        os.chmod(directory, 0o700)

    temporary_path = directory / f".{uuid4().hex}.tmp"
    target_path = directory / filename
    descriptor = os.open(
        temporary_path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as image_file:
            image_file.write(image_data)
        temporary_path.replace(target_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return target_path


def _normalize_uploaded_profile_image(image_data: bytes) -> bytes:
    """Validate a supported image and strip metadata by re-encoding to WebP."""
    import warnings

    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_data)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(
                        status_code=415,
                        detail="Choose a JPEG, PNG, or WebP image.",
                    )
                if (
                    image.width > _PROFILE_IMAGE_MAX_DIMENSION
                    or image.height > _PROFILE_IMAGE_MAX_DIMENSION
                    or image.width * image.height > _PROFILE_IMAGE_MAX_PIXELS
                ):
                    raise HTTPException(
                        status_code=413,
                        detail="Image dimensions must be 4096 pixels or smaller per side.",
                    )
                image.verify()

            with Image.open(BytesIO(image_data)) as image:
                normalized = ImageOps.exif_transpose(image)
                if normalized.mode not in {"RGB", "RGBA"}:
                    normalized = normalized.convert(
                        "RGBA" if "A" in normalized.getbands() else "RGB"
                    )
                normalized.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                output = BytesIO()
                normalized.save(output, format="WEBP", quality=88, method=6)
                return output.getvalue()
    except HTTPException:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=415,
            detail="The uploaded file is not a valid JPEG, PNG, or WebP image.",
        ) from exc


async def _remove_private_profile_image(profile_picture: str | None) -> None:
    path = _profile_image_path(profile_picture)
    if path is not None:
        await asyncio.to_thread(path.unlink, missing_ok=True)


class WebProfileUpdate(BaseModel):
    """Fields editable by the authenticated Web App profile form."""

    model_config = {"extra": "forbid"}

    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone_number: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    language: Literal["am", "en", "om"] | None = None
    notification_settings: dict[str, bool] | None = None
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    subcity: str | None = Field(None, max_length=100)
    woreda: str | None = Field(None, max_length=50)
    house_number: str | None = Field(None, max_length=50)
    landmark: str | None = Field(None, max_length=255)
    delete_address: bool = False

    @field_validator(
        "first_name",
        "last_name",
        "phone_number",
        "address_line1",
        "address_line2",
        "city",
        "subcity",
        "woreda",
        "house_number",
        "landmark",
        mode="before",
    )
    @classmethod
    def strip_optional_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("notification_settings")
    @classmethod
    def validate_notification_settings(cls, value):
        allowed = {
            "email_notifications",
            "sms_notifications",
            "push_notifications",
            "marketing_emails",
            "promotional_sms",
        }
        if value is not None and not set(value).issubset(allowed):
            raise ValueError("Unsupported notification preference.")
        return value

    @field_validator("first_name")
    @classmethod
    def require_first_name_when_supplied(cls, value):
        if value is None:
            raise ValueError("First name cannot be empty.")
        return value


class WebWishlistItem(BaseModel):
    """A product identifier for authenticated wishlist operations."""

    model_config = {"extra": "forbid"}

    product_id: int = Field(strict=True, gt=0)


class WebWishlistSync(BaseModel):
    """Legacy local wishlist IDs to import without trusting their display data."""

    model_config = {"extra": "forbid"}

    product_ids: list[Annotated[int, Field(strict=True, gt=0)]] = Field(
        default_factory=list, max_length=500
    )

    @field_validator("product_ids")
    @classmethod
    def validate_product_ids(cls, values: list[int]) -> list[int]:
        return list(dict.fromkeys(values))


class WebAddressCreate(BaseModel):
    """Address fields accepted by the authenticated account address book."""

    model_config = {"extra": "forbid"}

    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    subcity: str | None = Field(None, max_length=100)
    woreda: str | None = Field(None, max_length=50)
    house_number: str | None = Field(None, max_length=50)
    landmark: str | None = Field(None, max_length=255)
    recipient_name: str = Field(min_length=1, max_length=100)
    recipient_phone: str = Field(min_length=10, max_length=20)
    address_type: Literal["home", "work", "other"] = "home"
    is_default: bool = False

    @field_validator(
        "address_line1",
        "address_line2",
        "city",
        "subcity",
        "woreda",
        "house_number",
        "landmark",
        "recipient_name",
        mode="before",
    )
    @classmethod
    def strip_address_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("recipient_phone")
    @classmethod
    def normalize_recipient_phone(cls, value: str) -> str:
        normalized = Validator.phone(value, normalize=True)
        if not normalized:
            raise ValueError("Enter a valid Ethiopian phone number.")
        return normalized


class WebAddressUpdate(BaseModel):
    """Partial updates for a saved address owned by the authenticated user."""

    model_config = {"extra": "forbid"}

    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    subcity: str | None = Field(None, max_length=100)
    woreda: str | None = Field(None, max_length=50)
    house_number: str | None = Field(None, max_length=50)
    landmark: str | None = Field(None, max_length=255)
    recipient_name: str | None = Field(None, max_length=100)
    recipient_phone: str | None = Field(None, max_length=20)
    address_type: Literal["home", "work", "other"] | None = None
    is_default: bool | None = None

    @field_validator(
        "address_line1",
        "address_line2",
        "city",
        "subcity",
        "woreda",
        "house_number",
        "landmark",
        "recipient_name",
        mode="before",
    )
    @classmethod
    def strip_address_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("recipient_phone")
    @classmethod
    def normalize_recipient_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = Validator.phone(value, normalize=True)
        if not normalized:
            raise ValueError("Enter a valid Ethiopian phone number.")
        return normalized

    @model_validator(mode="after")
    def require_update_fields(self):
        if not self.model_fields_set:
            raise ValueError("At least one address field must be provided.")
        return self


class WebAdminProductCreate(BaseModel):
    """Fields required to create a catalog product from the admin panel."""

    vendor_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=255)
    name_am: str | None = Field(None, max_length=255)
    description: str | None = None
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    stock_quantity: int = Field(0, ge=0)
    sku: str = Field(min_length=1, max_length=100)
    category_id: int | None = Field(None, gt=0)

    @field_validator("name", "sku", mode="before")
    @classmethod
    def strip_required_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("name_am", "description", mode="before")
    @classmethod
    def strip_optional_text(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class WebVendorProductPayload(BaseModel):
    """Validated product fields submitted by a vendor in the Web App."""

    model_config = {"extra": "forbid"}

    name: str = Field(min_length=1, max_length=255)
    name_am: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=10000)
    category_id: int | None = Field(None, gt=0)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    compare_price: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    sku: str = Field(min_length=1, max_length=100)
    stock_quantity: int = Field(0, ge=0)

    @field_validator("name", "sku", mode="before")
    @classmethod
    def strip_required_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("name_am", "description", mode="before")
    @classmethod
    def strip_optional_text(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode="after")
    def compare_price_exceeds_price(self):
        if self.compare_price is not None and self.compare_price <= self.price:
            raise ValueError("Compare price must be greater than the selling price.")
        return self


class WebAdminProductUpdate(BaseModel):
    """Editable catalog fields exposed to admins."""

    model_config = {"extra": "forbid"}

    name: str | None = Field(None, min_length=1, max_length=255)
    name_am: str | None = Field(None, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    stock_quantity: int | None = Field(None, ge=0)
    sku: str | None = Field(None, min_length=1, max_length=100)
    category_id: int | None = Field(None, gt=0)

    @field_validator("name", "sku", mode="before")
    @classmethod
    def strip_optional_required_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class WebProductRejection(BaseModel):
    model_config = {"extra": "forbid"}

    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value):
        return value.strip() if isinstance(value, str) else value


class WebStoreSettingsUpdate(BaseModel):
    """Allowlisted, non-secret operational settings editable by store admins."""

    model_config = {"extra": "forbid"}

    store_open: bool | None = None
    enabled_payment_methods: list[Literal["chapa", "telebirr", "cbe", "cod"]] | None = None
    notification_settings: dict[str, bool] | None = None
    maintenance_message: str | None = Field(None, max_length=500)

    @field_validator("notification_settings")
    @classmethod
    def validate_notification_keys(cls, value):
        if value is not None:
            allowed = {"customer_orders", "vendor_updates", "admin_alerts", "support_updates"}
            unknown = set(value) - allowed
            if unknown:
                raise ValueError(f"Unknown notification settings: {', '.join(sorted(unknown))}")
        return value

    @field_validator("maintenance_message", mode="before")
    @classmethod
    def strip_maintenance_message(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class WebDiscountCreate(BaseModel):
    """Validated admin-managed coupon and product/category discount rule."""

    model_config = {"extra": "forbid"}

    code: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    discount_type: Literal["percentage", "fixed_amount"]
    discount_value: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    max_discount_amount: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    minimum_order_value: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    valid_from: datetime
    valid_to: datetime
    usage_limit: int | None = Field(None, gt=0)
    per_user_limit: int | None = Field(None, gt=0)
    scope: Literal["global", "category", "product"] = "global"
    scope_id: int | None = Field(None, gt=0)
    is_active: bool = True

    @field_validator("code", mode="before")
    @classmethod
    def normalize_discount_code(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("name", mode="before")
    @classmethod
    def normalize_discount_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_discount_description(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("valid_from", "valid_to")
    @classmethod
    def normalize_discount_dates(cls, value):
        zone = ZoneInfo(settings.TIMEZONE)
        if value.tzinfo is None:
            value = value.replace(tzinfo=zone)
        return value.astimezone(UTC).replace(tzinfo=None)

    @model_validator(mode="after")
    def validate_discount_rule(self):
        if self.valid_to <= self.valid_from:
            raise ValueError("Discount end must be after its start.")
        if self.scope == "global" and self.scope_id is not None:
            raise ValueError("Global discounts cannot include a scope ID.")
        if self.scope != "global" and self.scope_id is None:
            raise ValueError("Choose a category or product for this discount scope.")
        if self.discount_type == "percentage" and self.discount_value > 100:
            raise ValueError("Percentage discounts cannot exceed 100.")
        if self.discount_type == "fixed_amount" and self.max_discount_amount is not None:
            raise ValueError("Maximum discount is only valid for percentage discounts.")
        return self


# ---------------------------------------------------------------------------
# Telegram initData verification
# ---------------------------------------------------------------------------

def _verify_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    """Compatibility wrapper around the shared Telegram initData verifier."""
    return verify_telegram_init_data(init_data, bot_token)


# ---------------------------------------------------------------------------
# Checkout request schema
# ---------------------------------------------------------------------------


class CartItemIn(BaseModel):
    model_config = {"extra": "forbid"}

    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(ge=0, allow_inf_nan=False)
    qty: int = Field(gt=0, le=100)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class CheckoutRequest(BaseModel):
    model_config = {"extra": "forbid"}

    init_data: str | None = Field(None, max_length=8192)
    items: list[CartItemIn] = Field(max_length=100)
    full_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=7, max_length=20)
    city: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=500)
    payment_method: Literal["chapa", "telebirr", "cbe", "cod"]
    coupon_code: str | None = Field(None, min_length=3, max_length=50)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

    @field_validator("full_name", "phone", "city", "address", mode="before")
    @classmethod
    def strip_required_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_coordinates(self) -> "CheckoutRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Both latitude and longitude are required.")
        return self

    @field_validator("coupon_code", mode="before")
    @classmethod
    def normalize_coupon_code(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


_PAYMENT_MAP = {
    "chapa": "chapa",
    "telebirr": "telebirr",
    "cbe": "cbe_birr",
    "cod": "cash_on_delivery",
}

_PAYMENT_LABELS = {
    "chapa": "🏦 Chapa",
    "telebirr": "📱 Telebirr",
    "cbe": "🏛️ CBE Birr",
    "cod": "💵 Cash on Delivery",
}


# ---------------------------------------------------------------------------
# Internal: send Telegram order confirmation
# ---------------------------------------------------------------------------


async def _send_order_confirmation(
    telegram_id: int,
    order_number: str,
    full_name: str,
    city: str,
    total: float,
    items: list[CartItemIn],
    payment_method: str,
) -> None:
    """Fire-and-forget Telegram order confirmation message."""
    from telegram import Bot

    items_text = "\n".join(f"  • {i.name} x {i.qty}  —  ETB {i.price * i.qty:,.2f}" for i in items)
    pm_label = _PAYMENT_LABELS.get(payment_method, payment_method)
    text = (
        f"✅ *Order Confirmed!*\n\n"
        f"📦 Order No: `{order_number}`\n"
        f"👤 Name: {full_name}\n"
        f"📍 Delivery: {city}\n"
        f"💳 Payment: {pm_label}\n\n"
        f"*Items:*\n{items_text}\n\n"
        f"💰 *Total: ETB {total:,.2f}*\n\n"
        f"We'll notify you once your order ships. "
        f"Thank you for shopping at ወሎየዋ ሱቅ! 🇪🇹"
    )
    try:
        async with Bot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
            await bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode="Markdown",
            )
        logger.info(
            f"Order confirmation sent to Telegram user {telegram_id} for order {order_number}"
        )
    except Exception as exc:
        logger.warning(f"Could not send Telegram confirmation to {telegram_id}: {exc}")


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

_BASE_CTX = {"project_name": settings.PROJECT_NAME}


def _localized_page_context(request: Request, page: str) -> dict[str, object]:
    from bot.localization import SUPPORTED_LANGUAGES, get_web_profile_translations

    language = getattr(request, "query_params", {}).get("lang", "am")
    if language not in SUPPORTED_LANGUAGES:
        language = "am"
    return {
        **_BASE_CTX,
        "page": page,
        "page_language": language,
        "profile_text": get_web_profile_translations(language),
        "current_year": datetime.now(UTC).year,
    }


@web_app_router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(request, "index.html", _localized_page_context(request, "home"))


@web_app_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    from bot.localization import SUPPORTED_LANGUAGES, get_web_login_translations

    language = getattr(request, "query_params", {}).get("lang", "am")
    if language not in SUPPORTED_LANGUAGES:
        language = "am"
    page_context = _localized_page_context(request, "login")
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            **page_context,
            "page_language": language,
            "login_language": language,
            "login_text": get_web_login_translations(language),
            "current_year": datetime.now(UTC).year,
        },
    )


@web_app_router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request, "register.html", _localized_page_context(request, "register")
    )


@web_app_router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request, "forgot_password.html", _localized_page_context(request, "forgot-password")
    )


@web_app_router.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request):
    return templates.TemplateResponse(
        request, "categories.html", _localized_page_context(request, "categories")
    )


@web_app_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return await profile_page(request)


@web_app_router.get("/vendor/products", response_class=HTMLResponse)
async def vendor_products_page(request: Request):
    return templates.TemplateResponse(
        request,
        "vendor_products.html",
        _localized_page_context(request, "vendor-products"),
    )


@web_app_router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse(request, "admin.html", _localized_page_context(request, "admin"))


@web_app_router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    page_context = _localized_page_context(request, "profile")
    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            **page_context,
        },
    )


@web_app_router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_page(request: Request, product_id: int):
    from bot.localization import SUPPORTED_LANGUAGES, get_web_commerce_translations

    language = getattr(request, "query_params", {}).get("lang", "am")
    if language not in SUPPORTED_LANGUAGES:
        language = "am"
    return templates.TemplateResponse(
        request,
        "product.html",
        {
            **_localized_page_context(request, "product"),
            "commerce_text": get_web_commerce_translations(language),
            "product_id": product_id,
        },
    )


@web_app_router.get("/track", response_class=HTMLResponse)
async def order_tracking_page(request: Request):
    from bot.localization import SUPPORTED_LANGUAGES, get_web_commerce_translations

    language = getattr(request, "query_params", {}).get("lang", "am")
    if language not in SUPPORTED_LANGUAGES:
        language = "am"
    return templates.TemplateResponse(
        request,
        "track_order.html",
        {
            **_localized_page_context(request, "track-order"),
            "commerce_text": get_web_commerce_translations(language),
        },
    )


@web_app_router.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request):
    return templates.TemplateResponse(request, "cart.html", _localized_page_context(request, "cart"))


@web_app_router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """Checkout page."""
    return templates.TemplateResponse(
        request, "checkout.html", _localized_page_context(request, "checkout")
    )


@web_app_router.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    return templates.TemplateResponse(request, "orders.html", _localized_page_context(request, "orders"))


# ---------------------------------------------------------------------------
# Web Auth API endpoints  (non-Telegram users)
# ---------------------------------------------------------------------------


class WebRegisterRequest(BaseModel):
    full_name: str
    phone: str
    password: str
    email: str | None = None


class WebLoginRequest(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=1, max_length=256)


def _web_auth_response(db_user) -> dict:
    from core.security import create_access_token

    token = create_access_token(
        {
            "sub": str(db_user.id),
            "role": getattr(db_user, "role", "customer"),
            "token_version": getattr(db_user, "token_version", 0),
        }
    )
    name_parts = []
    if db_user.first_name:
        name_parts.append(db_user.first_name)
    if db_user.last_name:
        name_parts.append(db_user.last_name)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "full_name": " ".join(name_parts) or db_user.phone_number or "ደንበኛ",
            "phone": db_user.phone_number or "",
            "email": db_user.email or "",
        },
    }


@web_app_router.post("/api/web/register")
async def api_web_register(body: WebRegisterRequest, db=Depends(get_db_session)):
    """Register a new web (non-Telegram) customer account."""
    import re

    from sqlalchemy import select

    from apps.users.models import User
    from core.security import hash_password

    # Normalise phone
    phone = re.sub(r"[\s\-()]", "", body.phone)
    if not re.match(r"^(09|07)\d{8}$", phone):
        raise HTTPException(status_code=422, detail="ስልክ ቁጥሩ ልክ አይደለም (ምሳሌ: 0912345678)")

    if len(body.password) < 6:
        raise HTTPException(status_code=422, detail="የይለፍ ቃሉ ቢያንስ 6 ፊደል መሆን አለበት")

    # Check duplicate phone
    result = await db.execute(
        select(User).where(User.phone_number == phone, User.is_deleted.isnot(True))
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="ይህ ስልክ ቁጥር ቀደም ሲል ተመዝግቧል")

    # Parse name
    parts = body.full_name.strip().split(None, 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else None

    new_user = User(
        first_name=first_name,
        last_name=last_name,
        phone_number=phone,
        email=body.email or None,
        password_hash=hash_password(body.password),
        role="customer",
        status="active",
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    await db.commit()

    logger.info("Web registration: user_id=%s phone=%s", new_user.id, phone)
    return _web_auth_response(new_user)


@web_app_router.post("/api/web/login")
async def api_web_login(
    body: WebLoginRequest,
    request: Request,
    db=Depends(get_db_session),
):
    """Authenticate a web (non-Telegram) customer via phone + password."""
    from sqlalchemy import select

    from apps.users.models import User
    from core.dependencies import check_rate_limit
    from core.security import verify_password
    from core.utils.validators import Validator

    await check_rate_limit(request, key_prefix="web_login", limit=10, window=300)

    try:
        phone = Validator.phone(body.phone, normalize=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="ትክክለኛ የኢትዮጵያ ስልክ ቁጥር ያስገቡ።",
        ) from exc

    result = await db.execute(
        select(User).where(User.phone_number == phone, User.is_deleted.isnot(True))
    )
    user = result.scalar_one_or_none()

    invalid_credentials = HTTPException(
        status_code=401,
        detail="ስልክ ቁጥሩ ወይም የይለፍ ቃሉ ስህተት ነው",
    )
    if (
        not user
        or not user.password_hash
        or getattr(user, "status", "active") != "active"
        or not verify_password(body.password, user.password_hash)
    ):
        raise invalid_credentials

    logger.info("Web login: user_id=%s", user.id)
    return _web_auth_response(user)


@web_app_router.post("/api/auth/logout")
async def web_app_logout(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_transaction_session),
):
    """Revoke all existing sessions for the authenticated account."""
    from apps.users.models import User

    await db.execute(
        update(User)
        .where(User.id == current_user["id"])
        .values(token_version=User.token_version + 1)
    )
    await db.commit()
    logger.info("Web App session revoked for user_id=%s", current_user["id"])
    return {"success": True}


@web_app_router.get("/api/admin/session")
async def web_admin_session(current_user: dict = Depends(get_current_admin)):
    """Return the authenticated admin identity for Web App navigation."""
    return {
        "id": current_user["id"],
        "role": current_user["role"],
        "is_admin": True,
    }


def _store_settings_payload(store_settings) -> dict:
    """Return admin-editable options and non-sensitive environment status only."""
    from apps.store_settings.checkout import payment_gateway_status

    payment_secrets = payment_gateway_status()
    return {
        "store_open": store_settings.store_open if store_settings else True,
        "currency_code": store_settings.currency_code if store_settings else "ETB",
        "enabled_payment_methods": (
            store_settings.enabled_payment_methods
            if store_settings
            else ["chapa", "telebirr", "cbe", "cod"]
        ),
        "notification_settings": (
            store_settings.notification_settings
            if store_settings
            else {
                "customer_orders": True,
                "vendor_updates": True,
                "admin_alerts": True,
                "support_updates": True,
            }
        ),
        "maintenance_message": store_settings.maintenance_message if store_settings else None,
        "environment_status": {
            "telegram_bot": bool(settings.TELEGRAM_BOT_TOKEN),
            "telegram_webhook": bool(settings.TELEGRAM_WEBHOOK_URL),
            "payment_gateways": payment_secrets,
        },
    }


@web_app_router.get("/api/admin/settings")
async def web_admin_get_settings(
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_db_session),
):
    from apps.store_settings.models import StoreSettings

    return _store_settings_payload(await db.get(StoreSettings, 1))


@web_app_router.put("/api/admin/settings")
async def web_admin_update_settings(
    data: WebStoreSettingsUpdate,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    from apps.store_settings.models import StoreSettings

    update_data = data.model_dump(exclude_unset=True)
    if "enabled_payment_methods" in update_data:
        methods = update_data["enabled_payment_methods"]
        if not methods:
            raise HTTPException(status_code=422, detail="At least one payment method must remain enabled.")
        from apps.store_settings.checkout import payment_gateway_status

        configured = payment_gateway_status()
        configured["cod"] = True
        unavailable = [method for method in methods if not configured[method]]
        if unavailable:
            raise HTTPException(
                status_code=422,
                detail=f"Configure {', '.join(unavailable)} in the deployment environment before enabling it.",
            )

    store_settings = await db.get(StoreSettings, 1)
    if store_settings is None:
        store_settings = StoreSettings(id=1)
        db.add(store_settings)
    if "notification_settings" in update_data:
        current_notifications = dict(
            store_settings.notification_settings
            or {
                "customer_orders": True,
                "vendor_updates": True,
                "admin_alerts": True,
                "support_updates": True,
            }
        )
        current_notifications.update(update_data["notification_settings"])
        update_data["notification_settings"] = current_notifications
    for key, value in update_data.items():
        setattr(store_settings, key, value)
    await db.flush()
    return _store_settings_payload(store_settings)


def _discount_scope(coupon) -> tuple[str, int | None]:
    categories = coupon.applicable_categories or []
    products = coupon.applicable_products or []
    if products:
        return "product", int(products[0])
    if categories:
        return "category", int(categories[0])
    return "global", None


def _serialize_discount(coupon) -> dict:
    scope, scope_id = _discount_scope(coupon)
    return {
        "id": coupon.id,
        "code": coupon.code,
        "name": coupon.name,
        "description": coupon.description,
        "discount_type": coupon.discount_type,
        "discount_value": float(coupon.discount_value),
        "max_discount_amount": (
            float(coupon.max_discount_amount) if coupon.max_discount_amount is not None else None
        ),
        "minimum_order_value": (
            float(coupon.min_purchase_amount) if coupon.min_purchase_amount is not None else None
        ),
        "valid_from": coupon.valid_from.isoformat(),
        "valid_to": coupon.valid_to.isoformat(),
        "usage_limit": coupon.usage_limit,
        "per_user_limit": coupon.per_user_limit,
        "used_count": coupon.used_count,
        "scope": scope,
        "scope_id": scope_id,
        "is_active": coupon.is_active,
        "is_valid": coupon.is_valid,
    }


def _coupon_create_data(data: WebDiscountCreate) -> dict:
    return {
        "code": data.code,
        "name": data.name,
        "description": data.description,
        "discount_type": data.discount_type,
        "discount_value": data.discount_value,
        "max_discount_amount": data.max_discount_amount,
        "min_purchase_amount": data.minimum_order_value,
        "valid_from": data.valid_from,
        "valid_to": data.valid_to,
        "usage_limit": data.usage_limit,
        "per_user_limit": data.per_user_limit,
        "applicable_categories": [str(data.scope_id)] if data.scope == "category" else None,
        "applicable_products": [data.scope_id] if data.scope == "product" else None,
        "excluded_categories": None,
        "excluded_products": None,
        "new_customers_only": False,
        "first_order_only": False,
        "is_active": data.is_active,
        "is_stackable": False,
    }


@web_app_router.get("/api/admin/discounts")
async def web_admin_list_discounts(
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_db_session),
):
    from sqlalchemy import select

    from apps.marketing.models import Coupon

    coupons = await db.scalars(select(Coupon).order_by(Coupon.created_at.desc(), Coupon.id.desc()))
    return {"items": [_serialize_discount(coupon) for coupon in coupons.all()]}


async def _validate_discount_scope(db, data: WebDiscountCreate) -> None:
    if data.scope == "global":
        return
    from apps.products.models import Category, Product

    model = Category if data.scope == "category" else Product
    target = await db.get(model, data.scope_id)
    if target is None or (
        data.scope == "product" and getattr(target, "is_deleted", False)
    ):
        raise HTTPException(status_code=422, detail="The selected discount scope does not exist.")


@web_app_router.post("/api/admin/discounts", status_code=201)
async def web_admin_create_discount(
    data: WebDiscountCreate,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    from sqlalchemy import select

    from apps.marketing.models import Coupon

    await _validate_discount_scope(db, data)
    if await db.scalar(select(Coupon.id).where(Coupon.code == data.code)) is not None:
        raise HTTPException(status_code=409, detail="This coupon code already exists.")
    coupon = Coupon(**_coupon_create_data(data))
    db.add(coupon)
    await db.flush()
    return _serialize_discount(coupon)


@web_app_router.put("/api/admin/discounts/{discount_id}")
async def web_admin_update_discount(
    discount_id: int,
    data: WebDiscountCreate,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    from apps.marketing.models import Coupon

    coupon = await db.get(Coupon, discount_id)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Discount not found.")
    await _validate_discount_scope(db, data)
    if coupon.code != data.code:
        from sqlalchemy import select

        duplicate = await db.scalar(select(Coupon.id).where(Coupon.code == data.code))
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="This coupon code already exists.")
    for key, value in _coupon_create_data(data).items():
        setattr(coupon, key, value)
    await db.flush()
    return _serialize_discount(coupon)


@web_app_router.delete("/api/admin/discounts/{discount_id}")
async def web_admin_deactivate_discount(
    discount_id: int,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    from apps.marketing.models import Coupon

    coupon = await db.get(Coupon, discount_id)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Discount not found.")
    coupon.is_active = False
    await db.flush()
    return {"success": True, "id": coupon.id, "is_active": False}


@web_app_router.post("/api/admin/discounts/{discount_id}/activate")
async def web_admin_activate_discount(
    discount_id: int,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    from apps.marketing.models import Coupon

    coupon = await db.get(Coupon, discount_id)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Discount not found.")
    coupon.is_active = True
    await db.flush()
    return {"success": True, "id": coupon.id, "is_active": True}


@web_app_router.delete("/api/admin/discounts/{discount_id}/permanent")
async def web_admin_delete_discount(
    discount_id: int,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    from apps.marketing.models import Coupon, CouponUsage

    coupon = await db.get(Coupon, discount_id)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Discount not found.")
    usage_exists = await db.scalar(
        select(CouponUsage.id).where(CouponUsage.coupon_id == coupon.id).limit(1)
    )
    if coupon.used_count or usage_exists is not None:
        raise HTTPException(
            status_code=409,
            detail="This coupon has usage history and cannot be deleted. Deactivate it instead.",
        )
    await db.delete(coupon)
    await db.flush()
    return {"success": True, "id": discount_id}


class WebDiscountValidate(BaseModel):
    model_config = {"extra": "forbid"}

    code: str = Field(min_length=3, max_length=50)
    items: list[CartItemIn] = Field(min_length=1, max_length=100)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


@web_app_router.get("/api/discounts/active")
async def web_active_discounts(db=Depends(get_db_session)):
    from sqlalchemy import select

    from apps.marketing.models import Coupon

    now = datetime.utcnow()
    coupons = await db.scalars(
        select(Coupon)
        .where(
            Coupon.is_active.is_(True),
            Coupon.valid_from <= now,
            Coupon.valid_to >= now,
            (Coupon.usage_limit.is_(None)) | (Coupon.used_count < Coupon.usage_limit),
        )
        .order_by(Coupon.created_at.desc())
        .limit(5)
    )
    return {
        "items": [
            {
                "code": coupon.code,
                "name": coupon.name,
                "description": coupon.description or "",
                "discount_type": coupon.discount_type,
                "discount_value": float(coupon.discount_value),
                "valid_to": coupon.valid_to.isoformat() if coupon.valid_to else None,
                "scope": _discount_scope(coupon)[0],
                "scope_id": _discount_scope(coupon)[1],
                "minimum_order_value": (
                    float(coupon.min_purchase_amount)
                    if coupon.min_purchase_amount is not None
                    else None
                ),
            }
            for coupon in coupons.all()
        ]
    }


@web_app_router.get("/api/store/announcement")
async def web_store_announcement(db=Depends(get_db_session)):
    from apps.store_settings.checkout import (
        DEFAULT_PAYMENT_METHODS,
        get_checkout_availability,
    )

    availability = await get_checkout_availability(db)
    active_discounts = await web_active_discounts(db)
    return {
        "store_open": availability.store_open,
        "message": availability.maintenance_message,
        "discounts": active_discounts["items"],
        "enabled_payment_methods": [
            method
            for method in DEFAULT_PAYMENT_METHODS
            if method in availability.enabled_payment_methods
        ],
    }


@web_app_router.post("/api/discounts/validate")
async def web_validate_discount(
    data: WebDiscountValidate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_session),
):
    from sqlalchemy import func, select

    from apps.marketing.coupons import CouponManager
    from apps.marketing.models import Coupon, CouponUsage
    from apps.orders.models import Order
    from apps.products.models import Product

    product_ids = {item.id for item in data.items}
    result = await db.execute(
        select(Product.id, Product.category_id, Product.price).where(
            Product.id.in_(product_ids),
            Product.is_deleted.is_(False),
            Product.status == "active",
        )
    )
    products = {row.id: row for row in result.all()}
    if len(products) != len(product_ids):
        raise HTTPException(status_code=409, detail="One or more products are unavailable.")
    subtotal = sum(
        (Decimal(str(products[item.id].price)) * item.qty for item in data.items),
        start=Decimal("0"),
    )
    coupon = await db.scalar(select(Coupon).where(Coupon.code == data.code))
    if coupon is None:
        raise HTTPException(status_code=422, detail="This coupon code is not valid.")
    usage_count = await db.scalar(
        select(func.count(CouponUsage.id)).where(
            CouponUsage.coupon_id == coupon.id,
            CouponUsage.user_id == current_user["id"],
        )
    )
    order_count = await db.scalar(
        select(func.count()).select_from(Order).where(Order.user_id == current_user["id"])
    )
    eligible_items = [
        {
            "product_id": item.id,
            "category_id": products[item.id].category_id,
            "amount": Decimal(str(products[item.id].price)) * item.qty,
        }
        for item in data.items
    ]
    validation = await CouponManager(db).validate_coupon(
        data.code,
        current_user["id"],
        subtotal,
        user_order_count=order_count or 0,
        eligible_items=eligible_items,
        user_usage_count=usage_count or 0,
    )
    if not validation["is_valid"]:
        raise HTTPException(status_code=422, detail=validation["message"])
    discount = validation["discount_amount"]
    shipping_fee = Decimal("0") if subtotal >= Decimal("1000") else Decimal("50")
    tax = subtotal * Decimal("0.15")
    return {
        "code": coupon.code,
        "discount_amount": float(discount),
        "subtotal": float(subtotal),
        "shipping_fee": float(shipping_fee),
        "tax": float(tax),
        "total_after_discount": float(max(Decimal("0"), subtotal + shipping_fee + tax - discount)),
        "message": "Coupon applied successfully.",
    }


def _serialize_admin_product(product) -> dict:
    status = product.status.value if hasattr(product.status, "value") else str(product.status)
    return {
        "id": product.id,
        "vendor_id": product.vendor_id,
        "name": product.name,
        "name_am": product.name_am or "",
        "sku": product.sku,
        "price": float(product.price),
        "compare_price": float(product.compare_price) if product.compare_price else None,
        "stock_quantity": product.stock_quantity,
        "category_id": product.category_id,
        "status": status,
        "description": product.description or "",
        "images": product.images or [],
    }


@web_app_router.get("/api/admin/products")
async def web_admin_products(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    product_status: Annotated[str | None, Query(alias="status")] = None,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_db_session),
):
    """List catalog products for the authenticated admin."""
    from sqlalchemy import func, select

    from apps.products.models import Product

    conditions = [Product.is_deleted.is_(False)]
    if product_status:
        if product_status not in {"draft", "pending", "active", "rejected", "out_of_stock", "discontinued"}:
            raise HTTPException(status_code=422, detail="Invalid product status")
        conditions.append(Product.status == product_status)
    total = await db.scalar(select(func.count()).select_from(Product).where(*conditions))
    result = await db.execute(
        select(Product)
        .where(*conditions)
        .order_by(Product.created_at.desc(), Product.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return {
        "items": [_serialize_admin_product(product) for product in result.scalars().all()],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


def _normalize_uploaded_product_image(image_data: bytes) -> bytes:
    """Validate a real image and normalize it to metadata-free WebP."""
    import warnings
    from io import BytesIO

    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_data)) as image:
                if image.format not in {"JPEG", "PNG", "GIF", "WEBP"}:
                    raise HTTPException(status_code=415, detail="Use a JPEG, PNG, GIF, or WebP image.")
                if image.width * image.height > 40_000_000:
                    raise HTTPException(status_code=413, detail="Image dimensions are too large.")
                image.verify()
            with Image.open(BytesIO(image_data)) as image:
                image.seek(0)
                normalized = ImageOps.exif_transpose(image)
                if normalized.mode not in {"RGB", "RGBA"}:
                    normalized = normalized.convert("RGBA" if "A" in normalized.getbands() else "RGB")
                normalized.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
                output = BytesIO()
                normalized.save(output, format="WEBP", quality=88, method=6)
                return output.getvalue()
    except HTTPException:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid image.") from exc


@web_app_router.post("/api/vendor/products", status_code=201)
async def web_vendor_create_product(
    payload: Annotated[str, Form()],
    images: Annotated[list[UploadFile], File()],
    current_user: dict = Depends(get_current_vendor),
    db=Depends(get_transaction_session),
):
    """Create a vendor product for admin review with uploaded product images."""
    from apps.products.schemas import ProductCreate, ProductResponse
    from core.constants import MAX_IMAGE_SIZE_BYTES, MAX_PRODUCT_IMAGES, ProductStatus

    if not current_user.get("vendor_id"):
        raise HTTPException(status_code=403, detail="Vendor profile required")
    if not images or len(images) > MAX_PRODUCT_IMAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Upload between 1 and {MAX_PRODUCT_IMAGES} product images.",
        )

    uploaded_paths: list[Path] = []
    product_created = False
    try:
        data = WebVendorProductPayload.model_validate_json(payload)
        image_urls: list[str] = []
        uploads_dir = Path(__file__).parent / "static" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        for image in images:
            image_data = await image.read(MAX_IMAGE_SIZE_BYTES + 1)
            if not image_data:
                raise HTTPException(status_code=422, detail="An uploaded image is empty.")
            if len(image_data) > MAX_IMAGE_SIZE_BYTES:
                raise HTTPException(status_code=413, detail="Each image must be 5 MB or smaller.")
            normalized = _normalize_uploaded_product_image(image_data)
            filename = f"{uuid4().hex}.webp"
            image_path = uploads_dir / filename
            await asyncio.to_thread(image_path.write_bytes, normalized)
            uploaded_paths.append(image_path)
            image_urls.append(f"/app/static/uploads/{filename}")

        product_data = ProductCreate(
            name=data.name,
            name_am=data.name_am,
            description=data.description,
            category_id=data.category_id,
            price=data.price,
            compare_price=data.compare_price,
            sku=data.sku,
            stock_quantity=data.stock_quantity,
            images=image_urls,
            status=ProductStatus.PENDING,
        )
        product = await ProductService(db).create_product(
            current_user["vendor_id"],
            product_data,
        )
        response = ProductResponse.model_validate(product)
        await db.commit()
        product_created = True
        return response
    except PydanticValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        logger.exception("Vendor product creation failed for user %s", current_user["id"])
        raise
    finally:
        if not product_created:
            for image_path in uploaded_paths:
                if not image_path.exists():
                    continue
                try:
                    image_path.unlink()
                except OSError:
                    logger.exception("Failed to remove uncommitted product image %s", image_path)


@web_app_router.post("/api/admin/products/{product_id}/approve")
async def web_admin_approve_product(
    product_id: int,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    """Approve a pending product and make it publicly discoverable."""
    try:
        product = await ProductService(db).review_product(product_id, approved=True)
        return _serialize_admin_product(product)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@web_app_router.post("/api/admin/products/{product_id}/reject")
async def web_admin_reject_product(
    product_id: int,
    data: WebProductRejection,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    """Reject a pending product and notify its vendor with the review reason."""
    try:
        product = await ProductService(db).review_product(
            product_id,
            approved=False,
            reason=data.reason,
        )
        return _serialize_admin_product(product)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@web_app_router.post("/api/admin/products", status_code=201)
async def web_admin_create_product(
    data: WebAdminProductCreate,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    """Create an active catalog product for a selected vendor."""
    from apps.products.schemas import ProductCreate
    from core.constants import ProductStatus

    product_service = ProductService(db)
    try:
        product = await product_service.create_product(
            data.vendor_id,
            ProductCreate(
                name=data.name.strip(),
                name_am=data.name_am,
                description=data.description,
                price=data.price,
                stock_quantity=data.stock_quantity,
                sku=data.sku.strip(),
                category_id=data.category_id,
                status=ProductStatus.ACTIVE,
            ),
            admin_approved=True,
        )
        return _serialize_admin_product(product)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@web_app_router.put("/api/admin/products/{product_id}")
async def web_admin_update_product(
    product_id: int,
    data: WebAdminProductUpdate,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    """Update an existing product without bypassing product service rules."""
    from apps.products.schemas import ProductUpdate

    product_service = ProductService(db)
    try:
        current = await product_service.get_product(product_id)
        product = await product_service.update_product(
            product_id,
            current.vendor_id,
            ProductUpdate(**data.model_dump(exclude_unset=True)),
        )
        return _serialize_admin_product(product)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@web_app_router.delete("/api/admin/products/{product_id}")
async def web_admin_delete_product(
    product_id: int,
    current_user: dict = Depends(get_current_admin),
    db=Depends(get_transaction_session),
):
    """Soft-delete a product and synchronize inventory/category counts."""
    product_service = ProductService(db)
    try:
        product = await product_service.get_product(product_id)
        await product_service.delete_product(product_id, product.vendor_id)
        return {"message": f"Product {product_id} deleted successfully"}
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# JSON API endpoints
# ---------------------------------------------------------------------------


@web_app_router.get("/api/categories")
async def get_categories(db=Depends(get_db_session)):
    """Get categories for web app with live product counts."""
    from sqlalchemy import and_, func, select

    from apps.products.models import Category, Product
    from core.constants import ProductStatus

    result = await db.execute(
        select(
            Category,
            func.count(Product.id).label("live_count"),
        )
        .outerjoin(
            Product,
            and_(
                Product.category_id == Category.id,
                Product.is_deleted.is_(False),
                Product.status == ProductStatus.ACTIVE,
            ),
        )
        .where(Category.is_active.is_(True))
        .group_by(Category.id)
        .order_by(Category.display_order, Category.name)
    )
    rows = result.all()

    nodes = {}
    ordered_ids = []
    for category, direct_count in rows:
        node = {
            "id": category.id,
            "name": category.name,
            "name_am": category.name_am or "",
            "slug": category.slug or category.name,
            "parent_id": category.parent_id,
            "description": category.description or "",
            "description_am": category.description_am or "",
            "icon_url": category.icon_url or "",
            "image_url": category.image_url or "",
            "direct_product_count": int(direct_count or 0),
            "product_count": int(direct_count or 0),
            "is_featured": category.is_featured,
            "display_order": category.display_order,
            "children": [],
        }
        nodes[category.id] = node
        ordered_ids.append(category.id)

    roots = []
    for category_id in ordered_ids:
        node = nodes[category_id]
        parent_id = node["parent_id"]
        seen = {category_id}
        ancestor_id = parent_id
        has_cycle = False
        while ancestor_id in nodes:
            if ancestor_id in seen:
                has_cycle = True
                break
            seen.add(ancestor_id)
            ancestor_id = nodes[ancestor_id]["parent_id"]

        if parent_id in nodes and not has_cycle:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)

    def add_child_counts(node: dict) -> int:
        count = node["direct_product_count"] + sum(
            add_child_counts(child) for child in node["children"]
        )
        node["product_count"] = count
        return count

    for root in roots:
        add_child_counts(root)

    return roots


@web_app_router.get("/api/products")
async def get_products(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str, Query(max_length=120)] = "",
    category_id: Annotated[int | None, Query(ge=1)] = None,
    db=Depends(get_db_session),
):
    """Get products for web app with optional search and category filter."""
    from fastapi.responses import JSONResponse
    from sqlalchemy import false, func, or_, select

    from apps.products.models import Category, Product
    from core.constants import ProductStatus

    q = q.strip()
    conditions = [
        Product.is_deleted.is_(False),
        Product.status == ProductStatus.ACTIVE,
    ]

    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(
                func.lower(Product.name).like(func.lower(pattern)),
                func.lower(func.coalesce(Product.name_am, "")).like(func.lower(pattern)),
            )
        )
    if category_id is not None:
        category_result = await db.execute(
            select(Category.id, Category.parent_id).where(Category.is_active.is_(True))
        )
        category_rows = category_result.all()
        active_parent_ids = {row.id: row.parent_id for row in category_rows}

        if category_id not in active_parent_ids:
            conditions.append(false())
        else:
            children_by_parent: dict[int, list[int]] = {}
            for child_id, parent_id in active_parent_ids.items():
                if parent_id is not None:
                    children_by_parent.setdefault(parent_id, []).append(child_id)

            category_ids = {category_id}
            pending = [category_id]
            while pending:
                current_id = pending.pop()
                for child_id in children_by_parent.get(current_id, []):
                    if child_id not in category_ids:
                        category_ids.add(child_id)
                        pending.append(child_id)

            conditions.append(Product.category_id.in_(sorted(category_ids)))

    count_stmt = select(func.count()).select_from(Product).where(*conditions)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = (
        select(Product)
        .where(*conditions)
        .order_by(Product.is_featured.desc(), Product.id)
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    result = await db.execute(stmt)
    products = result.scalars().all()

    items = [
        {
            "id": p.id,
            "name": p.name,
            "name_am": p.name_am or "",
            "slug": p.slug or "",
            "description": p.description or "",
            "price": float(p.price),
            "compare_price": float(p.compare_price) if p.compare_price else None,
            "stock_quantity": p.stock_quantity,
            "images": p.images or [],
            "status": p.status if isinstance(p.status, str) else str(p.status.value),
            "is_featured": p.is_featured,
            "category_id": p.category_id,
            "category_type": p.category_type or "",
        }
        for p in products
    ]

    return JSONResponse(
        content={"items": items, "total": total, "page": page, "page_size": page_size},
        headers={"Cache-Control": "no-store"},
    )


@web_app_router.get("/api/search")
async def search_products(q: str = "", limit: int = 6, db=Depends(get_db_session)):
    """
    Autocomplete / search endpoint.
    Returns up to `limit` products whose name or Amharic name contains `q` (case-insensitive).
    """
    from sqlalchemy import func, or_, select
    from sqlalchemy.orm import selectinload

    from apps.products.models import Product
    from core.constants import ProductStatus

    q = q.strip()
    if not q:
        return {"items": [], "query": q}

    pattern = f"%{q}%"
    stmt = (
        select(Product)
        .options(selectinload(Product.category_rel))
        .where(
            Product.is_deleted.is_(False),
            Product.status == ProductStatus.ACTIVE,
            or_(
                func.lower(Product.name).like(func.lower(pattern)),
                func.lower(func.coalesce(Product.name_am, "")).like(func.lower(pattern)),
            ),
        )
        .order_by(Product.name)
        .limit(limit)
    )
    result = await db.execute(stmt)
    products = result.scalars().all()

    return {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "name_am": getattr(p, "name_am", "") or "",
                "price": float(p.price),
                "category": p.category_rel.name if p.category_rel else "",
                "image_url": (p.images[0] if p.images else "") if p.images else "",
            }
            for p in products
        ],
        "query": q,
    }


@web_app_router.get("/api/product/{product_id}")
async def get_product(product_id: int, db=Depends(get_db_session)):
    """Get single product."""
    product_service = ProductService(db)
    product = await product_service.get_product(product_id)
    from core.constants import ProductStatus

    if not product or product.status != ProductStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Product not found")
    return product.to_dict()


def _user_from_bearer(request: Request | str, db) -> int | None:
    """Extract user_id from Authorization: Bearer <jwt> header, or None."""
    auth = request if isinstance(request, str) else request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    from core.security import verify_token

    payload = verify_token(token)
    if not payload:
        return None
    try:
        return int(payload.get("sub", 0))
    except (ValueError, TypeError):
        return None


def _is_active_user(user) -> bool:
    status = getattr(user, "status", "active")
    return getattr(status, "value", status) == "active"


@web_app_router.post("/api/checkout")
async def api_checkout(
    request: Request,
    body: CheckoutRequest,
    db=Depends(get_transaction_session),
):
    """
    Place an order from the web app.
    Accepts:
      1. Telegram initData (HMAC-verified) in body.init_data
      2. JWT Bearer token in Authorization header (web-registered users)
      3. Test-only fallback to the first DB user when no auth token is supplied
    """
    from sqlalchemy import select

    from apps.orders.schemas import OrderCreate, OrderItemCreate
    from apps.store_settings.checkout import (
        get_checkout_availability,
        payment_gateway_status,
    )
    from apps.users.models import User
    from core.constants import PaymentMethod, ShippingMethod
    from core.utils.location import format_delivery_address

    if not body.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    checkout_availability = await get_checkout_availability(db)
    if not checkout_availability.store_open:
        raise HTTPException(
            status_code=503,
            detail=checkout_availability.maintenance_message
            or "The store is temporarily closed. Please try again later.",
        )

    user_service = UserService(db)
    db_user = None

    # ── 1. Telegram initData ─────────────────────────────────────────────────
    tg_user: dict | None = None
    if body.init_data:
        tg_user = _verify_telegram_init_data(body.init_data, settings.TELEGRAM_BOT_TOKEN)
        if tg_user and tg_user.get("id"):
            tg_id = int(tg_user["id"])
            db_user = await user_service.get_user_by_telegram(tg_id)
            if not db_user:
                db_user = await user_service.get_or_create_user(
                    telegram_id=tg_id,
                    first_name=tg_user.get("first_name") or body.full_name,
                    username=tg_user.get("username"),
                )

    # ── 2. Web JWT Bearer token ──────────────────────────────────────────────
    if not db_user:
        web_user_id = _user_from_bearer(request, db)
        if web_user_id:
            result = await db.execute(
                select(User).where(
                    User.id == web_user_id,
                    User.is_deleted.is_(False),
                    User.status == "active",
                )
            )
            db_user = result.scalar_one_or_none()

    # Only allow the fixture fallback in automated tests. DEBUG is not a safe
    # authentication boundary because development previews can be public.
    if not db_user and not body.init_data and settings.ENVIRONMENT == "testing":
        result = await db.execute(select(User).limit(1))
        db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="ይቅርታ — ለዚህ ትዕዛዝ መስጠት ይግቡ ወይም ይመዝገቡ።",
        )
    if not _is_active_user(db_user):
        raise HTTPException(status_code=403, detail="This user account is not active.")

    # ── Map payment method ───────────────────────────────────────────────────
    pm_value = _PAYMENT_MAP.get(body.payment_method, "cash_on_delivery")
    try:
        pm = PaymentMethod(pm_value)
    except ValueError:
        pm = PaymentMethod.CASH_ON_DELIVERY
    selected_payment_method = body.payment_method
    if selected_payment_method not in checkout_availability.enabled_payment_methods:
        raise HTTPException(status_code=422, detail="This payment method is currently unavailable.")
    if not payment_gateway_status().get(selected_payment_method, selected_payment_method == "cod"):
        raise HTTPException(
            status_code=503,
            detail="This payment provider is not configured by the store.",
        )

    # ── Calculate shipping fee ───────────────────────────────────────────────
    from sqlalchemy import select

    from apps.products.models import Product

    product_ids = [item.id for item in body.items]
    result = await db.execute(
        select(Product.id, Product.price).where(
            Product.id.in_(product_ids), Product.is_deleted.is_(False)
        )
    )
    current_prices = dict(result.all())
    if len(current_prices) != len(set(product_ids)):
        raise HTTPException(status_code=400, detail="One or more products are unavailable.")

    subtotal = sum(
        (Decimal(str(current_prices[item.id])) * item.qty for item in body.items),
        start=Decimal("0"),
    )
    shipping_fee = Decimal("0") if subtotal >= 1000 else Decimal("50")

    # ── Build and create order ───────────────────────────────────────────────
    order_data = OrderCreate(
        payment_method=pm,
        shipping_address=format_delivery_address(
            body.address,
            body.latitude,
            body.longitude,
        ),
        shipping_city=body.city,
        shipping_phone=body.phone,
        shipping_method=ShippingMethod.STANDARD,
        shipping_fee=shipping_fee,
        customer_notes=f"Mini App order — Recipient: {body.full_name}",
        items=[OrderItemCreate(product_id=i.id, quantity=i.qty) for i in body.items],
    )

    order_service = OrderService(db)
    try:
        order = await order_service.create_order(
            db_user.id,
            order_data,
            coupon_code=body.coupon_code,
        )
        payment_url = None
        if pm != PaymentMethod.CASH_ON_DELIVERY:
            from infrastructure.payments.factory import process_payment

            try:
                payment_response = await process_payment(
                    method=pm.value,
                    amount=order.total,
                    order_id=order.id,
                    order_number=order.order_number,
                    customer_name=db_user.full_name or body.full_name,
                    customer_email=db_user.email or "",
                    customer_phone=body.phone,
                )
            except Exception as exc:
                logger.exception("Web app payment initialization failed for order %s", order.id)
                raise HTTPException(
                    status_code=502,
                    detail="Payment provider could not initialize the payment.",
                ) from exc
            if not payment_response.success or not payment_response.transaction_id:
                raise HTTPException(
                    status_code=502,
                    detail="Payment provider could not initialize the payment.",
                )
            await order_service.update_payment_status(
                order.id,
                "pending",
                payment_response.transaction_id,
            )
            payment_url = payment_response.payment_url or payment_response.redirect_url
        await db.commit()
    except HTTPException:
        raise
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InsufficientStockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Order creation failed for user %s", db_user.id)
        raise HTTPException(
            status_code=500,
            detail="Could not place your order. Please try again.",
        ) from exc

    # ── Send Telegram confirmation (non-blocking) ────────────────────────────
    notify_tg_id = tg_user.get("id") if tg_user else None
    if not notify_tg_id and db_user.telegram_id:
        notify_tg_id = db_user.telegram_id

    if notify_tg_id:
        await _send_order_confirmation(
            telegram_id=int(notify_tg_id),
            order_number=order.order_number,
            full_name=body.full_name,
            city=body.city,
            total=float(order.total),
            items=[
                CartItemIn(id=i.id, name=i.name, price=float(current_prices[i.id]), qty=i.qty)
                for i in body.items
            ],
            payment_method=body.payment_method,
        )

    return {
        "order_number": order.order_number,
        "order_id": order.id,
        "total": float(order.total),
        "subtotal": float(order.subtotal),
        "discount": float(order.discount),
        "payment_url": payment_url,
        "payment_method": pm.value,
        "coupon_code": body.coupon_code,
    }


@web_app_router.post("/api/auth")
async def tg_auth(request: Request, db=Depends(get_db_session)):
    """
    Authenticate a Telegram Mini App user via initData HMAC-SHA256 verification.
    Returns a short-lived JWT access token + basic user info.

    In automated tests only, empty initData may use a fixture user. Development
    and production requests must provide valid Telegram initData.
    """
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON request body.") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Request body must be a JSON object.")

    init_data: str = body.get("init_data", "")
    if not isinstance(init_data, str) or len(init_data) > 8192:
        raise HTTPException(status_code=422, detail="Invalid Telegram authentication data.")
    tg_user: dict | None = None

    if init_data:
        tg_user = _verify_telegram_init_data(init_data, settings.TELEGRAM_BOT_TOKEN)
        if tg_user is None:
            raise HTTPException(status_code=401, detail="Invalid Telegram auth data")

    user_service = UserService(db)
    db_user = None

    if tg_user and tg_user.get("id"):
        db_user = await user_service.get_or_create_user(
            telegram_id=int(tg_user["id"]),
            first_name=tg_user.get("first_name") or "User",
            username=tg_user.get("username"),
        )
    elif settings.ENVIRONMENT == "testing":
        # Test-only fallback; never authenticate public development previews
        # as the first real user in the database.
        from sqlalchemy import select

        from apps.users.models import User

        result = await db.execute(select(User).limit(1))
        db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Could not identify your account. Please open the store via Telegram.",
        )
    if not _is_active_user(db_user):
        raise HTTPException(status_code=403, detail="This user account is not active.")

    from core.security import create_access_token

    token = create_access_token(
        {
            "sub": str(db_user.id),
            "telegram_id": db_user.telegram_id,
            "token_version": getattr(db_user, "token_version", 0),
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "first_name": db_user.first_name or "User",
            "last_name": db_user.last_name or "",
            "username": db_user.username or "",
            "telegram_id": db_user.telegram_id,
        },
    }


class MyOrdersRequest(BaseModel):
    init_data: str | None = None


@web_app_router.post("/api/my-orders")
async def api_my_orders(
    body: MyOrdersRequest,
    db=Depends(get_db_session),
    authorization: str | None = Header(None),
):
    """
    Return order history for a Telegram Mini App or web-authenticated user.
    Telegram initData is HMAC-verified; web accounts use the existing JWT.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from apps.orders.models import Order
    from apps.users.models import User

    tg_user: dict | None = None
    if body.init_data:
        tg_user = _verify_telegram_init_data(body.init_data, settings.TELEGRAM_BOT_TOKEN)
        if tg_user is None:
            raise HTTPException(status_code=401, detail="Invalid Telegram auth data")

    db_user = None
    if tg_user and tg_user.get("id"):
        user_service = UserService(db)
        db_user = await user_service.get_user_by_telegram(int(tg_user["id"]))

    auth_header = authorization if isinstance(authorization, str) else None
    if not db_user and auth_header:
        user_id = _user_from_bearer(auth_header, db)
        if user_id:
            result = await db.execute(
                select(User).where(
                    User.id == user_id,
                    User.is_deleted.is_(False),
                    User.status == "active",
                )
            )
            db_user = result.scalar_one_or_none()

    if (
        not db_user
        and not body.init_data
        and not auth_header
        and settings.ENVIRONMENT == "testing"
    ):
        result = await db.execute(select(User).limit(1))
        db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Could not identify your account. Please open this store via Telegram.",
        )
    if not _is_active_user(db_user):
        raise HTTPException(status_code=403, detail="This user account is not active.")

    result = await db.execute(
        select(Order)
        .where(Order.user_id == db_user.id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(30)
    )
    orders = result.scalars().all()

    def _serialize(o: Order) -> dict:
        items = []
        for it in o.items or []:
            name = f"Product #{it.product_id}"
            if hasattr(it, "product_name") and it.product_name:
                name = it.product_name
            elif it.product:
                name = it.product.name
            items.append(
                {
                    "product_id": it.product_id,
                    "name": name,
                    "quantity": it.quantity,
                    "unit_price": float(it.unit_price),
                    "total_price": float(it.total_price),
                }
            )
        return {
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status.value if hasattr(o.status, "value") else str(o.status),
            "payment_method": (
                o.payment_method.value
                if hasattr(o.payment_method, "value")
                else str(o.payment_method)
            ),
            "payment_status": (
                o.payment_status.value
                if hasattr(o.payment_status, "value")
                else str(o.payment_status)
            ),
            "subtotal": float(o.subtotal),
            "shipping_fee": float(o.shipping_fee),
            "tax": float(o.tax),
            "total": float(o.total),
            "shipping_city": o.shipping_city,
            "shipping_address": o.shipping_address,
            "shipping_phone": o.shipping_phone,
            "tracking_number": o.tracking_number,
            "customer_notes": o.customer_notes,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "items": items,
        }

    return {"orders": [_serialize(o) for o in orders], "total": len(orders)}


@web_app_router.get("/api/orders")
async def get_orders(
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
):
    """Get order history for the authenticated user."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from apps.orders.models import Order

    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user["id"])
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(50)
    )
    orders = result.scalars().all()

    def _fmt_order(o: "Order") -> dict:
        return {
            "id": o.id,
            "order_number": o.order_number,
            "status": str(o.status.value if hasattr(o.status, "value") else o.status),
            "total": float(o.total),
            "subtotal": float(o.subtotal),
            "shipping_fee": float(o.shipping_fee),
            "payment_method": str(
                o.payment_method.value if hasattr(o.payment_method, "value") else o.payment_method
            ),
            "payment_status": str(
                o.payment_status.value if hasattr(o.payment_status, "value") else o.payment_status
            ),
            "shipping_city": o.shipping_city,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "item_count": len(o.items),
        }

    return {"items": [_fmt_order(o) for o in orders], "total": len(orders)}


@web_app_router.get("/api/user/profile")
async def get_user_profile(
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
):
    """Get profile for the authenticated user."""
    user_service = UserService(db)
    user = await user_service.get_user(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    address_result = await db.execute(
        select(UserAddress)
        .where(UserAddress.user_id == user.id)
        .order_by(UserAddress.is_default.desc(), UserAddress.id.desc())
        .limit(1)
    )
    address = address_result.scalar_one_or_none()
    user_role = getattr(user, "role", "customer")
    user_status = getattr(user, "status", "active")
    preferences_result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    preferences = preferences_result.scalar_one_or_none()
    vendor = None
    if getattr(user_role, "value", user_role) == "vendor":
        vendor_result = await db.execute(select(Vendor).where(Vendor.user_id == user.id))
        vendor = vendor_result.scalar_one_or_none()
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name or "",
        "username": user.username or "",
        "telegram_id": user.telegram_id,
        "phone_number": user.phone_number or "",
        "email": user.email or "",
        "language": user.language,
        "has_custom_profile_picture": (
            _profile_image_filename(getattr(user, "profile_picture", None)) is not None
        ),
        "notification_settings": {
            key: getattr(preferences, key, default)
            for key, default in {
                "email_notifications": True,
                "sms_notifications": True,
                "push_notifications": True,
                "marketing_emails": False,
                "promotional_sms": False,
            }.items()
        },
        "has_password": bool(getattr(user, "password_hash", None)),
        "is_verified": bool(getattr(user, "is_verified", False)),
        "role": getattr(user_role, "value", user_role),
        "status": getattr(user_status, "value", user_status),
        "vendor": (
            {
                "business_name": vendor.business_name,
                "is_approved": vendor.is_approved,
                "is_rejected": vendor.rejected_at is not None,
            }
            if vendor
            else None
        ),
        "city": user.city or "",
        "address": (
            {
                "address_line1": address.address_line1,
                "address_line2": address.address_line2 or "",
                "city": address.city,
                "subcity": address.subcity or "",
                "woreda": address.woreda or "",
                "house_number": address.house_number or "",
                "landmark": address.landmark or "",
            }
            if address
            else None
        ),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _serialize_web_address(address: UserAddress) -> dict:
    return {
        "id": address.id,
        "address_line1": address.address_line1,
        "address_line2": address.address_line2 or "",
        "city": address.city,
        "subcity": address.subcity or "",
        "woreda": address.woreda or "",
        "house_number": address.house_number or "",
        "landmark": address.landmark or "",
        "recipient_name": address.recipient_name,
        "recipient_phone": address.recipient_phone,
        "address_type": address.address_type,
        "is_default": address.is_default,
        "created_at": address.created_at.isoformat() if address.created_at else None,
    }


def _web_wishlist_item(product: Product | None, wishlist: Wishlist) -> dict:
    if product is None:
        return {
            "id": wishlist.product_id,
            "name": None,
            "name_am": None,
            "price": None,
            "image": None,
            "available": False,
            "availability_reason": "not_found",
            "created_at": wishlist.created_at.isoformat() if wishlist.created_at else None,
        }

    status = getattr(product.status, "value", str(product.status))
    available = (
        not product.is_deleted
        and product.deleted_at is None
        and product.status == ProductStatus.ACTIVE
        and product.stock_quantity > 0
    )
    reason = (
        None
        if available
        else "deleted"
        if product.is_deleted or product.deleted_at is not None
        else "out_of_stock"
        if product.status == ProductStatus.OUT_OF_STOCK or product.stock_quantity <= 0
        else "unavailable"
    )
    return {
        "id": product.id,
        "name": product.name,
        "name_am": product.name_am,
        "price": str(product.price),
        "image": (product.images or [None])[0],
        "available": available,
        "availability_reason": reason,
        "status": status,
        "created_at": wishlist.created_at.isoformat() if wishlist.created_at else None,
    }


async def _list_web_wishlist_items(db, user_id: int) -> list[dict]:
    result = await db.execute(
        select(Wishlist, Product)
        .outerjoin(Product, Product.id == Wishlist.product_id)
        .where(Wishlist.user_id == user_id)
        .order_by(Wishlist.created_at.desc(), Wishlist.id.desc())
    )
    return [_web_wishlist_item(product, wishlist) for wishlist, product in result.all()]


async def _lock_web_user_wishlist(db, user_id: int) -> None:
    result = await db.execute(select(User.id).where(User.id == user_id).with_for_update())
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="User not found")


@web_app_router.get("/api/user/wishlist")
async def list_web_user_wishlist(
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
):
    """List current product data for only the authenticated user's wishlist."""
    return {"items": await _list_web_wishlist_items(db, current_user["id"])}


@web_app_router.put("/api/user/wishlist/{product_id}")
async def add_web_user_wishlist_item(
    product_id: int,
    current_user=Depends(get_current_user),
    db=Depends(get_transaction_session),
):
    """Add an active, in-stock product to the authenticated user's wishlist."""
    user_id = current_user["id"]
    try:
        await _lock_web_user_wishlist(db, user_id)
        existing = await db.execute(
            select(Wishlist).where(
                Wishlist.user_id == user_id,
                Wishlist.product_id == product_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return {"added": False}

        product_result = await db.execute(
            select(Product).where(Product.id == product_id).with_for_update()
        )
        product = product_result.scalar_one_or_none()
        if product is None or product.is_deleted or product.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Product not found")
        if product.status != ProductStatus.ACTIVE or product.stock_quantity <= 0:
            raise HTTPException(status_code=409, detail="Product is not currently available")

        db.add(Wishlist(user_id=user_id, product_id=product_id))
        await db.commit()
        return {"added": True}
    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError:
        await db.rollback()
        existing = await db.execute(
            select(Wishlist).where(
                Wishlist.user_id == user_id,
                Wishlist.product_id == product_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return {"added": False}
        raise
    except Exception:
        await db.rollback()
        raise


@web_app_router.delete("/api/user/wishlist/{product_id}", status_code=204)
async def remove_web_user_wishlist_item(
    product_id: int,
    current_user=Depends(get_current_user),
    db=Depends(get_transaction_session),
):
    """Remove a wishlist entry only when it belongs to the authenticated user."""
    try:
        await _lock_web_user_wishlist(db, current_user["id"])
        result = await db.execute(
            select(Wishlist).where(
                Wishlist.user_id == current_user["id"],
                Wishlist.product_id == product_id,
            )
        )
        wishlist = result.scalar_one_or_none()
        if wishlist is not None:
            await db.delete(wishlist)
        await db.commit()
        return Response(status_code=204)
    except Exception:
        await db.rollback()
        raise


@web_app_router.post("/api/user/wishlist/sync")
async def sync_web_user_wishlist(
    data: WebWishlistSync,
    current_user=Depends(get_current_user),
    db=Depends(get_transaction_session),
):
    """Import local wishlist IDs without trusting local names, prices, or images."""
    user_id = current_user["id"]
    skipped: list[dict[str, int | str]] = []
    try:
        await _lock_web_user_wishlist(db, user_id)
        if data.product_ids:
            existing_result = await db.execute(
                select(Wishlist.product_id).where(Wishlist.user_id == user_id)
            )
            existing_ids = set(existing_result.scalars().all())
            requested_ids = [item for item in data.product_ids if item not in existing_ids]
            if requested_ids:
                products_result = await db.execute(
                    select(Product).where(Product.id.in_(requested_ids))
                )
                products = {product.id: product for product in products_result.scalars().all()}
                added_any = False
                for product_id in requested_ids:
                    product = products.get(product_id)
                    if product is None:
                        skipped.append({"product_id": product_id, "reason": "not_found"})
                        continue
                    if product.is_deleted or product.deleted_at is not None:
                        skipped.append({"product_id": product_id, "reason": "deleted"})
                        continue
                    if product.status == ProductStatus.OUT_OF_STOCK or product.stock_quantity <= 0:
                        skipped.append({"product_id": product_id, "reason": "out_of_stock"})
                        continue
                    if product.status != ProductStatus.ACTIVE:
                        skipped.append({"product_id": product_id, "reason": "unavailable"})
                        continue
                    db.add(Wishlist(user_id=user_id, product_id=product_id))
                    added_any = True
                if added_any:
                    await db.commit()
                else:
                    await db.rollback()
        else:
            await db.rollback()
        return {
            "items": await _list_web_wishlist_items(db, user_id),
            "skipped": skipped,
        }
    except Exception:
        await db.rollback()
        raise


async def _set_preferred_shipping_address(db, user_id: int, address_id: int | None) -> None:
    result = await db.execute(select(UserPreferences).where(UserPreferences.user_id == user_id))
    preferences = result.scalar_one_or_none()
    if preferences:
        preferences.default_shipping_address_id = address_id


async def _lock_web_user_address_book(db, user_id: int) -> None:
    result = await db.execute(
        select(User.id).where(User.id == user_id).with_for_update()
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="User not found")


@web_app_router.get("/api/user/addresses")
async def list_web_user_addresses(
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
):
    """List only the authenticated user's saved delivery addresses."""
    result = await db.execute(
        select(UserAddress)
        .where(UserAddress.user_id == current_user["id"])
        .order_by(UserAddress.is_default.desc(), UserAddress.id.desc())
    )
    return {"items": [_serialize_web_address(address) for address in result.scalars().all()]}


@web_app_router.post("/api/user/addresses", status_code=201)
async def create_web_user_address(
    data: WebAddressCreate,
    current_user=Depends(get_current_user),
    db=Depends(get_transaction_session),
):
    """Create an address for the authenticated user and keep a usable default."""
    user_id = current_user["id"]
    try:
        await _lock_web_user_address_book(db, user_id)
        result = await db.execute(
            select(UserAddress)
            .where(UserAddress.user_id == user_id)
            .with_for_update()
        )
        addresses = result.scalars().all()
        is_default = data.is_default or not any(item.is_default for item in addresses)
        if is_default:
            for existing in addresses:
                existing.is_default = False

        address = UserAddress(
            user_id=user_id,
            **data.model_dump(exclude={"is_default"}),
            is_default=is_default,
        )
        db.add(address)
        await db.flush()
        if is_default:
            await _set_preferred_shipping_address(db, user_id, address.id)
        await db.commit()
        return _serialize_web_address(address)
    except Exception:
        await db.rollback()
        raise


@web_app_router.put("/api/user/addresses/{address_id}")
async def update_web_user_address(
    address_id: int,
    data: WebAddressUpdate,
    current_user=Depends(get_current_user),
    db=Depends(get_transaction_session),
):
    """Update an address only when it belongs to the authenticated user."""
    user_id = current_user["id"]
    try:
        await _lock_web_user_address_book(db, user_id)
        result = await db.execute(
            select(UserAddress)
            .where(UserAddress.id == address_id, UserAddress.user_id == user_id)
            .with_for_update()
        )
        address = result.scalar_one_or_none()
        if address is None:
            raise HTTPException(status_code=404, detail="Address not found")

        changes = data.model_dump(exclude_unset=True)
        required_fields = {
            "address_line1": address.address_line1,
            "city": address.city,
            "recipient_name": address.recipient_name,
            "recipient_phone": address.recipient_phone,
        }
        for field in required_fields:
            if field in changes:
                required_fields[field] = changes[field]
        if any(not value for value in required_fields.values()):
            raise HTTPException(
                status_code=422,
                detail="Address line, city, recipient name, and phone are required.",
            )

        requested_default = changes.pop("is_default", None)
        for field, value in changes.items():
            setattr(address, field, value)
        if requested_default is not None:
            result = await db.execute(
                select(UserAddress)
                .where(UserAddress.user_id == user_id)
                .with_for_update()
            )
            addresses = result.scalars().all()
            if requested_default:
                preferred = address
            else:
                preferred = next(
                    (item for item in addresses if item.id != address.id and item.is_default),
                    None,
                )
                preferred = preferred or address
            for existing in addresses:
                existing.is_default = existing.id == preferred.id
            await _set_preferred_shipping_address(db, user_id, preferred.id)

        await db.commit()
        return _serialize_web_address(address)
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise


@web_app_router.delete("/api/user/addresses/{address_id}", status_code=204)
async def delete_web_user_address(
    address_id: int,
    current_user=Depends(get_current_user),
    db=Depends(get_transaction_session),
):
    """Delete an owned address and promote a replacement when needed."""
    user_id = current_user["id"]
    try:
        await _lock_web_user_address_book(db, user_id)
        result = await db.execute(
            select(UserAddress)
            .where(UserAddress.user_id == user_id)
            .order_by(UserAddress.id.desc())
            .with_for_update()
        )
        addresses = result.scalars().all()
        address = next((item for item in addresses if item.id == address_id), None)
        if address is None:
            raise HTTPException(status_code=404, detail="Address not found")

        await db.delete(address)
        remaining = [item for item in addresses if item.id != address_id]
        preferred = next((item for item in remaining if item.is_default), None)
        if remaining and preferred is None:
            preferred = remaining[0]
        for item in remaining:
            item.is_default = item.id == preferred.id if preferred else False
        await _set_preferred_shipping_address(db, user_id, preferred.id if preferred else None)
        await db.commit()
        return Response(status_code=204)
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise


@web_app_router.put("/api/user/profile")
async def update_web_user_profile(
    data: WebProfileUpdate,
    current_user=Depends(get_current_user),
    db=Depends(get_transaction_session),
):
    """Update the authenticated user's personal details and primary delivery address."""
    user_service = UserService(db)
    try:
        user = await user_service.get_user(current_user["id"])
        payload = data.model_dump(exclude_unset=True)
        delete_address = payload.pop("delete_address", False)
        language = payload.pop("language", None)
        notification_settings = payload.pop("notification_settings", None)

        for field in ("phone_number", "email"):
            if field not in payload:
                continue
            incoming = payload.pop(field)
            existing = getattr(user, field)
            if field == "phone_number":
                incoming = Validator.phone(incoming, normalize=True) if incoming else None
                existing = Validator.phone(existing, normalize=True) if existing else None
            elif incoming and existing:
                incoming = incoming.casefold()
                existing = existing.casefold()
            if incoming != existing:
                raise HTTPException(
                    status_code=409,
                    detail="Changing phone or email requires a verified contact workflow.",
                )

        user_fields = {
            field: payload[field]
            for field in (
                "first_name",
                "last_name",
                "city",
                "subcity",
                "woreda",
            )
            if field in payload
        }
        if language is not None:
            user_fields["language"] = language
        if user_fields:
            await user_service.update_user(
                user.id,
                UserUpdate(**user_fields),
                partial=False,
            )
        if language is not None:
            user.preferred_language = language

        if language is not None or notification_settings is not None:
            preferences_result = await db.execute(
                select(UserPreferences).where(UserPreferences.user_id == user.id)
            )
            preferences = preferences_result.scalar_one_or_none()
            if preferences is None:
                preferences = UserPreferences(user_id=user.id)
                db.add(preferences)
            if language is not None:
                preferences.language = language
            if notification_settings is not None:
                for field, value in notification_settings.items():
                    setattr(preferences, field, value)

        address_fields = {
            field: payload[field]
            for field in (
                "address_line1",
                "address_line2",
                "city",
                "subcity",
                "woreda",
                "house_number",
                "landmark",
            )
            if field in payload
        }
        if delete_address or address_fields:
            await _lock_web_user_address_book(db, user.id)
        address_result = await db.execute(
            select(UserAddress)
            .where(UserAddress.user_id == user.id)
            .order_by(UserAddress.is_default.desc(), UserAddress.id.desc())
            .limit(1)
        )
        address = address_result.scalar_one_or_none()

        if delete_address:
            if address:
                await db.delete(address)
                await db.flush()
            remaining_result = await db.execute(
                select(UserAddress)
                .where(UserAddress.user_id == user.id)
                .order_by(UserAddress.is_default.desc(), UserAddress.id.desc())
            )
            remaining = remaining_result.scalars().all()
            preferred = next((item for item in remaining if item.is_default), None)
            if remaining and preferred is None:
                preferred = remaining[0]
            for item in remaining:
                item.is_default = item.id == preferred.id if preferred else False
            await _set_preferred_shipping_address(
                db,
                user.id,
                preferred.id if preferred else None,
            )
        elif address_fields:
            address_line1 = address_fields.get(
                "address_line1",
                address.address_line1 if address else None,
            )
            city = address_fields.get("city", address.city if address else None)
            if not address_line1 or not city:
                raise HTTPException(
                    status_code=422,
                    detail="A delivery address requires both address line and city.",
                )

            recipient_phone = payload.get("phone_number", user.phone_number)
            if not recipient_phone:
                raise HTTPException(
                    status_code=422,
                    detail="Add a phone number before saving a delivery address.",
                )
            recipient_name = " ".join(
                part
                for part in (
                    payload.get("first_name", user.first_name),
                    payload.get("last_name", user.last_name),
                )
                if part
            )
            address_values = {
                **address_fields,
                "address_line1": address_line1,
                "city": city,
                "recipient_name": recipient_name,
                "recipient_phone": recipient_phone,
                "is_default": True,
            }
            if address:
                for field, value in address_values.items():
                    setattr(address, field, value)
            else:
                address = UserAddress(user_id=user.id, **address_values)
                db.add(address)
                await db.flush()
            addresses_result = await db.execute(
                select(UserAddress)
                .where(UserAddress.user_id == user.id)
                .with_for_update()
            )
            for existing in addresses_result.scalars().all():
                existing.is_default = existing.id == address.id
            await _set_preferred_shipping_address(db, user.id, address.id)

        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except NotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("Duplicate profile value for user %s: %s", current_user["id"], exc)
        raise HTTPException(
            status_code=409,
            detail="That phone number or email address is already in use.",
        ) from exc
    except Exception:
        await db.rollback()
        logger.exception("Could not update profile for user %s", current_user["id"])
        raise HTTPException(
            status_code=500,
            detail="Could not save profile changes.",
        ) from None

    return await get_user_profile(current_user=current_user, db=db)


@web_app_router.put("/api/user/profile/photo")
async def upload_web_user_profile_photo(
    image: Annotated[UploadFile, File()],
    current_user=Depends(get_current_user),
    db=Depends(get_transaction_session),
) -> dict[str, bool]:
    """Replace only the authenticated user's profile image with a private normalized copy."""
    from core.constants import MAX_IMAGE_SIZE_BYTES

    try:
        image_data = await image.read(MAX_IMAGE_SIZE_BYTES + 1)
    finally:
        await image.close()
    if not image_data:
        raise HTTPException(status_code=422, detail="Choose a profile image to upload.")
    if len(image_data) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="The photo must be 5 MB or smaller.")
    normalized = _normalize_uploaded_profile_image(image_data)

    filename = f"{uuid4().hex}.webp"
    pointer = f"{_PROFILE_IMAGE_POINTER_PREFIX}{filename}"
    new_path: Path | None = None
    commit_started = False
    try:
        result = await db.execute(
            select(User).where(User.id == current_user["id"]).with_for_update()
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")

        new_path = await asyncio.to_thread(
            _write_private_profile_image,
            filename,
            normalized,
        )
        old_picture = user.profile_picture
        user.profile_picture = pointer
        commit_started = True
        await db.commit()
    except HTTPException:
        await db.rollback()
        if new_path is not None and not commit_started:
            try:
                await asyncio.to_thread(new_path.unlink, missing_ok=True)
            except OSError:
                logger.exception("Could not clean up a failed profile image upload")
        raise
    except Exception as exc:
        await db.rollback()
        if new_path is not None and not commit_started:
            try:
                await asyncio.to_thread(new_path.unlink, missing_ok=True)
            except OSError:
                logger.exception("Could not clean up a failed profile image upload")
        logger.exception("Could not save profile image for user %s", current_user["id"])
        raise HTTPException(status_code=500, detail="Could not save the profile image.") from exc

    cleanup_pending = False
    if _profile_image_filename(old_picture) is not None:
        try:
            await _remove_private_profile_image(old_picture)
        except OSError:
            cleanup_pending = True
            logger.exception("Could not remove the previous profile image for user %s", user.id)
    return {
        "uploaded": True,
        "has_custom_profile_picture": True,
        "cleanup_pending": cleanup_pending,
    }


@web_app_router.delete("/api/user/profile/photo")
async def remove_web_user_profile_photo(
    current_user=Depends(get_current_user),
    db=Depends(get_transaction_session),
) -> dict[str, bool]:
    """Remove only a profile image uploaded to this account's private image storage."""
    try:
        result = await db.execute(
            select(User).where(User.id == current_user["id"]).with_for_update()
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        if _profile_image_filename(user.profile_picture) is None:
            raise HTTPException(status_code=404, detail="No uploaded profile image to remove.")

        old_picture = user.profile_picture
        user.profile_picture = None
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("Could not remove profile image for user %s", current_user["id"])
        raise HTTPException(status_code=500, detail="Could not remove the profile image.") from exc

    cleanup_pending = False
    try:
        await _remove_private_profile_image(old_picture)
    except OSError:
        cleanup_pending = True
        logger.exception("Could not remove profile image file for user %s", user.id)
    return {"removed": True, "has_custom_profile_picture": False, "cleanup_pending": cleanup_pending}


@web_app_router.get("/api/user/profile/photo")
async def get_user_profile_photo(
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
) -> Response:
    """Serve the owner's private uploaded image or proxy their Telegram avatar."""
    user = await UserService(db).get_user(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    local_image_path = _profile_image_path(user.profile_picture)
    if local_image_path is not None:
        try:
            image_data = await asyncio.to_thread(local_image_path.read_bytes)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="No profile photo is available.") from exc
        return Response(
            content=image_data,
            media_type="image/webp",
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot is not configured")

    try:
        async with Bot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
            photo_ids: list[str] = []

            if user.telegram_id:
                try:
                    photos = await bot.get_user_profile_photos(
                        user_id=user.telegram_id,
                        limit=1,
                    )
                    if photos.photos and photos.photos[0]:
                        photo_ids.append(photos.photos[0][-1].file_id)
                except TelegramError as exc:
                    logger.warning(
                        "Could not retrieve Telegram profile photo for user %s: %s",
                        user.telegram_id,
                        exc,
                    )

            if user.profile_picture:
                photo_ids.append(user.profile_picture)

            for file_id in dict.fromkeys(photo_ids):
                try:
                    telegram_file = await bot.get_file(file_id)
                    image_data = await telegram_file.download_as_bytearray()
                    media_type = mimetypes.guess_type(telegram_file.file_path or "")[0]
                    if media_type not in {"image/jpeg", "image/png", "image/webp"}:
                        media_type = "image/jpeg"
                    return Response(
                        content=bytes(image_data),
                        media_type=media_type,
                        headers={
                            "Cache-Control": "private, no-store",
                            "X-Content-Type-Options": "nosniff",
                        },
                    )
                except TelegramError as exc:
                    logger.warning("Could not download profile photo: %s", exc)

            try:
                bot_user = await bot.get_me()
                banner = await bot.get_user_profile_photos(
                    user_id=bot_user.id,
                    limit=1,
                )
                if banner.photos and banner.photos[0]:
                    telegram_file = await bot.get_file(banner.photos[0][-1].file_id)
                    image_data = await telegram_file.download_as_bytearray()
                    media_type = mimetypes.guess_type(telegram_file.file_path or "")[0]
                    if media_type not in {"image/jpeg", "image/png", "image/webp"}:
                        media_type = "image/jpeg"
                    return Response(
                        content=bytes(image_data),
                        media_type=media_type,
                        headers={
                            "Cache-Control": "private, no-store",
                            "X-Content-Type-Options": "nosniff",
                        },
                    )
            except TelegramError as exc:
                logger.warning("Could not retrieve the store banner photo: %s", exc)

    except TelegramError as exc:
        logger.exception("Telegram profile image service is unavailable: %s", exc)
        raise HTTPException(status_code=502, detail="Could not retrieve profile photo") from exc

    raise HTTPException(status_code=404, detail="No profile photo is available")


@web_app_router.get("/api/bot-link")
async def get_telegram_bot_link() -> dict[str, str]:
    """Return the public t.me link for this configured Telegram bot."""
    global _telegram_bot_link_cache
    if _telegram_bot_link_cache:
        return {"url": _telegram_bot_link_cache}
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot is not configured")
    try:
        async with Bot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
            bot_user = await bot.get_me()
    except TelegramError as exc:
        logger.exception("Could not retrieve Telegram bot username: %s", exc)
        raise HTTPException(status_code=502, detail="Could not retrieve Telegram bot link") from exc
    if not bot_user.username:
        raise HTTPException(status_code=404, detail="Telegram bot has no public username")
    _telegram_bot_link_cache = f"https://t.me/{bot_user.username}"
    return {"url": _telegram_bot_link_cache}


__all__ = ["web_app_router"]
