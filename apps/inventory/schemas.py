# ============================
# WOLLOYEWA STORE BOT - INVENTORY SCHEMAS
# ============================
"""Pydantic schemas for inventory request/response validation."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import Field, validator

from apps.common.schemas import BaseSchema, IdSchema, TimestampSchema


# ============================
# Inventory Schemas
# ============================

class InventoryBase(BaseSchema):
    """Base inventory schema."""
    
    product_id: int = Field(..., description="Product ID")
    vendor_id: int = Field(..., description="Vendor ID")
    quantity: int = Field(0, ge=0, description="Current stock quantity")
    reserved_quantity: int = Field(0, ge=0, description="Reserved stock quantity")
    low_stock_threshold: int = Field(5, ge=0, description="Low stock alert threshold")
    critical_stock_threshold: int = Field(2, ge=0, description="Critical stock alert threshold")
    sku: str = Field(..., max_length=100, description="Stock keeping unit")
    barcode: Optional[str] = Field(None, max_length=100, description="Product barcode")
    warehouse_location: Optional[str] = Field(None, max_length=100, description="Warehouse location")
    shelf_location: Optional[str] = Field(None, max_length=50, description="Shelf location")
    is_active: bool = Field(True, description="Whether inventory is active")
    is_tracking_enabled: bool = Field(True, description="Whether stock tracking is enabled")
    
    @validator('sku')
    def validate_sku(cls, v):
        if v:
            return v.upper().strip()
        return v


class InventoryCreate(InventoryBase):
    """Schema for creating inventory."""
    
    pass


class InventoryUpdate(BaseSchema):
    """Schema for updating inventory."""
    
    quantity: Optional[int] = Field(None, ge=0)
    reserved_quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    critical_stock_threshold: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    warehouse_location: Optional[str] = Field(None, max_length=100)
    shelf_location: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    is_tracking_enabled: Optional[bool] = None
    reason: Optional[str] = Field(None, description="Reason for update")


class InventoryResponse(InventoryBase, IdSchema, TimestampSchema):
    """Schema for inventory response."""
    
    available_quantity: int = Field(..., description="Available stock (quantity - reserved)")
    is_low_stock: bool = Field(False, description="Whether stock is low")
    is_critical_stock: bool = Field(False, description="Whether stock is critical")
    is_out_of_stock: bool = Field(False, description="Whether product is out of stock")
    last_counted_at: Optional[datetime] = None
    last_restocked_at: Optional[datetime] = None
    product_name: Optional[str] = Field(None, description="Product name")
    
    class Config:
        from_attributes = True


class LowStockAlert(BaseSchema):
    """Schema for low stock alert."""
    
    product_id: int
    product_name: str
    vendor_id: int
    vendor_name: Optional[str]
    current_stock: int
    threshold: int
    sku: str


# ============================
# Inventory Movement Schemas
# ============================

class InventoryMovementBase(BaseSchema):
    """Base inventory movement schema."""
    
    inventory_id: int = Field(..., description="Inventory ID")
    movement_type: str = Field(..., description="Movement type (purchase, sale, return, adjustment, restock)")
    quantity: int = Field(..., description="Quantity changed")
    previous_quantity: int = Field(..., description="Quantity before change")
    new_quantity: int = Field(..., description="Quantity after change")
    reason: Optional[str] = Field(None, description="Reason for movement")
    reference_id: Optional[int] = Field(None, description="Reference ID (order_id, etc.)")
    reference_type: Optional[str] = Field(None, description="Reference type (order, return, etc.)")
    performed_by: Optional[int] = Field(None, description="User ID who performed action")
    notes: Optional[str] = Field(None, description="Additional notes")


class InventoryMovementCreate(InventoryMovementBase):
    """Schema for creating inventory movement."""
    
    pass


class InventoryMovementResponse(InventoryMovementBase, IdSchema, TimestampSchema):
    """Schema for inventory movement response."""
    
    class Config:
        from_attributes = True


# ============================
# Stock Reservation Schemas
# ============================

class StockReservationBase(BaseSchema):
    """Base stock reservation schema."""
    
    inventory_id: int = Field(..., description="Inventory ID")
    quantity: int = Field(..., ge=1, description="Reserved quantity")
    reference_id: int = Field(..., description="Reference ID (order_id, cart_id)")
    reference_type: str = Field(..., description="Reference type (order, cart)")
    expires_in_minutes: int = Field(30, ge=1, le=1440, description="Expiration time in minutes")


class StockReservationCreate(StockReservationBase):
    """Schema for creating stock reservation."""
    
    pass


class StockReservationResponse(StockReservationBase, IdSchema, TimestampSchema):
    """Schema for stock reservation response."""
    
    status: str = Field(..., description="Reservation status (active, confirmed, expired, cancelled)")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    is_expired: bool = Field(False, description="Whether reservation has expired")
    
    class Config:
        from_attributes = True


# ============================
# Stock Adjustment Schemas
# ============================

class StockAdjustmentRequest(BaseSchema):
    """Schema for stock adjustment request."""
    
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity to add/remove")
    operation: str = Field(..., description="Operation (add, remove, set)")
    reason: str = Field(..., description="Reason for adjustment")
    notes: Optional[str] = Field(None, description="Additional notes")


class BulkStockUpdateRequest(BaseSchema):
    """Schema for bulk stock update."""
    
    updates: List[StockAdjustmentRequest] = Field(..., min_length=1, description="List of stock updates")


class StockCountRequest(BaseSchema):
    """Schema for stock count request."""
    
    product_id: int = Field(..., description="Product ID")
    counted_quantity: int = Field(..., ge=0, description="Physical count quantity")
    notes: Optional[str] = Field(None, description="Count notes")


# ============================
# Stock Report Schemas
# ============================

class InventoryReportResponse(BaseSchema):
    """Schema for inventory report response."""
    
    total_products: int = Field(0, description="Total products in inventory")
    total_units: int = Field(0, description="Total units in stock")
    total_value: Decimal = Field(0, description="Total inventory value")
    out_of_stock_count: int = Field(0, description="Out of stock products count")
    low_stock_count: int = Field(0, description="Low stock products count")
    in_stock_count: int = Field(0, description="In stock products count")
    by_vendor: Optional[Dict[str, Any]] = Field(None, description="Breakdown by vendor")


__all__ = [
    "InventoryBase", "InventoryCreate", "InventoryUpdate", "InventoryResponse",
    "InventoryMovementBase", "InventoryMovementCreate", "InventoryMovementResponse",
    "StockReservationBase", "StockReservationCreate", "StockReservationResponse",
    "StockAdjustmentRequest", "BulkStockUpdateRequest", "StockCountRequest",
    "InventoryReportResponse", "LowStockAlert",
]