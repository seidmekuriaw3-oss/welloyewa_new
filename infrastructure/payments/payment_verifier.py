# ============================
# WOLLOYEWA STORE BOT - PAYMENT VERIFIER
# ============================
"""Payment verification utilities for webhook validation and signature checking."""

import hashlib
import hmac
import json
from typing import Dict, Any, Optional
from decimal import Decimal

from infrastructure.payments.base import PaymentVerification, PaymentStatus
from infrastructure.payments.factory import get_payment_provider
from core.config import settings
from core.logger import logger


class PaymentVerifier:
    """
    Payment verification utility.
    
    Provides methods to verify payment status and validate webhook signatures.
    """
    
    def __init__(self):
        self._providers = {}
    
    async def verify_payment(
        self,
        method: str,
        transaction_id: str,
    ) -> PaymentVerification:
        """
        Verify payment status with provider.
        
        Args:
            method: Payment method (chapa, telebirr, cbe_birr)
            transaction_id: Transaction ID from gateway
            
        Returns:
            Payment verification result
        """
        provider = await get_payment_provider(method)
        return await provider.verify_payment(transaction_id)
    
    async def verify_webhook(
        self,
        method: str,
        payload: Dict[str, Any],
    ) -> PaymentVerification:
        """
        Verify and process webhook payload.
        
        Args:
            method: Payment method
            payload: Raw webhook payload
            
        Returns:
            Payment verification result
        """
        provider = await get_payment_provider(method)
        return await provider.process_webhook(payload)
    
    async def get_payment_status(
        self,
        method: str,
        transaction_id: str,
    ) -> PaymentStatus:
        """Get payment status from provider."""
        verification = await self.verify_payment(method, transaction_id)
        return verification.status


def verify_payment_signature(
    payload: Dict[str, Any],
    secret: str,
    signature_header: Optional[str] = None,
    signature_field: Optional[str] = None,
) -> bool:
    """
    Verify webhook signature for payment notifications.
    
    Args:
        payload: Webhook payload
        secret: Secret key for signature
        signature_header: Header containing signature (e.g., 'X-Signature')
        signature_field: Field in payload containing signature
        
    Returns:
        True if signature is valid
    """
    # Get signature from header or payload
    signature = None
    if signature_header:
        # Would need to access headers from request context
        pass
    elif signature_field:
        signature = payload.get(signature_field)
    
    if not signature:
        logger.warning("No signature found in webhook")
        return False
    
    # Remove signature field from payload for verification
    payload_copy = {k: v for k, v in payload.items() if k != signature_field}
    payload_json = json.dumps(payload_copy, sort_keys=True)
    
    # Compute expected signature
    expected = hmac.new(
        secret.encode(),
        payload_json.encode(),
        hashlib.sha256,
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(expected, signature)


async def verify_and_update_order_payment(
    db,
    order_id: int,
    method: str,
    transaction_id: str,
) -> bool:
    """
    Verify payment and update order status.
    
    Args:
        db: Database session
        order_id: Order ID
        method: Payment method
        transaction_id: Transaction ID
        
    Returns:
        True if payment is verified and order updated
    """
    from apps.orders.services import OrderService
    from apps.orders.schemas import OrderStatusUpdate
    from core.constants import OrderStatus, PaymentStatus
    
    verifier = PaymentVerifier()
    verification = await verifier.verify_payment(method, transaction_id)
    
    if verification.verified:
        # Update order payment status
        order_service = OrderService(db)
        await order_service.update_payment_status(
            order_id=order_id,
            payment_status=PaymentStatus.PAID.value,
            transaction_id=transaction_id,
        )
        
        # Update order status if not already confirmed
        order = await order_service.get_order(order_id)
        if order.status == OrderStatus.PENDING.value:
            await order_service.update_order_status(
                order_id=order_id,
                data=OrderStatusUpdate(status=OrderStatus.CONFIRMED.value),
                user_id=None,
            )
        
        logger.info(f"Payment verified and order {order_id} updated")
        return True
    
    return False


__all__ = [
    "PaymentVerifier",
    "verify_payment_signature",
    "verify_and_update_order_payment",
]