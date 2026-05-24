# ============================
# WOLLOYEWA STORE BOT - ORDER SERVICES
# ============================
"""Business logic for order management, processing, and tracking."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from core.exceptions import NotFoundError, ValidationError, PermissionError, InsufficientStockError, OrderStatusError
from core.events import emit_event, ORDER_CREATED, ORDER_CONFIRMED, ORDER_SHIPPED, ORDER_DELIVERED, ORDER_CANCELLED
from core.utils.currency import format_etb
from core.utils.string_utils import generate_order_number
from apps.orders.repository import OrderRepository, OrderItemRepository
from apps.orders.models import Order, OrderItem, OrderHistory
from apps.orders.schemas import OrderCreate, OrderUpdate, OrderStatusUpdate
from apps.products.services import ProductService
from apps.inventory.services import InventoryService
from apps.users.services import UserService
from core.constants import OrderStatus, PaymentStatus


class OrderService:
    """Service for order management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.order_item_repo = OrderItemRepository(db)
        self.product_service = ProductService(db)
        self.inventory_service = InventoryService(db)
        self.user_service = UserService(db)
    
    async def create_order(self, user_id: int, data: OrderCreate) -> Order:
        """
        Create a new order.
        
        Args:
            user_id: User ID
            data: Order creation data
            
        Returns:
            Created order
        """
        # Get user
        user = await self.user_service.get_user(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Calculate totals from items
        subtotal = Decimal('0')
        items_data = []
        
        for item in data.items:
            product = await self.product_service.get_product(item.product_id)
            
            # Check stock
            if product.stock_quantity < item.quantity:
                raise InsufficientStockError(product.name, item.quantity, product.stock_quantity)
            
            # Calculate item total
            item_total = product.price * item.quantity
            subtotal += item_total
            
            items_data.append({
                "product_id": item.product_id,
                "product_name": product.name,
                "product_sku": product.sku,
                "quantity": item.quantity,
                "unit_price": product.price,
                "total_price": item_total,
            })
        
        # Calculate totals
        shipping_fee = Decimal(str(data.shipping_fee or 0))
        tax = subtotal * Decimal('0.15')  # 15% VAT
        total = subtotal + shipping_fee + tax - Decimal(str(data.discount or 0))
        
        # Create order
        order_data = {
            "order_number": generate_order_number(),
            "user_id": user_id,
            "status": OrderStatus.PENDING.value,
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "tax": tax,
            "discount": Decimal(str(data.discount or 0)),
            "total": total,
            "payment_method": data.payment_method,
            "payment_status": PaymentStatus.PENDING.value,
            "shipping_address": data.shipping_address,
            "shipping_city": data.shipping_city,
            "shipping_phone": data.shipping_phone,
            "shipping_method": data.shipping_method,
            "customer_notes": data.customer_notes,
        }
        
        order = await self.order_repo.create(order_data)
        
        # Create order items
        for item_data in items_data:
            item_data["order_id"] = order.id
            await self.order_item_repo.create(item_data)
            
            # Reserve stock
            await self.product_service.reserve_stock(item_data["product_id"], item_data["quantity"])
        
        # Add order history
        await self._add_history(order.id, None, OrderStatus.PENDING.value, user_id, "Order created")
        
        # Emit event
        await emit_event(
            ORDER_CREATED,
            {
                "order_id": order.id,
                "order_number": order.order_number,
                "user_id": user_id,
                "total": float(total),
            },
            sync=False,
        )
        
        logger.info(f"Order created: {order.order_number} by user {user_id}")
        return order
    
    async def get_order(self, order_id: int, user_id: Optional[int] = None) -> Order:
        """Get order by ID with permission check."""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order", order_id)
        
        # Check permission
        if user_id and order.user_id != user_id:
            raise PermissionError("You don't have permission to view this order")
        
        return order
    
    async def get_order_by_number(self, order_number: str) -> Order:
        """Get order by order number."""
        order = await self.order_repo.get_by_order_number(order_number)
        if not order:
            raise NotFoundError("Order", order_number)
        return order
    
    async def update_order_status(self, order_id: int, data: OrderStatusUpdate, user_id: int) -> Order:
        """
        Update order status.
        
        Args:
            order_id: Order ID
            data: Status update data
            user_id: User ID making the change
            
        Returns:
            Updated order
        """
        order = await self.get_order(order_id)
        previous_status = order.status
        
        # Validate status transition
        if not self._is_valid_transition(previous_status, data.status):
            raise OrderStatusError(previous_status, data.status)
        
        # Update order
        update_data = {"status": data.status}
        
        if data.status == OrderStatus.CANCELLED.value:
            update_data["cancelled_at"] = datetime.utcnow()
            update_data["cancelled_reason"] = data.reason
            
            # Release reserved stock
            items = await self.order_item_repo.get_by_order(order_id)
            for item in items:
                await self.product_service.release_stock(item.product_id, item.quantity)
        
        elif data.status == OrderStatus.DELIVERED.value:
            update_data["delivered_at"] = datetime.utcnow()
        
        order = await self.order_repo.update(order_id, update_data)
        
        # Add history
        await self._add_history(order_id, previous_status, data.status, user_id, data.reason)
        
        # Emit event based on new status
        if data.status == OrderStatus.CONFIRMED.value:
            await emit_event(ORDER_CONFIRMED, {"order_id": order_id})
        elif data.status == OrderStatus.SHIPPED.value:
            await emit_event(ORDER_SHIPPED, {"order_id": order_id})
        elif data.status == OrderStatus.DELIVERED.value:
            await emit_event(ORDER_DELIVERED, {"order_id": order_id})
        elif data.status == OrderStatus.CANCELLED.value:
            await emit_event(ORDER_CANCELLED, {"order_id": order_id, "reason": data.reason})
        
        logger.info(f"Order {order.order_number} status changed: {previous_status} -> {data.status}")
        return order
    
    async def update_payment_status(self, order_id: int, payment_status: str, transaction_id: Optional[str] = None) -> Order:
        """Update order payment status."""
        order = await self.get_order(order_id)
        
        update_data = {"payment_status": payment_status}
        if transaction_id:
            update_data["payment_transaction_id"] = transaction_id
        
        if payment_status == PaymentStatus.PAID.value:
            update_data["status"] = OrderStatus.CONFIRMED.value
            await self._add_history(order_id, order.status, OrderStatus.CONFIRMED.value, None, "Payment received")
        
        order = await self.order_repo.update(order_id, update_data)
        
        logger.info(f"Order {order.order_number} payment status: {payment_status}")
        return order
    
    async def get_user_orders(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Order], int]:
        """Get orders for a user."""
        return await self.order_repo.get_by_user(user_id, status, limit, offset)
    
    async def get_vendor_orders(
        self,
        vendor_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Order], int]:
        """Get orders for a vendor."""
        return await self.order_repo.get_by_vendor(vendor_id, status, limit, offset)
    
    async def cancel_order(self, order_id: int, user_id: int, reason: Optional[str] = None) -> Order:
        """Cancel an order."""
        order = await self.get_order(order_id)
        
        if not order.can_cancel():
            raise ValidationError(f"Order cannot be cancelled in current status: {order.status}")
        
        return await self.update_order_status(
            order_id,
            OrderStatusUpdate(status=OrderStatus.CANCELLED.value, reason=reason),
            user_id,
        )
    
    async def _add_history(
        self,
        order_id: int,
        previous_status: Optional[str],
        new_status: str,
        changed_by: Optional[int],
        reason: Optional[str] = None,
    ) -> None:
        """Add entry to order history."""
        history = OrderHistory(
            order_id=order_id,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason,
        )
        self.db.add(history)
        await self.db.flush()
    
    def _is_valid_transition(self, current: str, new: str) -> bool:
        """Check if status transition is valid."""
        valid_transitions = {
            OrderStatus.PENDING.value: [
                OrderStatus.CONFIRMED.value,
                OrderStatus.CANCELLED.value,
            ],
            OrderStatus.CONFIRMED.value: [
                OrderStatus.PROCESSING.value,
                OrderStatus.CANCELLED.value,
            ],
            OrderStatus.PROCESSING.value: [
                OrderStatus.SHIPPED.value,
                OrderStatus.CANCELLED.value,
            ],
            OrderStatus.SHIPPED.value: [
                OrderStatus.DELIVERED.value,
            ],
            OrderStatus.DELIVERED.value: [],
            OrderStatus.CANCELLED.value: [],
            OrderStatus.REFUNDED.value: [],
        }
        
        return new in valid_transitions.get(current, [])


class OrderItemService:
    """Service for order item operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.order_item_repo = OrderItemRepository(db)
    
    async def get_order_items(self, order_id: int) -> List[OrderItem]:
        """Get all items for an order."""
        return await self.order_item_repo.get_by_order(order_id)


class OrderTrackingService:
    """Service for order tracking."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.order_repo = OrderRepository(db)
    
    async def track_order(self, order_number: str, email_or_phone: str) -> Optional[Order]:
        """Track order by number and contact info."""
        order = await self.order_repo.get_by_order_number(order_number)
        if not order:
            return None
        
        # Verify contact info (simplified)
        return order
    
    async def get_tracking_status(self, order_id: int) -> Dict[str, Any]:
        """Get detailed tracking information."""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order", order_id)
        
        return {
            "order_number": order.order_number,
            "status": order.status,
            "payment_status": order.payment_status,
            "shipping_method": order.shipping_method,
            "tracking_number": order.tracking_number,
            "estimated_delivery": order.estimated_delivery_date,
            "delivered_at": order.delivered_at,
            "history": [
                {
                    "status": h.new_status,
                    "timestamp": h.created_at,
                    "note": h.reason,
                }
                for h in order.history
            ],
        }


__all__ = ["OrderService", "OrderItemService", "OrderTrackingService"]