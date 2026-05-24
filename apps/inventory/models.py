# ============================
# WOLLOYEWA STORE BOT - INVENTORY MODELS
# ============================
"""Inventory management database models."""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float,
    BigInteger, Text, JSON, ForeignKey, Numeric, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from apps.common.models import BaseModel, TimestampMixin

if TYPE_CHECKING:
    from apps.products.models import Product
    from apps.users.models import Vendor


class Inventory(BaseModel, TimestampMixin):
    """
    Inventory model for tracking product stock levels.
    
    Each product has one inventory record.
    """
    
    __tablename__ = "inventories"
    
    # Relationships
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    vendor_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    # Stock levels
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    @hybrid_property
    def available_quantity(self) -> int:
        """Calculate available stock (quantity - reserved)."""
        return self.quantity - self.reserved_quantity
    
    # Thresholds
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    critical_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    
    # Stock keeping
    sku: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Locations
    warehouse_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shelf_location: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_tracking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Last counts
    last_counted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_restocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product")
    vendor: Mapped["Vendor"] = relationship("Vendor")
    movements: Mapped[List["InventoryMovement"]] = relationship(
        "InventoryMovement", back_populates="inventory", cascade="all, delete-orphan"
    )
    reservations: Mapped[List["StockReservation"]] = relationship(
        "StockReservation", back_populates="inventory", cascade="all, delete-orphan"
    )
    
    @hybrid_property
    def is_low_stock(self) -> bool:
        """Check if stock is low."""
        return self.available_quantity <= self.low_stock_threshold
    
    @hybrid_property
    def is_critical_stock(self) -> bool:
        """Check if stock is critical."""
        return self.available_quantity <= self.critical_stock_threshold
    
    @hybrid_property
    def is_out_of_stock(self) -> bool:
        """Check if product is out of stock."""
        return self.available_quantity <= 0
    
    def add_stock(self, quantity: int, reason: str = "restock") -> None:
        """Add stock to inventory."""
        self.quantity += quantity
        self.last_restocked_at = datetime.utcnow()
    
    def remove_stock(self, quantity: int, reason: str = "sale") -> bool:
        """Remove stock from inventory."""
        if self.available_quantity < quantity:
            return False
        self.quantity -= quantity
        return True
    
    def reserve(self, quantity: int) -> bool:
        """Reserve stock for an order."""
        if self.available_quantity < quantity:
            return False
        self.reserved_quantity += quantity
        return True
    
    def release_reservation(self, quantity: int) -> None:
        """Release reserved stock."""
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)
    
    def __repr__(self) -> str:
        return f"<Inventory(product_id={self.product_id}, quantity={self.quantity}, reserved={self.reserved_quantity})>"


class InventoryMovement(BaseModel, TimestampMixin):
    """
    Inventory movement log.
    
    Tracks all changes to inventory levels for audit and reporting.
    """
    
    __tablename__ = "inventory_movements"
    
    inventory_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventories.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    # Movement details
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False)  # purchase, sale, return, adjustment, restock
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    new_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Reference
    reference_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # order_id, purchase_order_id, etc.
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # order, return, adjustment
    
    # Metadata
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    performed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # user_id
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    inventory: Mapped["Inventory"] = relationship("Inventory", back_populates="movements")
    
    __table_args__ = (
        Index('idx_movements_inventory', 'inventory_id', 'created_at'),
        Index('idx_movements_type', 'movement_type', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<InventoryMovement(inventory_id={self.inventory_id}, type={self.movement_type}, quantity={self.quantity})>"


class StockReservation(BaseModel, TimestampMixin):
    """
    Stock reservation for pending orders.
    
    Temporarily reserves stock for orders that are not yet confirmed.
    """
    
    __tablename__ = "stock_reservations"
    
    inventory_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventories.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    # Reservation details
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # order_id, cart_id
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)  # order, cart
    
    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")  # active, confirmed, expired, cancelled
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Metadata
    expires_in_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    
    # Relationships
    inventory: Mapped["Inventory"] = relationship("Inventory", back_populates="reservations")
    
    def is_expired(self) -> bool:
        """Check if reservation has expired."""
        return datetime.utcnow() > self.expires_at
    
    def confirm(self) -> None:
        """Confirm and convert reservation to actual stock deduction."""
        self.status = "confirmed"
    
    def cancel(self) -> None:
        """Cancel reservation and release stock."""
        self.status = "cancelled"
        self.inventory.release_reservation(self.quantity)
    
    def expire(self) -> None:
        """Expire reservation."""
        self.status = "expired"
        self.inventory.release_reservation(self.quantity)
    
    def __repr__(self) -> str:
        return f"<StockReservation(inventory_id={self.inventory_id}, quantity={self.quantity}, status={self.status})>"