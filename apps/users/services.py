# ============================
# WOLLOYEWA STORE BOT - USER SERVICES
# ============================
"""Business logic for user management, authentication, and vendor operations."""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import User, UserPreferences, Vendor
from apps.users.repository import UserRepository, VendorRepository
from apps.users.schemas import (
    ChangePasswordRequest,
    UserCreate,
    UserLogin,
    UserRegister,
    UserUpdate,
    VendorApplicationCreate,
    VendorCreate,
    VendorUpdate,
)
from core.events import (
    USER_LOGIN,
    USER_REGISTERED,
    USER_UPDATED,
    VENDOR_APPROVED,
    VENDOR_REGISTERED,
    VENDOR_REJECTED,
    emit_event,
)
from core.exceptions import (
    AuthenticationError,
    DuplicateRecordError,
    NotFoundError,
    ValidationError,
)
from core.logger import logger
from core.security import create_access_token, hash_password, verify_password
from core.utils.validators import Validator


class AuthService:
    """Authentication service for login, registration, and token management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, data: UserRegister) -> User:
        """
        Register a new user.

        Args:
            data: User registration data

        Returns:
            Created user

        Raises:
            ValidationError: If validation fails
            DuplicateRecordError: If user already exists
        """
        # Validate phone number if provided
        phone = None
        if data.phone_number:
            try:
                phone = Validator.phone(data.phone_number, normalize=True)
            except ValueError as exc:
                raise ValidationError(f"Invalid phone number: {data.phone_number}") from exc

        # Check if user already exists
        if data.telegram_id:
            existing = await self.user_repo.get_by_telegram(data.telegram_id)
            if existing:
                raise DuplicateRecordError("User", "telegram_id", data.telegram_id)

        if phone:
            existing = await self.user_repo.get_by_phone(phone)
            if existing:
                raise DuplicateRecordError("User", "phone_number", phone)

        # Create user
        user_data = UserCreate(
            telegram_id=data.telegram_id,
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            phone_number=phone,
            email=data.email,
            language=data.language,
        )

        user = await self.user_repo.create(user_data.dict())

        # Create default preferences
        preferences = UserPreferences(
            user_id=user.id,
            language=data.language,
        )
        self.db.add(preferences)
        await self.db.flush()

        # Emit event
        await emit_event(
            USER_REGISTERED,
            {
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "role": user.role,
            },
            sync=False,
        )

        logger.info(f"New user registered: {user.id} (telegram: {user.telegram_id})")
        return user

    async def login(self, data: UserLogin) -> tuple[User, str]:
        """
        Authenticate user and return access token.

        Args:
            data: Login credentials

        Returns:
            Tuple of (user, access_token)

        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Find user by telegram_id or phone
        user = None
        if data.telegram_id:
            user = await self.user_repo.get_by_telegram(data.telegram_id)
        elif data.phone_number:
            try:
                normalized = Validator.phone(data.phone_number, normalize=True)
            except ValueError as exc:
                raise AuthenticationError("Invalid credentials") from exc
            user = await self.user_repo.get_by_phone(normalized)

        if not user:
            raise AuthenticationError("Invalid credentials")

        # Phone-based login must prove knowledge of the account password.
        if data.phone_number:
            if (
                not data.password
                or not user.password_hash
                or not verify_password(data.password, user.password_hash)
            ):
                raise AuthenticationError("Invalid credentials")

        # Check if user is active
        if user.status != "active":
            raise AuthenticationError("Account is not active")

        # Update last active
        await self.user_repo.update_last_active(user.id, data.ip_address)

        # Create access token
        token_data = {
            "sub": str(user.id),
            "telegram_id": user.telegram_id,
            "role": user.role,
            "token_version": user.token_version,
        }
        access_token = create_access_token(token_data)

        # Emit event
        await emit_event(
            USER_LOGIN,
            {
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "ip_address": data.ip_address,
            },
            sync=False,
        )

        logger.info(f"User logged in: {user.id}")
        return user, access_token

    async def change_password(self, user_id: int, data: ChangePasswordRequest) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            data: Password change request

        Returns:
            True if successful
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        if not user.password_hash:
            raise AuthenticationError("Password is not configured for this account")
        if not verify_password(data.current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")

        await self.user_repo.update(user_id, {"password_hash": hash_password(data.new_password)})
        logger.info(f"Password changed for user {user_id}")
        return True

    async def verify_telegram_auth(self, auth_data: dict[str, Any]) -> User | None:
        """
        Verify Telegram login authorization.

        Args:
            auth_data: Telegram authentication data

        Returns:
            User if verification successful
        """
        # Implement Telegram login verification
        # https://core.telegram.org/widgets/login#checking-authorization
        telegram_id = auth_data.get("id")
        if not telegram_id:
            return None

        user = await self.user_repo.get_by_telegram(int(telegram_id))
        return user


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def get_user(self, user_id: int) -> User:
        """Get user by ID."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user

    async def get_user_by_telegram(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        return await self.user_repo.get_by_telegram(telegram_id)

    async def update_user(
        self,
        user_id: int,
        data: UserUpdate | dict[str, Any],
        *,
        partial: bool = True,
    ) -> User:
        """Update user information."""
        update_data = (
            data.model_dump(exclude_unset=True)
            if isinstance(data, UserUpdate)
            else dict(data)
        )

        # Validate phone if provided
        if update_data.get("phone_number"):
            try:
                update_data["phone_number"] = Validator.phone(
                    update_data["phone_number"],
                    normalize=True,
                )
            except ValueError as exc:
                raise ValidationError(
                    f"Invalid phone number: {update_data['phone_number']}"
                ) from exc

        user = await self.user_repo.update(
            user_id,
            update_data,
            partial=partial,
        )
        if not user:
            raise NotFoundError("User", user_id)

        # Emit event
        await emit_event(
            USER_UPDATED,
            {
                "user_id": user.id,
                "updated_fields": list(update_data.keys()),
            },
            sync=False,
        )

        return user

    async def get_or_create_user(
        self, telegram_id: int, first_name: str, username: str | None = None
    ) -> User:
        """Get existing user or create new one."""
        user = await self.user_repo.get_by_telegram(telegram_id)
        if not user:
            user = await self.user_repo.create(
                {
                    "telegram_id": telegram_id,
                    "first_name": first_name,
                    "username": username,
                }
            )

            # Create preferences
            preferences = UserPreferences(user_id=user.id)
            self.db.add(preferences)
            await self.db.flush()

        return user

    async def get_user_stats(self, user_id: int) -> dict[str, Any]:
        """Get user statistics (orders, spending, etc.)."""
        user = await self.get_user(user_id)

        # Get order statistics
        from apps.orders.repository import OrderRepository

        order_repo = OrderRepository(self.db)
        order_stats = await order_repo.get_user_stats(user_id)

        return {
            "user_id": user_id,
            "join_date": user.created_at,
            "last_active": user.last_active,
            "total_orders": order_stats.get("total_orders", 0),
            "total_spent": order_stats.get("total_spent", 0),
            "average_order_value": order_stats.get("avg_order_value", 0),
        }


class VendorService:
    """Service for vendor management operations."""

    _required_application_fields = (
        "business_name",
        "business_license",
        "tin_number",
        "license_document_file_id",
        "license_document_type",
        "business_category",
        "region",
        "city",
        "subcity",
        "specific_location",
        "business_phone",
        "bank_name",
        "bank_account_name",
        "bank_account_number",
    )

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vendor_repo = VendorRepository(db)
        self.user_repo = UserRepository(db)

    @classmethod
    def is_application_complete(cls, vendor: Vendor) -> bool:
        """Return whether a stored application contains every required review field."""
        return all(
            getattr(vendor, field, None)
            for field in cls._required_application_fields
        )

    async def create_vendor(
        self,
        user_id: int,
        data: VendorCreate | VendorApplicationCreate,
        *,
        notify_admins_on_event: bool = True,
    ) -> Vendor:
        """
        Create a vendor profile.

        Args:
            user_id: User ID (must be a customer)
            data: Vendor creation data

        Returns:
            Created vendor
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        if user.is_deleted or user.status != "active":
            raise ValidationError("Inactive accounts cannot submit vendor applications")

        existing = await self.vendor_repo.get_by_user_id(user_id)
        if existing and (
            existing.is_approved
            or (existing.rejected_at is None and self.is_application_complete(existing))
        ):
            raise DuplicateRecordError("Vendor", "user_id", user_id)
        if user.role not in {"customer", "vendor"}:
            raise ValidationError("This account cannot submit a vendor application")

        vendor_data = data.model_dump(exclude_unset=True)
        if vendor_data.get("business_license"):
            license_owner = await self.vendor_repo.get_by_license(
                vendor_data["business_license"]
            )
            if license_owner and license_owner.user_id != user_id:
                raise DuplicateRecordError(
                    "Vendor", "business_license", vendor_data["business_license"]
                )
        if vendor_data.get("tin_number"):
            tin_owner = await self.vendor_repo.get_by_tin(vendor_data["tin_number"])
            if tin_owner and tin_owner.user_id != user_id:
                raise DuplicateRecordError("Vendor", "tin_number", vendor_data["tin_number"])

        vendor_data["business_address"] = (
            vendor_data.get("business_address")
            or ", ".join(
                value
                for value in (
                    vendor_data.get("region"),
                    vendor_data.get("city"),
                    vendor_data.get("subcity"),
                    vendor_data.get("specific_location"),
                )
                if value
            )
        )
        if existing:
            vendor = await self.vendor_repo.update(
                existing.id,
                {
                    **vendor_data,
                    "is_approved": False,
                    "rejected_at": None,
                    "rejection_reason": None,
                },
                partial=False,
            )
            if not vendor:
                raise NotFoundError("Vendor", existing.id)
        else:
            vendor = await self.vendor_repo.create({"user_id": user_id, **vendor_data})

        if vendor_data.get("business_phone"):
            await self.user_repo.update(
                user_id, {"phone_number": vendor_data["business_phone"]}
            )
        await emit_event(
            VENDOR_REGISTERED,
            {
                "vendor_id": vendor.id,
                "user_id": user_id,
                "business_name": vendor.business_name,
                "notify_admins": notify_admins_on_event,
            },
        )
        logger.info("Vendor application submitted: %s (user: %s)", vendor.id, user_id)
        return vendor

    async def get_vendor(self, vendor_id: int) -> Vendor:
        """Get vendor by ID."""
        vendor = await self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        return vendor

    async def get_vendor_by_user(self, user_id: int) -> Vendor | None:
        """Get vendor by user ID."""
        return await self.vendor_repo.get_by_user_id(user_id)

    async def update_vendor(self, vendor_id: int, data: VendorUpdate) -> Vendor:
        """Update vendor information."""
        vendor = await self.vendor_repo.update(vendor_id, data.dict(exclude_unset=True))
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        return vendor

    async def approve_vendor(self, vendor_id: int, admin_id: int) -> Vendor:
        """Approve a vendor application."""
        current = await self.get_vendor(vendor_id)
        if current.is_approved:
            raise ValidationError(f"Vendor {vendor_id} is already approved")
        if not self.is_application_complete(current):
            raise ValidationError("Vendor application is incomplete and cannot be approved")
        vendor = await self.vendor_repo.update(
            vendor_id,
            {
                "is_approved": True,
                "approved_at": datetime.utcnow(),
                "approved_by": admin_id,
                "rejected_at": None,
                "rejection_reason": None,
            },
            partial=False,
        )

        if not vendor:
            raise NotFoundError("Vendor", vendor_id)

        await self.user_repo.update(vendor.user_id, {"role": "vendor"})
        await emit_event(
            VENDOR_APPROVED,
            {
                "vendor_id": vendor.id,
                "user_id": vendor.user_id,
                "business_name": vendor.business_name,
            },
        )
        logger.info(f"Vendor {vendor_id} approved by admin {admin_id}")
        return vendor

    async def reject_vendor(self, vendor_id: int, reason: str) -> Vendor:
        """Reject a vendor application."""
        current = await self.get_vendor(vendor_id)
        if current.is_approved:
            raise ValidationError(f"Approved vendor {vendor_id} cannot be rejected")
        if current.rejected_at is not None:
            raise ValidationError(f"Vendor {vendor_id} is already rejected")
        vendor = await self.vendor_repo.update(
            vendor_id,
            {
                "is_approved": False,
                "rejected_at": datetime.utcnow(),
                "rejection_reason": reason,
            },
        )

        if not vendor:
            raise NotFoundError("Vendor", vendor_id)

        user = await self.user_repo.get_by_id(vendor.user_id)
        if user and user.role == "vendor":
            await self.user_repo.update(vendor.user_id, {"role": "customer"})
        await emit_event(
            VENDOR_REJECTED,
            {
                "vendor_id": vendor.id,
                "user_id": vendor.user_id,
                "business_name": vendor.business_name,
                "reason": reason,
            },
        )
        logger.info(f"Vendor {vendor_id} rejected: {reason}")
        return vendor

    async def get_vendor_stats(self, vendor_id: int) -> dict[str, Any]:
        """Get vendor statistics."""
        vendor = await self.get_vendor(vendor_id)

        # Get product stats
        from apps.products.repository import ProductRepository

        product_repo = ProductRepository(self.db)
        product_stats = await product_repo.get_vendor_stats(vendor_id)

        # Get order stats
        from apps.orders.repository import OrderRepository

        order_repo = OrderRepository(self.db)
        order_stats = await order_repo.get_vendor_stats(vendor_id)

        return {
            "vendor_id": vendor_id,
            "business_name": vendor.business_name,
            "rating": vendor.rating,
            "total_products": product_stats.get("total", 0),
            "active_products": product_stats.get("active", 0),
            "out_of_stock": product_stats.get("out_of_stock", 0),
            "total_orders": order_stats.get("total_orders", 0),
            "total_revenue": order_stats.get("total_revenue", 0),
            "pending_orders": order_stats.get("pending", 0),
        }


class UserAddress:
    """Placeholder or service class for managing user delivery addresses.
    Added to prevent ImportError during Telegram bot handler registration.
    """

    def __init__(self, db: AsyncSession):
        self.db = db


__all__ = ["AuthService", "UserAddress", "UserService", "VendorService"]
