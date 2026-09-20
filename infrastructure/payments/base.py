# ============================
# WOLLOYEWA STORE BOT - PAYMENTS BASE
# ============================
"""Base classes and interfaces for payment providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any


class PaymentStatus(StrEnum):
    """Payment status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    """Payment methods supported."""

    CHAPA = "chapa"
    TELEBIRR = "telebirr"
    CBE_BIRR = "cbe_birr"
    CASH_ON_DELIVERY = "cash_on_delivery"


class PaymentError(Exception):
    """Base exception for payment errors."""

    def __init__(self, message: str, code: str | None = None):
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
    order_id: int | None = None
    order_number: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    description: str | None = None
    callback_url: str | None = None
    webhook_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


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
    transaction_id: str | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    message: str | None = None
    redirect_url: str | None = None
    payment_url: str | None = None
    reference: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


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
    transaction_id: str | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    amount: Decimal | None = None
    currency: str = "ETB"
    customer_email: str | None = None
    customer_phone: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)


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
    async def process_webhook(self, payload: dict[str, Any]) -> PaymentVerification:
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
        amount: Decimal | None = None,
        reason: str | None = None,
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
    "PaymentError",
    "PaymentMethod",
    "PaymentProvider",
    "PaymentRequest",
    "PaymentResponse",
    "PaymentStatus",
    "PaymentVerification",
]
