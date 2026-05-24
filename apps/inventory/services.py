# ============================
# WOLLOYEWA STORE BOT - INVENTORY SERVICES
# ============================
"""Business logic for inventory management."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from core.exceptions import NotFoundError, ValidationError, InsufficientStockError
from core.events import emit_event, PRODUCT_STOCK_LOW, PRODUCT_STOCK_OUT
from apps.inventory.repository import InventoryRepository, InventoryMovementRepository, StockReservationRepository
from apps.inventory.models import Inventory, InventoryMovement, StockReservation
from apps.inventory.schemas import InventoryCreate, InventoryUpdate, InventoryMovementCreate


class InventoryService:
    """Service for inventory management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory_repo = InventoryRepository(db)
        self.movement_repo = InventoryMovementRepository(db)
        self.reservation_repo = StockReservationRepository(db)
    
    async def create_inventory(self, data: InventoryCreate) -> Inventory:
        """Create new inventory record for a product."""
        # Check if inventory already exists
        existing = await self.inventory_repo.get_by_product(data.product_id)
        if existing:
            raise ValidationError(f"Inventory already exists for product {data.product_id}")
        
        inventory = await self.inventory_repo.create(data.dict())
        
        # Create initial movement log
        if inventory.quantity > 0:
            await self._record_movement(
                inventory_id=inventory.id,
                movement_type="initial",
                quantity=inventory.quantity,
                previous_quantity=0,
                new_quantity=inventory.quantity,
                reason="Initial inventory setup",
            )
        
        logger.info(f"Inventory created for product {data.product_id}")
        return inventory
    
    async def get_inventory(self, product_id: int) -> Optional[Inventory]:
        """Get inventory by product ID."""
        return await self.inventory_repo.get_by_product(product_id)
    
    async def update_inventory(self, product_id: int, data: InventoryUpdate) -> Inventory:
        """Update inventory record."""
        inventory = await self.inventory_repo.get_by_product(product_id)
        if not inventory:
            raise NotFoundError("Inventory", f"product_id={product_id}")
        
        old_quantity = inventory.quantity
        updated = await self.inventory_repo.update(inventory.id, data.dict(exclude_unset=True))
        
        # Log quantity change
        if data.quantity is not None and data.quantity != old_quantity:
            await self._record_movement(
                inventory_id=inventory.id,
                movement_type="adjustment",
                quantity=data.quantity - old_quantity,
                previous_quantity=old_quantity,
                new_quantity=data.quantity,
                reason=data.reason or "Manual adjustment",
            )
            
            # Check stock levels and emit events
            await self._check_stock_alerts(inventory)
        
        return updated
    
    async def add_stock(
        self,
        product_id: int,
        quantity: int,
        reason: str = "restock",
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
    ) -> Inventory:
        """Add stock to inventory."""
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        inventory = await self.inventory_repo.get_by_product(product_id)
        if not inventory:
            raise NotFoundError("Inventory", f"product_id={product_id}")
        
        old_quantity = inventory.quantity
        inventory.add_stock(quantity, reason)
        await self.inventory_repo.update(inventory.id, {"quantity": inventory.quantity})
        
        # Record movement
        await self._record_movement(
            inventory_id=inventory.id,
            movement_type="restock",
            quantity=quantity,
            previous_quantity=old_quantity,
            new_quantity=inventory.quantity,
            reason=reason,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        
        logger.info(f"Added {quantity} units to product {product_id}. New stock: {inventory.quantity}")
        return inventory
    
    async def remove_stock(
        self,
        product_id: int,
        quantity: int,
        reason: str = "sale",
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
    ) -> Inventory:
        """Remove stock from inventory."""
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        inventory = await self.inventory_repo.get_by_product(product_id)
        if not inventory:
            raise NotFoundError("Inventory", f"product_id={product_id}")
        
        if inventory.available_quantity < quantity:
            raise InsufficientStockError(
                f"Product {product_id}",
                quantity,
                inventory.available_quantity
            )
        
        old_quantity = inventory.quantity
        success = inventory.remove_stock(quantity, reason)
        if not success:
            raise InsufficientStockError(f"Product {product_id}", quantity, inventory.quantity)
        
        await self.inventory_repo.update(inventory.id, {"quantity": inventory.quantity})
        
        # Record movement
        await self._record_movement(
            inventory_id=inventory.id,
            movement_type="sale",
            quantity=-quantity,
            previous_quantity=old_quantity,
            new_quantity=inventory.quantity,
            reason=reason,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        
        # Check stock alerts
        await self._check_stock_alerts(inventory)
        
        logger.info(f"Removed {quantity} units from product {product_id}. New stock: {inventory.quantity}")
        return inventory
    
    async def reserve_stock(
        self,
        product_id: int,
        quantity: int,
        reference_id: int,
        reference_type: str = "order",
        expires_minutes: int = 30,
    ) -> StockReservation:
        """Reserve stock for an order or cart."""
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        inventory = await self.inventory_repo.get_by_product(product_id)
        if not inventory:
            raise NotFoundError("Inventory", f"product_id={product_id}")
        
        if inventory.available_quantity < quantity:
            raise InsufficientStockError(
                f"Product {product_id}",
                quantity,
                inventory.available_quantity
            )
        
        # Create reservation
        reservation = await self.reservation_repo.create({
            "inventory_id": inventory.id,
            "quantity": quantity,
            "reference_id": reference_id,
            "reference_type": reference_type,
            "expires_in_minutes": expires_minutes,
            "expires_at": datetime.utcnow() + timedelta(minutes=expires_minutes),
        })
        
        # Update inventory reserved quantity
        inventory.reserve(quantity)
        await self.inventory_repo.update(inventory.id, {"reserved_quantity": inventory.reserved_quantity})
        
        logger.info(f"Reserved {quantity} units of product {product_id} for {reference_type} {reference_id}")
        return reservation
    
    async def confirm_reservation(self, reservation_id: int) -> None:
        """Confirm a reservation (convert to actual stock deduction)."""
        reservation = await self.reservation_repo.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundError("Reservation", reservation_id)
        
        if reservation.status != "active":
            raise ValidationError(f"Reservation is already {reservation.status}")
        
        reservation.confirm()
        await self.reservation_repo.update(reservation_id, {"status": "confirmed"})
        
        logger.info(f"Reservation {reservation_id} confirmed")
    
    async def release_reservation(self, reservation_id: int) -> None:
        """Release a reservation (cancel and free stock)."""
        reservation = await self.reservation_repo.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundError("Reservation", reservation_id)
        
        if reservation.status not in ["active", "expired"]:
            return
        
        reservation.cancel()
        await self.reservation_repo.update(reservation_id, {"status": "cancelled"})
        
        # Update inventory
        inventory = await self.inventory_repo.get_by_id(reservation.inventory_id)
        if inventory:
            inventory.release_reservation(reservation.quantity)
            await self.inventory_repo.update(inventory.id, {"reserved_quantity": inventory.reserved_quantity})
        
        logger.info(f"Reservation {reservation_id} released")
    
    async def expire_old_reservations(self) -> int:
        """Expire all reservations that have passed their expiry time."""
        expired = await self.reservation_repo.get_expired_reservations()
        expired_count = 0
        
        for reservation in expired:
            await self.release_reservation(reservation.id)
            expired_count += 1
        
        if expired_count > 0:
            logger.info(f"Expired {expired_count} stale reservations")
        
        return expired_count
    
    async def get_low_stock_products(
        self,
        vendor_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Inventory]:
        """Get products with low stock."""
        return await self.inventory_repo.get_low_stock(vendor_id, limit)
    
    async def get_out_of_stock_products(
        self,
        vendor_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Inventory]:
        """Get out of stock products."""
        return await self.inventory_repo.get_out_of_stock(vendor_id, limit)
    
    async def get_inventory_movements(
        self,
        product_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[InventoryMovement], int]:
        """Get inventory movement history for a product."""
        inventory = await self.inventory_repo.get_by_product(product_id)
        if not inventory:
            return [], 0
        
        return await self.movement_repo.get_by_inventory(inventory.id, limit, offset)
    
    async def _record_movement(
        self,
        inventory_id: int,
        movement_type: str,
        quantity: int,
        previous_quantity: int,
        new_quantity: int,
        reason: Optional[str] = None,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
        performed_by: Optional[int] = None,
    ) -> None:
        """Record inventory movement."""
        movement = InventoryMovementCreate(
            inventory_id=inventory_id,
            movement_type=movement_type,
            quantity=quantity,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            reason=reason,
            reference_id=reference_id,
            reference_type=reference_type,
            performed_by=performed_by,
        )
        await self.movement_repo.create(movement.dict())
    
    async def _check_stock_alerts(self, inventory: Inventory) -> None:
        """Check stock levels and emit alert events."""
        if inventory.is_critical_stock:
            await emit_event(
                PRODUCT_STOCK_OUT,
                {
                    "product_id": inventory.product_id,
                    "vendor_id": inventory.vendor_id,
                    "current_stock": inventory.available_quantity,
                },
                sync=False,
            )
            logger.warning(f"Product {inventory.product_id} is out of stock!")
        elif inventory.is_low_stock:
            await emit_event(
                PRODUCT_STOCK_LOW,
                {
                    "product_id": inventory.product_id,
                    "vendor_id": inventory.vendor_id,
                    "current_stock": inventory.available_quantity,
                    "threshold": inventory.low_stock_threshold,
                },
                sync=False,
            )
            logger.info(f"Product {inventory.product_id} has low stock: {inventory.available_quantity}")


class StockMovementService:
    """Service for stock movement reporting."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.movement_repo = InventoryMovementRepository(db)
    
    async def get_movements_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        vendor_id: Optional[int] = None,
    ) -> List[InventoryMovement]:
        """Get stock movements within date range."""
        return await self.movement_repo.get_by_date_range(start_date, end_date, vendor_id)
    
    async def get_movement_summary(
        self,
        vendor_id: Optional[int] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get stock movement summary."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        movements = await self.movement_repo.get_by_date_range(cutoff, datetime.utcnow(), vendor_id)
        
        summary = {
            "total_in": 0,
            "total_out": 0,
            "net_change": 0,
            "by_type": {},
        }
        
        for movement in movements:
            if movement.quantity > 0:
                summary["total_in"] += movement.quantity
            else:
                summary["total_out"] += abs(movement.quantity)
            
            if movement.movement_type not in summary["by_type"]:
                summary["by_type"][movement.movement_type] = 0
            summary["by_type"][movement.movement_type] += movement.quantity
        
        summary["net_change"] = summary["total_in"] - summary["total_out"]
        return summary


class ReservationService:
    """Service for stock reservation management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.reservation_repo = StockReservationRepository(db)
    
    async def get_active_reservations(
        self,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
    ) -> List[StockReservation]:
        """Get active reservations."""
        return await self.reservation_repo.get_active_reservations(reference_id, reference_type)
    
    async def cleanup_expired_reservations(self) -> int:
        """Clean up expired reservations."""
        expired = await self.reservation_repo.get_expired_reservations()
        for reservation in expired:
            await self._expire_reservation(reservation)
        return len(expired)
    
    async def _expire_reservation(self, reservation: StockReservation) -> None:
        """Expire a single reservation."""
        reservation.expire()
        await self.reservation_repo.update(reservation.id, {"status": "expired"})


__all__ = ["InventoryService", "StockMovementService", "ReservationService"]