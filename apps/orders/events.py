# ============================
# WOLLOYEWA STORE BOT - ORDER EVENTS
# ============================
"""Event definitions and handlers for order-related events."""

from enum import Enum
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from core.logger import logger
from core.events import event_bus, Event, EventPriority, emit_event


class OrderEventType(str, Enum):
    """Order event types."""
    
    CREATED = "order.created"
    CONFIRMED = "order.confirmed"
    PROCESSING = "order.processing"
    SHIPPED = "order.shipped"
    DELIVERED = "order.delivered"
    CANCELLED = "order.cancelled"
    REFUNDED = "order.refunded"
    PAYMENT_RECEIVED = "order.payment_received"
    PAYMENT_FAILED = "order.payment_failed"


@dataclass
class OrderEvent:
    """Order event data."""
    
    event_type: OrderEventType
    order_id: int
    order_number: str
    user_id: int
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


async def emit_order_event(
    event_type: OrderEventType,
    order_id: int,
    order_number: str,
    user_id: int,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emit an order event to the event bus.
    
    Args:
        event_type: Type of order event
        order_id: Order ID
        order_number: Order number
        user_id: User ID
        data: Additional event data
    """
    event = OrderEvent(
        event_type=event_type,
        order_id=order_id,
        order_number=order_number,
        user_id=user_id,
        data=data or {},
    )
    
    await emit_event(
        event_type.value,
        {
            "order_id": order_id,
            "order_number": order_number,
            "user_id": user_id,
            "data": data or {},
            "timestamp": event.timestamp.isoformat(),
        },
        sync=False,
    )
    
    logger.debug(f"Emitted order event: {event_type.value} for order {order_number}")


# ============================
# Event Handlers
# ============================

async def on_order_created(event: Event) -> None:
    """Handle order created event."""
    order_id = event.data.get("order_id")
    user_id = event.data.get("user_id")
    total = event.data.get("total", 0)
    
    logger.info(f"Order {order_id} created for user {user_id}. Total: {total}")
    
    # Send confirmation notification
    from infrastructure.notifications.telegram_notifier import send_order_confirmation
    await send_order_confirmation(order_id, user_id)


async def on_order_confirmed(event: Event) -> None:
    """Handle order confirmed event."""
    order_id = event.data.get("order_id")
    
    logger.info(f"Order {order_id} confirmed")
    
    # Notify vendor
    from apps.orders.services import OrderService
    from infrastructure.database.session import get_db_session
    
    async for db in get_db_session():
        service = OrderService(db)
        order = await service.get_order(order_id)
        if order.vendor_id:
            from infrastructure.notifications.telegram_notifier import notify_vendor
            await notify_vendor(order.vendor_id, f"New order confirmed: {order.order_number}")
        break


async def on_order_shipped(event: Event) -> None:
    """Handle order shipped event."""
    order_id = event.data.get("order_id")
    tracking_number = event.data.get("tracking_number")
    
    logger.info(f"Order {order_id} shipped. Tracking: {tracking_number}")
    
    # Notify customer
    from infrastructure.notifications.telegram_notifier import send_shipping_notification
    await send_shipping_notification(order_id, tracking_number)


async def on_order_delivered(event: Event) -> None:
    """Handle order delivered event."""
    order_id = event.data.get("order_id")
    
    logger.info(f"Order {order_id} delivered")
    
    # Request review
    from apps.orders.services import OrderService
    from infrastructure.database.session import get_db_session
    
    async for db in get_db_session():
        service = OrderService(db)
        order = await service.get_order(order_id)
        
        from infrastructure.notifications.telegram_notifier import request_review
        await request_review(order.user_id, order_id, order.order_number)
        break


async def on_order_cancelled(event: Event) -> None:
    """Handle order cancelled event."""
    order_id = event.data.get("order_id")
    reason = event.data.get("reason")
    
    logger.info(f"Order {order_id} cancelled. Reason: {reason}")
    
    # Process refund if payment was made
    from apps.orders.refunds import process_refund
    await process_refund(order_id, reason="Order cancelled")


async def on_payment_received(event: Event) -> None:
    """Handle payment received event."""
    order_id = event.data.get("order_id")
    transaction_id = event.data.get("transaction_id")
    
    logger.info(f"Payment received for order {order_id}. Transaction: {transaction_id}")
    
    # Update order status to confirmed
    from apps.orders.services import OrderService
    from infrastructure.database.session import get_db_session
    
    async for db in get_db_session():
        service = OrderService(db)
        from apps.orders.schemas import OrderStatusUpdate
        from core.constants import OrderStatus
        
        await service.update_order_status(
            order_id,
            OrderStatusUpdate(status=OrderStatus.CONFIRMED.value),
            user_id=None,
        )
        break


# ============================
# Register Event Handlers
# ============================

def register_order_handlers() -> None:
    """Register all order event handlers with the event bus."""
    event_bus.subscribe(OrderEventType.CREATED.value, on_order_created, priority=EventPriority.HIGH)
    event_bus.subscribe(OrderEventType.CONFIRMED.value, on_order_confirmed, priority=EventPriority.HIGH)
    event_bus.subscribe(OrderEventType.SHIPPED.value, on_order_shipped)
    event_bus.subscribe(OrderEventType.DELIVERED.value, on_order_delivered)
    event_bus.subscribe(OrderEventType.CANCELLED.value, on_order_cancelled, priority=EventPriority.HIGH)
    event_bus.subscribe(OrderEventType.PAYMENT_RECEIVED.value, on_payment_received, priority=EventPriority.CRITICAL)
    
    logger.info("Registered order event handlers")


# Call this function when the application starts
def on_order_status_change(order_id: int, old_status: str, new_status: str) -> None:
    """Helper function to emit events on status change."""
    event_map = {
        "confirmed": OrderEventType.CONFIRMED,
        "processing": OrderEventType.PROCESSING,
        "shipped": OrderEventType.SHIPPED,
        "delivered": OrderEventType.DELIVERED,
        "cancelled": OrderEventType.CANCELLED,
        "refunded": OrderEventType.REFUNDED,
    }
    
    if new_status in event_map:
        import asyncio
        asyncio.create_task(
            emit_order_event(
                event_map[new_status],
                order_id,
                "",  # order_number would be fetched here
                0,   # user_id would be fetched here
            )
        )


__all__ = [
    "OrderEventType",
    "OrderEvent",
    "emit_order_event",
    "register_order_handlers",
    "on_order_status_change",
]