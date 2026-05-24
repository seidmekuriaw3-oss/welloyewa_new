# ============================
# WOLLOYEWA STORE BOT - MARKETING MODELS
# ============================
"""Marketing, promotions, coupons, and loyalty program database models."""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float,
    BigInteger, Text, JSON, ForeignKey, Numeric, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from apps.common.models import BaseModel, TimestampMixin

if TYPE_CHECKING:
    from apps.users.models import User


class Coupon(BaseModel, TimestampMixin):
    """
    Discount coupon model.
    
    Supports percentage and fixed amount discounts, with usage limits.
    """
    
    __tablename__ = "coupons"
    
    # Basic info
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Discount type
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # percentage, fixed_amount
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_discount_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Minimum purchase
    min_purchase_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Validity period
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Usage limits
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Total usage limit
    per_user_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Per user limit
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Restrictions
    applicable_categories: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    applicable_products: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    excluded_categories: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    excluded_products: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    
    # Customer eligibility
    new_customers_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_order_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_stackable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Relationships
    usages: Mapped[List["CouponUsage"]] = relationship("CouponUsage", back_populates="coupon", cascade="all, delete-orphan")
    
    @hybrid_property
    def is_valid(self) -> bool:
        """Check if coupon is currently valid."""
        now = datetime.utcnow()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_to and
            (self.usage_limit is None or self.used_count < self.usage_limit)
        )
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if coupon is expired."""
        return datetime.utcnow() > self.valid_to
    
    def calculate_discount(self, amount: Decimal) -> Decimal:
        """Calculate discount amount for a given purchase amount."""
        if self.min_purchase_amount and amount < self.min_purchase_amount:
            return Decimal('0')
        
        if self.discount_type == "percentage":
            discount = amount * (self.discount_value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = self.discount_value
        
        return min(discount, amount)
    
    def can_use_by_user(self, user_id: int, user_order_count: int = 0) -> bool:
        """Check if coupon can be used by a specific user."""
        if self.new_customers_only and user_order_count > 0:
            return False
        
        if self.first_order_only and user_order_count > 0:
            return False
        
        if self.per_user_limit:
            user_usage = sum(1 for usage in self.usages if usage.user_id == user_id)
            if user_usage >= self.per_user_limit:
                return False
        
        return True
    
    def use(self) -> None:
        """Increment usage count."""
        self.used_count += 1
    
    def __repr__(self) -> str:
        return f"<Coupon(id={self.id}, code={self.code}, discount={self.discount_value} {self.discount_type})>"


class CouponUsage(BaseModel, TimestampMixin):
    """Record of coupon usage by users."""
    
    __tablename__ = "coupon_usages"
    
    coupon_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    order_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Relationships
    coupon: Mapped["Coupon"] = relationship("Coupon", back_populates="usages")
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self) -> str:
        return f"<CouponUsage(coupon_id={self.coupon_id}, user_id={self.user_id}, order_id={self.order_id})>"


class LoyaltyProgram(BaseModel, TimestampMixin):
    """Loyalty program configuration."""
    
    __tablename__ = "loyalty_programs"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Points configuration
    points_per_birr: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)  # Points per ETB spent
    points_per_review: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    points_per_share: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    points_per_birthday: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    
    # Redemption
    birr_per_point: Mapped[float] = mapped_column(Float, nullable=False, default=0.01)  # Value per point
    min_redeem_points: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    max_redeem_per_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Tiers
    tier_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tier_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    def points_to_birr(self, points: int) -> Decimal:
        """Convert points to Birr value."""
        return Decimal(str(points * self.birr_per_point))
    
    def birr_to_points(self, amount: Decimal) -> int:
        """Convert Birr amount to points."""
        return int(float(amount) * self.points_per_birr)


class LoyaltyTransaction(BaseModel, TimestampMixin):
    """Loyalty points transaction record."""
    
    __tablename__ = "loyalty_transactions"
    
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Transaction details
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # earn, redeem, expire, adjust
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    points_balance: Mapped[int] = mapped_column(Integer, nullable=False)  # Running balance
    
    # Reference
    reference_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # order_id, review_id, etc.
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # order, review, share
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (
        Index('idx_loyalty_user_date', 'user_id', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<LoyaltyTransaction(user_id={self.user_id}, type={self.transaction_type}, points={self.points})>"


class Campaign(BaseModel, TimestampMixin):
    """Marketing campaign model."""
    
    __tablename__ = "campaigns"
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Campaign type
    campaign_type: Mapped[str] = mapped_column(String(50), nullable=False)  # discount, flash_sale, bundle, referral
    
    # Schedule
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Target audience
    target_segments: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    target_cities: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Budget
    budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    spent: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")  # draft, active, paused, completed, cancelled
    
    # Metrics
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    
    # Content
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Rules
    rules: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    promotions: Mapped[List["Promotion"]] = relationship("Promotion", back_populates="campaign", cascade="all, delete-orphan")
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if campaign is currently active."""
        now = datetime.utcnow()
        return self.status == "active" and self.start_date <= now <= self.end_date
    
    @hybrid_property
    def conversion_rate(self) -> float:
        """Calculate conversion rate."""
        if self.impressions == 0:
            return 0.0
        return (self.conversions / self.impressions) * 100
    
    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name={self.name}, type={self.campaign_type})>"


class CampaignRule(BaseModel, TimestampMixin):
    """Campaign eligibility rule."""
    
    __tablename__ = "campaign_rules"
    
    campaign_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # min_order, first_purchase, user_segment
    operator: Mapped[str] = mapped_column(String(20), nullable=False)  # eq, gt, lt, in, contains
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign")
    
    def evaluate(self, context: dict) -> bool:
        """Evaluate rule against context."""
        # Rule evaluation logic
        pass


class Promotion(BaseModel, TimestampMixin):
    """Product-specific promotion."""
    
    __tablename__ = "promotions"
    
    campaign_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Promotion type
    promotion_type: Mapped[str] = mapped_column(String(50), nullable=False)  # discount, buy_x_get_y, free_shipping
    
    # Target
    product_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    category_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    
    # Discount
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # percentage, fixed_amount
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_discount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Buy X Get Y
    buy_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    get_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    get_product_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    
    # Schedule
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Usage limits
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Relationships
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", back_populates="promotions")
    
    @hybrid_property
    def is_valid(self) -> bool:
        """Check if promotion is currently valid."""
        now = datetime.utcnow()
        return (
            self.is_active and
            self.start_date <= now <= self.end_date and
            (self.usage_limit is None or self.used_count < self.usage_limit)
        )
    
    def __repr__(self) -> str:
        return f"<Promotion(id={self.id}, type={self.promotion_type}, discount={self.discount_value})>"