# ============================
# WOLLOYEWA STORE BOT - PAYMENTS BASE
# ============================
"""Base classes and interfaces for payment providers."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from decimal import Decimal


class PaymentStatus(str, Enum):
    """Payment status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Payment methods supported."""
    CHAPA = "chapa"
    TELEBIRR = "telebirr"
    CBE_BIRR = "cbe_birr"
    CASH_ON_DELIVERY = "cash_on_delivery"


class PaymentError(Exception):
    """Base exception for payment errors."""
    
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
        super().__init__(message)


@dataclass
class PaymentRequest:
    """
    Payment request data.
    
    Attributes:
        amount: Amount to charge
        currency: Currency code (ETB)
        order_id: Order ID
        order_number: Order number for reference
        customer_name: Customer full name
        customer_email: Customer email
        customer_phone: Customer phone number
        description: Payment description
        callback_url: URL to redirect after payment
        webhook_url: URL for payment notifications
        metadata: Additional metadata
    """
    
    amount: Decimal
    currency: str = "ETB"
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    description: Optional[str] = None
    callback_url: Optional[str] = None
    webhook_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentResponse:
    """
    Payment response data.
    
    Attributes:
        success: Whether payment was successful
        transaction_id: Gateway transaction ID
        status: Payment status
        message: Response message
        redirect_url: URL to redirect customer for payment
        payment_url: URL for payment page
        reference: Payment reference
        raw_response: Raw gateway response
    """
    
    success: bool
    transaction_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    message: Optional[str] = None
    redirect_url: Optional[str] = None
    payment_url: Optional[str] = None
    reference: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentVerification:
    """
    Payment verification result.
    
    Attributes:
        verified: Whether payment is verified
        transaction_id: Gateway transaction ID
        status: Payment status
        amount: Amount paid
        currency: Currency
        customer_email: Customer email
        customer_phone: Customer phone
        metadata: Additional data
        raw_response: Raw gateway response
    """
    
    verified: bool
    transaction_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    amount: Optional[Decimal] = None
    currency: str = "ETB"
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_response: Dict[str, Any] = field(default_factory=dict)


class PaymentProvider(ABC):
    """
    Abstract base class for payment providers.
    
    All payment gateways must implement this interface.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @abstractmethod
    async def initialize_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Initialize a payment.
        
        Args:
            request: Payment request data
            
        Returns:
            Payment response with redirect URL or payment link
        """
        pass
    
    @abstractmethod
    async def verify_payment(self, transaction_id: str) -> PaymentVerification:
        """
        Verify payment status.
        
        Args:
            transaction_id: Gateway transaction ID
            
        Returns:
            Payment verification result
        """
        pass
    
    @abstractmethod
    async def process_webhook(self, payload: Dict[str, Any]) -> PaymentVerification:
        """
        Process webhook notification from gateway.
        
        Args:
            payload: Raw webhook payload
            
        Returns:
            Payment verification result
        """
        pass
    
    @abstractmethod
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Refund a payment.
        
        Args:
            transaction_id: Gateway transaction ID
            amount: Amount to refund (None for full refund)
            reason: Refund reason
            
        Returns:
            True if refund successful
        """
        pass
    
    async def get_payment_status(self, transaction_id: str) -> PaymentStatus:
        """
        Get payment status.
        
        Args:
            transaction_id: Gateway transaction ID
            
        Returns:
            Payment status
        """
        verification = await self.verify_payment(transaction_id)
        return verification.status


__all__ = [
    "PaymentProvider",
    "PaymentRequest",
    "PaymentResponse",
    "PaymentVerification",
    "PaymentStatus",
    "PaymentMethod",
    "PaymentError",
]