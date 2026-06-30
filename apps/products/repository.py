# ============================
# WOLLOYEWA STORE BOT - PRODUCT REPOSITORIES
# ============================
"""Database repositories for Product, Category, and Review models."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from sqlalchemy import select, update, func, and_, or_, String
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.repository import BaseRepository
from apps.products.models import Product, Category, Review
from core.constants import ProductStatus
from core.logger import logger


class ProductRepository(BaseRepository[Product]):
    """Repository for Product model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Product, db)
    
    async def get_by_slug(self, slug: str) -> Optional[Product]:
        """Get product by slug."""
        query = select(Product).where(Product.slug == slug, Product.is_deleted == False)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU."""
        query = select(Product).where(Product.sku == sku, Product.is_deleted == False)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_vendor(
        self,
        vendor_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """Get products by vendor ID."""
        query = select(Product).where(Product.vendor_id == vendor_id, Product.is_deleted == False)
        
        if status:
            query = query.where(Product.status == status)
        
        query = query.order_by(Product.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_category(
        self,
        category_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """Get products by category ID."""
        query = select(Product).where(
            Product.category_id == category_id,
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False
        )
        query = query.order_by(Product.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_active_products(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """Get active products."""
        query = select(Product).where(
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False
        )
        query = query.order_by(Product.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_featured(self, limit: int = 10) -> List[Product]:
        """Get featured products."""
        query = select(Product).where(
            Product.is_featured == True,
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False
        )
        query = query.order_by(Product.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_on_sale(self, limit: int = 20) -> List[Product]:
        """Get products currently on sale."""
        now = datetime.utcnow()
        query = select(Product).where(
            Product.is_on_sale == True,
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False,
            or_(
                Product.sale_start_date <= now,
                Product.sale_start_date.is_(None)
            ),
            or_(
                Product.sale_end_date >= now,
                Product.sale_end_date.is_(None)
            )
        )
        query = query.order_by(Product.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_new_arrivals(self, limit: int = 10, days: int = 30) -> List[Product]:
        """Get recently added products."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = select(Product).where(
            Product.created_at >= cutoff,
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False
        )
        query = query.order_by(Product.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 20,
    ) -> List[Product]:
        """Search products by name, description, or tags."""
        search_pattern = f"%{query}%"
        
        conditions = [
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False,
            or_(
                Product.name.ilike(search_pattern),
                Product.name_am.ilike(search_pattern),
                Product.description.ilike(search_pattern),
                Product.tags.cast(String).ilike(search_pattern)
            )
        ]
        
        if category:
            conditions.append(Product.category == category)
        
        if min_price is not None:
            conditions.append(Product.price >= min_price)
        
        if max_price is not None:
            conditions.append(Product.price <= max_price)
        
        stmt = select(Product).where(and_(*conditions))
        stmt = stmt.order_by(Product.sales_count.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_low_stock_products(
        self,
        vendor_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Product]:
        """Get products with low stock."""
        query = select(Product).where(
            Product.stock_quantity <= Product.low_stock_threshold,
            Product.stock_quantity > 0,
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False
        )
        
        if vendor_id:
            query = query.where(Product.vendor_id == vendor_id)
        
        query = query.order_by(Product.stock_quantity.asc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_out_of_stock_products(
        self,
        vendor_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Product]:
        """Get out of stock products."""
        query = select(Product).where(
            Product.stock_quantity == 0,
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False
        )
        
        if vendor_id:
            query = query.where(Product.vendor_id == vendor_id)
        
        query = query.order_by(Product.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def increment_views(self, product_id: int) -> None:
        """Increment product view count."""
        await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(views_count=Product.views_count + 1)
        )
        await self.db.flush()
    
    async def increment_sales(self, product_id: int, quantity: int = 1) -> None:
        """Increment product sales count."""
        await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(sales_count=Product.sales_count + quantity)
        )
        await self.db.flush()
    
    async def get_vendor_stats(self, vendor_id: int) -> Dict[str, Any]:
        """Get product statistics for a vendor."""
        query = select(
            func.count().label("total"),
            func.sum(func.case((Product.status == ProductStatus.ACTIVE.value, 1), else_=0)).label("active"),
            func.sum(func.case((Product.status == ProductStatus.DRAFT.value, 1), else_=0)).label("draft"),
            func.sum(func.case((Product.stock_quantity == 0, 1), else_=0)).label("out_of_stock"),
            func.sum(func.case((Product.stock_quantity <= Product.low_stock_threshold, 1), else_=0)).label("low_stock"),
        ).where(Product.vendor_id == vendor_id, Product.is_deleted == False)
        
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "total": row.total or 0,
            "active": row.active or 0,
            "draft": row.draft or 0,
            "out_of_stock": row.out_of_stock or 0,
            "low_stock": row.low_stock or 0,
        }


class CategoryRepository(BaseRepository[Category]):
    """Repository for Category model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Category, db)
    
    async def get_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug."""
        query = select(Category).where(Category.slug == slug)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_parent_categories(self) -> List[Category]:
        """Get top-level categories (no parent)."""
        query = select(Category).where(Category.parent_id.is_(None), Category.is_active == True)
        query = query.order_by(Category.display_order)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_subcategories(self, parent_id: int) -> List[Category]:
        """Get subcategories for a parent category."""
        query = select(Category).where(
            Category.parent_id == parent_id,
            Category.is_active == True
        )
        query = query.order_by(Category.display_order)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_tree(self) -> List[Dict[str, Any]]:
        """Get hierarchical category tree."""
        def build_tree(categories, parent_id=None):
            tree = []
            for cat in categories:
                if cat.parent_id == parent_id:
                    children = build_tree(categories, cat.id)
                    tree.append({
                        "id": cat.id,
                        "name": cat.name,
                        "name_am": cat.name_am,
                        "slug": cat.slug,
                        "image_url": cat.image_url,
                        "product_count": cat.product_count,
                        "children": children,
                    })
            return tree
        
        categories = await self.get_all(active_only=True)
        return build_tree(categories)
    
    async def update_product_count(self, category_id: int) -> None:
        """Update product count for a category."""
        from apps.products.models import Product
        from core.constants import ProductStatus
        
        count_query = select(func.count()).where(
            Product.category_id == category_id,
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False
        )
        count = await self.db.execute(count_query)
        product_count = count.scalar() or 0
        
        await self.update(category_id, {"product_count": product_count})


class ReviewRepository(BaseRepository[Review]):
    """Repository for Review model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Review, db)
    
    async def get_by_product(
        self,
        product_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Review], int]:
        """Get reviews for a product (approved only)."""
        # Get total count
        count_query = select(func.count()).where(
            Review.product_id == product_id,
            Review.is_approved == True
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Get reviews
        query = select(Review).where(
            Review.product_id == product_id,
            Review.is_approved == True
        )
        query = query.order_by(Review.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        
        return result.scalars().all(), total
    
    async def get_by_user_product(self, user_id: int, product_id: int) -> Optional[Review]:
        """Get review by user and product."""
        query = select(Review).where(
            Review.user_id == user_id,
            Review.product_id == product_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_pending_reviews(self, limit: int = 50) -> List[Review]:
        """Get reviews awaiting approval."""
        query = select(Review).where(Review.is_approved == False)
        query = query.order_by(Review.created_at.asc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_summary(self, product_id: int) -> Dict[str, Any]:
        """Get review summary for a product."""
        query = select(
            func.count().label("total"),
            func.avg(Review.rating).label("average"),
            func.sum(func.case((Review.rating == 5, 1), else_=0)).label("rating_5"),
            func.sum(func.case((Review.rating == 4, 1), else_=0)).label("rating_4"),
            func.sum(func.case((Review.rating == 3, 1), else_=0)).label("rating_3"),
            func.sum(func.case((Review.rating == 2, 1), else_=0)).label("rating_2"),
            func.sum(func.case((Review.rating == 1, 1), else_=0)).label("rating_1"),
        ).where(
            Review.product_id == product_id,
            Review.is_approved == True
        )
        
        result = await self.db.execute(query)
        row = result.one()
        
        total = row.total or 0
        average = float(row.average) if row.average else 0.0
        
        return {
            "total_reviews": total,
            "average_rating": round(average, 1),
            "rating_distribution": {
                5: row.rating_5 or 0,
                4: row.rating_4 or 0,
                3: row.rating_3 or 0,
                2: row.rating_2 or 0,
                1: row.rating_1 or 0,
            },
        }
    
    async def mark_helpful(self, review_id: int) -> None:
        """Mark a review as helpful."""
        await self.db.execute(
            update(Review)
            .where(Review.id == review_id)
            .values(helpful_count=Review.helpful_count + 1)
        )
        await self.db.flush()
    
    async def mark_not_helpful(self, review_id: int) -> None:
        """Mark a review as not helpful."""
        await self.db.execute(
            update(Review)
            .where(Review.id == review_id)
            .values(not_helpful_count=Review.not_helpful_count + 1)
        )
        await self.db.flush()


__all__ = ["ProductRepository", "CategoryRepository", "ReviewRepository"]