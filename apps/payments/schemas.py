from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class PaymentInitiateRequest(BaseModel):
    order_id: int = Field(..., description="Order ID to pay for")
    provider: str = Field(..., description="Payment method (telebirr, cbe_birr, chapa, etc.)")
    amount: Decimal | None = Field(None, description="Amount to pay")
    currency: str = "ETB"
    callback_url: str | None = Field(None, description="Callback URL after payment")
    webhook_url: str | None = Field(None, description="Webhook URL for payment status updates")
    metadata: dict[str, Any] | None = None


class PaymentInitiateResponse(BaseModel):
    success: bool
    transaction_id: str | None = None
    payment_url: str | None = None
    redirect_url: str | None = None
    message: str | None = None


class PaymentVerifyResponse(BaseModel):
    success: bool
    transaction_id: str
    status: str
    amount: float | None = None
    currency: str | None = None
    message: str | None = None


class PaymentRefundRequest(BaseModel):
    transaction_id: str = Field(..., description="Transaction ID to refund")
    amount: Decimal | None = Field(None, description="Amount to refund (full refund if None)")
    reason: str | None = Field(None, description="Reason for refund")


class PaymentRefundResponse(BaseModel):
    success: bool
    refund_id: str | None = None
    status: str | None = None
    message: str | None = None


class PaymentVerify(BaseModel):
    transaction_id: str
    provider: str


class PaymentWebhook(BaseModel):
    provider: str
    data: dict[str, Any]


class PaymentResponse(BaseModel):
    success: bool
    transaction_id: str | None = None
    payment_url: str | None = None
    message: str | None = None


__all__ = [
    "PaymentInitiateRequest",
    "PaymentInitiateResponse",
    "PaymentRefundRequest",
    "PaymentRefundResponse",
    "PaymentResponse",
    "PaymentVerify",
    "PaymentVerifyResponse",
    "PaymentWebhook",
]
