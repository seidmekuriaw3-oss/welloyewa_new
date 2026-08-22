# ============================
# WOLLOYEWA STORE BOT - MARKETING SCHEMAS
# ============================
"""Pydantic schemas for marketing request/response validation."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, validator

from apps.common.schemas import BaseSchema, IdSchema, TimestampSchema

# ============================
# Coupon Schemas
# ============================


class CouponBase(BaseSchema):
    """Base coupon schema."""

    code: str = Field(..., max_length=50, description="Unique coupon code")
    name: str = Field(..., max_length=200, description="Coupon name")
    description: str | None = Field(None, description="Coupon description")

    discount_type: str = Field(..., description="Discount type (percentage, fixed_amount)")
    discount_value: Decimal = Field(..., ge=0, description="Discount value")
    max_discount_amount: Decimal | None = Field(None, ge=0, description="Maximum discount amount")

    min_purchase_amount: Decimal | None = Field(None, ge=0, description="Minimum purchase amount")

    valid_from: datetime = Field(..., description="Start date")
    valid_to: datetime = Field(..., description="End date")

    usage_limit: int | None = Field(None, ge=1, description="Total usage limit")
    per_user_limit: int | None = Field(None, ge=1, description="Per user limit")

    applicable_categories: list[str] | None = Field(None, description="Applicable categories")
    applicable_products: list[int] | None = Field(None, description="Applicable product IDs")
    excluded_categories: list[str] | None = Field(None, description="Excluded categories")
    excluded_products: list[int] | None = Field(None, description="Excluded product IDs")

    new_customers_only: bool = Field(False, description="New customers only")
    first_order_only: bool = Field(False, description="First order only")

    is_active: bool = Field(True, description="Whether coupon is active")
    is_stackable: bool = Field(False, description="Whether can stack with other coupons")


class CouponCreate(CouponBase):
    """Schema for creating a coupon."""

    @validator("code")
    def validate_code(cls, v):
        return v.upper().strip()


class CouponUpdate(BaseSchema):
    """Schema for updating a coupon."""

    name: str | None = Field(None, max_length=200)
    description: str | None = None
    discount_type: str | None = None
    discount_value: Decimal | None = Field(None, ge=0)
    max_discount_amount: Decimal | None = Field(None, ge=0)
    min_purchase_amount: Decimal | None = Field(None, ge=0)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    usage_limit: int | None = Field(None, ge=1)
    per_user_limit: int | None = Field(None, ge=1)
    applicable_categories: list[str] | None = None
    applicable_products: list[int] | None = None
    excluded_categories: list[str] | None = None
    excluded_products: list[int] | None = None
    new_customers_only: bool | None = None
    first_order_only: bool | None = None
    is_active: bool | None = None
    is_stackable: bool | None = None


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
    message: str | None = Field(None, description="Validation message")
    coupon: CouponResponse | None = Field(None, description="Coupon details if valid")


# ============================
# Loyalty Program Schemas
# ============================


class LoyaltyProgramBase(BaseSchema):
    """Base loyalty program schema."""

    name: str = Field(..., max_length=100)
    description: str | None = None
    is_active: bool = True

    points_per_birr: float = Field(1.0, ge=0, description="Points per ETB spent")
    points_per_review: int = Field(10, ge=0)
    points_per_share: int = Field(5, ge=0)
    points_per_birthday: int = Field(50, ge=0)

    birr_per_point: float = Field(0.01, ge=0, description="Birr value per point")
    min_redeem_points: int = Field(100, ge=1)
    max_redeem_per_order: int | None = Field(None, ge=1)

    tier_enabled: bool = False
    tier_config: dict[str, Any] | None = None


class LoyaltyProgramCreate(LoyaltyProgramBase):
    """Schema for creating a loyalty program."""

    pass


class LoyaltyProgramUpdate(BaseSchema):
    """Schema for updating a loyalty program."""

    name: str | None = Field(None, max_length=100)
    description: str | None = None
    is_active: bool | None = None
    points_per_birr: float | None = Field(None, ge=0)
    points_per_review: int | None = Field(None, ge=0)
    points_per_share: int | None = Field(None, ge=0)
    points_per_birthday: int | None = Field(None, ge=0)
    birr_per_point: float | None = Field(None, ge=0)
    min_redeem_points: int | None = Field(None, ge=1)
    max_redeem_per_order: int | None = Field(None, ge=1)
    tier_enabled: bool | None = None
    tier_config: dict[str, Any] | None = None


class LoyaltyProgramResponse(LoyaltyProgramBase, IdSchema, TimestampSchema):
    """Schema for loyalty program response."""

    class Config:
        from_attributes = True


class LoyaltyTransactionCreate(BaseSchema):
    """Schema for creating a loyalty transaction."""

    user_id: int = Field(..., description="User ID")
    transaction_type: str = Field(
        ..., description="Transaction type (earn, redeem, expire, adjust)"
    )
    points: int = Field(..., description="Points amount")
    reference_id: int | None = Field(None, description="Reference ID")
    reference_type: str | None = Field(None, description="Reference type")
    description: str | None = Field(None, description="Transaction description")


class LoyaltyTransactionResponse(IdSchema, TimestampSchema):
    """Schema for loyalty transaction response."""

    user_id: int
    transaction_type: str
    points: int
    points_balance: int
    reference_id: int | None
    reference_type: str | None
    description: str | None

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
    description: str | None = None

    campaign_type: str = Field(
        ..., description="Campaign type (discount, flash_sale, bundle, referral)"
    )

    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")

    target_segments: list[str] | None = Field(None, description="Target customer segments")
    target_cities: list[str] | None = Field(None, description="Target cities")

    budget: Decimal | None = Field(None, ge=0, description="Campaign budget")

    title: str | None = Field(None, max_length=200, description="Campaign title")
    message: str | None = Field(None, description="Campaign message")
    image_url: str | None = Field(None, max_length=500, description="Campaign image URL")

    rules: list[dict[str, Any]] | None = Field(None, description="Campaign rules")


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign."""

    pass


class CampaignUpdate(BaseSchema):
    """Schema for updating a campaign."""

    name: str | None = Field(None, max_length=200)
    description: str | None = None
    campaign_type: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    target_segments: list[str] | None = None
    target_cities: list[str] | None = None
    budget: Decimal | None = Field(None, ge=0)
    title: str | None = Field(None, max_length=200)
    message: str | None = None
    image_url: str | None = Field(None, max_length=500)
    rules: list[dict[str, Any]] | None = None
    status: str | None = None


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

    campaign_id: int | None = Field(None, description="Associated campaign ID")

    promotion_type: str = Field(
        ..., description="Promotion type (discount, buy_x_get_y, free_shipping)"
    )

    product_ids: list[int] | None = Field(None, description="Applicable product IDs")
    category_ids: list[int] | None = Field(None, description="Applicable category IDs")

    discount_type: str = Field(..., description="Discount type (percentage, fixed_amount)")
    discount_value: Decimal = Field(..., ge=0, description="Discount value")
    max_discount: Decimal | None = Field(None, ge=0, description="Maximum discount amount")

    buy_quantity: int | None = Field(None, ge=1, description="Buy X quantity")
    get_quantity: int | None = Field(None, ge=1, description="Get Y quantity")
    get_product_ids: list[int] | None = Field(None, description="Free product IDs")

    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")

    usage_limit: int | None = Field(None, ge=1, description="Usage limit")

    is_active: bool = Field(True, description="Whether promotion is active")


class PromotionCreate(PromotionBase):
    """Schema for creating a promotion."""

    pass


class PromotionUpdate(BaseSchema):
    """Schema for updating a promotion."""

    campaign_id: int | None = None
    promotion_type: str | None = None
    product_ids: list[int] | None = None
    category_ids: list[int] | None = None
    discount_type: str | None = None
    discount_value: Decimal | None = Field(None, ge=0)
    max_discount: Decimal | None = Field(None, ge=0)
    buy_quantity: int | None = Field(None, ge=1)
    get_quantity: int | None = Field(None, ge=1)
    get_product_ids: list[int] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    usage_limit: int | None = Field(None, ge=1)
    is_active: bool | None = None


class PromotionResponse(PromotionBase, IdSchema, TimestampSchema):
    """Schema for promotion response."""

    used_count: int = Field(0, description="Times used")
    is_valid: bool = Field(False, description="Whether promotion is currently valid")

    class Config:
        from_attributes = True


__all__ = [
    "CampaignBase",
    "CampaignCreate",
    "CampaignResponse",
    "CampaignUpdate",
    "CouponBase",
    "CouponCreate",
    "CouponResponse",
    "CouponUpdate",
    "CouponValidateRequest",
    "CouponValidateResponse",
    "LoyaltyProgramBase",
    "LoyaltyProgramCreate",
    "LoyaltyProgramResponse",
    "LoyaltyProgramUpdate",
    "LoyaltyTransactionCreate",
    "LoyaltyTransactionResponse",
    "PromotionBase",
    "PromotionCreate",
    "PromotionResponse",
    "PromotionUpdate",
    "UserPointsResponse",
]
