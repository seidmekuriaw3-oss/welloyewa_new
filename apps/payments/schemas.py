<<<<<<< HEAD
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from decimal import Decimal

class PaymentInitiateRequest(BaseModel):
    order_id: int
    provider: str
    amount: Decimal
    currency: str = "ETB"
    metadata: Optional[Dict[str, Any]] = None

class PaymentInitiateResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    payment_url: Optional[str] = None
    message: Optional[str] = None

class PaymentVerifyResponse(BaseModel):
    success: bool
    transaction_id: str
    status: str
    message: Optional[str] = None

class PaymentRefundRequest(BaseModel):
    transaction_id: str
    amount: Optional[Decimal] = None
    reason: Optional[str] = None

class PaymentRefundResponse(BaseModel):
    success: bool
    refund_id: Optional[str] = None
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
    "PaymentInitiateRequest", "PaymentInitiateResponse",
    "PaymentVerifyResponse", "PaymentRefundRequest", "PaymentRefundResponse",
    "PaymentVerify", "PaymentWebhook", "PaymentResponse",
=======
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
>>>>>>> 58a16d4ee3078d96a16a22860de294107e7c3aef
]
