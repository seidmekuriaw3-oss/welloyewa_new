# ============================
# WOLLOYEWA STORE BOT - PRODUCT MODELS
# ============================
"""Product, Category, Review, and related database models."""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, 
    BigInteger, Text, JSON, ForeignKey, Numeric, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from sqlalchemy.ext.hybrid import hybrid_property

from apps.common.models import BaseModel, TimestampMixin, SoftDeleteMixin, MetadataMixin
from core.constants import ProductStatus, ProductCategory

if TYPE_CHECKING:
    from apps.users.models import Vendor
    from apps.orders.models import OrderItem


class Category(BaseModel, TimestampMixin):
    """
    Product category model.
    
    Supports hierarchical categories (parent-child relationship).
    """
    
    __tablename__ = "categories"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name_am: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_am: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Hierarchy
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    
    # Media
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # SEO
    meta_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Display
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Counts
    product_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Hierarchy
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side=lambda: Category.id,
        primaryjoin="Category.id == foreign(Category.parent_id)",
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children: Mapped[List["Category"]] = relationship(
        "Category",
        primaryjoin="Category.parent_id == foreign(Category.id)",
        back_populates="parent",
        foreign_keys=[parent_id],
        cascade="all, delete-orphan",
    )
    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="category_rel",
        primaryjoin="Category.id == foreign(Product.category_id)",
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, slug={self.slug})>"


class Product(BaseModel, TimestampMixin, SoftDeleteMixin, MetadataMixin):
    """
    Product model for items sold by vendors.
    """
    
    __tablename__ = "products"
    
    # Vendor association
    vendor_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vendors.id", ondelete="CASCADE"), 
        nullable=False, index=True
    )
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name_am: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    slug: Mapped[str] = mapped_column(String(280), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_am: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Categorization
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    
    # ስሙን category ወደ category_type ቀይረው
    category_type: Mapped[Optional[str]] = mapped_column(
        SQLEnum(ProductCategory, name="product_category"), 
        nullable=True, index=True
    )
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    compare_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)  # Original price for discount display
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)   # Vendor cost
    
    # Inventory
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    sku: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Shipping
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in kg
    dimensions: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # LxWxH
    
    # Media
    images: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # List of image URLs
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        SQLEnum(ProductStatus, name="product_status"),
        nullable=False,
        default=ProductStatus.DRAFT,
        index=True
    )
    
    # Features
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_on_sale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sale_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sale_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # SEO
    meta_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Statistics
    views_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sales_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reviews_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Relationships
    vendor: Mapped["Vendor"] = relationship(
        "Vendor",
        back_populates="products",
        foreign_keys=[vendor_id],
        primaryjoin="Vendor.id == foreign(Product.vendor_id)",
    )
    category_rel: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="products",
        foreign_keys=[category_id],
        primaryjoin="Category.id == foreign(Product.category_id)",
    )
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product")
    
    @hybrid_property
    def discounted_price(self) -> Optional[Decimal]:
        """Calculate discounted price if product is on sale."""
        if self.is_on_sale and self.compare_price and self.compare_price > self.price:
            return self.price
        return None
    
    @hybrid_property
    def discount_percent(self) -> Optional[float]:
        """Calculate discount percentage."""
        if self.is_on_sale and self.compare_price and self.compare_price > self.price:
            discount = (self.compare_price - self.price) / self.compare_price * 100
            return round(float(discount), 1)
        return None
    
    @hybrid_property
    def is_in_stock(self) -> bool:
        """Check if product is in stock."""
        return self.stock_quantity > 0 and self.status == ProductStatus.ACTIVE.value
    
    @hybrid_property
    def is_low_stock(self) -> bool:
        """Check if stock is below threshold."""
        return 0 < self.stock_quantity <= self.low_stock_threshold
    
    def reduce_stock(self, quantity: int) -> bool:
        """Reduce stock quantity."""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            return True
        return False
    
    def increase_stock(self, quantity: int) -> None:
        """Increase stock quantity."""
        self.stock_quantity += quantity
    
    def update_rating(self) -> None:
        """Update average rating based on reviews."""
        if self.reviews:
            total_rating = sum(r.rating for r in self.reviews if r.is_approved)
            self.rating = total_rating / len(self.reviews)
            self.reviews_count = len(self.reviews)
    
    def increment_views(self) -> None:
        """Increment view count."""
        self.views_count += 1
    
    def increment_sales(self, quantity: int = 1) -> None:
        """Increment sales count."""
        self.sales_count += quantity
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name={self.name}, sku={self.sku})>"


class ProductImage(BaseModel, TimestampMixin):
    """
    Individual product image with ordering.
    """
    
    __tablename__ = "product_images"
    
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    alt_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", backref="image_objects")
    
    def __repr__(self) -> str:
        return f"<ProductImage(id={self.id}, product_id={self.product_id}, is_primary={self.is_primary})>"


class Review(BaseModel, TimestampMixin):
    """
    Product review and rating from customers.
    """
    
    __tablename__ = "reviews"
    
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    order_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)  # Verified purchase
    
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comment_am: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Media
    images: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Moderation
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Vendor response
    vendor_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vendor_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Helpfulness
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    not_helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reviews")
    product: Mapped["Product"] = relationship("Product", back_populates="reviews")
    
    def __repr__(self) -> str:
        return f"<Review(id={self.id}, user_id={self.user_id}, product_id={self.product_id}, rating={self.rating})>"