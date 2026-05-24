# ============================
# WOLLOYEWA STORE BOT - ESCROW SERVICE
# ============================
"""Escrow service for secure transactions between buyers and sellers."""

from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from infrastructure.payments.base import PaymentRequest, PaymentResponse
from infrastructure.payments.factory import get_payment_provider
from core.logger import logger
from core.config import settings


class EscrowStatus(str, Enum):
    """Status of escrow transaction."""
    PENDING = "pending"          # Escrow created, payment pending
    FUNDED = "funded"            # Payment received in escrow
    IN_DISPUTE = "in_dispute"    # Buyer raised dispute
    RELEASED = "released"        # Funds released to seller
    REFUNDED = "refunded"        # Funds refunded to buyer
    CANCELLED = "cancelled"      # Transaction cancelled
    EXPIRED = "expired"          # Escrow expired


@dataclass
class EscrowTransaction:
    """Escrow transaction record."""
    
    escrow_id: str
    order_id: int
    order_number: str
    buyer_id: int
    seller_id: int
    amount: Decimal
    status: EscrowStatus
    release_date: Optional[datetime] = None
    dispute_reason: Optional[str] = None
    dispute_resolved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    transaction_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EscrowService:
    """
    Escrow service for secure transactions.
    
    Features:
    - Hold funds until order completion
    - Dispute resolution workflow
    - Automatic release after holding period
    - Refund protection for buyers
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.holding_days = 7  # Default holding period in days
    
    async def create_escrow(
        self,
        order_id: int,
        order_number: str,
        buyer_id: int,
        seller_id: int,
        amount: Decimal,
        holding_days: Optional[int] = None,
        payment_method: str = "chapa",
    ) -> EscrowTransaction:
        """
        Create an escrow transaction.
        
        Args:
            order_id: Order ID
            order_number: Order number
            buyer_id: Buyer user ID
            seller_id: Seller user ID
            amount: Amount to hold in escrow
            holding_days: Days to hold funds (default 7)
            payment_method: Payment method
            
        Returns:
            EscrowTransaction
        """
        holding_days = holding_days or self.holding_days
        expires_at = datetime.utcnow() + timedelta(days=holding_days)
        
        # Create escrow record
        escrow = EscrowTransaction(
            escrow_id=self._generate_escrow_id(),
            order_id=order_id,
            order_number=order_number,
            buyer_id=buyer_id,
            seller_id=seller_id,
            amount=amount,
            status=EscrowStatus.PENDING,
            expires_at=expires_at,
        )
        
        # Store in database
        await self._store_escrow(escrow)
        
        # Process payment
        provider = await get_payment_provider(payment_method)
        
        request = PaymentRequest(
            amount=amount,
            currency="ETB",
            order_id=order_id,
            order_number=order_number,
            description=f"Escrow payment for order {order_number}",
            metadata={
                "escrow_id": escrow.escrow_id,
                "is_escrow": True,
            },
        )
        
        response = await provider.initialize_payment(request)
        
        if response.success:
            escrow.status = EscrowStatus.FUNDED
            escrow.transaction_id = response.transaction_id
            await self._update_escrow(escrow)
            logger.info(f"Escrow {escrow.escrow_id} funded: {amount} ETB")
        else:
            escrow.status = EscrowStatus.CANCELLED
            await self._update_escrow(escrow)
            logger.error(f"Escrow payment failed for {escrow.escrow_id}")
        
        return escrow
    
    async def release_funds(
        self,
        escrow_id: str,
        released_by: int,
    ) -> bool:
        """
        Release escrow funds to seller.
        
        Args:
            escrow_id: Escrow ID
            released_by: User ID releasing funds
            
        Returns:
            True if funds released successfully
        """
        escrow = await self._get_escrow(escrow_id)
        
        if not escrow:
            logger.error(f"Escrow not found: {escrow_id}")
            return False
        
        if escrow.status != EscrowStatus.FUNDED:
            logger.warning(f"Cannot release escrow {escrow_id}: status {escrow.status}")
            return False
        
        # Transfer funds to seller
        success = await self._transfer_to_seller(escrow)
        
        if success:
            escrow.status = EscrowStatus.RELEASED
            escrow.release_date = datetime.utcnow()
            await self._update_escrow(escrow)
            logger.info(f"Escrow {escrow_id} released to seller {escrow.seller_id}")
            return True
        
        return False
    
    async def refund_buyer(
        self,
        escrow_id: str,
        reason: str,
        refunded_by: int,
    ) -> bool:
        """
        Refund escrow funds to buyer.
        
        Args:
            escrow_id: Escrow ID
            reason: Refund reason
            refunded_by: User ID processing refund
            
        Returns:
            True if refund successful
        """
        escrow = await self._get_escrow(escrow_id)
        
        if not escrow:
            logger.error(f"Escrow not found: {escrow_id}")
            return False
        
        if escrow.status != EscrowStatus.FUNDED:
            logger.warning(f"Cannot refund escrow {escrow_id}: status {escrow.status}")
            return False
        
        # Process refund
        provider = await get_payment_provider("chapa")  # Use original payment method
        success = await provider.refund_payment(escrow.transaction_id, amount=escrow.amount)
        
        if success:
            escrow.status = EscrowStatus.REFUNDED
            await self._update_escrow(escrow)
            logger.info(f"Escrow {escrow_id} refunded to buyer: {reason}")
            return True
        
        return False
    
    async def raise_dispute(
        self,
        escrow_id: str,
        buyer_id: int,
        reason: str,
    ) -> bool:
        """
        Raise a dispute for escrow transaction.
        
        Args:
            escrow_id: Escrow ID
            buyer_id: Buyer ID
            reason: Dispute reason
            
        Returns:
            True if dispute raised
        """
        escrow = await self._get_escrow(escrow_id)
        
        if not escrow or escrow.buyer_id != buyer_id:
            return False
        
        if escrow.status != EscrowStatus.FUNDED:
            return False
        
        escrow.status = EscrowStatus.IN_DISPUTE
        escrow.dispute_reason = reason
        await self._update_escrow(escrow)
        
        logger.info(f"Dispute raised for escrow {escrow_id}: {reason}")
        
        # Notify admin for manual resolution
        await self._notify_admin_dispute(escrow)
        
        return True
    
    async def resolve_dispute(
        self,
        escrow_id: str,
        resolve_in_favor_of: str,  # 'buyer' or 'seller'
        admin_id: int,
    ) -> bool:
        """
        Resolve an escrow dispute.
        
        Args:
            escrow_id: Escrow ID
            resolve_in_favor_of: Resolve in favor of 'buyer' or 'seller'
            admin_id: Admin ID resolving dispute
            
        Returns:
            True if dispute resolved
        """
        escrow = await self._get_escrow(escrow_id)
        
        if not escrow or escrow.status != EscrowStatus.IN_DISPUTE:
            return False
        
        if resolve_in_favor_of == "buyer":
            success = await self.refund_buyer(escrow_id, "Dispute resolved in favor of buyer", admin_id)
        elif resolve_in_favor_of == "seller":
            success = await self.release_funds(escrow_id, admin_id)
        else:
            return False
        
        if success:
            escrow.dispute_resolved_at = datetime.utcnow()
            await self._update_escrow(escrow)
            logger.info(f"Dispute resolved for escrow {escrow_id} in favor of {resolve_in_favor_of}")
            return True
        
        return False
    
    async def auto_release_expired(self) -> int:
        """Auto-release funds for expired escrow transactions."""
        expired_escrows = await self._get_expired_escrows()
        released_count = 0
        
        for escrow in expired_escrows:
            success = await self.release_funds(escrow.escrow_id, None)
            if success:
                released_count += 1
        
        logger.info(f"Auto-released {released_count} expired escrows")
        return released_count
    
    def _generate_escrow_id(self) -> str:
        """Generate unique escrow ID."""
        import uuid
        return f"ESC_{uuid.uuid4().hex[:12].upper()}"
    
    async def _store_escrow(self, escrow: EscrowTransaction) -> None:
        """Store escrow in database."""
        # Implement database storage
        pass
    
    async def _get_escrow(self, escrow_id: str) -> Optional[EscrowTransaction]:
        """Get escrow from database."""
        # Implement database retrieval
        return None
    
    async def _update_escrow(self, escrow: EscrowTransaction) -> None:
        """Update escrow in database."""
        pass
    
    async def _get_expired_escrows(self) -> list:
        """Get expired escrows."""
        return []
    
    async def _transfer_to_seller(self, escrow: EscrowTransaction) -> bool:
        """Transfer funds to seller."""
        # Implement actual transfer logic
        logger.info(f"Transferring {escrow.amount} ETB to seller {escrow.seller_id}")
        return True
    
    async def _notify_admin_dispute(self, escrow: EscrowTransaction) -> None:
        """Notify admin about dispute."""
        logger.warning(f"ESCROW DISPUTE: {escrow.escrow_id} - {escrow.dispute_reason}")


async def create_escrow(
    db,
    order_id: int,
    order_number: str,
    buyer_id: int,
    seller_id: int,
    amount: Decimal,
    holding_days: Optional[int] = None,
) -> EscrowTransaction:
    """Create an escrow transaction."""
    service = EscrowService(db)
    return await service.create_escrow(order_id, order_number, buyer_id, seller_id, amount, holding_days)


async def release_escrow(db, escrow_id: str, released_by: int) -> bool:
    """Release escrow funds to seller."""
    service = EscrowService(db)
    return await service.release_funds(escrow_id, released_by)


async def refund_escrow(db, escrow_id: str, reason: str, refunded_by: int) -> bool:
    """Refund escrow funds to buyer."""
    service = EscrowService(db)
    return await service.refund_buyer(escrow_id, reason, refunded_by)


__all__ = [
    "EscrowService",
    "EscrowTransaction",
    "EscrowStatus",
    "create_escrow",
    "release_escrow",
    "refund_escrow",
]