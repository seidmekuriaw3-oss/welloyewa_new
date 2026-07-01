# ============================
# WOLLOYEWA STORE BOT - PRODUCT SERVICES
# ============================
"""Business logic for product management, categories, and reviews."""

from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from core.exceptions import NotFoundError, ValidationError, PermissionError, InsufficientStockError
from core.events import emit_event, PRODUCT_CREATED, PRODUCT_UPDATED, PRODUCT_DELETED, PRODUCT_STOCK_LOW
from core.utils.validators import Validator
from core.utils.string_utils import slugify
from apps.products.repository import ProductRepository, CategoryRepository, ReviewRepository
from apps.products.models import Product, Category, Review
from apps.products.schemas import ProductCreate, ProductUpdate, CategoryCreate, CategoryUpdate, ReviewCreate
from apps.inventory.services import InventoryService


class ProductService:
    """Service for product management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.category_repo = CategoryRepository(db)
        self.inventory_service = InventoryService(db)
    
    async def create_product(self, vendor_id: int, data: ProductCreate) -> Product:
        """
        Create a new product.
        
        Args:
            vendor_id: ID of the vendor creating the product
            data: Product creation data
            
        Returns:
            Created product
        """
        # Generate slug if not provided
        if not data.slug:
            base_slug = slugify(data.name)
            slug = base_slug
            counter = 1
            while await self.product_repo.get_by_slug(slug):
                slug = f"{base_slug}-{counter}"
                counter += 1
            data.slug = slug
        
        # Create product
        product_data = data.dict()
        product_data["vendor_id"] = vendor_id
        
        product = await self.product_repo.create(product_data)
        
        # Create inventory record
        await self.inventory_service.create_inventory(
            product_id=product.id,
            vendor_id=vendor_id,
            quantity=data.stock_quantity,
            low_stock_threshold=data.low_stock_threshold,
        )
        
        # Emit event
        await emit_event(
            PRODUCT_CREATED,
            {
                "product_id": product.id,
                "vendor_id": vendor_id,
                "name": product.name,
                "price": float(product.price),
            },
            sync=False,
        )
        
        logger.info(f"Product created: {product.id} by vendor {vendor_id}")
        return product
    
    async def get_product(self, product_id: int) -> Product:
        """Get product by ID."""
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product", product_id)
        return product
    
    async def get_product_by_slug(self, slug: str) -> Product:
        """Get product by slug."""
        product = await self.product_repo.get_by_slug(slug)
        if not product:
            raise NotFoundError("Product", slug)
        return product
    
    async def update_product(
        self,
        product_id: int,
        vendor_id: int,
        data: ProductUpdate,
    ) -> Product:
        """
        Update a product.
        
        Args:
            product_id: Product ID
            vendor_id: Vendor ID (for permission check)
            data: Update data
            
        Returns:
            Updated product
        """
        product = await self.get_product(product_id)
        
        # Check permission
        if product.vendor_id != vendor_id:
            raise PermissionError("You don't have permission to update this product")
        
        # Update slug if name changed
        if data.name and data.name != product.name:
            base_slug = slugify(data.name)
            slug = base_slug
            counter = 1
            while await self.product_repo.get_by_slug(slug) and slug != product.slug:
                slug = f"{base_slug}-{counter}"
                counter += 1
            data.slug = slug
        
        # Update product
        updated = await self.product_repo.update(product_id, data.dict(exclude_unset=True))
        
        # Update inventory if stock changed
        if data.stock_quantity is not None:
            await self.inventory_service.update_inventory(
                product_id=product_id,
                quantity=data.stock_quantity,
            )
        
        # Check low stock
        if data.stock_quantity is not None and data.stock_quantity <= product.low_stock_threshold:
            await emit_event(
                PRODUCT_STOCK_LOW,
                {
                    "product_id": product_id,
                    "vendor_id": vendor_id,
                    "current_stock": data.stock_quantity,
                    "threshold": product.low_stock_threshold,
                },
                sync=False,
            )
        
        # Emit event
        await emit_event(
            PRODUCT_UPDATED,
            {
                "product_id": product_id,
                "vendor_id": vendor_id,
                "updated_fields": list(data.dict(exclude_unset=True).keys()),
            },
            sync=False,
        )
        
        logger.info(f"Product updated: {product_id}")
        return updated
    
    async def delete_product(self, product_id: int, vendor_id: int) -> bool:
        """Soft delete a product."""
        product = await self.get_product(product_id)
        
        if product.vendor_id != vendor_id:
            raise PermissionError("You don't have permission to delete this product")
        
        result = await self.product_repo.delete(product_id, soft=True)
        
        # Emit event
        await emit_event(
            PRODUCT_DELETED,
            {
                "product_id": product_id,
                "vendor_id": vendor_id,
                "name": product.name,
            },
            sync=False,
        )
        
        logger.info(f"Product deleted: {product_id}")
        return result
    
    async def update_stock(
        self,
        product_id: int,
        quantity: int,
        operation: str = "set",  # 'set', 'add', 'subtract'
    ) -> Product:
        """Update product stock quantity."""
        product = await self.get_product(product_id)
        
        if operation == "set":
            product.stock_quantity = quantity
        elif operation == "add":
            product.stock_quantity += quantity
        elif operation == "subtract":
            if product.stock_quantity < quantity:
                raise InsufficientStockError(product.name, quantity, product.stock_quantity)
            product.stock_quantity -= quantity
        
        await self.product_repo.update(product_id, {"stock_quantity": product.stock_quantity})
        
        # Update inventory service
        await self.inventory_service.update_inventory(product_id, product.stock_quantity)
        
        # Check low stock
        if product.stock_quantity <= product.low_stock_threshold:
            await emit_event(
                PRODUCT_STOCK_LOW,
                {
                    "product_id": product_id,
                    "vendor_id": product.vendor_id,
                    "current_stock": product.stock_quantity,
                    "threshold": product.low_stock_threshold,
                },
                sync=False,
            )
        
        return product
    
    async def reserve_stock(self, product_id: int, quantity: int) -> bool:
        """Reserve stock for an order."""
        product = await self.get_product(product_id)
        
        if product.stock_quantity < quantity:
            return False
        
        product.stock_quantity -= quantity
        await self.product_repo.update(product_id, {"stock_quantity": product.stock_quantity})
        
        # Create reservation in inventory service
        await self.inventory_service.reserve_inventory(product_id, quantity)
        
        return True
    
    async def release_stock(self, product_id: int, quantity: int) -> None:
        """Release reserved stock."""
        product = await self.get_product(product_id)
        product.stock_quantity += quantity
        await self.product_repo.update(product_id, {"stock_quantity": product.stock_quantity})
        
        await self.inventory_service.release_reservation(product_id, quantity)
    
    async def get_vendor_products(
        self,
        vendor_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """Get products for a specific vendor."""
        return await self.product_repo.get_by_vendor(vendor_id, status, limit, offset)
    
    async def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 20,
    ) -> List[Product]:
        """Search products by name, description, or tags."""
        return await self.product_repo.search(query, category, min_price, max_price, limit)
    
    async def get_featured_products(self, limit: int = 10) -> List[Product]:
        """Get featured products."""
        return await self.product_repo.get_featured(limit)
    
    async def get_new_arrivals(self, limit: int = 10, days: int = 30) -> List[Product]:
        """Get recently added products."""
        return await self.product_repo.get_new_arrivals(limit, days)
    
    async def get_products_on_sale(self, limit: int = 20) -> List[Product]:
        """Get products currently on sale."""
        return await self.product_repo.get_on_sale(limit)
    
    async def increment_view_count(self, product_id: int) -> None:
        """Increment product view count."""
        await self.product_repo.increment_views(product_id)


class CategoryService:
    """Service for category management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.category_repo = CategoryRepository(db)
    
    async def create_category(self, data: CategoryCreate) -> Category:
        """Create a new category."""
        # Generate slug
        if not data.slug:
            data.slug = slugify(data.name)
        
        return await self.category_repo.create(data.dict())
    
    async def get_category(self, category_id: int) -> Category:
        """Get category by ID."""
        category = await self.category_repo.get_by_id(category_id)
        if not category:
            raise NotFoundError("Category", category_id)
        return category
    
    async def get_category_by_slug(self, slug: str) -> Category:
        """Get category by slug."""
        category = await self.category_repo.get_by_slug(slug)
        if not category:
            raise NotFoundError("Category", slug)
        return category
    
    async def update_category(self, category_id: int, data: CategoryUpdate) -> Category:
        """Update a category."""
        category = await self.get_category(category_id)
        
        # Update slug if name changed
        if data.name and data.name != category.name:
            data.slug = slugify(data.name)
        
        return await self.category_repo.update(category_id, data.dict(exclude_unset=True))
    
    async def delete_category(self, category_id: int) -> bool:
        """Delete a category."""
        return await self.category_repo.delete(category_id, soft=False)
    
    async def get_category_tree(self) -> List[Dict[str, Any]]:
        """Get hierarchical category tree."""
        return await self.category_repo.get_tree()
    
    async def get_all_categories(self, active_only: bool = True) -> List[Category]:
        """Get all categories with children eagerly loaded."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        stmt = select(Category).options(selectinload(Category.children))
        if active_only:
            stmt = stmt.where(Category.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalars().all()


class ReviewService:
    """Service for product review management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.review_repo = ReviewRepository(db)
        self.product_repo = ProductRepository(db)
    
    async def create_review(
        self,
        user_id: int,
        product_id: int,
        data: ReviewCreate,
    ) -> Review:
        """Create a product review."""
        # Check if product exists
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product", product_id)
        
        # Check if user already reviewed this product
        existing = await self.review_repo.get_by_user_product(user_id, product_id)
        if existing:
            raise ValidationError("You have already reviewed this product")
        
        # Create review
        review = await self.review_repo.create({
            "user_id": user_id,
            "product_id": product_id,
            "rating": data.rating,
            "title": data.title,
            "comment": data.comment,
        })
        
        # Update product rating
        await self._update_product_rating(product_id)
        
        logger.info(f"Review created: user {user_id} for product {product_id}, rating {data.rating}")
        return review
    
    async def get_product_reviews(
        self,
        product_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Review], int]:
        """Get reviews for a product."""
        return await self.review_repo.get_by_product(product_id, limit, offset)
    
    async def get_review_summary(self, product_id: int) -> Dict[str, Any]:
        """Get review summary statistics."""
        return await self.review_repo.get_summary(product_id)
    
    async def approve_review(self, review_id: int, admin_id: int) -> Review:
        """Approve a review (admin only)."""
        review = await self.review_repo.update(review_id, {
            "is_approved": True,
            "approved_at": datetime.utcnow(),
            "approved_by": admin_id,
        })
        
        if review:
            await self._update_product_rating(review.product_id)
        
        return review
    
    async def delete_review(self, review_id: int, user_id: int, is_admin: bool = False) -> bool:
        """Delete a review."""
        review = await self.review_repo.get_by_id(review_id)
        if not review:
            raise NotFoundError("Review", review_id)
        
        # Check permission
        if not is_admin and review.user_id != user_id:
            raise PermissionError("You don't have permission to delete this review")
        
        product_id = review.product_id
        result = await self.review_repo.delete(review_id)
        
        # Update product rating
        await self._update_product_rating(product_id)
        
        return result
    
    async def _update_product_rating(self, product_id: int) -> None:
        """Update product's average rating."""
        summary = await self.review_repo.get_summary(product_id)
        await self.product_repo.update(product_id, {
            "rating": summary["average_rating"],
            "reviews_count": summary["total_reviews"],
        })


from datetime import datetime


class SearchService:
    """Wrapper around ProductService for search operations."""

    def __init__(self, db):
        self._product_service = ProductService(db)

    async def search(self, query: str, **kwargs):
        return await self._product_service.search_products(query, **kwargs)


__all__ = ["ProductService", "CategoryService", "ReviewService", "SearchService"]