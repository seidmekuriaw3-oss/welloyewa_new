# ============================
# WOLLOYEWA STORE BOT - USER MODELS
# ============================
"""User, Vendor, and related database models."""

from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Float, 
    BigInteger, Text, JSON, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from sqlalchemy.ext.hybrid import hybrid_property

from apps.common.models import BaseModel, TimestampMixin, SoftDeleteMixin, MetadataMixin
from core.constants import UserRole, UserStatus, Gender

if TYPE_CHECKING:
    from apps.products.models import Product, Review
    from apps.orders.models import Order


class User(BaseModel, TimestampMixin, SoftDeleteMixin, MetadataMixin):
    """
    User model for customers, vendors, and admins.
    
    Stores all user accounts in the system.
    """
    
    __tablename__ = "users"
    
    # Identification
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Contact info
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Role and status
    role: Mapped[str] = mapped_column(
        SQLEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.CUSTOMER,
        index=True
    )
    status: Mapped[str] = mapped_column(
        SQLEnum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.ACTIVE,
        index=True
    )
    
    # Personal info
    gender: Mapped[Optional[str]] = mapped_column(SQLEnum(Gender, name="gender"), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    profile_picture: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Preferences
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="am")
    
    # Location (last known)
    location_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subcity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    woreda: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    house_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Activity tracking
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Security
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # ====================
    # RELATIONSHIPS - ትክክለኛ አገባብ
    # ====================
    
    # UserAddress (one-to-many)
    addresses: Mapped[List["UserAddress"]] = relationship(
        "UserAddress",
        back_populates="user",
        cascade="all, delete-orphan",
        primaryjoin="User.id == foreign(UserAddress.user_id)",
    )
    
    # UserPreferences (one-to-one)
    preferences: Mapped[Optional["UserPreferences"]] = relationship(
        "UserPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        primaryjoin="User.id == foreign(UserPreferences.user_id)",
    )
    
    # Vendor (one-to-one)
    vendor_profile: Mapped[Optional["Vendor"]] = relationship(
        "Vendor",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        primaryjoin="User.id == foreign(Vendor.user_id)",
    )
    
    # Orders where this user is the buyer
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        foreign_keys="Order.user_id",
        back_populates="user",
        primaryjoin="User.id == foreign(Order.user_id)",
    )
    
    # Orders where this user is a vendor
    # በVendor በኩል ያለውን ግንኙነት ለማሳየት
    vendor_orders: Mapped[List["Order"]] = relationship(
        "Order",
        secondary="vendors",
        primaryjoin="User.id == foreign(Vendor.user_id)",
        secondaryjoin="Vendor.id == foreign(Order.vendor_id)",
        viewonly=True,
    )
    
    # Products sold by this user (via their vendor profile).
    products: Mapped[List["Product"]] = relationship(
        "Product",
        secondary="vendors",
        primaryjoin="User.id == foreign(Vendor.user_id)",
        secondaryjoin="Vendor.id == foreign(Product.vendor_id)",
        viewonly=True,
    )
    
    # Reviews (one-to-many)
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="user",
        primaryjoin="User.id == foreign(Review.user_id)",
    )
    
    @hybrid_property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    @hybrid_property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]
    
    @hybrid_property
    def is_vendor(self) -> bool:
        """Check if user is vendor."""
        return self.role == UserRole.VENDOR.value
    
    @hybrid_property
    def is_customer(self) -> bool:
        """Check if user is customer."""
        return self.role == UserRole.CUSTOMER.value
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Vendor(BaseModel, TimestampMixin):
    """
    Vendor profile extended information.
    
    Linked to User with role='vendor'.
    """
    
    __tablename__ = "vendors"
    
    # Links to user account
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, unique=True, index=True
    )
    
    # Business information
    business_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    business_license: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    tin_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    business_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    business_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Media
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cover_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Performance metrics
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_sales: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_products: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Approval status
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Rejection info
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="vendor_profile")
    # Products sold by this user (when user has a vendor profile).
    # This is a view-only relationship that joins through the vendors table:
    # User.id -> Vendor.user_id  AND  Vendor.id -> Product.vendor_id
    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="vendor",
        foreign_keys="Product.vendor_id",
        primaryjoin="Vendor.id == foreign(Product.vendor_id)",
    )
    
    # Vendor orders - ትክክለኛ አገባብ
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="vendor",
        foreign_keys="Order.vendor_id",
        primaryjoin="Vendor.id == foreign(Order.vendor_id)",
    )
    
    def __repr__(self) -> str:
        return f"<Vendor(id={self.id}, business_name={self.business_name})>"


class UserAddress(BaseModel, TimestampMixin):
    """
    User saved addresses for shipping.
    """
    
    __tablename__ = "user_addresses"
    
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, index=True
    )
    
    # Address details
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    subcity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    woreda: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    house_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    landmark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Contact for this address
    recipient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Location coordinates
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Flags
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    address_type: Mapped[str] = mapped_column(String(20), nullable=False, default="home")  # home, work, other
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="addresses")
    
    def __repr__(self) -> str:
        return f"<UserAddress(id={self.id}, user_id={self.user_id}, city={self.city})>"


class UserPreferences(BaseModel, TimestampMixin):
    """
    User-specific preferences and settings.
    """
    
    __tablename__ = "user_preferences"
    
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, unique=True, index=True
    )
    
    # Notification settings
    email_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sms_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    push_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Marketing preferences
    marketing_emails: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    promotional_sms: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Display preferences
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="am")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="ETB")
    
    # Shopping preferences
    default_shipping_address_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    preferred_categories: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Privacy
    share_activity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")
    
    def __repr__(self) -> str:
        return f"<UserPreferences(user_id={self.user_id}, language={self.language})>"