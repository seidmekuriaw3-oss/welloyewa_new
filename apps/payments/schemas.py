from typing import Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field


class PaymentInitiateRequest(BaseModel):
    order_id: int = Field(..., description="Order ID to pay for")
    provider: str = Field(..., description="Payment method (telebirr, cbe_birr, chapa, etc.)")
    amount: Optional[Decimal] = Field(None, description="Amount to pay")
    currency: str = "ETB"
    callback_url: Optional[str] = Field(None, description="Callback URL after payment")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for payment status updates")
    metadata: Optional[Dict[str, Any]] = None


class PaymentInitiateResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    payment_url: Optional[str] = None
    redirect_url: Optional[str] = None
    message: Optional[str] = None


class PaymentVerifyResponse(BaseModel):
    success: bool
    transaction_id: str
    status: str
    amount: Optional[float] = None
    currency: Optional[str] = None
    message: Optional[str] = None


class PaymentRefundRequest(BaseModel):
    transaction_id: str = Field(..., description="Transaction ID to refund")
    amount: Optional[Decimal] = Field(None, description="Amount to refund (full refund if None)")
    reason: Optional[str] = Field(None, description="Reason for refund")


class PaymentRefundResponse(BaseModel):
    success: bool
    refund_id: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None


class PaymentVerify(BaseModel):
    transaction_id: str
    provider: str


class PaymentWebhook(BaseModel):
    provider: str
    data: Dict[str, Any]


class PaymentResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    payment_url: Optional[str] = None
    message: Optional[str] = None


__all__ = [
    "PaymentInitiateRequest",
    "PaymentInitiateResponse",
    "PaymentVerifyResponse",
    "PaymentRefundRequest",
    "PaymentRefundResponse",
    "PaymentVerify",
    "PaymentWebhook",
    "PaymentResponse",
]
