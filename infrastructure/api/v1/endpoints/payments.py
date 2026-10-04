# ============================
# WOLLOYEWA STORE BOT - PAYMENTS API ENDPOINTS
# ============================
"""REST API endpoints for payment processing."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.orders.services import OrderService
from apps.payments.schemas import (
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentRefundRequest,
    PaymentRefundResponse,
    PaymentVerifyResponse,
)
from core.dependencies import get_current_admin, get_current_user, get_db_session
from core.exceptions import NotFoundError, PaymentError, ValidationError
from infrastructure.payments.factory import get_payment_provider, process_payment

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e

    # Check if payment is already processed
    if order.payment_status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order already paid")

    # Process payment
    try:
        response = await process_payment(
            method=data.provider,
            amount=order.total,
            order_id=order.id,
            order_number=order.order_number,
            customer_name=current_user.get("full_name", ""),
            customer_email=current_user.get("email", ""),
            customer_phone=current_user.get("phone_number", ""),
            callback_url=data.callback_url,
            webhook_url=data.webhook_url,
        )

        if response.success:
            if not response.transaction_id:
                raise PaymentError("Payment provider returned no transaction reference")
            await order_service.save_payment_transaction_id(order.id, response.transaction_id)

        return PaymentInitiateResponse(
            success=response.success,
            transaction_id=response.transaction_id,
            payment_url=response.payment_url,
            redirect_url=response.redirect_url,
            message=response.message,
        )

    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


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
    order_service = OrderService(db)
    try:
        order = await order_service.get_order_by_payment_transaction_id(transaction_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found") from e

    if order.user_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    stored_method = getattr(order.payment_method, "value", order.payment_method)
    if stored_method != method:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment method mismatch")

    try:
        provider = await get_payment_provider(method)
        verification = await provider.verify_payment(transaction_id)
        verified = (
            verification.verified
            and verification.transaction_id == transaction_id
            and verification.amount == order.total
            and verification.currency.upper() == "ETB"
        )

        if verified and order.payment_status != "paid":
            await order_service.update_payment_status(
                order_id=order.id,
                payment_status="paid",
                transaction_id=transaction_id,
            )

        return PaymentVerifyResponse(
            success=verified,
            status=verification.status.value if verification.status else "unknown",
            amount=float(verification.amount) if verification.amount is not None else None,
            currency=verification.currency,
            transaction_id=transaction_id,
            message="Payment verified" if verified else "Payment not verified",
        )

    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


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

    try:
        order = await order_service.get_order(data.order_id)

        if not order.payment_transaction_id:
            raise ValidationError("No payment transaction found for this order")

        if order.payment_status != "paid":
            raise ValidationError("Order is not in paid status")

        refund_amount = Decimal(str(data.amount)) if data.amount is not None else order.total
        refundable_amount = order.total - (order.refunded_amount or Decimal("0"))
        if refund_amount <= 0 or refund_amount > refundable_amount:
            raise ValidationError("Refund amount exceeds the remaining refundable balance")

        provider_name = getattr(order.payment_method, "value", order.payment_method)
        provider = await get_payment_provider(provider_name)
        success = await provider.refund_payment(
            transaction_id=order.payment_transaction_id,
            amount=refund_amount,
            reason=data.reason,
        )

        if success:
            order.refunded_amount = (order.refunded_amount or Decimal("0")) + refund_amount
            order.refunded_at = datetime.now(UTC).replace(tzinfo=None)
            if order.refunded_amount >= order.total:
                order.payment_status = "refunded"
                order.status = "refunded"
            await db.commit()
            return PaymentRefundResponse(
                success=True,
                amount=float(refund_amount),
                status="completed",
                message="Refund processed successfully",
            )
        else:
            return PaymentRefundResponse(
                success=False,
                status="failed",
                message="Refund failed",
            )

    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


# ============================
# Payment Method Endpoints
# ============================


@router.get("/methods", response_model=dict[str, Any])
async def get_payment_methods(
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
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
