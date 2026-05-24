# ============================
# WOLLOYEWA STORE BOT - USER SCHEMAS
# ============================
"""Pydantic schemas for user request/response validation."""

from datetime import datetime, date
from typing import Optional, List
from pydantic import Field, EmailStr, validator

from apps.common.schemas import BaseSchema, IdSchema, TimestampSchema
from core.constants import UserRole, UserStatus, Gender


# ============================
# User Schemas
# ============================

class UserBase(BaseSchema):
    """Base user schema."""
    
    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, max_length=100, description="Telegram username")
    first_name: str = Field(..., max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    language: str = Field("am", max_length=10, description="Preferred language")
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if v:
            from core.utils.validators import validate_phone
            is_valid, _ = validate_phone(v)
            if not is_valid:
                raise ValueError('Invalid Ethiopian phone number')
        return v


class UserCreate(UserBase):
    """Schema for creating a user."""
    
    pass


class UserUpdate(BaseSchema):
    """Schema for updating a user."""
    
    username: Optional[str] = Field(None, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    language: Optional[str] = Field(None, max_length=10)
    profile_picture: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    subcity: Optional[str] = Field(None, max_length=100)
    woreda: Optional[str] = Field(None, max_length=50)
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if v:
            from core.utils.validators import validate_phone
            is_valid, _ = validate_phone(v)
            if not is_valid:
                raise ValueError('Invalid Ethiopian phone number')
        return v


class UserResponse(UserBase, IdSchema, TimestampSchema):
    """Schema for user response."""
    
    role: UserRole = Field(default=UserRole.CUSTOMER)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    profile_picture: Optional[str] = None
    city: Optional[str] = None
    subcity: Optional[str] = None
    woreda: Optional[str] = None
    house_number: Optional[str] = None
    is_verified: bool = False
    last_active: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================
# Authentication Schemas
# ============================

class UserRegister(BaseSchema):
    """Schema for user registration."""
    
    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, max_length=100)
    first_name: str = Field(..., max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    language: str = Field("am", max_length=10)
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if v:
            from core.utils.validators import validate_phone
            is_valid, _ = validate_phone(v)
            if not is_valid:
                raise ValueError('Invalid Ethiopian phone number')
        return v


class UserLogin(BaseSchema):
    """Schema for user login."""
    
    telegram_id: Optional[int] = Field(None, description="Telegram user ID")
    phone_number: Optional[str] = Field(None, max_length=20)
    ip_address: Optional[str] = Field(None, description="Client IP address")
    
    @validator('telegram_id', 'phone_number')
    def validate_login_credentials(cls, v, values):
        if not v and not values.get('telegram_id'):
            raise ValueError('Either telegram_id or phone_number is required')
        return v


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
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class ResetPasswordRequest(BaseSchema):
    """Schema for password reset request."""
    
    phone_number: str = Field(..., description="Registered phone number")
    otp: str = Field(..., description="One-time password")
    new_password: str = Field(..., min_length=6, description="New password")
    confirm_password: str = Field(..., min_length=6, description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


# ============================
# Vendor Schemas
# ============================

class VendorBase(BaseSchema):
    """Base vendor schema."""
    
    business_name: str = Field(..., max_length=200, description="Business name")
    business_license: Optional[str] = Field(None, max_length=100, description="Business license number")
    tin_number: Optional[str] = Field(None, max_length=50, description="Tax identification number")
    business_address: Optional[str] = Field(None, description="Business address")
    business_phone: Optional[str] = Field(None, max_length=20, description="Business phone")
    business_email: Optional[EmailStr] = Field(None, description="Business email")
    website: Optional[str] = Field(None, max_length=255, description="Website URL")
    description: Optional[str] = Field(None, description="Business description")


class VendorCreate(VendorBase):
    """Schema for creating a vendor."""
    
    pass


class VendorUpdate(BaseSchema):
    """Schema for updating a vendor."""
    
    business_name: Optional[str] = Field(None, max_length=200)
    business_license: Optional[str] = Field(None, max_length=100)
    tin_number: Optional[str] = Field(None, max_length=50)
    business_address: Optional[str] = None
    business_phone: Optional[str] = Field(None, max_length=20)
    business_email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    cover_image: Optional[str] = Field(None, max_length=500)


class VendorResponse(VendorBase, IdSchema, TimestampSchema):
    """Schema for vendor response."""
    
    user_id: int = Field(..., description="Associated user ID")
    logo_url: Optional[str] = None
    cover_image: Optional[str] = None
    rating: float = Field(0.0, ge=0, le=5)
    total_sales: int = Field(0)
    total_products: int = Field(0)
    is_approved: bool = False
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


# ============================
# Address Schemas
# ============================

class AddressBase(BaseSchema):
    """Base address schema."""
    
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    subcity: Optional[str] = Field(None, max_length=100)
    woreda: Optional[str] = Field(None, max_length=50)
    house_number: Optional[str] = Field(None, max_length=50)
    landmark: Optional[str] = Field(None, max_length=255)
    recipient_name: str = Field(..., max_length=100)
    recipient_phone: str = Field(..., max_length=20)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False
    address_type: str = Field("home", description="home, work, or other")


class AddressCreate(AddressBase):
    """Schema for creating an address."""
    
    pass


class AddressUpdate(BaseSchema):
    """Schema for updating an address."""
    
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    subcity: Optional[str] = Field(None, max_length=100)
    woreda: Optional[str] = Field(None, max_length=50)
    house_number: Optional[str] = Field(None, max_length=50)
    landmark: Optional[str] = Field(None, max_length=255)
    recipient_name: Optional[str] = Field(None, max_length=100)
    recipient_phone: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: Optional[bool] = None
    address_type: Optional[str] = None


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
    
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    promotional_sms: Optional[bool] = None
    language: Optional[str] = Field(None, max_length=10)
    currency: Optional[str] = Field(None, max_length=3)
    share_activity: Optional[bool] = None


class PreferencesResponse(PreferencesBase, IdSchema, TimestampSchema):
    """Schema for preferences response."""
    
    user_id: int = Field(..., description="User ID")
    
    class Config:
        from_attributes = True


__all__ = [
    "UserBase", "UserCreate", "UserUpdate", "UserResponse",
    "UserRegister", "UserLogin", "TokenResponse",
    "ChangePasswordRequest", "ResetPasswordRequest",
    "VendorBase", "VendorCreate", "VendorUpdate", "VendorResponse",
    "AddressBase", "AddressCreate", "AddressUpdate", "AddressResponse",
    "PreferencesBase", "PreferencesUpdate", "PreferencesResponse",
]