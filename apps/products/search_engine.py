# ============================
# WOLLOYEWA STORE BOT - PRODUCT SEARCH ENGINE
# ============================
"""Advanced product search with full-text search and filtering."""

from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from apps.products.models import Product
from apps.products.repository import ProductRepository
from core.constants import ProductStatus


class ProductSearchEngine:
    """
    Advanced product search engine.
    
    Features:
    - Full-text search on product names and descriptions
    - Multi-language support (Amharic, English)
    - Faceted search with filters
    - Sorting by relevance, price, rating, etc.
    - Pagination support
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_repo = ProductRepository(db)
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        category_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        min_rating: Optional[float] = None,
        in_stock_only: bool = False,
        on_sale_only: bool = False,
        sort_by: str = "relevance",
        sort_desc: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Product], int]:
        """
        Search products with filters.
        
        Args:
            query: Search query string
            category: Filter by category enum
            category_id: Filter by category ID
            vendor_id: Filter by vendor ID
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_rating: Minimum rating filter
            in_stock_only: Show only in-stock products
            on_sale_only: Show only products on sale
            sort_by: Sort field (relevance, price, rating, sales, newest)
            sort_desc: Sort descending
            page: Page number
            page_size: Items per page
            
        Returns:
            Tuple of (products, total_count)
        """
        # Build base conditions
        conditions = [
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False,
        ]
        
        # Search query (full-text)
        if query:
            search_conditions = await self._build_search_conditions(query)
            conditions.append(search_conditions)
        
        # Filters
        if category:
            conditions.append(Product.category == category)
        
        if category_id:
            conditions.append(Product.category_id == category_id)
        
        if vendor_id:
            conditions.append(Product.vendor_id == vendor_id)
        
        if min_price is not None:
            conditions.append(Product.price >= min_price)
        
        if max_price is not None:
            conditions.append(Product.price <= max_price)
        
        if min_rating is not None:
            conditions.append(Product.rating >= min_rating)
        
        if in_stock_only:
            conditions.append(Product.stock_quantity > 0)
        
        if on_sale_only:
            from datetime import datetime
            now = datetime.utcnow()
            conditions.append(Product.is_on_sale == True)
            conditions.append(
                or_(
                    Product.sale_start_date <= now,
                    Product.sale_start_date.is_(None)
                )
            )
            conditions.append(
                or_(
                    Product.sale_end_date >= now,
                    Product.sale_end_date.is_(None)
                )
            )
        
        # Build query
        query_stmt = select(Product).where(and_(*conditions))
        
        # Get total count
        count_stmt = select(func.count()).select_from(Product).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Apply sorting
        query_stmt = self._apply_sorting(query_stmt, sort_by, sort_desc, query)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query_stmt = query_stmt.offset(offset).limit(page_size)
        
        # Execute query
        result = await self.db.execute(query_stmt)
        products = result.scalars().all()
        
        return products, total
    
    async def _build_search_conditions(self, query: str):
        """Build search conditions for full-text search."""
        search_pattern = f"%{query}%"
        
        # Try PostgreSQL full-text search if available
        try:
            # Use tsvector for better search
            ts_query = func.plainto_tsquery('english', query)
            ts_vector = func.to_tsvector('english', 
                func.concat(Product.name, ' ', Product.description, ' ', Product.tags)
            )
            return ts_vector.op('@@')(ts_query)
        except Exception:
            # Fallback to LIKE search
            return or_(
                Product.name.ilike(search_pattern),
                Product.name_am.ilike(search_pattern),
                Product.description.ilike(search_pattern),
                Product.tags.cast(String).ilike(search_pattern)
            )
    
    def _apply_sorting(self, query, sort_by: str, sort_desc: bool, search_query: str):
        """Apply sorting to query."""
        if sort_by == "relevance" and search_query:
            # Sort by relevance (using ts_rank if available)
            try:
                ts_query = func.plainto_tsquery('english', search_query)
                ts_vector = func.to_tsvector('english',
                    func.concat(Product.name, ' ', Product.description)
                )
                relevance = func.ts_rank(ts_vector, ts_query)
                query = query.order_by(relevance.desc())
            except Exception:
                query = query.order_by(Product.sales_count.desc())
        elif sort_by == "price":
            order_col = Product.price
            query = query.order_by(order_col.desc() if sort_desc else order_col)
        elif sort_by == "rating":
            order_col = Product.rating
            query = query.order_by(order_col.desc() if sort_desc else order_col)
        elif sort_by == "sales":
            order_col = Product.sales_count
            query = query.order_by(order_col.desc() if sort_desc else order_col)
        elif sort_by == "newest":
            order_col = Product.created_at
            query = query.order_by(order_col.desc() if sort_desc else order_col)
        else:
            # Default: sort by relevance or sales
            query = query.order_by(Product.sales_count.desc())
        
        return query
    
    async def autocomplete(self, prefix: str, limit: int = 10) -> List[str]:
        """
        Get autocomplete suggestions for search query.
        
        Args:
            prefix: Search prefix
            limit: Maximum number of suggestions
            
        Returns:
            List of suggestion strings
        """
        search_pattern = f"{prefix}%"
        
        query = select(Product.name).where(
            and_(
                Product.status == ProductStatus.ACTIVE.value,
                Product.is_deleted == False,
                or_(
                    Product.name.ilike(search_pattern),
                    Product.name_am.ilike(search_pattern)
                )
            )
        ).distinct().limit(limit)
        
        result = await self.db.execute(query)
        suggestions = result.scalars().all()
        
        return suggestions
    
    async def get_facets(
        self,
        query: Optional[str] = None,
        category_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get search facets for filtering.
        
        Returns:
            Dictionary with facet counts
        """
        conditions = [
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False,
        ]
        
        if query:
            search_conditions = await self._build_search_conditions(query)
            conditions.append(search_conditions)
        
        if category_id:
            conditions.append(Product.category_id == category_id)
        
        # Category facets
        category_query = select(
            Product.category,
            func.count().label("count")
        ).where(and_(*conditions)).group_by(Product.category)
        
        category_result = await self.db.execute(category_query)
        categories = {row.category: row.count for row in category_result.all() if row.category}
        
        # Price range facets
        price_query = select(
            func.min(Product.price).label("min_price"),
            func.max(Product.price).label("max_price")
        ).where(and_(*conditions))
        
        price_result = await self.db.execute(price_query)
        price_row = price_result.one()
        
        # Rating facets
        rating_query = select(
            func.floor(Product.rating).label("rating_star"),
            func.count().label("count")
        ).where(and_(*conditions, Product.rating > 0)).group_by("rating_star")
        
        rating_result = await self.db.execute(rating_query)
        ratings = {int(row.rating_star): row.count for row in rating_result.all()}
        
        return {
            "categories": categories,
            "price_range": {
                "min": float(price_row.min_price) if price_row.min_price else 0,
                "max": float(price_row.max_price) if price_row.max_price else 0,
            },
            "ratings": ratings,
        }


async def search_products(
    db: AsyncSession,
    query: str,
    **kwargs,
) -> Tuple[List[Product], int]:
    """Convenience function for product search."""
    engine = ProductSearchEngine(db)
    return await engine.search(query, **kwargs)


async def index_product(db: AsyncSession, product_id: int) -> None:
    """Index a product for search (placeholder for Elasticsearch integration)."""
    logger.debug(f"Indexing product {product_id} for search")


async def delete_product_index(db: AsyncSession, product_id: int) -> None:
    """Delete product from search index."""
    logger.debug(f"Deleting product {product_id} from search index")


__all__ = [
    "ProductSearchEngine",
    "search_products",
    "index_product",
    "delete_product_index",
]