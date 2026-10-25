# ============================
# WOLLOYEWA STORE BOT - PRODUCT SERVICES
# ============================
"""Business logic for product management, categories, and reviews."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.inventory.schemas import InventoryCreate, InventoryUpdate
from apps.inventory.services import InventoryService
from apps.products.models import Category, Product, Review
from apps.products.repository import CategoryRepository, ProductRepository, ReviewRepository
from apps.products.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductUpdate,
    ReviewCreate,
)
from core.constants import ProductStatus
from core.events import (
    PRODUCT_CREATED,
    PRODUCT_DELETED,
    PRODUCT_STOCK_LOW,
    PRODUCT_UPDATED,
    emit_event,
)
from core.exceptions import InsufficientStockError, NotFoundError, PermissionError, ValidationError
from core.logger import logger
from core.utils.string_utils import slugify


class ProductService:
    """Service for product management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.category_repo = CategoryRepository(db)
        self.inventory_service = InventoryService(db)

    async def create_product(
        self,
        vendor_id: int,
        data: ProductCreate,
        *,
        admin_approved: bool = False,
    ) -> Product:
        """
        Create a new product.

        Args:
            vendor_id: ID of the vendor creating the product
            data: Product creation data

        Returns:
            Created product
        """
        vendor_allowed_statuses = {ProductStatus.DRAFT, ProductStatus.PENDING}
        if not admin_approved and data.status not in vendor_allowed_statuses:
            raise ValidationError("Only administrators can create an active product")
        if admin_approved and data.status is not ProductStatus.ACTIVE:
            raise ValidationError("Administrator-created products must be active")

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
        if data.category_id is not None:
            if not await self.category_repo.get_by_id(data.category_id):
                raise NotFoundError("Category", data.category_id)

        product = await self.product_repo.create(product_data)

        await self._sync_inventory(
            product,
            quantity=data.stock_quantity,
            low_stock_threshold=data.low_stock_threshold,
        )
        if product.category_id is not None:
            await self.category_repo.update_product_count(product.category_id)

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
        update_data = data.dict(exclude_unset=True)
        requested_status = update_data.get("status")
        if requested_status is not None and requested_status not in {
            ProductStatus.DRAFT,
            ProductStatus.PENDING,
            ProductStatus.DISCONTINUED,
        }:
            raise ValidationError("Only administrators can change this product status")
        non_nullable_fields = {
            "name",
            "price",
            "stock_quantity",
            "low_stock_threshold",
            "sku",
            "status",
            "is_featured",
            "is_on_sale",
        }
        if any(
            field in update_data and update_data[field] is None
            for field in non_nullable_fields
        ):
            raise ValidationError("Required product fields cannot be set to null")
        if update_data.get("slug") is None:
            update_data.pop("slug")
        if update_data.get("category_id") is not None:
            category_id = update_data["category_id"]
            if not await self.category_repo.get_by_id(category_id):
                raise NotFoundError("Category", category_id)
        if (
            update_data.get("name")
            and update_data["name"] != product.name
            and "slug" not in update_data
        ):
            base_slug = slugify(update_data["name"])
            slug = base_slug
            counter = 1
            while await self.product_repo.get_by_slug(slug) and slug != product.slug:
                slug = f"{base_slug}-{counter}"
                counter += 1
            update_data["slug"] = slug

        previous_category_id = product.category_id
        # Update product
        updated = await self.product_repo.update(product_id, update_data, partial=False)
        if updated is None:
            raise NotFoundError("Product", product_id)

        if (
            data.stock_quantity is not None
            or data.low_stock_threshold is not None
            or data.sku is not None
            or data.barcode is not None
        ):
            await self._sync_inventory(
                updated,
                quantity=updated.stock_quantity,
                low_stock_threshold=updated.low_stock_threshold,
            )

        # Check low stock
        if (
            data.stock_quantity is not None
            and updated.stock_quantity <= updated.low_stock_threshold
        ):
            await emit_event(
                PRODUCT_STOCK_LOW,
                {
                    "product_id": product_id,
                    "vendor_id": vendor_id,
                    "current_stock": updated.stock_quantity,
                    "threshold": updated.low_stock_threshold,
                },
                sync=False,
            )

        # Emit event
        await emit_event(
            PRODUCT_UPDATED,
            {
                "product_id": product_id,
                "vendor_id": vendor_id,
                "updated_fields": list(update_data),
            },
            sync=False,
        )

        logger.info(f"Product updated: {product_id}")
        if previous_category_id != updated.category_id:
            if previous_category_id is not None:
                await self.category_repo.update_product_count(previous_category_id)
            if updated.category_id is not None:
                await self.category_repo.update_product_count(updated.category_id)
        return updated

    async def delete_product(self, product_id: int, vendor_id: int) -> bool:
        """Soft delete a product."""
        product = await self.get_product(product_id)

        if product.vendor_id != vendor_id:
            raise PermissionError("You don't have permission to delete this product")

        result = await self.product_repo.delete(product_id, soft=True)
        if product.category_id is not None:
            await self.category_repo.update_product_count(product.category_id)

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
        if quantity < 0:
            raise ValidationError("Stock quantity cannot be negative")
        if operation not in {"set", "add", "subtract"}:
            raise ValidationError(f"Unsupported stock operation: {operation}")
        if operation != "set" and quantity == 0:
            raise ValidationError("Stock adjustment quantity must be positive")

        product = await self.product_repo.adjust_stock(product_id, quantity, operation)
        if product is None:
            existing = await self.get_product(product_id)
            if operation == "subtract":
                raise InsufficientStockError(existing.name, quantity, existing.stock_quantity)
            raise NotFoundError("Product", product_id)

        # Update inventory service
        await self._sync_inventory(
            product,
            quantity=product.stock_quantity,
            low_stock_threshold=product.low_stock_threshold,
        )

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
        """Reserve stock for an order by decrementing stock_quantity on the product row."""
        if quantity <= 0:
            raise ValidationError("Reservation quantity must be positive")
        updated = await self.product_repo.adjust_stock(product_id, quantity, "subtract")
        if updated is None:
            await self.get_product(product_id)
            return False
        await self._sync_inventory(
            updated,
            quantity=updated.stock_quantity,
            low_stock_threshold=updated.low_stock_threshold,
        )
        logger.info(
            "Stock reserved: product=%s qty=-%s remaining=%s",
            product_id,
            quantity,
            updated.stock_quantity,
        )
        return True

    async def release_stock(self, product_id: int, quantity: int) -> None:
        """Return stock to the product row (e.g. on order cancellation)."""
        if quantity <= 0:
            raise ValidationError("Released quantity must be positive")
        updated = await self.product_repo.adjust_stock(product_id, quantity, "add")
        if updated is None:
            raise NotFoundError("Product", product_id)
        await self._sync_inventory(
            updated,
            quantity=updated.stock_quantity,
            low_stock_threshold=updated.low_stock_threshold,
        )
        logger.info(
            "Stock released: product=%s qty=+%s total=%s",
            product_id,
            quantity,
            updated.stock_quantity,
        )

    async def _sync_inventory(
        self,
        product: Product,
        *,
        quantity: int,
        low_stock_threshold: int,
    ) -> None:
        """Keep the inventory row aligned with product stock and SKU fields."""
        inventory = await self.inventory_service.get_inventory(product.id)
        if inventory is None:
            await self.inventory_service.create_inventory(
                InventoryCreate(
                    product_id=product.id,
                    vendor_id=product.vendor_id,
                    quantity=quantity,
                    low_stock_threshold=low_stock_threshold,
                    sku=product.sku,
                    barcode=product.barcode,
                )
            )
            return

        await self.inventory_service.update_inventory(
            product.id,
            InventoryUpdate(
                quantity=quantity,
                low_stock_threshold=low_stock_threshold,
                sku=product.sku,
                barcode=product.barcode,
            ),
        )

    async def get_vendor_products(
        self,
        vendor_id: int,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Product]:
        """Get products for a specific vendor."""
        return await self.product_repo.get_by_vendor(vendor_id, status, limit, offset)

    async def search_products(
        self,
        query: str,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        limit: int = 20,
    ) -> list[Product]:
        """Search products by name, description, or tags."""
        return await self.product_repo.search(query, category, min_price, max_price, limit)

    async def search_products_with_count(
        self,
        query: str,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        vendor_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        """Search products with vendor filtering, offset pagination, and a matching count."""
        return await self.product_repo.search_with_count(
            query=query,
            category=category,
            min_price=min_price,
            max_price=max_price,
            vendor_id=vendor_id,
            limit=limit,
            offset=offset,
        )

    async def get_featured_products(self, limit: int = 10) -> list[Product]:
        """Get featured products."""
        return await self.product_repo.get_featured(limit)

    async def get_new_arrivals(self, limit: int = 10, days: int = 30) -> list[Product]:
        """Get recently added products."""
        return await self.product_repo.get_new_arrivals(limit, days)

    async def get_products_on_sale(self, limit: int = 20) -> list[Product]:
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
        category_data = data.dict()
        base_slug = category_data.get("slug") or slugify(data.name)
        slug = base_slug
        counter = 1
        while await self.category_repo.get_by_slug(slug):
            if category_data.get("slug"):
                raise ValidationError(f"Category slug '{slug}' is already in use")
            slug = f"{base_slug}-{counter}"
            counter += 1
        category_data["slug"] = slug
        if category_data.get("parent_id") is not None:
            await self.get_category(category_data["parent_id"])
        return await self.category_repo.create(category_data)

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

        update_data = data.dict(exclude_unset=True)
        non_nullable_fields = {"name", "display_order", "is_active", "is_featured"}
        if any(
            field in update_data and update_data[field] is None
            for field in non_nullable_fields
        ):
            raise ValidationError("Required category fields cannot be set to null")
        if update_data.get("slug") is None:
            update_data.pop("slug")
        if data.name and data.name != category.name and "slug" not in update_data:
            base_slug = slugify(data.name)
            slug = base_slug
            counter = 1
            while await self.category_repo.get_by_slug(slug) and slug != category.slug:
                slug = f"{base_slug}-{counter}"
                counter += 1
            update_data["slug"] = slug

        parent_id = update_data.get("parent_id", category.parent_id)
        if parent_id == category_id:
            raise ValidationError("A category cannot be its own parent")
        if parent_id is not None:
            parent = await self.get_category(parent_id)
            visited = {category_id}
            while parent is not None:
                if parent.id in visited:
                    raise ValidationError("Category hierarchy cannot contain a cycle")
                visited.add(parent.id)
                parent = (
                    await self.get_category(parent.parent_id)
                    if parent.parent_id is not None
                    else None
                )

        if update_data.get("slug") and update_data["slug"] != category.slug:
            existing_slug = await self.category_repo.get_by_slug(update_data["slug"])
            if existing_slug:
                raise ValidationError(f"Category slug '{update_data['slug']}' is already in use")

        updated = await self.category_repo.update(category_id, update_data, partial=False)
        if updated is None:
            raise NotFoundError("Category", category_id)
        return updated

    async def delete_category(self, category_id: int) -> bool:
        """Delete a category."""
        category = await self.get_category(category_id)
        product_count = await self.db.scalar(
            select(func.count(Product.id)).where(Product.category_id == category_id)
        )
        child_count = await self.db.scalar(
            select(func.count(Category.id)).where(Category.parent_id == category_id)
        )
        if product_count or child_count:
            raise ValidationError("Cannot delete a category that has products or subcategories")
        return await self.category_repo.delete(category.id, soft=False)

    async def get_category_tree(self) -> list[dict[str, Any]]:
        """Get hierarchical category tree."""
        return await self.category_repo.get_tree()

    async def get_all_categories(self, active_only: bool = True) -> list[Category]:
        """Get all categories with children eagerly loaded."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = select(Category).options(selectinload(Category.children))
        if active_only:
            stmt = stmt.where(Category.is_active)
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
        review = await self.review_repo.create(
            {
                "user_id": user_id,
                "product_id": product_id,
                "rating": data.rating,
                "title": data.title,
                "comment": data.comment,
            }
        )

        # Update product rating
        await self._update_product_rating(product_id)

        logger.info(
            f"Review created: user {user_id} for product {product_id}, rating {data.rating}"
        )
        return review

    async def get_product_reviews(
        self,
        product_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Review], int]:
        """Get reviews for a product."""
        return await self.review_repo.get_by_product(product_id, limit, offset)

    async def get_review_summary(self, product_id: int) -> dict[str, Any]:
        """Get review summary statistics."""
        return await self.review_repo.get_summary(product_id)

    async def approve_review(self, review_id: int, admin_id: int) -> Review:
        """Approve a review (admin only)."""
        review = await self.review_repo.update(
            review_id,
            {
                "is_approved": True,
                "approved_at": datetime.utcnow(),
                "approved_by": admin_id,
            },
        )

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
        await self.product_repo.update(
            product_id,
            {
                "rating": summary["average_rating"],
                "reviews_count": summary["total_reviews"],
            },
        )


class SearchService:
    """Wrapper around ProductService for search operations."""

    def __init__(self, db):
        self._product_service = ProductService(db)

    async def search(self, query: str, **kwargs):
        return await self._product_service.search_products(query, **kwargs)


__all__ = ["CategoryService", "ProductService", "ReviewService", "SearchService"]
