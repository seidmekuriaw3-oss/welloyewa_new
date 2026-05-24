# ============================
# WOLLOYEWA STORE BOT - ORDER MODELS
# ============================
"""Order, OrderItem, and related database models."""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, 
    BigInteger, Text, JSON, ForeignKey, Numeric, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from apps.common.models import BaseModel, TimestampMixin
from core.constants import OrderStatus, PaymentStatus, PaymentMethod, ShippingMethod

if TYPE_CHECKING:
    from apps.users.models import User, Vendor
    from apps.products.models import Product


class Order(BaseModel, TimestampMixin):
    """
    Order model for customer purchases.
    """
    
    __tablename__ = "orders"
    
    # Order identification
    order_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    
    # Relationships
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        SQLEnum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True
    )
    
    # Financials
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    tax: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    
    # Payment
    payment_method: Mapped[str] = mapped_column(SQLEnum(PaymentMethod, name="payment_method"), nullable=False)
    payment_status: Mapped[str] = mapped_column(
        SQLEnum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True
    )
    payment_transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payment_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Shipping
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    shipping_city: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    shipping_method: Mapped[str] = mapped_column(
        SQLEnum(ShippingMethod, name="shipping_method"),
        nullable=False,
        default=ShippingMethod.STANDARD
    )
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_carrier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estimated_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Notes
    customer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Cancellation
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancelled_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Refund
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    refund_transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="orders")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", foreign_keys=[vendor_id], back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    history: Mapped[List["OrderHistory"]] = relationship("OrderHistory", back_populates="order", cascade="all, delete-orphan")
    
    @hybrid_property
    def is_paid(self) -> bool:
        """Check if order is paid."""
        return self.payment_status == PaymentStatus.PAID.value
    
    @hybrid_property
    def is_delivered(self) -> bool:
        """Check if order is delivered."""
        return self.status == OrderStatus.DELIVERED.value
    
    @hybrid_property
    def is_cancelled(self) -> bool:
        """Check if order is cancelled."""
        return self.status == OrderStatus.CANCELLED.value
    
    def can_cancel(self) -> bool:
        """Check if order can be cancelled."""
        cancelable_statuses = [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]
        return self.status in cancelable_statuses and not self.is_paid
    
    def can_refund(self) -> bool:
        """Check if order can be refunded."""
        return self.is_paid and self.status != OrderStatus.REFUNDED.value
    
    def cancel(self, reason: Optional[str] = None, user_id: Optional[int] = None) -> None:
        """Cancel the order."""
        self.status = OrderStatus.CANCELLED.value
        self.cancelled_at = datetime.utcnow()
        self.cancelled_reason = reason
        self.cancelled_by = user_id
    
    def refund(self, amount: Decimal, transaction_id: Optional[str] = None) -> None:
        """Process refund for the order."""
        self.refunded_amount = amount
        self.refunded_at = datetime.utcnow()
        self.refund_transaction_id = transaction_id
        self.payment_status = PaymentStatus.REFUNDED.value
        self.status = OrderStatus.REFUNDED.value
    
    def __repr__(self) -> str:
        return f"<Order(id={self.id}, order_number={self.order_number}, status={self.status})>"


class OrderItem(BaseModel, TimestampMixin):
    """
    Individual item within an order.
    """
    
    __tablename__ = "order_items"
    
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Snapshot of product details at time of purchase
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_sku: Mapped[str] = mapped_column(String(100), nullable=False)
    product_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Quantity and pricing
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")
    
    def __repr__(self) -> str:
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id}, quantity={self.quantity})>"


class OrderHistory(BaseModel, TimestampMixin):
    """
    Order status change history.
    """
    
    __tablename__ = "order_history"
    
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # User ID who made the change
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="history")
    
    def __repr__(self) -> str:
        return f"<OrderHistory(order_id={self.order_id}, {self.previous_status} -> {self.new_status})>"


class Shipment(BaseModel, TimestampMixin):
    """
    Shipment tracking information.
    """
    
    __tablename__ = "shipments"
    
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    tracking_number: Mapped[str] = mapped_column(String(100), nullable=False)
    carrier: Mapped[str] = mapped_column(String(50), nullable=False)
    tracking_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Tracking updates
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")  # pending, picked_up, in_transit, out_for_delivery, delivered
    estimated_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Tracking history
    tracking_history: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    order: Mapped["Order"] = relationship("Order")
    
    def add_tracking_update(self, status: str, location: Optional[str] = None, note: Optional[str] = None) -> None:
        """Add a tracking update."""
        if not self.tracking_history:
            self.tracking_history = []
        
        self.tracking_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "location": location,
            "note": note,
        })
        
        self.status = status
    
    def mark_delivered(self) -> None:
        """Mark shipment as delivered."""
        self.status = "delivered"
        self.actual_delivery = datetime.utcnow()
        self.add_tracking_update("delivered", note="Package delivered")
    
    def __repr__(self) -> str:
        return f"<Shipment(order_id={self.order_id}, tracking_number={self.tracking_number}, status={self.status})>"