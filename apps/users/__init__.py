# ============================
# WOLLOYEWA STORE BOT - USERS MODULE
# ============================
"""User management module including customers and vendors."""

from apps.users.models import User, Vendor, UserAddress, UserPreferences
from apps.users.services import UserService, VendorService, AuthService
from apps.users.repository import UserRepository, VendorRepository
from apps.users.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    UserRegister,
    TokenResponse,
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    AddressCreate,
    AddressUpdate,
    AddressResponse,
    PreferencesUpdate,
    PreferencesResponse,
    ChangePasswordRequest,
    ResetPasswordRequest,
)
from apps.users.preferences import (
    UserPreferencesManager,
    get_user_preferences,
    update_user_preferences,
    get_notification_settings,
    update_notification_settings,
)

__all__ = [
    # Models
    "User",
    "Vendor",
    "UserAddress",
    "UserPreferences",
    # Services
    "UserService",
    "VendorService",
    "AuthService",
    # Repositories
    "UserRepository",
    "VendorRepository",
    # Schemas
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "UserRegister",
    "TokenResponse",
    "VendorCreate",
    "VendorUpdate",
    "VendorResponse",
    "AddressCreate",
    "AddressUpdate",
    "AddressResponse",
    "PreferencesUpdate",
    "PreferencesResponse",
    "ChangePasswordRequest",
    "ResetPasswordRequest",
    # Preferences
    "UserPreferencesManager",
    "get_user_preferences",
    "update_user_preferences",
    "get_notification_settings",
    "update_notification_settings",
]