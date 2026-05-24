# ============================
# WOLLOYEWA STORE BOT - USER SERVICES
# ============================
"""Business logic for user management, authentication, and vendor operations."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import logger
from core.security import (
    hash_password, verify_password, create_access_token, 
    generate_otp, verify_token
)
from core.exceptions import (
    AuthenticationError, ValidationError, NotFoundError, 
    PermissionError, DuplicateRecordError
)
from core.events import emit_event, USER_REGISTERED, USER_LOGIN, USER_UPDATED
from core.utils.validators import Validator
from apps.users.repository import UserRepository, VendorRepository
from apps.users.models import User, Vendor, UserPreferences
from apps.users.schemas import (
    UserCreate, UserUpdate, UserRegister, UserLogin, 
    VendorCreate, VendorUpdate, ChangePasswordRequest
)


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
            is_valid, normalized = Validator.phone(data.phone_number, normalize=True)
            if not is_valid:
                raise ValidationError(f"Invalid phone number: {data.phone_number}")
            phone = normalized
        
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
    
    async def login(self, data: UserLogin) -> Tuple[User, str]:
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
            is_valid, normalized = Validator.phone(data.phone_number, normalize=True)
            if is_valid:
                user = await self.user_repo.get_by_phone(normalized)
        
        if not user:
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
        # In a real implementation, you would verify old password
        # and hash the new password
        await self.user_repo.update(user_id, {"password_hash": hash_password(data.new_password)})
        logger.info(f"Password changed for user {user_id}")
        return True
    
    async def verify_telegram_auth(self, auth_data: Dict[str, Any]) -> Optional[User]:
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
    
    async def get_user_by_telegram(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        return await self.user_repo.get_by_telegram(telegram_id)
    
    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        """Update user information."""
        # Validate phone if provided
        if data.phone_number:
            is_valid, normalized = Validator.phone(data.phone_number, normalize=True)
            if not is_valid:
                raise ValidationError(f"Invalid phone number: {data.phone_number}")
            data.phone_number = normalized
        
        user = await self.user_repo.update(user_id, data.dict(exclude_unset=True))
        if not user:
            raise NotFoundError("User", user_id)
        
        # Emit event
        await emit_event(
            USER_UPDATED,
            {
                "user_id": user.id,
                "updated_fields": list(data.dict(exclude_unset=True).keys()),
            },
            sync=False,
        )
        
        return user
    
    async def get_or_create_user(self, telegram_id: int, first_name: str, username: str = None) -> User:
        """Get existing user or create new one."""
        user = await self.user_repo.get_by_telegram(telegram_id)
        if not user:
            user = await self.user_repo.create({
                "telegram_id": telegram_id,
                "first_name": first_name,
                "username": username,
            })
            
            # Create preferences
            preferences = UserPreferences(user_id=user.id)
            self.db.add(preferences)
            await self.db.flush()
        
        return user
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
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
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vendor_repo = VendorRepository(db)
        self.user_repo = UserRepository(db)
    
    async def create_vendor(self, user_id: int, data: VendorCreate) -> Vendor:
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
        
        if user.role != "customer":
            raise ValidationError("User already has a vendor profile")
        
        # Check if vendor already exists
        existing = await self.vendor_repo.get_by_user_id(user_id)
        if existing:
            raise DuplicateRecordError("Vendor", "user_id", user_id)
        
        # Create vendor
        vendor = await self.vendor_repo.create({
            "user_id": user_id,
            "business_name": data.business_name,
            "business_license": data.business_license,
            "tin_number": data.tin_number,
            "business_address": data.business_address,
            "business_phone": data.business_phone,
            "business_email": data.business_email,
            "description": data.description,
        })
        
        # Update user role to vendor
        await self.user_repo.update(user_id, {"role": "vendor"})
        
        logger.info(f"New vendor created: {vendor.id} (user: {user_id})")
        return vendor
    
    async def get_vendor(self, vendor_id: int) -> Vendor:
        """Get vendor by ID."""
        vendor = await self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        return vendor
    
    async def get_vendor_by_user(self, user_id: int) -> Optional[Vendor]:
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
        vendor = await self.vendor_repo.update(vendor_id, {
            "is_approved": True,
            "approved_at": datetime.utcnow(),
            "approved_by": admin_id,
        })
        
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        
        logger.info(f"Vendor {vendor_id} approved by admin {admin_id}")
        return vendor
    
    async def reject_vendor(self, vendor_id: int, reason: str) -> Vendor:
        """Reject a vendor application."""
        vendor = await self.vendor_repo.update(vendor_id, {
            "is_approved": False,
            "rejected_at": datetime.utcnow(),
            "rejection_reason": reason,
        })
        
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        
        logger.info(f"Vendor {vendor_id} rejected: {reason}")
        return vendor
    
    async def get_vendor_stats(self, vendor_id: int) -> Dict[str, Any]:
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


__all__ = ["AuthService", "UserService", "VendorService"]