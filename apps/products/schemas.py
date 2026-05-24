# ============================
# WOLLOYEWA STORE BOT - PRODUCT SCHEMAS
# ============================
"""Pydantic schemas for product request/response validation."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import Field, validator, root_validator

from apps.common.schemas import BaseSchema, IdSchema, TimestampSchema
from core.constants import ProductStatus, ProductCategory


# ============================
# Product Schemas
# ============================

class ProductBase(BaseSchema):
    """Base product schema."""
    
    name: str = Field(..., max_length=255, description="Product name")
    name_am: Optional[str] = Field(None, max_length=255, description="Product name in Amharic")
    slug: Optional[str] = Field(None, max_length=280, description="URL-friendly slug")
    description: Optional[str] = Field(None, description="Product description")
    description_am: Optional[str] = Field(None, description="Product description in Amharic")
    short_description: Optional[str] = Field(None, max_length=500, description="Short description")
    
    category_id: Optional[int] = Field(None, description="Category ID")
    category: Optional[ProductCategory] = Field(None, description="Product category")
    subcategory: Optional[str] = Field(None, max_length=100, description="Subcategory")
    tags: Optional[List[str]] = Field(None, description="Product tags")
    
    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2, description="Price in ETB")
    compare_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2, description="Compare at price")
    cost_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2, description="Cost price")
    
    stock_quantity: int = Field(0, ge=0, description="Available stock quantity")
    low_stock_threshold: int = Field(5, ge=0, description="Low stock alert threshold")
    sku: str = Field(..., max_length=100, description="Stock keeping unit")
    barcode: Optional[str] = Field(None, max_length=100, description="Product barcode")
    
    weight: Optional[float] = Field(None, ge=0, description="Weight in kg")
    dimensions: Optional[str] = Field(None, max_length=100, description="Dimensions (LxWxH)")
    
    images: Optional[List[str]] = Field(None, description="Product image URLs")
    video_url: Optional[str] = Field(None, max_length=500, description="Product video URL")
    
    status: ProductStatus = Field(ProductStatus.DRAFT, description="Product status")
    is_featured: bool = Field(False, description="Featured product flag")
    is_on_sale: bool = Field(False, description="On sale flag")
    sale_start_date: Optional[datetime] = Field(None, description="Sale start date")
    sale_end_date: Optional[datetime] = Field(None, description="Sale end date")
    
    meta_title: Optional[str] = Field(None, max_length=255, description="SEO meta title")
    meta_description: Optional[str] = Field(None, description="SEO meta description")


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    
    @validator('sku')
    def validate_sku(cls, v):
        if v:
            return v.upper().strip()
        return v


class ProductUpdate(BaseSchema):
    """Schema for updating a product."""
    
    name: Optional[str] = Field(None, max_length=255)
    name_am: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=280)
    description: Optional[str] = None
    description_am: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    
    category_id: Optional[int] = None
    category: Optional[ProductCategory] = None
    subcategory: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    
    price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    compare_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    cost_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    
    stock_quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    
    weight: Optional[float] = Field(None, ge=0)
    dimensions: Optional[str] = Field(None, max_length=100)
    
    images: Optional[List[str]] = None
    video_url: Optional[str] = Field(None, max_length=500)
    
    status: Optional[ProductStatus] = None
    is_featured: Optional[bool] = None
    is_on_sale: Optional[bool] = None
    sale_start_date: Optional[datetime] = None
    sale_end_date: Optional[datetime] = None
    
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = None


class ProductResponse(ProductBase, IdSchema, TimestampSchema):
    """Schema for product response."""
    
    vendor_id: int = Field(..., description="Vendor ID")
    vendor_name: Optional[str] = Field(None, description="Vendor business name")
    category_name: Optional[str] = Field(None, description="Category name")
    
    views_count: int = Field(0, description="Number of views")
    sales_count: int = Field(0, description="Number of sales")
    rating: float = Field(0.0, ge=0, le=5, description="Average rating")
    reviews_count: int = Field(0, description="Number of reviews")
    
    discounted_price: Optional[Decimal] = Field(None, description="Current discounted price")
    discount_percent: Optional[float] = Field(None, description="Discount percentage")
    is_in_stock: bool = Field(True, description="Whether product is in stock")
    is_low_stock: bool = Field(False, description="Whether stock is low")
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseSchema):
    """Schema for product list response."""
    
    items: List[ProductResponse]
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
    name_am: Optional[str] = Field(None, max_length=100, description="Category name in Amharic")
    slug: Optional[str] = Field(None, max_length=120, description="URL-friendly slug")
    description: Optional[str] = Field(None, description="Category description")
    description_am: Optional[str] = Field(None, description="Category description in Amharic")
    parent_id: Optional[int] = Field(None, description="Parent category ID")
    image_url: Optional[str] = Field(None, max_length=500, description="Category image URL")
    icon_url: Optional[str] = Field(None, max_length=500, description="Category icon URL")
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None)
    display_order: int = Field(0, description="Display order")
    is_active: bool = Field(True, description="Whether category is active")
    is_featured: bool = Field(False, description="Featured category flag")


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""
    
    pass


class CategoryUpdate(BaseSchema):
    """Schema for updating a category."""
    
    name: Optional[str] = Field(None, max_length=100)
    name_am: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    description_am: Optional[str] = None
    parent_id: Optional[int] = None
    image_url: Optional[str] = Field(None, max_length=500)
    icon_url: Optional[str] = Field(None, max_length=500)
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class CategoryResponse(CategoryBase, IdSchema, TimestampSchema):
    """Schema for category response."""
    
    product_count: int = Field(0, description="Number of products in category")
    children: List["CategoryResponse"] = Field(default_factory=list, description="Child categories")
    
    class Config:
        from_attributes = True


CategoryResponse.model_rebuild()


# ============================
# Review Schemas
# ============================

class ReviewBase(BaseSchema):
    """Base review schema."""
    
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    title: Optional[str] = Field(None, max_length=255, description="Review title")
    comment: Optional[str] = Field(None, description="Review comment")
    comment_am: Optional[str] = Field(None, description="Review comment in Amharic")
    images: Optional[List[str]] = Field(None, description="Review images")


class ReviewCreate(ReviewBase):
    """Schema for creating a review."""
    
    pass


class ReviewUpdate(BaseSchema):
    """Schema for updating a review."""
    
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = None
    comment_am: Optional[str] = None


class ReviewResponse(ReviewBase, IdSchema, TimestampSchema):
    """Schema for review response."""
    
    user_id: int = Field(..., description="User ID")
    user_name: Optional[str] = Field(None, description="User name")
    product_id: int = Field(..., description="Product ID")
    order_id: Optional[int] = Field(None, description="Order ID")
    is_approved: bool = Field(False, description="Whether review is approved")
    is_verified_purchase: bool = Field(False, description="Verified purchase flag")
    helpful_count: int = Field(0, description="Number of helpful votes")
    not_helpful_count: int = Field(0, description="Number of not helpful votes")
    vendor_response: Optional[str] = Field(None, description="Vendor response")
    vendor_response_at: Optional[datetime] = Field(None, description="Vendor response time")
    
    class Config:
        from_attributes = True


class ReviewSummaryResponse(BaseSchema):
    """Schema for review summary."""
    
    total_reviews: int = Field(0, description="Total number of reviews")
    average_rating: float = Field(0.0, description="Average rating")
    rating_distribution: Dict[int, int] = Field(default_factory=dict, description="Rating distribution")


# ============================
# Search Schemas
# ============================

class ProductSearchParams(BaseSchema):
    """Schema for product search parameters."""
    
    query: str = Field(..., description="Search query")
    category: Optional[ProductCategory] = Field(None, description="Filter by category")
    category_id: Optional[int] = Field(None, description="Filter by category ID")
    vendor_id: Optional[int] = Field(None, description="Filter by vendor ID")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[Decimal] = Field(None, ge=0, description="Maximum price")
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating")
    in_stock_only: bool = Field(False, description="Show only in-stock products")
    on_sale_only: bool = Field(False, description="Show only products on sale")
    sort_by: Optional[str] = Field(None, description="Sort field (price, rating, sales, newest)")
    sort_desc: bool = Field(True, description="Sort descending")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


__all__ = [
    "ProductBase", "ProductCreate", "ProductUpdate", "ProductResponse", "ProductListResponse",
    "CategoryBase", "CategoryCreate", "CategoryUpdate", "CategoryResponse",
    "ReviewBase", "ReviewCreate", "ReviewUpdate", "ReviewResponse", "ReviewSummaryResponse",
    "ProductSearchParams",
]