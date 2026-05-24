# ============================
# WOLLOYEWA STORE BOT - INVENTORY REPOSITORIES
# ============================
"""Database repositories for Inventory models."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.repository import BaseRepository
from apps.inventory.models import Inventory, InventoryMovement, StockReservation
from core.logger import logger


class InventoryRepository(BaseRepository[Inventory]):
    """Repository for Inventory model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Inventory, db)
    
    async def get_by_product(self, product_id: int) -> Optional[Inventory]:
        """Get inventory by product ID."""
        query = select(Inventory).where(Inventory.product_id == product_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_vendor(
        self,
        vendor_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Inventory]:
        """Get inventory records for a vendor."""
        query = select(Inventory).where(Inventory.vendor_id == vendor_id)
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_low_stock(
        self,
        vendor_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Inventory]:
        """Get products with low stock (quantity <= threshold)."""
        conditions = [
            Inventory.quantity <= Inventory.low_stock_threshold,
            Inventory.quantity > 0,
        ]
        if vendor_id:
            conditions.append(Inventory.vendor_id == vendor_id)
        
        query = select(Inventory).where(and_(*conditions))
        query = query.order_by(Inventory.quantity.asc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_out_of_stock(
        self,
        vendor_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Inventory]:
        """Get out of stock products."""
        conditions = [Inventory.quantity <= 0]
        if vendor_id:
            conditions.append(Inventory.vendor_id == vendor_id)
        
        query = select(Inventory).where(and_(*conditions))
        query = query.order_by(Inventory.last_restocked_at.asc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_in_stock(
        self,
        vendor_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Inventory]:
        """Get in-stock products."""
        conditions = [Inventory.quantity > 0]
        if vendor_id:
            conditions.append(Inventory.vendor_id == vendor_id)
        
        query = select(Inventory).where(and_(*conditions))
        query = query.order_by(Inventory.quantity.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_inventory_value(self, vendor_id: Optional[int] = None) -> float:
        """Calculate total inventory value (sum of quantity * product price)."""
        from apps.products.models import Product
        
        query = select(
            func.sum(Inventory.quantity * Product.price)
        ).join(Product, Inventory.product_id == Product.id)
        
        if vendor_id:
            query = query.where(Inventory.vendor_id == vendor_id)
        
        result = await self.db.execute(query)
        value = result.scalar() or 0
        return float(value)
    
    async def get_inventory_stats(self, vendor_id: Optional[int] = None) -> Dict[str, Any]:
        """Get inventory statistics."""
        conditions = []
        if vendor_id:
            conditions.append(Inventory.vendor_id == vendor_id)
        
        query = select(
            func.count().label("total_products"),
            func.sum(func.case((Inventory.quantity == 0, 1), else_=0)).label("out_of_stock"),
            func.sum(func.case((Inventory.quantity <= Inventory.low_stock_threshold, 1), else_=0)).label("low_stock"),
            func.sum(func.case((Inventory.quantity > 0, 1), else_=0)).label("in_stock"),
            func.sum(Inventory.quantity).label("total_units"),
        ).where(and_(*conditions) if conditions else True)
        
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "total_products": row.total_products or 0,
            "out_of_stock": row.out_of_stock or 0,
            "low_stock": row.low_stock or 0,
            "in_stock": row.in_stock or 0,
            "total_units": row.total_units or 0,
        }


class InventoryMovementRepository(BaseRepository[InventoryMovement]):
    """Repository for InventoryMovement model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(InventoryMovement, db)
    
    async def get_by_inventory(
        self,
        inventory_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[InventoryMovement], int]:
        """Get movements for a specific inventory record."""
        # Count
        count_query = select(func.count()).where(InventoryMovement.inventory_id == inventory_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Data
        query = select(InventoryMovement).where(InventoryMovement.inventory_id == inventory_id)
        query = query.order_by(InventoryMovement.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        
        return result.scalars().all(), total
    
    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        vendor_id: Optional[int] = None,
    ) -> List[InventoryMovement]:
        """Get movements within date range."""
        query = select(InventoryMovement).where(
            InventoryMovement.created_at >= start_date,
            InventoryMovement.created_at <= end_date,
        )
        
        if vendor_id:
            query = query.join(Inventory).where(Inventory.vendor_id == vendor_id)
        
        query = query.order_by(InventoryMovement.created_at)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_movements_by_type(
        self,
        movement_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[InventoryMovement]:
        """Get movements by type."""
        conditions = [InventoryMovement.movement_type == movement_type]
        
        if start_date:
            conditions.append(InventoryMovement.created_at >= start_date)
        if end_date:
            conditions.append(InventoryMovement.created_at <= end_date)
        
        query = select(InventoryMovement).where(and_(*conditions))
        query = query.order_by(InventoryMovement.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()


class StockReservationRepository(BaseRepository[StockReservation]):
    """Repository for StockReservation model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(StockReservation, db)
    
    async def get_active_reservations(
        self,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
    ) -> List[StockReservation]:
        """Get active reservations."""
        conditions = [StockReservation.status == "active"]
        
        if reference_id:
            conditions.append(StockReservation.reference_id == reference_id)
        if reference_type:
            conditions.append(StockReservation.reference_type == reference_type)
        
        query = select(StockReservation).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_reservations_by_inventory(
        self,
        inventory_id: int,
        status: Optional[str] = None,
    ) -> List[StockReservation]:
        """Get reservations for a specific inventory."""
        conditions = [StockReservation.inventory_id == inventory_id]
        
        if status:
            conditions.append(StockReservation.status == status)
        
        query = select(StockReservation).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_expired_reservations(self) -> List[StockReservation]:
        """Get expired but still active reservations."""
        now = datetime.utcnow()
        query = select(StockReservation).where(
            StockReservation.expires_at <= now,
            StockReservation.status == "active"
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_reservations_by_reference(
        self,
        reference_id: int,
        reference_type: str,
    ) -> List[StockReservation]:
        """Get reservations by reference ID and type."""
        query = select(StockReservation).where(
            StockReservation.reference_id == reference_id,
            StockReservation.reference_type == reference_type,
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def cancel_reservations_by_reference(
        self,
        reference_id: int,
        reference_type: str,
    ) -> int:
        """Cancel all reservations for a reference."""
        reservations = await self.get_reservations_by_reference(reference_id, reference_type)
        cancelled = 0
        
        for reservation in reservations:
            if reservation.status == "active":
                reservation.cancel()
                await self.update(reservation.id, {"status": "cancelled"})
                cancelled += 1
        
        return cancelled


__all__ = ["InventoryRepository", "InventoryMovementRepository", "StockReservationRepository"]