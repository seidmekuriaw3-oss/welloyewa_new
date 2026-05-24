# ============================
# WOLLOYEWA STORE BOT - SPLIT PAYMENTS
# ============================
"""Split payment functionality for multi-vendor orders."""

from decimal import Decimal
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from infrastructure.payments.base import PaymentRequest, PaymentResponse
from infrastructure.payments.factory import get_payment_provider
from core.logger import logger
from core.utils.currency import split_amount


class SplitPaymentStatus(str, Enum):
    """Status of split payment."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class SplitPayment:
    """Individual split payment for a vendor."""
    
    vendor_id: int
    vendor_name: str
    amount: Decimal
    status: SplitPaymentStatus = SplitPaymentStatus.PENDING
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


@dataclass
class SplitPaymentResult:
    """Result of split payment processing."""
    
    main_transaction_id: str
    total_amount: Decimal
    splits: List[SplitPayment]
    status: SplitPaymentStatus
    completed_at: datetime = field(default_factory=datetime.utcnow)


class SplitPaymentManager:
    """
    Split payment manager for multi-vendor orders.
    
    Features:
    - Split single payment across multiple vendors
    - Track individual payment status per vendor
    - Handle partial failures
    - Automatic retry for failed splits
    """
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def create_split_payment(
        self,
        order_id: int,
        order_number: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        vendor_splits: List[Dict[str, Any]],
        payment_method: str = "chapa",
    ) -> SplitPaymentResult:
        """
        Create split payment for order.
        
        Args:
            order_id: Order ID
            order_number: Order number
            customer_name: Customer name
            customer_email: Customer email
            customer_phone: Customer phone
            vendor_splits: List of vendor splits with amount
            payment_method: Payment method to use
            
        Returns:
            SplitPaymentResult
        """
        total_amount = sum(Decimal(str(s["amount"])) for s in vendor_splits)
        
        # Initialize split payments
        splits = []
        for vendor_split in vendor_splits:
            splits.append(SplitPayment(
                vendor_id=vendor_split["vendor_id"],
                vendor_name=vendor_split.get("vendor_name", f"Vendor {vendor_split['vendor_id']}"),
                amount=Decimal(str(vendor_split["amount"])),
            ))
        
        # Create main payment request
        provider = await get_payment_provider(payment_method)
        
        request = PaymentRequest(
            amount=total_amount,
            currency="ETB",
            order_id=order_id,
            order_number=order_number,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            description=f"Order {order_number} - Multi-vendor payment",
            metadata={
                "is_split_payment": True,
                "vendor_count": len(vendor_splits),
                "splits": vendor_splits,
            },
        )
        
        # Initialize payment
        response = await provider.initialize_payment(request)
        
        if not response.success:
            logger.error(f"Split payment initialization failed for order {order_number}")
            return SplitPaymentResult(
                main_transaction_id="",
                total_amount=total_amount,
                splits=splits,
                status=SplitPaymentStatus.FAILED,
            )
        
        # Store split payment info in database
        await self._store_split_payment(
            order_id=order_id,
            main_transaction_id=response.transaction_id,
            splits=splits,
        )
        
        return SplitPaymentResult(
            main_transaction_id=response.transaction_id,
            total_amount=total_amount,
            splits=splits,
            status=SplitPaymentStatus.PENDING,
        )
    
    async def process_split_payment(
        self,
        main_transaction_id: str,
    ) -> SplitPaymentResult:
        """
        Process split payment distribution.
        
        Args:
            main_transaction_id: Main payment transaction ID
            
        Returns:
            Updated SplitPaymentResult
        """
        # Get split payment info from database
        split_info = await self._get_split_payment(main_transaction_id)
        
        if not split_info:
            logger.error(f"Split payment not found: {main_transaction_id}")
            return None
        
        # Process each vendor split
        all_successful = True
        any_successful = False
        
        for split in split_info["splits"]:
            if split.status != SplitPaymentStatus.PENDING:
                continue
            
            try:
                # Transfer funds to vendor account
                success = await self._transfer_to_vendor(
                    vendor_id=split.vendor_id,
                    amount=split.amount,
                    reference=main_transaction_id,
                )
                
                if success:
                    split.status = SplitPaymentStatus.COMPLETED
                    split.completed_at = datetime.utcnow()
                    any_successful = True
                else:
                    split.status = SplitPaymentStatus.FAILED
                    split.error_message = "Transfer failed"
                    all_successful = False
                    
            except Exception as e:
                split.status = SplitPaymentStatus.FAILED
                split.error_message = str(e)
                all_successful = False
        
        # Determine overall status
        if all_successful:
            status = SplitPaymentStatus.COMPLETED
        elif any_successful:
            status = SplitPaymentStatus.PARTIALLY_COMPLETED
        else:
            status = SplitPaymentStatus.FAILED
        
        # Update database
        await self._update_split_payment_status(main_transaction_id, status, split_info["splits"])
        
        return SplitPaymentResult(
            main_transaction_id=main_transaction_id,
            total_amount=split_info["total_amount"],
            splits=split_info["splits"],
            status=status,
        )
    
    async def _transfer_to_vendor(
        self,
        vendor_id: int,
        amount: Decimal,
        reference: str,
    ) -> bool:
        """
        Transfer funds to vendor account.
        
        Args:
            vendor_id: Vendor ID
            amount: Amount to transfer
            reference: Transaction reference
            
        Returns:
            True if transfer successful
        """
        # In production, integrate with actual payout system
        # This could be bank transfer, Telebirr merchant payment, etc.
        logger.info(f"Transferring {amount} ETB to vendor {vendor_id} (ref: {reference})")
        
        # Mock implementation
        return True
    
    async def _store_split_payment(
        self,
        order_id: int,
        main_transaction_id: str,
        splits: List[SplitPayment],
    ) -> None:
        """Store split payment information in database."""
        # Implement database storage
        logger.info(f"Stored split payment for order {order_id}: {main_transaction_id}")
    
    async def _get_split_payment(self, main_transaction_id: str) -> Optional[Dict]:
        """Get split payment information from database."""
        # Implement database retrieval
        return None
    
    async def _update_split_payment_status(
        self,
        main_transaction_id: str,
        status: SplitPaymentStatus,
        splits: List[SplitPayment],
    ) -> None:
        """Update split payment status in database."""
        logger.info(f"Updated split payment {main_transaction_id} status: {status}")


async def create_split_payment(
    db,
    order_id: int,
    order_number: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    vendor_splits: List[Dict[str, Any]],
    payment_method: str = "chapa",
) -> SplitPaymentResult:
    """Create split payment for order."""
    manager = SplitPaymentManager(db)
    return await manager.create_split_payment(
        order_id, order_number, customer_name, customer_email,
        customer_phone, vendor_splits, payment_method
    )


async def process_split_payment(
    db,
    main_transaction_id: str,
) -> SplitPaymentResult:
    """Process split payment distribution."""
    manager = SplitPaymentManager(db)
    return await manager.process_split_payment(main_transaction_id)


__all__ = [
    "SplitPayment",
    "SplitPaymentManager",
    "SplitPaymentStatus",
    "SplitPaymentResult",
    "create_split_payment",
    "process_split_payment",
]