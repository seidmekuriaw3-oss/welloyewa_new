# ============================
# WOLLOYEWA STORE BOT - ORDER SCHEMAS
# ============================
"""Pydantic schemas for order request/response validation."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import Field, validator, root_validator

from apps.common.schemas import BaseSchema, IdSchema, TimestampSchema
from core.constants import OrderStatus, PaymentStatus, PaymentMethod, ShippingMethod


# ============================
# Order Item Schemas
# ============================

class OrderItemBase(BaseSchema):
    """Base order item schema."""
    
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., ge=1, description="Quantity")
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError('Quantity must be at least 1')
        if v > 999:
            raise ValueError('Quantity cannot exceed 999')
        return v


class OrderItemCreate(OrderItemBase):
    """Schema for creating an order item."""
    
    pass


class OrderItemResponse(OrderItemBase, IdSchema, TimestampSchema):
    """Schema for order item response."""
    
    order_id: int = Field(..., description="Order ID")
    product_name: str = Field(..., description="Product name at purchase time")
    product_sku: str = Field(..., description="Product SKU")
    product_image: Optional[str] = Field(None, description="Product image URL")
    unit_price: Decimal = Field(..., description="Unit price at purchase")
    total_price: Decimal = Field(..., description="Total price for quantity")
    discount: Decimal = Field(0, description="Discount applied")
    
    class Config:
        from_attributes = True


# ============================
# Order Schemas
# ============================

class OrderBase(BaseSchema):
    """Base order schema."""
    
    payment_method: PaymentMethod = Field(..., description="Payment method")
    shipping_address: str = Field(..., max_length=500, description="Shipping address")
    shipping_city: str = Field(..., max_length=100, description="Shipping city")
    shipping_phone: str = Field(..., max_length=20, description="Shipping phone number")
    shipping_method: ShippingMethod = Field(ShippingMethod.STANDARD, description="Shipping method")
    customer_notes: Optional[str] = Field(None, max_length=500, description="Customer notes")
    discount: Optional[Decimal] = Field(0, ge=0, description="Discount amount")
    shipping_fee: Optional[Decimal] = Field(0, ge=0, description="Shipping fee")


class OrderCreate(OrderBase):
    """Schema for creating an order."""
    
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Order items")


class OrderUpdate(BaseSchema):
    """Schema for updating an order."""
    
    shipping_address: Optional[str] = Field(None, max_length=500)
    shipping_city: Optional[str] = Field(None, max_length=100)
    shipping_phone: Optional[str] = Field(None, max_length=20)
    customer_notes: Optional[str] = Field(None, max_length=500)
    admin_notes: Optional[str] = Field(None, max_length=500)


class OrderStatusUpdate(BaseSchema):
    """Schema for updating order status."""
    
    status: OrderStatus = Field(..., description="New order status")
    reason: Optional[str] = Field(None, max_length=255, description="Reason for status change")


class OrderResponse(OrderBase, IdSchema, TimestampSchema):
    """Schema for order response."""
    
    order_number: str = Field(..., description="Unique order number")
    user_id: int = Field(..., description="User ID")
    vendor_id: Optional[int] = Field(None, description="Vendor ID")
    status: OrderStatus = Field(..., description="Order status")
    subtotal: Decimal = Field(..., description="Subtotal amount")
    tax: Decimal = Field(..., description="Tax amount")
    total: Decimal = Field(..., description="Total amount")
    payment_status: PaymentStatus = Field(..., description="Payment status")
    payment_transaction_id: Optional[str] = Field(None, description="Payment transaction ID")
    tracking_number: Optional[str] = Field(None, description="Tracking number")
    estimated_delivery_date: Optional[datetime] = Field(None, description="Estimated delivery date")
    delivered_at: Optional[datetime] = Field(None, description="Delivery timestamp")
    cancelled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    cancelled_reason: Optional[str] = Field(None, description="Cancellation reason")
    refunded_amount: Decimal = Field(0, description="Refunded amount")
    items: List[OrderItemResponse] = Field(default_factory=list, description="Order items")
    
    class Config:
        from_attributes = True


class OrderListResponse(BaseSchema):
    """Schema for order list response."""
    
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================
# Order Tracking Schemas
# ============================

class OrderTrackingResponse(BaseSchema):
    """Schema for order tracking response."""
    
    order_number: str = Field(..., description="Order number")
    status: OrderStatus = Field(..., description="Current order status")
    estimated_delivery: Optional[datetime] = Field(None, description="Estimated delivery date")
    tracking_number: Optional[str] = Field(None, description="Tracking number")
    tracking_url: Optional[str] = Field(None, description="Tracking URL")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Status history")


class OrderTrackRequest(BaseSchema):
    """Schema for order tracking request."""
    
    order_number: str = Field(..., description="Order number")
    email: Optional[str] = Field(None, description="Customer email")
    phone: Optional[str] = Field(None, description="Customer phone number")
    
    @root_validator
    def validate_contact(cls, values):
        if not values.get('email') and not values.get('phone'):
            raise ValueError('Either email or phone is required')
        return values


# ============================
# Order Statistics Schemas
# ============================

class OrderStatisticsResponse(BaseSchema):
    """Schema for order statistics response."""
    
    total_orders: int = Field(0, description="Total number of orders")
    total_revenue: Decimal = Field(0, description="Total revenue")
    average_order_value: Decimal = Field(0, description="Average order value")
    pending_orders: int = Field(0, description="Pending orders count")
    processing_orders: int = Field(0, description="Processing orders count")
    completed_orders: int = Field(0, description="Completed orders count")
    cancelled_orders: int = Field(0, description="Cancelled orders count")
    
    class Config:
        from_attributes = True


class DailySalesResponse(BaseSchema):
    """Schema for daily sales response."""
    
    date: str = Field(..., description="Date")
    order_count: int = Field(0, description="Number of orders")
    total_sales: Decimal = Field(0, description="Total sales amount")


# ============================
# Refund Schemas
# ============================

class RefundRequest(BaseSchema):
    """Schema for refund request."""
    
    order_id: int = Field(..., description="Order ID")
    amount: Optional[Decimal] = Field(None, ge=0, description="Refund amount (default: full amount)")
    reason: str = Field(..., max_length=255, description="Refund reason")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")


class RefundResponse(BaseSchema):
    """Schema for refund response."""
    
    refund_id: str = Field(..., description="Refund ID")
    order_id: int = Field(..., description="Order ID")
    amount: Decimal = Field(..., description="Refund amount")
    status: str = Field(..., description="Refund status")
    transaction_id: Optional[str] = Field(None, description="Refund transaction ID")
    created_at: datetime = Field(..., description="Refund creation time")
    
    class Config:
        from_attributes = True


__all__ = [
    "OrderItemBase", "OrderItemCreate", "OrderItemResponse",
    "OrderBase", "OrderCreate", "OrderUpdate", "OrderStatusUpdate",
    "OrderResponse", "OrderListResponse",
    "OrderTrackingResponse", "OrderTrackRequest",
    "OrderStatisticsResponse", "DailySalesResponse",
    "RefundRequest", "RefundResponse",
]