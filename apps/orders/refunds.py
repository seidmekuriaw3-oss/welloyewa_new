# ============================
# WOLLOYEWA STORE BOT - REFUNDS
# ============================
"""Order refund processing with payment gateway integration."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field

from core.logger import logger
from core.exceptions import NotFoundError, ValidationError, PaymentError
from core.events import emit_event
from core.utils.currency import format_etb
from apps.orders.repository import OrderRepository


class RefundStatus(str, Enum):
    """Refund status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class Refund:
    """Refund record."""
    
    refund_id: str
    order_id: int
    amount: Decimal
    reason: str
    status: RefundStatus
    transaction_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None


class RefundManager:
    """
    Order refund manager.
    
    Features:
    - Process refunds via payment gateways
    - Partial refund support
    - Refund status tracking
    - Automatic restocking
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.order_repo = OrderRepository(db_session)
        self._refunds: Dict[str, Refund] = {}
    
    async def request_refund(
        self,
        order_id: int,
        amount: Optional[Decimal] = None,
        reason: str = "Customer request",
        notes: Optional[str] = None,
    ) -> Refund:
        """
        Request a refund for an order.
        
        Args:
            order_id: Order ID
            amount: Refund amount (defaults to full order amount)
            reason: Refund reason
            notes: Additional notes
            
        Returns:
            Refund record
        """
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order", order_id)
        
        # Check if order can be refunded
        if not order.can_refund():
            raise ValidationError(f"Order cannot be refunded in current status: {order.status}")
        
        # Check if already refunded
        if order.refunded_amount > 0:
            raise ValidationError("Order has already been refunded")
        
        # Set refund amount
        if amount is None:
            amount = order.total
        elif amount > order.total:
            raise ValidationError(f"Refund amount cannot exceed order total: {format_etb(order.total)}")
        
        # Create refund record
        refund = Refund(
            refund_id=f"REF-{order.order_number}-{int(datetime.utcnow().timestamp())}",
            order_id=order_id,
            amount=amount,
            reason=reason,
            status=RefundStatus.PENDING,
            notes=notes,
        )
        
        self._refunds[refund.refund_id] = refund
        logger.info(f"Refund requested for order {order.order_number}: {format_etb(amount)}")
        
        # Emit event
        await emit_event(
            "refund.requested",
            {
                "order_id": order_id,
                "refund_id": refund.refund_id,
                "amount": float(amount),
                "reason": reason,
            },
            sync=False,
        )
        
        return refund
    
    async def process_refund(
        self,
        refund_id: str,
        gateway: str = "auto",
    ) -> Refund:
        """
        Process a refund through payment gateway.
        
        Args:
            refund_id: Refund ID
            gateway: Payment gateway to use (auto, chapa, telebirr, cbe_birr)
            
        Returns:
            Updated refund record
        """
        refund = self._refunds.get(refund_id)
        if not refund:
            raise NotFoundError("Refund", refund_id)
        
        if refund.status != RefundStatus.PENDING:
            raise ValidationError(f"Refund already {refund.status}")
        
        refund.status = RefundStatus.PROCESSING
        
        try:
            # Get order details
            order = await self.order_repo.get_by_id(refund.order_id)
            
            # Process refund based on payment method
            payment_method = order.payment_method
            if gateway == "auto":
                gateway = payment_method
            
            transaction_id = await self._process_gateway_refund(
                gateway=gateway,
                order=order,
                amount=refund.amount,
            )
            
            # Update refund
            refund.status = RefundStatus.COMPLETED
            refund.transaction_id = transaction_id
            refund.processed_at = datetime.utcnow()
            
            # Update order
            await self.order_repo.update(refund.order_id, {
                "refunded_amount": refund.amount,
                "refunded_at": datetime.utcnow(),
                "refund_transaction_id": transaction_id,
                "payment_status": "refunded",
                "status": "refunded",
            })
            
            # Restock products
            await self._restock_order_products(refund.order_id)
            
            logger.info(f"Refund processed: {refund_id} - {format_etb(refund.amount)}")
            
            # Emit event
            await emit_event(
                "refund.completed",
                {
                    "order_id": refund.order_id,
                    "refund_id": refund_id,
                    "amount": float(refund.amount),
                    "transaction_id": transaction_id,
                },
                sync=False,
            )
            
        except Exception as e:
            refund.status = RefundStatus.FAILED
            refund.failure_reason = str(e)
            logger.error(f"Refund failed: {refund_id} - {e}")
            
            # Emit failure event
            await emit_event(
                "refund.failed",
                {
                    "order_id": refund.order_id,
                    "refund_id": refund_id,
                    "error": str(e),
                },
                sync=False,
            )
            
            raise PaymentError(f"Refund processing failed: {e}")
        
        return refund
    
    async def _process_gateway_refund(
        self,
        gateway: str,
        order: Any,
        amount: Decimal,
    ) -> str:
        """
        Process refund through specific payment gateway.
        
        Args:
            gateway: Payment gateway name
            order: Order object
            amount: Refund amount
            
        Returns:
            Gateway transaction ID
        """
        # In production, implement actual gateway integration
        
        if gateway == "chapa":
            # Chapa refund API
            # POST https://api.chapa.co/v1/refund
            transaction_id = f"chapa_refund_{int(datetime.utcnow().timestamp())}"
            return transaction_id
        
        elif gateway == "telebirr":
            # Telebirr refund API
            transaction_id = f"telebirr_refund_{int(datetime.utcnow().timestamp())}"
            return transaction_id
        
        elif gateway == "cbe_birr":
            # CBE Birr refund API
            transaction_id = f"cbe_refund_{int(datetime.utcnow().timestamp())}"
            return transaction_id
        
        else:
            # Mock refund for development
            transaction_id = f"mock_refund_{int(datetime.utcnow().timestamp())}"
            return transaction_id
    
    async def _restock_order_products(self, order_id: int) -> None:
        """Restock products from cancelled/refunded order."""
        from apps.products.services import ProductService
        
        items = await self.order_repo.db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        items = items.scalars().all()
        
        product_service = ProductService(self.db)
        for item in items:
            await product_service.release_stock(item.product_id, item.quantity)
        
        logger.info(f"Restocked {len(items)} products from order {order_id}")
    
    async def get_refund_status(self, refund_id: str) -> Optional[Dict[str, Any]]:
        """Get refund status."""
        refund = self._refunds.get(refund_id)
        if not refund:
            return None
        
        return {
            "refund_id": refund.refund_id,
            "order_id": refund.order_id,
            "amount": float(refund.amount),
            "status": refund.status.value,
            "transaction_id": refund.transaction_id,
            "reason": refund.reason,
            "created_at": refund.created_at.isoformat(),
            "processed_at": refund.processed_at.isoformat() if refund.processed_at else None,
            "failure_reason": refund.failure_reason,
        }
    
    async def get_order_refunds(self, order_id: int) -> List[Dict[str, Any]]:
        """Get all refunds for an order."""
        order_refunds = [
            refund for refund in self._refunds.values()
            if refund.order_id == order_id
        ]
        
        return [
            {
                "refund_id": r.refund_id,
                "amount": float(r.amount),
                "status": r.status.value,
                "reason": r.reason,
                "created_at": r.created_at.isoformat(),
            }
            for r in order_refunds
        ]
    
    async def reject_refund(self, refund_id: str, reason: str) -> Refund:
        """Reject a refund request."""
        refund = self._refunds.get(refund_id)
        if not refund:
            raise NotFoundError("Refund", refund_id)
        
        refund.status = RefundStatus.REJECTED
        refund.failure_reason = reason
        refund.processed_at = datetime.utcnow()
        
        logger.info(f"Refund rejected: {refund_id} - {reason}")
        
        # Emit event
        await emit_event(
            "refund.rejected",
            {
                "order_id": refund.order_id,
                "refund_id": refund_id,
                "reason": reason,
            },
            sync=False,
        )
        
        return refund


# Global refund manager placeholder
# In production, this would be initialized with a DB session
_refund_manager = None


async def get_refund_manager(db) -> RefundManager:
    """Get or create refund manager instance."""
    global _refund_manager
    if _refund_manager is None or _refund_manager.db != db:
        _refund_manager = RefundManager(db)
    return _refund_manager


async def process_refund(
    order_id: int,
    amount: Optional[Decimal] = None,
    reason: str = "Customer request",
    db=None,
) -> Refund:
    """Convenience function to process a refund."""
    manager = await get_refund_manager(db)
    refund = await manager.request_refund(order_id, amount, reason)
    return await manager.process_refund(refund.refund_id)


async def get_refund_status(refund_id: str, db) -> Optional[Dict[str, Any]]:
    """Convenience function to get refund status."""
    manager = await get_refund_manager(db)
    return await manager.get_refund_status(refund_id)


__all__ = [
    "RefundManager",
    "Refund",
    "RefundStatus",
    "process_refund",
    "get_refund_status",
]