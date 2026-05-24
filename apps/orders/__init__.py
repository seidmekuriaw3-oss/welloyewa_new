# ============================
# WOLLOYEWA STORE BOT - ORDERS MODULE
# ============================
"""Order management module including orders, items, and tracking."""

from apps.orders.models import Order, OrderItem, OrderHistory, Shipment
from apps.orders.services import OrderService, OrderItemService, OrderTrackingService
from apps.orders.repository import OrderRepository, OrderItemRepository
from apps.orders.schemas import (
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderItemCreate,
    OrderItemResponse,
    OrderStatusUpdate,
    OrderTrackingResponse,
)
from apps.orders.events import (
    OrderEvent,
    emit_order_event,
    on_order_status_change,
)
from apps.orders.invoice_gen import (
    InvoiceGenerator,
    generate_order_invoice,
    generate_invoice_pdf,
)
from apps.orders.tracking import (
    OrderTracker,
    track_order,
    update_tracking_status,
    get_tracking_info,
)
from apps.orders.refunds import (
    RefundManager,
    process_refund,
    get_refund_status,
    RefundStatus,
)

__all__ = [
    # Models
    "Order",
    "OrderItem",
    "OrderHistory",
    "Shipment",
    # Services
    "OrderService",
    "OrderItemService",
    "OrderTrackingService",
    # Repositories
    "OrderRepository",
    "OrderItemRepository",
    # Schemas
    "OrderCreate",
    "OrderUpdate",
    "OrderResponse",
    "OrderItemCreate",
    "OrderItemResponse",
    "OrderStatusUpdate",
    "OrderTrackingResponse",
    # Events
    "OrderEvent",
    "emit_order_event",
    "on_order_status_change",
    # Invoice
    "InvoiceGenerator",
    "generate_order_invoice",
    "generate_invoice_pdf",
    # Tracking
    "OrderTracker",
    "track_order",
    "update_tracking_status",
    "get_tracking_info",
    # Refunds
    "RefundManager",
    "process_refund",
    "get_refund_status",
    "RefundStatus",
]