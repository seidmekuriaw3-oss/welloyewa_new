# ============================
# WOLLOYEWA STORE BOT - BASE REPOSITORY
# ============================
"""Base repository class with common CRUD operations."""

from typing import Dict, Any, List, Optional, Type, TypeVar, Generic, Union
from datetime import datetime

from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from core.logger import logger
from apps.common.models import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common database operations.
    
    Provides CRUD operations and common query patterns.
    
    Usage:
        class UserRepository(BaseRepository[User]):
            pass
    """
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def create(self, data: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            data: Dictionary of field values
            
        Returns:
            Created model instance
        """
        try:
            instance = self.model(**data)
            self.db.add(instance)
            await self.db.flush()
            await self.db.refresh(instance)
            logger.debug(f"Created {self.model.__name__}: {instance.id}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create {self.model.__name__}: {e}")
            raise
    
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get record by ID.
        
        Args:
            id: Record ID
            
        Returns:
            Model instance or None
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_one(self, filters: Dict[str, Any]) -> Optional[ModelType]:
        """
        Get single record matching filters.
        
        Args:
            filters: Dictionary of field-value pairs
            
        Returns:
            Model instance or None
        """
        query = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    def _build_filter_clause(self, key: str, value: Any):
        """
        Build a SQLAlchemy filter clause from a key that may carry an operator suffix.

        Supported suffixes:
          __gte  → >=
          __lte  → <=
          __gt   → >
          __lt   → <
          __in   → IN (value must be a list/tuple)
          __ne   → !=
          __like → LIKE
          (no suffix) → ==
        
        Keys that reference non-existent model columns are silently ignored
        (returns None).
        """
        operators = ("__gte", "__lte", "__gt", "__lt", "__in", "__ne", "__like")
        field_name = key
        operator = None
        for op in operators:
            if key.endswith(op):
                field_name = key[: -len(op)]
                operator = op
                break

        if not hasattr(self.model, field_name):
            return None

        column = getattr(self.model, field_name)
        if operator == "__gte":
            return column >= value
        elif operator == "__lte":
            return column <= value
        elif operator == "__gt":
            return column > value
        elif operator == "__lt":
            return column < value
        elif operator == "__in":
            return column.in_(value)
        elif operator == "__ne":
            return column != value
        elif operator == "__like":
            return column.like(value)
        else:
            return column == value

    async def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ModelType]:
        """
        Get all records with optional filters.
        
        Args:
            filters: Dictionary of field-value pairs (supports __gte/__lte/__gt/__lt/__in/__ne/__like suffixes)
            order_by: Field name to order by
            order_desc: Whether to order descending
            limit: Maximum number of records
            offset: Number of records to skip
            
        Returns:
            List of model instances
        """
        query = select(self.model)
        
        # Apply filters
        if filters:
            clauses = [self._build_filter_clause(k, v) for k, v in filters.items()]
            clauses = [c for c in clauses if c is not None]
            if clauses:
                query = query.where(and_(*clauses))
        
        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            if order_desc:
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column)
        
        # Apply pagination
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update(
        self,
        id: int,
        data: Dict[str, Any],
        partial: bool = True,
    ) -> Optional[ModelType]:
        """
        Update a record.
        
        Args:
            id: Record ID
            data: Dictionary of fields to update
            partial: Whether to update only provided fields
            
        Returns:
            Updated model instance or None
        """
        try:
            # Remove None values if partial update
            if partial:
                data = {k: v for k, v in data.items() if v is not None}
            
            if not data:
                return await self.get_by_id(id)
            
            # Add updated_at timestamp
            data['updated_at'] = datetime.utcnow()
            
            # Execute update
            stmt = (
                update(self.model)
                .where(self.model.id == id)
                .values(**data)
                .returning(self.model)
            )
            result = await self.db.execute(stmt)
            await self.db.flush()
            
            updated = result.scalar_one_or_none()
            if updated:
                await self.db.refresh(updated)
                logger.debug(f"Updated {self.model.__name__}: {id}")
            
            return updated
            
        except Exception as e:
            logger.error(f"Failed to update {self.model.__name__} {id}: {e}")
            raise
    
    async def delete(self, id: int, soft: bool = True) -> bool:
        """
        Delete a record.
        
        Args:
            id: Record ID
            soft: Whether to perform soft delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            if soft and hasattr(self.model, 'soft_delete'):
                # Soft delete
                instance = await self.get_by_id(id)
                if instance:
                    instance.soft_delete()
                    await self.db.flush()
                    logger.debug(f"Soft deleted {self.model.__name__}: {id}")
                    return True
                return False
            else:
                # Hard delete
                stmt = delete(self.model).where(self.model.id == id)
                result = await self.db.execute(stmt)
                await self.db.flush()
                deleted = result.rowcount > 0
                if deleted:
                    logger.debug(f"Hard deleted {self.model.__name__}: {id}")
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to delete {self.model.__name__} {id}: {e}")
            raise
    
    async def exists(self, filters: Dict[str, Any]) -> bool:
        """
        Check if a record exists matching filters.
        
        Args:
            filters: Dictionary of field-value pairs (supports __gte/__lte etc. suffixes)
            
        Returns:
            True if exists, False otherwise
        """
        query = select(func.count()).select_from(self.model)
        clauses = [self._build_filter_clause(k, v) for k, v in filters.items()]
        clauses = [c for c in clauses if c is not None]
        if clauses:
            query = query.where(and_(*clauses))
        
        result = await self.db.execute(query)
        count = result.scalar()
        return count > 0
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records matching filters.
        
        Args:
            filters: Dictionary of field-value pairs (supports __gte/__lte etc. suffixes)
            
        Returns:
            Number of records
        """
        query = select(func.count()).select_from(self.model)
        
        if filters:
            clauses = [self._build_filter_clause(k, v) for k, v in filters.items()]
            clauses = [c for c in clauses if c is not None]
            if clauses:
                query = query.where(and_(*clauses))
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in bulk.
        
        Args:
            data_list: List of data dictionaries
            
        Returns:
            List of created model instances
        """
        instances = []
        for data in data_list:
            instance = self.model(**data)
            self.db.add(instance)
            instances.append(instance)
        
        await self.db.flush()
        
        for instance in instances:
            await self.db.refresh(instance)
        
        logger.debug(f"Bulk created {len(instances)} {self.model.__name__}")
        return instances
    
    async def bulk_update(self, updates: Dict[int, Dict[str, Any]]) -> int:
        """
        Update multiple records.
        
        Args:
            updates: Dictionary mapping ID to update data
            
        Returns:
            Number of updated records
        """
        updated_count = 0
        for id, data in updates.items():
            result = await self.update(id, data)
            if result:
                updated_count += 1
        
        logger.debug(f"Bulk updated {updated_count} {self.model.__name__}")
        return updated_count


__all__ = ["BaseRepository"]