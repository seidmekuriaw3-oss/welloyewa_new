# ============================
# WOLLOYEWA STORE BOT - WEBHOOK ENDPOINTS
# ============================
"""Webhook endpoints for payment gateway notifications and external integrations."""

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from core.config import settings
from core.logger import logger
from infrastructure.payments.payment_verifier import verify_payment_signature

router = APIRouter(tags=["webhooks"])


@router.post("/chapa")
async def chapa_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Chapa payment gateway webhook.

    Receives payment status updates from Chapa.
    """
    try:
        # Get request body
        body = await request.body()
        payload = json.loads(body)

        # Get signature from headers
        signature = request.headers.get("Chapa-Signature")

        if not signature:
            logger.warning("Chapa webhook missing signature")
            raise HTTPException(status_code=401, detail="Missing signature")

        # Reject forged payment notifications before scheduling any state change.
        if not settings.CHAPA_WEBHOOK_SECRET or not verify_payment_signature(
            payload,
            settings.CHAPA_WEBHOOK_SECRET,
            signature_header=signature,
        ):
            logger.warning("Chapa webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Process in background
        background_tasks.add_task(process_chapa_webhook, payload)

        logger.info(f"Received Chapa webhook: {payload.get('event', 'unknown')}")
        return {"status": "received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chapa webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/telebirr")
async def telebirr_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Telebirr payment gateway webhook.

    Receives payment status updates from Telebirr.
    """
    try:
        body = await request.body()
        payload = json.loads(body)

        from infrastructure.payments.telebirr import TelebirrProvider

        if not settings.TELEBIRR_APP_KEY or not TelebirrProvider()._verify_signature(payload):
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Process in background
        background_tasks.add_task(process_telebirr_webhook, payload)

        logger.info(f"Received Telebirr webhook: {payload.get('tradeStatus', 'unknown')}")
        return {"status": "received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Telebirr webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/cbe-birr")
async def cbe_birr_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    CBE Birr payment gateway webhook.

    Receives payment status updates from CBE Birr.
    """
    try:
        body = await request.body()
        payload = json.loads(body)

        from infrastructure.payments.cbe_birr import CBEBirrProvider

        if not settings.CBE_BIRR_SECRET_KEY or not CBEBirrProvider()._verify_signature(payload):
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Process in background
        background_tasks.add_task(process_cbe_birr_webhook, payload)

        logger.info(f"Received CBE Birr webhook: {payload.get('transactionStatus', 'unknown')}")
        return {"status": "received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CBE Birr webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
) -> dict[str, Any]:
    """
    Telegram bot webhook.

    Receives updates from Telegram Bot API.
    """
    try:
        body = await request.body()
        payload = json.loads(body)

        # Forward to bot handler
        from bot.webhooks import handle_telegram_update

        await handle_telegram_update(payload)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/generic")
async def generic_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Generic webhook endpoint for custom integrations.
    """
    try:
        body = await request.body()
        payload = json.loads(body)

        # Extract webhook type from headers or body
        webhook_type = request.headers.get("X-Webhook-Type", "generic")

        background_tasks.add_task(process_generic_webhook, webhook_type, payload)

        logger.info(f"Received generic webhook: {webhook_type}")
        return {"status": "received"}

    except Exception as e:
        logger.error(f"Generic webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================
# Background Task Handlers
# ============================


async def process_chapa_webhook(payload: dict[str, Any]) -> None:
    """Process Chapa webhook in background."""
    from infrastructure.database.session import get_db_session
    from infrastructure.payments.payment_verifier import verify_and_update_order_payment

    event = payload.get("event")
    data = payload.get("data", {})

    if event == "charge.success":
        transaction_id = data.get("tx_ref")

        async for db in get_db_session():
            await _verify_payment_reference(db, transaction_id, "chapa")
            break


async def process_telebirr_webhook(payload: dict[str, Any]) -> None:
    """Process Telebirr webhook in background."""
    from infrastructure.database.session import get_db_session
    from infrastructure.payments.payment_verifier import verify_and_update_order_payment

    trade_status = payload.get("tradeStatus")

    if trade_status == "TRADE_SUCCESS":
        transaction_id = payload.get("outTradeNo")

        async for db in get_db_session():
            await _verify_payment_reference(db, transaction_id, "telebirr")
            break


async def process_cbe_birr_webhook(payload: dict[str, Any]) -> None:
    """Process CBE Birr webhook in background."""
    from infrastructure.database.session import get_db_session
    from infrastructure.payments.payment_verifier import verify_and_update_order_payment

    transaction_status = payload.get("transactionStatus")

    if transaction_status == "SUCCESS":
        transaction_id = payload.get("transactionId")

        async for db in get_db_session():
            await _verify_payment_reference(db, transaction_id, "cbe_birr")
            break


async def _verify_payment_reference(db, reference: str | None, method: str) -> bool:
    """Resolve gateway order references and update only the matching order."""
    from apps.orders.services import OrderService
    from infrastructure.payments.payment_verifier import verify_and_update_order_payment

    if not reference:
        logger.warning("Ignoring payment webhook without a transaction reference")
        return False

    order_service = OrderService(db)
    order_id = extract_order_id_from_ref(reference)
    if order_id:
        return await verify_and_update_order_payment(db, order_id, method, reference)

    order_number = extract_order_number_from_ref(reference)
    if not order_number:
        logger.warning("Ignoring payment webhook with invalid reference: %s", reference)
        return False
    try:
        order = await order_service.get_order_by_number(order_number)
    except Exception as exc:
        logger.warning("Payment reference did not match an order: %s (%s)", reference, exc)
        return False
    return await verify_and_update_order_payment(db, order.id, method, reference)


async def process_generic_webhook(webhook_type: str, payload: dict[str, Any]) -> None:
    """Process generic webhook."""
    logger.debug(f"Processing generic webhook {webhook_type}: {payload}")


def extract_order_id_from_ref(reference: str) -> int:
    """Extract order ID from transaction reference."""
    # Reference format: ORDER_{order_id} or similar
    if reference and reference.startswith("ORDER_"):
        try:
            return int(reference.split("_")[1])
        except (IndexError, ValueError):
            pass
    return 0


def extract_order_number_from_ref(reference: str | None) -> str | None:
    """Extract an order number from ORDER_<number> or ORD_<number> references."""
    if not reference:
        return None
    for prefix in ("ORDER_", "ORD_"):
        if reference.startswith(prefix):
            return reference[len(prefix) :] or None
    return None


__all__ = ["router"]
