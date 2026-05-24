# ============================
# WOLLOYEWA STORE BOT - PAYMENTS API ENDPOINTS
# ============================
"""REST API endpoints for payment processing."""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Optional, Dict, Any
from decimal import Decimal

from core.dependencies import get_current_user, get_current_admin, get_db_session
from core.exceptions import NotFoundError, ValidationError, PaymentError
from apps.orders.services import OrderService
from infrastructure.payments.factory import get_payment_provider, process_payment
from infrastructure.payments.base import PaymentRequest, PaymentResponse
from apps.payments.schemas import (
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyResponse,
    PaymentRefundRequest,
    PaymentRefundResponse,
)
from apps.common.schemas import MessageResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ============================
# Payment Processing Endpoints
# ============================

@router.post("/initiate", response_model=PaymentInitiateResponse)
async def initiate_payment(
    data: PaymentInitiateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PaymentInitiateResponse:
    """
    Initiate a payment for an order.
    
    Creates a payment request and returns checkout URL or payment link.
    """
    order_service = OrderService(db)
    
    # Get order details
    try:
        order = await order_service.get_order(data.order_id, current_user["id"])
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    
    # Check if payment is already processed
    if order.payment_status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order already paid"
        )
    
    # Process payment
    try:
        response = await process_payment(
            method=data.payment_method,
            amount=order.total,
            order_id=order.id,
            order_number=order.order_number,
            customer_name=current_user.get("full_name", ""),
            customer_email=current_user.get("email", ""),
            customer_phone=current_user.get("phone_number", ""),
            callback_url=data.callback_url,
            webhook_url=data.webhook_url,
        )
        
        return PaymentInitiateResponse(
            success=response.success,
            transaction_id=response.transaction_id,
            payment_url=response.payment_url,
            redirect_url=response.redirect_url,
            message=response.message,
        )
        
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/verify/{transaction_id}", response_model=PaymentVerifyResponse)
async def verify_payment(
    transaction_id: str,
    method: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PaymentVerifyResponse:
    """
    Verify payment status.
    
    Checks the status of a payment transaction.
    """
    try:
        provider = await get_payment_provider(method)
        verification = await provider.verify_payment(transaction_id)
        
        # Update order payment status if verified
        if verification.verified and verification.order_id:
            order_service = OrderService(db)
            await order_service.update_payment_status(
                order_id=verification.order_id,
                payment_status="paid",
                transaction_id=transaction_id,
            )
        
        return PaymentVerifyResponse(
            verified=verification.verified,
            status=verification.status.value if verification.status else "unknown",
            amount=float(verification.amount) if verification.amount else 0,
            transaction_id=verification.transaction_id,
            message="Payment verified" if verification.verified else "Payment not verified",
        )
        
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================
# Refund Endpoints
# ============================

@router.post("/refund", response_model=PaymentRefundResponse)
async def process_refund(
    data: PaymentRefundRequest,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> PaymentRefundResponse:
    """
    Process a refund (admin only).
    
    Refunds a payment for an order.
    """
    order_service = OrderService(db)
    from apps.orders.refunds import RefundManager
    
    try:
        order = await order_service.get_order(data.order_id)
        
        if not order.payment_transaction_id:
            raise ValidationError("No payment transaction found for this order")
        
        if order.payment_status != "paid":
            raise ValidationError("Order is not in paid status")
        
        # Process refund
        refund_manager = RefundManager(db)
        refund = await refund_manager.request_refund(
            order_id=data.order_id,
            amount=Decimal(str(data.amount)) if data.amount else None,
            reason=data.reason,
            notes=data.notes,
        )
        
        # Process through payment gateway
        provider = await get_payment_provider(order.payment_method)
        success = await provider.refund_payment(
            transaction_id=order.payment_transaction_id,
            amount=Decimal(str(data.amount)) if data.amount else None,
            reason=data.reason,
        )
        
        if success:
            return PaymentRefundResponse(
                success=True,
                refund_id=refund.refund_id,
                amount=data.amount or float(order.total),
                message="Refund processed successfully",
            )
        else:
            return PaymentRefundResponse(
                success=False,
                message="Refund failed",
            )
            
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================
# Payment Method Endpoints
# ============================

@router.get("/methods", response_model=Dict[str, Any])
async def get_payment_methods(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get available payment methods.
    
    Returns list of supported payment methods and their configuration.
    """
    return {
        "methods": [
            {
                "id": "chapa",
                "name": "Chapa",
                "icon": "/static/images/payments/chapa.png",
                "supported_currencies": ["ETB"],
                "min_amount": 1,
                "max_amount": 1000000,
            },
            {
                "id": "telebirr",
                "name": "Telebirr",
                "icon": "/static/images/payments/telebirr.png",
                "supported_currencies": ["ETB"],
                "min_amount": 1,
                "max_amount": 50000,
            },
            {
                "id": "cbe_birr",
                "name": "CBE Birr",
                "icon": "/static/images/payments/cbe_birr.png",
                "supported_currencies": ["ETB"],
                "min_amount": 1,
                "max_amount": 50000,
            },
            {
                "id": "cash_on_delivery",
                "name": "Cash on Delivery",
                "icon": "/static/images/payments/cod.png",
                "supported_currencies": ["ETB"],
                "min_amount": 1,
                "max_amount": 10000,
            },
        ]
    }


# ============================
# Payment Webhook (already in webhook.py)
# ============================

# Note: Payment webhook endpoints are in webhook.py
# - POST /webhook/chapa
# - POST /webhook/telebirr
# - POST /webhook/cbe-birr


__all__ = ["router"]