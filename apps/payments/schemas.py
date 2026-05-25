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
]
