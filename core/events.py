# ============================
# WOLLOYEWA STORE BOT - EVENT SYSTEM
# ============================
"""Event-driven architecture for handling domain events and webhooks."""

import asyncio
from typing import Any, Callable, Dict, List, Optional, TypeVar, Awaitable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps

from core.logger import logger
from core.circuit_breaker import circuit_breaker_registry

T = TypeVar('T')


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """Base domain event."""
    
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    event_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate event ID if not provided."""
        if self.event_id is None:
            import uuid
            self.event_id = str(uuid.uuid4())


class EventHandler:
    """Wrapper for event handler functions."""
    
    def __init__(
        self,
        func: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        async_handler: bool = True,
    ):
        self.func = func
        self.priority = priority
        self.async_handler = async_handler
        self.name = func.__name__
    
    async def execute(self, event: Event) -> Any:
        """Execute the handler with the given event."""
        try:
            if self.async_handler:
                return await self.func(event)
            else:
                return self.func(event)
        except Exception as e:
            logger.error(f"Event handler '{self.name}' failed for event '{event.name}': {e}")
            raise


class EventBus:
    """
    Central event bus for publishing and subscribing to events.
    
    Implements observer pattern for loose coupling between components.
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._is_running = False
        self._worker_task: Optional[asyncio.Task] = None
    
    def subscribe(
        self,
        event_name: str,
        handler: Callable,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        """
        Subscribe a handler to an event.
        
        Args:
            event_name: Name of the event to subscribe to (use '*' for all events)
            handler: Handler function (async or sync)
            priority: Handler priority
        """
        handler_wrapper = EventHandler(handler, priority)
        
        if event_name == '*':
            self._wildcard_handlers.append(handler_wrapper)
            # Sort by priority (higher priority first)
            self._wildcard_handlers.sort(key=lambda h: h.priority.value, reverse=True)
        else:
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            self._handlers[event_name].append(handler_wrapper)
            # Sort by priority (higher priority first)
            self._handlers[event_name].sort(key=lambda h: h.priority.value, reverse=True)
        
        logger.debug(f"Handler '{handler.__name__}' subscribed to event '{event_name}'")
    
    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        """
        Unsubscribe a handler from an event.
        
        Args:
            event_name: Name of the event
            handler: Handler function to remove
        """
        if event_name == '*':
            self._wildcard_handlers = [
                h for h in self._wildcard_handlers if h.func != handler
            ]
        elif event_name in self._handlers:
            self._handlers[event_name] = [
                h for h in self._handlers[event_name] if h.func != handler
            ]
        
        logger.debug(f"Handler '{handler.__name__}' unsubscribed from event '{event_name}'")
    
    async def publish(self, event: Event) -> None:
        """
        Publish an event synchronously (handlers run immediately).
        
        Args:
            event: Event to publish
        """
        logger.debug(f"Publishing event: {event.name}")
        
        # Get handlers for this event
        handlers = self._handlers.get(event.name, [])
        
        # Add wildcard handlers
        handlers = self._wildcard_handlers + handlers
        
        # Execute handlers
        for handler in handlers:
            try:
                await handler.execute(event)
            except Exception as e:
                logger.error(f"Error in handler {handler.name} for event {event.name}: {e}")
    
    async def publish_async(self, event: Event) -> None:
        """
        Publish an event asynchronously (adds to queue).
        
        Args:
            event: Event to publish
        """
        await self._event_queue.put(event)
    
    async def _process_events(self) -> None:
        """Background worker to process queued events."""
        while self._is_running:
            try:
                event = await self._event_queue.get()
                await self.publish(event)
                self._event_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event from queue: {e}")
    
    async def start(self) -> None:
        """Start the event processing worker."""
        if self._is_running:
            return
        
        self._is_running = True
        self._worker_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")
    
    async def stop(self) -> None:
        """Stop the event processing worker."""
        self._is_running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event bus stopped")
    
    async def wait_for_empty(self, timeout: float = 30.0) -> None:
        """Wait for all queued events to be processed."""
        try:
            await asyncio.wait_for(self._event_queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for event queue to empty after {timeout}s")


# Global event bus instance
event_bus = EventBus()


# ============================
# Event Decorators
# ============================

def event_listener(event_name: str, priority: EventPriority = EventPriority.NORMAL):
    """
    Decorator to mark a function as an event listener.
    
    Args:
        event_name: Name of the event to listen for
        priority: Handler priority
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        event_bus.subscribe(event_name, func, priority)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================
# Built-in Domain Events
# ============================

# User Events
USER_REGISTERED = "user.registered"
USER_UPDATED = "user.updated"
USER_DELETED = "user.deleted"
USER_LOGIN = "user.login"
USER_LOGOUT = "user.logout"
USER_VERIFIED = "user.verified"

# Order Events
ORDER_CREATED = "order.created"
ORDER_CONFIRMED = "order.confirmed"
ORDER_PROCESSING = "order.processing"
ORDER_SHIPPED = "order.shipped"
ORDER_DELIVERED = "order.delivered"
ORDER_CANCELLED = "order.cancelled"
ORDER_REFUNDED = "order.refunded"

# Payment Events
PAYMENT_INITIATED = "payment.initiated"
PAYMENT_COMPLETED = "payment.completed"
PAYMENT_FAILED = "payment.failed"
PAYMENT_REFUNDED = "payment.refunded"

# Product Events
PRODUCT_CREATED = "product.created"
PRODUCT_UPDATED = "product.updated"
PRODUCT_DELETED = "product.deleted"
PRODUCT_STOCK_LOW = "product.stock_low"
PRODUCT_STOCK_OUT = "product.stock_out"
PRODUCT_RESTOCKED = "product.restocked"

# Vendor Events
VENDOR_REGISTERED = "vendor.registered"
VENDOR_APPROVED = "vendor.approved"
VENDOR_REJECTED = "vendor.rejected"
VENDOR_SUSPENDED = "vendor.suspended"

# Notification Events
NOTIFICATION_SENT = "notification.sent"
NOTIFICATION_FAILED = "notification.failed"


# ============================
# Example Event Handlers
# ============================

@event_listener(ORDER_CREATED, priority=EventPriority.HIGH)
async def on_order_created(event: Event) -> None:
    """Handle order created event."""
    order_id = event.data.get("order_id")
    user_id = event.data.get("user_id")
    
    logger.info(f"Order {order_id} created for user {user_id}")
    
    # Send confirmation notification
    from infrastructure.notifications.telegram_notifier import send_order_confirmation
    await send_order_confirmation(order_id, user_id)


@event_listener(PAYMENT_COMPLETED, priority=EventPriority.CRITICAL)
async def on_payment_completed(event: Event) -> None:
    """Handle payment completed event."""
    order_id = event.data.get("order_id")
    transaction_id = event.data.get("transaction_id")
    
    logger.info(f"Payment completed for order {order_id}, transaction: {transaction_id}")
    
    # Update order status
    from apps.orders.services import OrderService
    await OrderService.confirm_order(order_id)


@event_listener(PRODUCT_STOCK_LOW)
async def on_product_stock_low(event: Event) -> None:
    """Handle low stock event."""
    product_id = event.data.get("product_id")
    current_stock = event.data.get("current_stock")
    threshold = event.data.get("threshold")
    
    logger.warning(f"Product {product_id} has low stock: {current_stock} (threshold: {threshold})")
    
    # Notify vendor
    from infrastructure.notifications.email_service import send_low_stock_alert
    await send_low_stock_alert(product_id, current_stock)


# ============================
# Helper Functions
# ============================

async def emit_event(
    name: str,
    data: Dict[str, Any],
    sync: bool = False,
    **kwargs,
) -> None:
    """
    Emit an event to the event bus.
    
    Args:
        name: Event name
        data: Event data
        sync: Whether to publish synchronously
        **kwargs: Additional event parameters
    """
    event = Event(
        name=name,
        data=data,
        source=kwargs.get("source"),
        priority=kwargs.get("priority", EventPriority.NORMAL),
        correlation_id=kwargs.get("correlation_id"),
        causation_id=kwargs.get("causation_id"),
    )
    
    if sync:
        await event_bus.publish(event)
    else:
        await event_bus.publish_async(event)


__all__ = [
    "Event",
    "EventBus",
    "EventPriority",
    "event_bus",
    "event_listener",
    "emit_event",
    # Event names
    "USER_REGISTERED",
    "USER_UPDATED",
    "USER_DELETED",
    "USER_LOGIN",
    "USER_LOGOUT",
    "USER_VERIFIED",
    "ORDER_CREATED",
    "ORDER_CONFIRMED",
    "ORDER_PROCESSING",
    "ORDER_SHIPPED",
    "ORDER_DELIVERED",
    "ORDER_CANCELLED",
    "ORDER_REFUNDED",
    "PAYMENT_INITIATED",
    "PAYMENT_COMPLETED",
    "PAYMENT_FAILED",
    "PAYMENT_REFUNDED",
    "PRODUCT_CREATED",
    "PRODUCT_UPDATED",
    "PRODUCT_DELETED",
    "PRODUCT_STOCK_LOW",
    "PRODUCT_STOCK_OUT",
    "PRODUCT_RESTOCKED",
    "VENDOR_REGISTERED",
    "VENDOR_APPROVED",
    "VENDOR_REJECTED",
    "VENDOR_SUSPENDED",
    "NOTIFICATION_SENT",
    "NOTIFICATION_FAILED",
]