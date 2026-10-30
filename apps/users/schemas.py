# ============================
# WOLLOYEWA STORE BOT - USER SCHEMAS
# ============================
"""Pydantic schemas for user request/response validation."""

from datetime import date, datetime

from pydantic import EmailStr, Field, field_validator, model_validator, validator

from apps.common.schemas import BaseSchema, IdSchema, TimestampSchema
from core.constants import Gender, UserRole, UserStatus

# ============================
# User Schemas
# ============================


class UserBase(BaseSchema):
    """Base user schema."""

    telegram_id: int = Field(..., description="Telegram user ID")
    username: str | None = Field(None, max_length=100, description="Telegram username")
    first_name: str = Field(..., max_length=100, description="First name")
    last_name: str | None = Field(None, max_length=100, description="Last name")
    phone_number: str | None = Field(None, max_length=20, description="Phone number")
    email: EmailStr | None = Field(None, description="Email address")
    language: str = Field("am", max_length=10, description="Preferred language")

    @validator("phone_number")
    def validate_phone(cls, v):
        if v:
            from core.utils.validators import validate_phone

            is_valid, _ = validate_phone(v)
            if not is_valid:
                raise ValueError("Invalid Ethiopian phone number")
        return v


class UserCreate(UserBase):
    """Schema for creating a user."""

    pass


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    username: str | None = Field(None, max_length=100)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone_number: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    language: str | None = Field(None, max_length=10)
    profile_picture: str | None = Field(None, max_length=500)
    location_lat: float | None = None
    location_lng: float | None = None
    city: str | None = Field(None, max_length=100)
    subcity: str | None = Field(None, max_length=100)
    woreda: str | None = Field(None, max_length=50)

    @validator("phone_number")
    def validate_phone(cls, v):
        if v:
            from core.utils.validators import validate_phone

            is_valid, _ = validate_phone(v)
            if not is_valid:
                raise ValueError("Invalid Ethiopian phone number")
        return v


class UserResponse(UserBase, IdSchema, TimestampSchema):
    """Schema for user response."""

    role: UserRole = Field(default=UserRole.CUSTOMER)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    gender: Gender | None = None
    date_of_birth: date | None = None
    profile_picture: str | None = None
    city: str | None = None
    subcity: str | None = None
    woreda: str | None = None
    house_number: str | None = None
    is_verified: bool = False
    last_active: datetime | None = None

    class Config:
        from_attributes = True


# ============================
# Authentication Schemas
# ============================


class UserRegister(BaseSchema):
    """Schema for user registration."""

    telegram_id: int = Field(..., description="Telegram user ID")
    init_data: str | None = Field(
        None,
        max_length=8192,
        description="Telegram Mini App initData used to verify the Telegram identity",
    )
    username: str | None = Field(None, max_length=100)
    first_name: str = Field(..., max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone_number: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    language: str = Field("am", max_length=10)

    @validator("phone_number")
    def validate_phone(cls, v):
        if v:
            from core.utils.validators import validate_phone

            is_valid, _ = validate_phone(v)
            if not is_valid:
                raise ValueError("Invalid Ethiopian phone number")
        return v


class UserLogin(BaseSchema):
    """Schema for user login."""

    telegram_id: int | None = Field(None, description="Telegram user ID")
    init_data: str | None = Field(
        None,
        max_length=8192,
        description="Signed Telegram Mini App initData",
    )
    phone_number: str | None = Field(None, max_length=20)
    password: str | None = Field(None, max_length=256)
    ip_address: str | None = Field(None, description="Client IP address")

    @model_validator(mode="after")
    def validate_login_credentials(self):
        if not self.telegram_id and not self.phone_number:
            raise ValueError("Either telegram_id or phone_number is required")
        if self.telegram_id and self.phone_number:
            raise ValueError("Use either Telegram login or phone login, not both")
        if self.phone_number and not self.password:
            raise ValueError("Password is required for phone login")
        if self.telegram_id and self.password:
            raise ValueError("Do not send a password with Telegram login")
        return self


class TokenResponse(BaseSchema):
    """Schema for authentication token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserResponse = Field(..., description="Authenticated user")


class ChangePasswordRequest(BaseSchema):
    """Schema for password change request."""

    current_password: str = Field(..., min_length=6, description="Current password")
    new_password: str = Field(..., min_length=6, description="New password")
    confirm_password: str = Field(..., min_length=6, description="Confirm new password")

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class PasswordResetStartRequest(BaseSchema):
    """Start password recovery for a registered Ethiopian phone number."""

    phone_number: str = Field(..., min_length=10, max_length=20)

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value):
        from core.utils.validators import Validator

        try:
            return Validator.phone(value, normalize=True)
        except ValueError as exc:
            raise ValueError("Invalid Ethiopian phone number") from exc


class ResetPasswordRequest(BaseSchema):
    """Schema for password reset request."""

    phone_number: str = Field(
        ..., min_length=10, max_length=20, description="Registered Ethiopian phone number"
    )
    otp: str = Field(..., pattern=r"^\d{6}$", description="Six-digit one-time password")
    new_password: str = Field(..., min_length=6, description="New password")
    confirm_password: str = Field(..., min_length=6, description="Confirm new password")

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value):
        from core.utils.validators import Validator

        try:
            return Validator.phone(value, normalize=True)
        except ValueError as exc:
            raise ValueError("Invalid Ethiopian phone number") from exc

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v


# ============================
# Vendor Schemas
# ============================


class VendorBase(BaseSchema):
    """Base vendor schema."""

    business_name: str = Field(..., max_length=200, description="Business name")
    business_license: str | None = Field(
        None, max_length=100, description="Business license number"
    )
    tin_number: str | None = Field(None, max_length=50, description="Tax identification number")
    business_address: str | None = Field(None, description="Business address")
    business_phone: str | None = Field(None, max_length=20, description="Business phone")
    business_email: EmailStr | None = Field(None, description="Business email")
    license_document_file_id: str | None = Field(None, max_length=255)
    license_document_type: str | None = Field(None, max_length=20)
    business_category: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)
    subcity: str | None = Field(None, max_length=100)
    specific_location: str | None = None
    maps_link: str | None = Field(None, max_length=500)
    bank_name: str | None = Field(None, max_length=100)
    bank_account_name: str | None = Field(None, max_length=200)
    bank_account_number: str | None = Field(None, max_length=64)
    website: str | None = Field(None, max_length=255, description="Website URL")
    description: str | None = Field(None, description="Business description")


class VendorCreate(VendorBase):
    """Schema for creating a vendor."""

    pass


class VendorApplicationCreate(VendorCreate):
    """Validated data required to submit a complete vendor application."""

    business_name: str = Field(..., min_length=2, max_length=200)
    business_license: str = Field(..., min_length=3, max_length=100)
    tin_number: str = Field(..., min_length=10, max_length=10)
    license_document_file_id: str = Field(..., min_length=1, max_length=255)
    license_document_type: str = Field(..., pattern="^(photo|document)$")
    business_category: str = Field(..., min_length=2, max_length=100)
    region: str = Field(..., min_length=2, max_length=100)
    city: str = Field(..., min_length=2, max_length=100)
    subcity: str = Field(..., min_length=2, max_length=100)
    specific_location: str = Field(..., min_length=3, max_length=1000)
    business_address: str = Field(..., min_length=5, max_length=2000)
    business_phone: str = Field(..., min_length=10, max_length=20)
    bank_name: str = Field(..., min_length=2, max_length=100)
    bank_account_name: str = Field(..., min_length=2, max_length=200)
    bank_account_number: str = Field(..., min_length=6, max_length=64)
    maps_link: str | None = Field(None, max_length=500)

    @field_validator("business_license")
    @classmethod
    def validate_license(cls, value: str) -> str:
        from core.utils.validators import validate_business_license

        value = value.strip().upper()
        if not validate_business_license(value):
            raise ValueError("Invalid Ethiopian business license number")
        return value

    @field_validator("tin_number")
    @classmethod
    def validate_tin(cls, value: str) -> str:
        from core.utils.validators import validate_ethiopian_tin

        value = value.strip()
        if not validate_ethiopian_tin(value):
            raise ValueError("TIN must contain 10 digits")
        return value

    @field_validator("business_phone")
    @classmethod
    def validate_business_phone(cls, value: str) -> str:
        from core.utils.validators import Validator

        try:
            return Validator.phone(value, normalize=True)
        except ValueError as exc:
            raise ValueError("Invalid Ethiopian phone number") from exc

    @field_validator("bank_account_number")
    @classmethod
    def validate_account_number(cls, value: str) -> str:
        normalized = "".join(value.split()).replace("-", "")
        if not normalized.isdigit() or not 6 <= len(normalized) <= 34:
            raise ValueError("Bank account number must contain 6 to 34 digits")
        return normalized

    @field_validator("maps_link")
    @classmethod
    def validate_maps_link(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from urllib.parse import urlsplit

        normalized = value.strip()
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Maps link must be an absolute HTTP(S) URL")
        return normalized


class VendorUpdate(BaseSchema):
    """Schema for updating a vendor."""

    business_name: str | None = Field(None, max_length=200)
    business_license: str | None = Field(None, max_length=100)
    tin_number: str | None = Field(None, max_length=50)
    license_document_file_id: str | None = Field(None, max_length=255)
    license_document_type: str | None = Field(None, max_length=20)
    business_category: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)
    subcity: str | None = Field(None, max_length=100)
    specific_location: str | None = None
    business_address: str | None = None
    business_phone: str | None = Field(None, max_length=20)
    business_email: EmailStr | None = None
    maps_link: str | None = Field(None, max_length=500)
    bank_name: str | None = Field(None, max_length=100)
    bank_account_name: str | None = Field(None, max_length=200)
    bank_account_number: str | None = Field(None, max_length=64)
    website: str | None = Field(None, max_length=255)
    description: str | None = None
    logo_url: str | None = Field(None, max_length=500)
    cover_image: str | None = Field(None, max_length=500)


class VendorResponse(VendorBase, IdSchema, TimestampSchema):
    """Schema for vendor response."""

    user_id: int = Field(..., description="Associated user ID")
    logo_url: str | None = None
    cover_image: str | None = None
    rating: float = Field(0.0, ge=0, le=5)
    total_sales: int = Field(0)
    total_products: int = Field(0)
    is_approved: bool = False
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None

    class Config:
        from_attributes = True


# ============================
# Address Schemas
# ============================


class AddressBase(BaseSchema):
    """Base address schema."""

    address_line1: str = Field(..., max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    subcity: str | None = Field(None, max_length=100)
    woreda: str | None = Field(None, max_length=50)
    house_number: str | None = Field(None, max_length=50)
    landmark: str | None = Field(None, max_length=255)
    recipient_name: str = Field(..., max_length=100)
    recipient_phone: str = Field(..., max_length=20)
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool = False
    address_type: str = Field("home", description="home, work, or other")


class AddressCreate(AddressBase):
    """Schema for creating an address."""

    pass


class AddressUpdate(BaseSchema):
    """Schema for updating an address."""

    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    subcity: str | None = Field(None, max_length=100)
    woreda: str | None = Field(None, max_length=50)
    house_number: str | None = Field(None, max_length=50)
    landmark: str | None = Field(None, max_length=255)
    recipient_name: str | None = Field(None, max_length=100)
    recipient_phone: str | None = Field(None, max_length=20)
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool | None = None
    address_type: str | None = None


class AddressResponse(AddressBase, IdSchema, TimestampSchema):
    """Schema for address response."""

    user_id: int = Field(..., description="User ID")

    class Config:
        from_attributes = True


# ============================
# Preferences Schemas
# ============================


class PreferencesBase(BaseSchema):
    """Base preferences schema."""

    email_notifications: bool = True
    sms_notifications: bool = True
    push_notifications: bool = True
    marketing_emails: bool = False
    promotional_sms: bool = False
    language: str = "am"
    currency: str = "ETB"
    share_activity: bool = False


class PreferencesUpdate(BaseSchema):
    """Schema for updating preferences."""

    email_notifications: bool | None = None
    sms_notifications: bool | None = None
    push_notifications: bool | None = None
    marketing_emails: bool | None = None
    promotional_sms: bool | None = None
    language: str | None = Field(None, max_length=10)
    currency: str | None = Field(None, max_length=3)
    share_activity: bool | None = None


class PreferencesResponse(PreferencesBase, IdSchema, TimestampSchema):
    """Schema for preferences response."""

    user_id: int = Field(..., description="User ID")

    class Config:
        from_attributes = True


__all__ = [
    "AddressBase",
    "AddressCreate",
    "AddressResponse",
    "AddressUpdate",
    "ChangePasswordRequest",
    "PasswordResetStartRequest",
    "ResetPasswordRequest",
    "PreferencesBase",
    "PreferencesResponse",
    "PreferencesUpdate",
    "ResetPasswordRequest",
    "TokenResponse",
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserRegister",
    "UserResponse",
    "UserUpdate",
    "VendorBase",
    "VendorCreate",
    "VendorResponse",
    "VendorUpdate",
]
