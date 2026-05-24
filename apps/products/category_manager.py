# ============================
# WOLLOYEWA STORE BOT - CATEGORY MANAGER
# ============================
"""Category management with hierarchical structure and product associations."""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.logger import logger
from apps.products.models import Category, Product
from core.constants import ProductStatus


class CategoryManager:
    """
    Manager for product categories with hierarchical structure.
    
    Features:
    - Category tree management
    - Product count tracking
    - Path generation for breadcrumbs
    - Category merging and moving
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_category_tree(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get hierarchical category tree.
        
        Args:
            include_inactive: Whether to include inactive categories
            
        Returns:
            List of category nodes with children
        """
        # Get all categories
        query = select(Category)
        if not include_inactive:
            query = query.where(Category.is_active == True)
        query = query.order_by(Category.display_order)
        
        result = await self.db.execute(query)
        categories = result.scalars().all()
        
        # Build tree
        category_map = {cat.id: self._category_to_node(cat) for cat in categories}
        root_nodes = []
        
        for cat in categories:
            if cat.parent_id and cat.parent_id in category_map:
                category_map[cat.parent_id]["children"].append(category_map[cat.id])
            else:
                root_nodes.append(category_map[cat.id])
        
        return root_nodes
    
    def _category_to_node(self, category: Category) -> Dict[str, Any]:
        """Convert category to node dictionary."""
        return {
            "id": category.id,
            "name": category.name,
            "name_am": category.name_am,
            "slug": category.slug,
            "description": category.description,
            "image_url": category.image_url,
            "icon_url": category.icon_url,
            "product_count": category.product_count,
            "is_active": category.is_active,
            "is_featured": category.is_featured,
            "display_order": category.display_order,
            "children": [],
        }
    
    async def get_category_path(self, category_id: int) -> List[Category]:
        """
        Get breadcrumb path for a category.
        
        Args:
            category_id: Category ID
            
        Returns:
            List of categories from root to target
        """
        path = []
        current_id = category_id
        
        while current_id:
            category = await self.db.get(Category, current_id)
            if not category:
                break
            path.insert(0, category)
            current_id = category.parent_id
        
        return path
    
    async def get_category_products(
        self,
        category_id: int,
        include_subcategories: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """
        Get products in a category (optionally including subcategories).
        
        Args:
            category_id: Category ID
            include_subcategories: Whether to include products from subcategories
            limit: Maximum number of products
            offset: Number of products to skip
            
        Returns:
            List of products
        """
        if not include_subcategories:
            # Direct products only
            query = select(Product).where(
                Product.category_id == category_id,
                Product.status == ProductStatus.ACTIVE.value,
                Product.is_deleted == False
            )
            query = query.offset(offset).limit(limit)
            result = await self.db.execute(query)
            return result.scalars().all()
        
        # Get all subcategory IDs
        category_ids = await self._get_all_subcategory_ids(category_id)
        category_ids.append(category_id)
        
        query = select(Product).where(
            Product.category_id.in_(category_ids),
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False
        )
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _get_all_subcategory_ids(self, parent_id: int) -> List[int]:
        """Recursively get all subcategory IDs."""
        query = select(Category.id).where(Category.parent_id == parent_id)
        result = await self.db.execute(query)
        sub_ids = result.scalars().all()
        
        all_ids = []
        for sub_id in sub_ids:
            all_ids.append(sub_id)
            all_ids.extend(await self._get_all_subcategory_ids(sub_id))
        
        return all_ids
    
    async def get_category_product_count(self, category_id: int, include_subcategories: bool = True) -> int:
        """
        Get product count for a category.
        
        Args:
            category_id: Category ID
            include_subcategories: Whether to include subcategory products
            
        Returns:
            Number of products
        """
        if not include_subcategories:
            query = select(func.count()).select_from(Product).where(
                Product.category_id == category_id,
                Product.status == ProductStatus.ACTIVE.value,
                Product.is_deleted == False
            )
            result = await self.db.execute(query)
            return result.scalar() or 0
        
        category_ids = await self._get_all_subcategory_ids(category_id)
        category_ids.append(category_id)
        
        query = select(func.count()).select_from(Product).where(
            Product.category_id.in_(category_ids),
            Product.status == ProductStatus.ACTIVE.value,
            Product.is_deleted == False
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def update_category_product_counts(self, category_id: int) -> None:
        """
        Update product count for a category and all ancestors.
        
        Args:
            category_id: Category ID to update
        """
        # Update current category
        count = await self.get_category_product_count(category_id, include_subcategories=True)
        await self.db.execute(
            update(Category)
            .where(Category.id == category_id)
            .values(product_count=count)
        )
        
        # Update parent categories
        category = await self.db.get(Category, category_id)
        if category and category.parent_id:
            await self.update_category_product_counts(category.parent_id)
        
        await self.db.flush()
    
    async def move_category(self, category_id: int, new_parent_id: Optional[int]) -> bool:
        """
        Move a category to a different parent.
        
        Args:
            category_id: Category ID to move
            new_parent_id: New parent category ID (None for root)
            
        Returns:
            True if successful
        """
        # Check for circular reference
        if new_parent_id:
            ancestors = await self._get_ancestor_ids(new_parent_id)
            if category_id in ancestors:
                logger.warning(f"Cannot move category {category_id} to its own descendant")
                return False
        
        category = await self.db.get(Category, category_id)
        if not category:
            return False
        
        category.parent_id = new_parent_id
        await self.db.flush()
        
        # Update counts
        await self.update_category_product_counts(category_id)
        logger.info(f"Moved category {category_id} to parent {new_parent_id}")
        
        return True
    
    async def _get_ancestor_ids(self, category_id: int) -> List[int]:
        """Get all ancestor IDs for a category."""
        ancestors = []
        current_id = category_id
        
        while current_id:
            category = await self.db.get(Category, current_id)
            if not category:
                break
            ancestors.append(current_id)
            current_id = category.parent_id
        
        return ancestors
    
    async def merge_categories(self, source_id: int, target_id: int) -> bool:
        """
        Merge one category into another.
        
        Args:
            source_id: Category to merge from
            target_id: Category to merge into
            
        Returns:
            True if successful
        """
        # Move all products from source to target
        await self.db.execute(
            update(Product)
            .where(Product.category_id == source_id)
            .values(category_id=target_id)
        )
        
        # Move all subcategories to target
        await self.db.execute(
            update(Category)
            .where(Category.parent_id == source_id)
            .values(parent_id=target_id)
        )
        
        # Delete source category
        await self.db.delete(await self.db.get(Category, source_id))
        await self.db.flush()
        
        # Update counts
        await self.update_category_product_counts(target_id)
        
        logger.info(f"Merged category {source_id} into {target_id}")
        return True


async def get_category_tree(db: AsyncSession, include_inactive: bool = False) -> List[Dict[str, Any]]:
    """Convenience function to get category tree."""
    manager = CategoryManager(db)
    return await manager.get_category_tree(db, include_inactive)


async def get_category_products(
    db: AsyncSession,
    category_id: int,
    include_subcategories: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> List[Product]:
    """Convenience function to get category products."""
    manager = CategoryManager(db)
    return await manager.get_category_products(category_id, include_subcategories, limit, offset)


__all__ = [
    "CategoryManager",
    "get_category_tree",
    "get_category_products",
]