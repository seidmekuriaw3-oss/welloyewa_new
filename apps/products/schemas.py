# ============================
# WOLLOYEWA STORE BOT - PRODUCT SCHEMAS
# ============================
"""Pydantic schemas for product request/response validation."""

from datetime import datetime
from decimal import Decimal

from pydantic import Field, validator

from apps.common.schemas import BaseSchema, IdSchema, TimestampSchema
from core.constants import ProductCategory, ProductStatus

# ============================
# Product Schemas
# ============================


class ProductBase(BaseSchema):
    """Base product schema."""

    name: str = Field(..., max_length=255, description="Product name")
    name_am: str | None = Field(None, max_length=255, description="Product name in Amharic")
    slug: str | None = Field(None, max_length=280, description="URL-friendly slug")
    description: str | None = Field(None, description="Product description")
    description_am: str | None = Field(None, description="Product description in Amharic")
    short_description: str | None = Field(None, max_length=500, description="Short description")

    category_id: int | None = Field(None, description="Category ID")
    category: ProductCategory | None = Field(None, description="Product category")
    subcategory: str | None = Field(None, max_length=100, description="Subcategory")
    tags: list[str] | None = Field(None, description="Product tags")

    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2, description="Price in ETB")
    compare_price: Decimal | None = Field(
        None, ge=0, max_digits=10, decimal_places=2, description="Compare at price"
    )
    cost_price: Decimal | None = Field(
        None, ge=0, max_digits=10, decimal_places=2, description="Cost price"
    )

    stock_quantity: int = Field(0, ge=0, description="Available stock quantity")
    low_stock_threshold: int = Field(5, ge=0, description="Low stock alert threshold")
    sku: str = Field(..., max_length=100, description="Stock keeping unit")
    barcode: str | None = Field(None, max_length=100, description="Product barcode")

    weight: float | None = Field(None, ge=0, description="Weight in kg")
    dimensions: str | None = Field(None, max_length=100, description="Dimensions (LxWxH)")

    images: list[str] | None = Field(None, description="Product image URLs")
    video_url: str | None = Field(None, max_length=500, description="Product video URL")

    status: ProductStatus = Field(ProductStatus.DRAFT, description="Product status")
    is_featured: bool = Field(False, description="Featured product flag")
    is_on_sale: bool = Field(False, description="On sale flag")
    sale_start_date: datetime | None = Field(None, description="Sale start date")
    sale_end_date: datetime | None = Field(None, description="Sale end date")

    meta_title: str | None = Field(None, max_length=255, description="SEO meta title")
    meta_description: str | None = Field(None, description="SEO meta description")


class ProductCreate(ProductBase):
    """Schema for creating a product."""

    @validator("sku")
    def validate_sku(cls, v):
        if v:
            return v.upper().strip()
        return v


class ProductUpdate(BaseSchema):
    """Schema for updating a product."""

    name: str | None = Field(None, max_length=255)
    name_am: str | None = Field(None, max_length=255)
    slug: str | None = Field(None, max_length=280)
    description: str | None = None
    description_am: str | None = None
    short_description: str | None = Field(None, max_length=500)

    category_id: int | None = None
    category: ProductCategory | None = None
    subcategory: str | None = Field(None, max_length=100)
    tags: list[str] | None = None

    price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    compare_price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    cost_price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)

    stock_quantity: int | None = Field(None, ge=0)
    low_stock_threshold: int | None = Field(None, ge=0)
    sku: str | None = Field(None, max_length=100)
    barcode: str | None = Field(None, max_length=100)

    weight: float | None = Field(None, ge=0)
    dimensions: str | None = Field(None, max_length=100)

    images: list[str] | None = None
    video_url: str | None = Field(None, max_length=500)

    status: ProductStatus | None = None
    is_featured: bool | None = None
    is_on_sale: bool | None = None
    sale_start_date: datetime | None = None
    sale_end_date: datetime | None = None

    meta_title: str | None = Field(None, max_length=255)
    meta_description: str | None = None


class ProductResponse(ProductBase, IdSchema, TimestampSchema):
    """Schema for product response."""

    vendor_id: int = Field(..., description="Vendor ID")
    vendor_name: str | None = Field(None, description="Vendor business name")
    category_name: str | None = Field(None, description="Category name")

    views_count: int = Field(0, description="Number of views")
    sales_count: int = Field(0, description="Number of sales")
    rating: float = Field(0.0, ge=0, le=5, description="Average rating")
    reviews_count: int = Field(0, description="Number of reviews")

    discounted_price: Decimal | None = Field(None, description="Current discounted price")
    discount_percent: float | None = Field(None, description="Discount percentage")
    is_in_stock: bool = Field(True, description="Whether product is in stock")
    is_low_stock: bool = Field(False, description="Whether stock is low")

    class Config:
        from_attributes = True


class ProductListResponse(BaseSchema):
    """Schema for product list response."""

    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================
# Category Schemas
# ============================


class CategoryBase(BaseSchema):
    """Base category schema."""

    name: str = Field(..., max_length=100, description="Category name")
    name_am: str | None = Field(None, max_length=100, description="Category name in Amharic")
    slug: str | None = Field(None, max_length=120, description="URL-friendly slug")
    description: str | None = Field(None, description="Category description")
    description_am: str | None = Field(None, description="Category description in Amharic")
    parent_id: int | None = Field(None, description="Parent category ID")
    image_url: str | None = Field(None, max_length=500, description="Category image URL")
    icon_url: str | None = Field(None, max_length=500, description="Category icon URL")
    meta_title: str | None = Field(None, max_length=255)
    meta_description: str | None = Field(None)
    display_order: int = Field(0, description="Display order")
    is_active: bool = Field(True, description="Whether category is active")
    is_featured: bool = Field(False, description="Featured category flag")


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""

    pass


class CategoryUpdate(BaseSchema):
    """Schema for updating a category."""

    name: str | None = Field(None, max_length=100)
    name_am: str | None = Field(None, max_length=100)
    slug: str | None = Field(None, max_length=120)
    description: str | None = None
    description_am: str | None = None
    parent_id: int | None = None
    image_url: str | None = Field(None, max_length=500)
    icon_url: str | None = Field(None, max_length=500)
    meta_title: str | None = Field(None, max_length=255)
    meta_description: str | None = None
    display_order: int | None = None
    is_active: bool | None = None
    is_featured: bool | None = None


class CategoryResponse(CategoryBase, IdSchema, TimestampSchema):
    """Schema for category response."""

    product_count: int = Field(0, description="Number of products in category")
    children: list["CategoryResponse"] = Field(default_factory=list, description="Child categories")

    class Config:
        from_attributes = True


CategoryResponse.model_rebuild()


# ============================
# Review Schemas
# ============================


class ReviewBase(BaseSchema):
    """Base review schema."""

    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    title: str | None = Field(None, max_length=255, description="Review title")
    comment: str | None = Field(None, description="Review comment")
    comment_am: str | None = Field(None, description="Review comment in Amharic")
    images: list[str] | None = Field(None, description="Review images")


class ReviewCreate(ReviewBase):
    """Schema for creating a review."""

    pass


class ReviewUpdate(BaseSchema):
    """Schema for updating a review."""

    rating: int | None = Field(None, ge=1, le=5)
    title: str | None = Field(None, max_length=255)
    comment: str | None = None
    comment_am: str | None = None


class ReviewResponse(ReviewBase, IdSchema, TimestampSchema):
    """Schema for review response."""

    user_id: int = Field(..., description="User ID")
    user_name: str | None = Field(None, description="User name")
    product_id: int = Field(..., description="Product ID")
    order_id: int | None = Field(None, description="Order ID")
    is_approved: bool = Field(False, description="Whether review is approved")
    is_verified_purchase: bool = Field(False, description="Verified purchase flag")
    helpful_count: int = Field(0, description="Number of helpful votes")
    not_helpful_count: int = Field(0, description="Number of not helpful votes")
    vendor_response: str | None = Field(None, description="Vendor response")
    vendor_response_at: datetime | None = Field(None, description="Vendor response time")

    class Config:
        from_attributes = True


class ReviewSummaryResponse(BaseSchema):
    """Schema for review summary."""

    total_reviews: int = Field(0, description="Total number of reviews")
    average_rating: float = Field(0.0, description="Average rating")
    rating_distribution: dict[int, int] = Field(
        default_factory=dict, description="Rating distribution"
    )


# ============================
# Search Schemas
# ============================


class ProductSearchParams(BaseSchema):
    """Schema for product search parameters."""

    query: str = Field(..., description="Search query")
    category: ProductCategory | None = Field(None, description="Filter by category")
    category_id: int | None = Field(None, description="Filter by category ID")
    vendor_id: int | None = Field(None, description="Filter by vendor ID")
    min_price: Decimal | None = Field(None, ge=0, description="Minimum price")
    max_price: Decimal | None = Field(None, ge=0, description="Maximum price")
    min_rating: float | None = Field(None, ge=0, le=5, description="Minimum rating")
    in_stock_only: bool = Field(False, description="Show only in-stock products")
    on_sale_only: bool = Field(False, description="Show only products on sale")
    sort_by: str | None = Field(None, description="Sort field (price, rating, sales, newest)")
    sort_desc: bool = Field(True, description="Sort descending")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


__all__ = [
    "CategoryBase",
    "CategoryCreate",
    "CategoryResponse",
    "CategoryUpdate",
    "ProductBase",
    "ProductCreate",
    "ProductListResponse",
    "ProductResponse",
    "ProductSearchParams",
    "ProductUpdate",
    "ReviewBase",
    "ReviewCreate",
    "ReviewResponse",
    "ReviewSummaryResponse",
    "ReviewUpdate",
]
