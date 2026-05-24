# ============================
# WOLLOYEWA STORE BOT - MARKETING SCHEMAS
# ============================
"""Pydantic schemas for marketing request/response validation."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import Field, validator

from apps.common.schemas import BaseSchema, IdSchema, TimestampSchema


# ============================
# Coupon Schemas
# ============================

class CouponBase(BaseSchema):
    """Base coupon schema."""
    
    code: str = Field(..., max_length=50, description="Unique coupon code")
    name: str = Field(..., max_length=200, description="Coupon name")
    description: Optional[str] = Field(None, description="Coupon description")
    
    discount_type: str = Field(..., description="Discount type (percentage, fixed_amount)")
    discount_value: Decimal = Field(..., ge=0, description="Discount value")
    max_discount_amount: Optional[Decimal] = Field(None, ge=0, description="Maximum discount amount")
    
    min_purchase_amount: Optional[Decimal] = Field(None, ge=0, description="Minimum purchase amount")
    
    valid_from: datetime = Field(..., description="Start date")
    valid_to: datetime = Field(..., description="End date")
    
    usage_limit: Optional[int] = Field(None, ge=1, description="Total usage limit")
    per_user_limit: Optional[int] = Field(None, ge=1, description="Per user limit")
    
    applicable_categories: Optional[List[str]] = Field(None, description="Applicable categories")
    applicable_products: Optional[List[int]] = Field(None, description="Applicable product IDs")
    excluded_categories: Optional[List[str]] = Field(None, description="Excluded categories")
    excluded_products: Optional[List[int]] = Field(None, description="Excluded product IDs")
    
    new_customers_only: bool = Field(False, description="New customers only")
    first_order_only: bool = Field(False, description="First order only")
    
    is_active: bool = Field(True, description="Whether coupon is active")
    is_stackable: bool = Field(False, description="Whether can stack with other coupons")


class CouponCreate(CouponBase):
    """Schema for creating a coupon."""
    
    @validator('code')
    def validate_code(cls, v):
        return v.upper().strip()


class CouponUpdate(BaseSchema):
    """Schema for updating a coupon."""
    
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = Field(None, ge=0)
    max_discount_amount: Optional[Decimal] = Field(None, ge=0)
    min_purchase_amount: Optional[Decimal] = Field(None, ge=0)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    usage_limit: Optional[int] = Field(None, ge=1)
    per_user_limit: Optional[int] = Field(None, ge=1)
    applicable_categories: Optional[List[str]] = None
    applicable_products: Optional[List[int]] = None
    excluded_categories: Optional[List[str]] = None
    excluded_products: Optional[List[int]] = None
    new_customers_only: Optional[bool] = None
    first_order_only: Optional[bool] = None
    is_active: Optional[bool] = None
    is_stackable: Optional[bool] = None


class CouponResponse(CouponBase, IdSchema, TimestampSchema):
    """Schema for coupon response."""
    
    used_count: int = Field(0, description="Number of times used")
    is_valid: bool = Field(False, description="Whether coupon is currently valid")
    is_expired: bool = Field(False, description="Whether coupon is expired")
    
    class Config:
        from_attributes = True


class CouponValidateRequest(BaseSchema):
    """Schema for coupon validation request."""
    
    code: str = Field(..., description="Coupon code")
    order_amount: Decimal = Field(..., ge=0, description="Order amount")
    user_id: int = Field(..., description="User ID")


class CouponValidateResponse(BaseSchema):
    """Schema for coupon validation response."""
    
    is_valid: bool = Field(..., description="Whether coupon is valid")
    discount_amount: Decimal = Field(0, description="Calculated discount amount")
    message: Optional[str] = Field(None, description="Validation message")
    coupon: Optional[CouponResponse] = Field(None, description="Coupon details if valid")


# ============================
# Loyalty Program Schemas
# ============================

class LoyaltyProgramBase(BaseSchema):
    """Base loyalty program schema."""
    
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_active: bool = True
    
    points_per_birr: float = Field(1.0, ge=0, description="Points per ETB spent")
    points_per_review: int = Field(10, ge=0)
    points_per_share: int = Field(5, ge=0)
    points_per_birthday: int = Field(50, ge=0)
    
    birr_per_point: float = Field(0.01, ge=0, description="Birr value per point")
    min_redeem_points: int = Field(100, ge=1)
    max_redeem_per_order: Optional[int] = Field(None, ge=1)
    
    tier_enabled: bool = False
    tier_config: Optional[Dict[str, Any]] = None


class LoyaltyProgramCreate(LoyaltyProgramBase):
    """Schema for creating a loyalty program."""
    
    pass


class LoyaltyProgramUpdate(BaseSchema):
    """Schema for updating a loyalty program."""
    
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    points_per_birr: Optional[float] = Field(None, ge=0)
    points_per_review: Optional[int] = Field(None, ge=0)
    points_per_share: Optional[int] = Field(None, ge=0)
    points_per_birthday: Optional[int] = Field(None, ge=0)
    birr_per_point: Optional[float] = Field(None, ge=0)
    min_redeem_points: Optional[int] = Field(None, ge=1)
    max_redeem_per_order: Optional[int] = Field(None, ge=1)
    tier_enabled: Optional[bool] = None
    tier_config: Optional[Dict[str, Any]] = None


class LoyaltyProgramResponse(LoyaltyProgramBase, IdSchema, TimestampSchema):
    """Schema for loyalty program response."""
    
    class Config:
        from_attributes = True


class LoyaltyTransactionCreate(BaseSchema):
    """Schema for creating a loyalty transaction."""
    
    user_id: int = Field(..., description="User ID")
    transaction_type: str = Field(..., description="Transaction type (earn, redeem, expire, adjust)")
    points: int = Field(..., description="Points amount")
    reference_id: Optional[int] = Field(None, description="Reference ID")
    reference_type: Optional[str] = Field(None, description="Reference type")
    description: Optional[str] = Field(None, description="Transaction description")


class LoyaltyTransactionResponse(IdSchema, TimestampSchema):
    """Schema for loyalty transaction response."""
    
    user_id: int
    transaction_type: str
    points: int
    points_balance: int
    reference_id: Optional[int]
    reference_type: Optional[str]
    description: Optional[str]
    
    class Config:
        from_attributes = True


class UserPointsResponse(BaseSchema):
    """Schema for user points response."""
    
    user_id: int
    points: int
    points_value_birr: Decimal
    tier: str


# ============================
# Campaign Schemas
# ============================

class CampaignBase(BaseSchema):
    """Base campaign schema."""
    
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    
    campaign_type: str = Field(..., description="Campaign type (discount, flash_sale, bundle, referral)")
    
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    
    target_segments: Optional[List[str]] = Field(None, description="Target customer segments")
    target_cities: Optional[List[str]] = Field(None, description="Target cities")
    
    budget: Optional[Decimal] = Field(None, ge=0, description="Campaign budget")
    
    title: Optional[str] = Field(None, max_length=200, description="Campaign title")
    message: Optional[str] = Field(None, description="Campaign message")
    image_url: Optional[str] = Field(None, max_length=500, description="Campaign image URL")
    
    rules: Optional[List[Dict[str, Any]]] = Field(None, description="Campaign rules")


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign."""
    
    pass


class CampaignUpdate(BaseSchema):
    """Schema for updating a campaign."""
    
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    campaign_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    target_segments: Optional[List[str]] = None
    target_cities: Optional[List[str]] = None
    budget: Optional[Decimal] = Field(None, ge=0)
    title: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    rules: Optional[List[Dict[str, Any]]] = None
    status: Optional[str] = None


class CampaignResponse(CampaignBase, IdSchema, TimestampSchema):
    """Schema for campaign response."""
    
    status: str = Field("draft", description="Campaign status")
    spent: Decimal = Field(0, description="Amount spent")
    impressions: int = Field(0, description="Impressions count")
    clicks: int = Field(0, description="Clicks count")
    conversions: int = Field(0, description="Conversions count")
    revenue: Decimal = Field(0, description="Revenue generated")
    is_active: bool = Field(False, description="Whether campaign is currently active")
    conversion_rate: float = Field(0.0, description="Conversion rate percentage")
    
    class Config:
        from_attributes = True


# ============================
# Promotion Schemas
# ============================

class PromotionBase(BaseSchema):
    """Base promotion schema."""
    
    campaign_id: Optional[int] = Field(None, description="Associated campaign ID")
    
    promotion_type: str = Field(..., description="Promotion type (discount, buy_x_get_y, free_shipping)")
    
    product_ids: Optional[List[int]] = Field(None, description="Applicable product IDs")
    category_ids: Optional[List[int]] = Field(None, description="Applicable category IDs")
    
    discount_type: str = Field(..., description="Discount type (percentage, fixed_amount)")
    discount_value: Decimal = Field(..., ge=0, description="Discount value")
    max_discount: Optional[Decimal] = Field(None, ge=0, description="Maximum discount amount")
    
    buy_quantity: Optional[int] = Field(None, ge=1, description="Buy X quantity")
    get_quantity: Optional[int] = Field(None, ge=1, description="Get Y quantity")
    get_product_ids: Optional[List[int]] = Field(None, description="Free product IDs")
    
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    
    usage_limit: Optional[int] = Field(None, ge=1, description="Usage limit")
    
    is_active: bool = Field(True, description="Whether promotion is active")


class PromotionCreate(PromotionBase):
    """Schema for creating a promotion."""
    
    pass


class PromotionUpdate(BaseSchema):
    """Schema for updating a promotion."""
    
    campaign_id: Optional[int] = None
    promotion_type: Optional[str] = None
    product_ids: Optional[List[int]] = None
    category_ids: Optional[List[int]] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = Field(None, ge=0)
    max_discount: Optional[Decimal] = Field(None, ge=0)
    buy_quantity: Optional[int] = Field(None, ge=1)
    get_quantity: Optional[int] = Field(None, ge=1)
    get_product_ids: Optional[List[int]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    usage_limit: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class PromotionResponse(PromotionBase, IdSchema, TimestampSchema):
    """Schema for promotion response."""
    
    used_count: int = Field(0, description="Times used")
    is_valid: bool = Field(False, description="Whether promotion is currently valid")
    
    class Config:
        from_attributes = True


__all__ = [
    "CouponBase", "CouponCreate", "CouponUpdate", "CouponResponse",
    "CouponValidateRequest", "CouponValidateResponse",
    "LoyaltyProgramBase", "LoyaltyProgramCreate", "LoyaltyProgramUpdate", "LoyaltyProgramResponse",
    "LoyaltyTransactionCreate", "LoyaltyTransactionResponse", "UserPointsResponse",
    "CampaignBase", "CampaignCreate", "CampaignUpdate", "CampaignResponse",
    "PromotionBase", "PromotionCreate", "PromotionUpdate", "PromotionResponse",
]