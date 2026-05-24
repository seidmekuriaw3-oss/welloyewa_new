# ============================
# WOLLOYEWA STORE BOT - PRODUCTS MODULE
# ============================
"""Product management module including products, categories, and reviews."""

from apps.products.models import Product, Category, ProductImage, Review
from apps.products.services import ProductService, CategoryService, ReviewService, SearchService
from apps.products.repository import ProductRepository, CategoryRepository, ReviewRepository
from apps.products.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ProductSearchParams,
)
from apps.products.search_engine import (
    ProductSearchEngine,
    search_products,
    index_product,
    delete_product_index,
)
from apps.products.pricing_engine import (
    PricingEngine,
    calculate_discounted_price,
    apply_bulk_discount,
    PriceRule,
)
from apps.products.category_manager import (
    CategoryManager,
    get_category_tree,
    get_category_products,
)
from apps.products.reviews import (
    ReviewManager,
    calculate_product_rating,
    get_product_reviews_summary,
)

__all__ = [
    # Models
    "Product",
    "Category",
    "ProductImage",
    "Review",
    # Services
    "ProductService",
    "CategoryService",
    "ReviewService",
    "SearchService",
    # Repositories
    "ProductRepository",
    "CategoryRepository",
    "ReviewRepository",
    # Schemas
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductListResponse",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "ReviewCreate",
    "ReviewUpdate",
    "ReviewResponse",
    "ProductSearchParams",
    # Search Engine
    "ProductSearchEngine",
    "search_products",
    "index_product",
    "delete_product_index",
    # Pricing Engine
    "PricingEngine",
    "calculate_discounted_price",
    "apply_bulk_discount",
    "PriceRule",
    # Category Manager
    "CategoryManager",
    "get_category_tree",
    "get_category_products",
    # Reviews
    "ReviewManager",
    "calculate_product_rating",
    "get_product_reviews_summary",
]