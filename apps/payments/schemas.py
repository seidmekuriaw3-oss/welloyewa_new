from typing import Optional
from pydantic import Field
from apps.common.schemas import BaseSchema


class PaymentInitiateRequest(BaseSchema):
    order_id: int = Field(..., description="Order ID to pay for")
    payment_method: str = Field(..., description="Payment method (telebirr, cbe_birr, etc.)")
    callback_url: Optional[str] = Field(None, description="Callback URL after payment")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for payment status updates")


class PaymentInitiateResponse(BaseSchema):
    success: bool
    transaction_id: Optional[str] = None
    payment_url: Optional[str] = None
    redirect_url: Optional[str] = None
    message: Optional[str] = None


class PaymentVerifyResponse(BaseSchema):
    success: bool
    transaction_id: str
    status: str
    amount: Optional[float] = None
    currency: Optional[str] = None
    message: Optional[str] = None


class PaymentRefundRequest(BaseSchema):
    transaction_id: str = Field(..., description="Transaction ID to refund")
    amount: Optional[float] = Field(None, description="Amount to refund (full refund if None)")
    reason: Optional[str] = Field(None, description="Reason for refund")


class PaymentRefundResponse(BaseSchema):
    success: bool
    refund_id: Optional[str] = None
    status: str
    message: Optional[str] = None


__all__ = [
    "PaymentInitiateRequest",
    "PaymentInitiateResponse",
    "PaymentVerifyResponse",
    "PaymentRefundRequest",
    "PaymentRefundResponse",
]
