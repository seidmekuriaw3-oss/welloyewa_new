# ============================
# WOLLOYEWA STORE BOT - WEBHOOK ENDPOINTS
# ============================
"""Webhook endpoints for payment gateway notifications and external integrations."""

from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any
import json

from core.logger import logger
from core.security import verify_telegram_webhook
from infrastructure.payments.payment_verifier import verify_payment_signature, PaymentVerifier
from infrastructure.queues.task_deduplicator import deduplicate_task

router = APIRouter(tags=["webhooks"])


@router.post("/chapa")
async def chapa_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
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
        
        # Verify webhook signature
        # is_valid = verify_payment_signature(payload, settings.CHAPA_WEBHOOK_SECRET, signature)
        
        # Process in background
        background_tasks.add_task(process_chapa_webhook, payload)
        
        logger.info(f"Received Chapa webhook: {payload.get('event', 'unknown')}")
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Chapa webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/telebirr")
async def telebirr_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Telebirr payment gateway webhook.
    
    Receives payment status updates from Telebirr.
    """
    try:
        body = await request.body()
        payload = json.loads(body)
        
        # Process in background
        background_tasks.add_task(process_telebirr_webhook, payload)
        
        logger.info(f"Received Telebirr webhook: {payload.get('tradeStatus', 'unknown')}")
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Telebirr webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cbe-birr")
async def cbe_birr_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    CBE Birr payment gateway webhook.
    
    Receives payment status updates from CBE Birr.
    """
    try:
        body = await request.body()
        payload = json.loads(body)
        
        # Process in background
        background_tasks.add_task(process_cbe_birr_webhook, payload)
        
        logger.info(f"Received CBE Birr webhook: {payload.get('transactionStatus', 'unknown')}")
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"CBE Birr webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
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
        raise HTTPException(status_code=500, detail=str(e))


# ============================
# Background Task Handlers
# ============================

async def process_chapa_webhook(payload: Dict[str, Any]) -> None:
    """Process Chapa webhook in background."""
    from infrastructure.payments.payment_verifier import verify_and_update_order_payment
    from infrastructure.database.session import get_db_session
    
    event = payload.get("event")
    data = payload.get("data", {})
    
    if event == "charge.success":
        transaction_id = data.get("tx_ref")
        order_id = extract_order_id_from_ref(transaction_id)
        
        async for db in get_db_session():
            await verify_and_update_order_payment(db, order_id, "chapa", transaction_id)
            break


async def process_telebirr_webhook(payload: Dict[str, Any]) -> None:
    """Process Telebirr webhook in background."""
    from infrastructure.payments.payment_verifier import verify_and_update_order_payment
    from infrastructure.database.session import get_db_session
    
    trade_status = payload.get("tradeStatus")
    
    if trade_status == "TRADE_SUCCESS":
        transaction_id = payload.get("outTradeNo")
        order_id = extract_order_id_from_ref(transaction_id)
        
        async for db in get_db_session():
            await verify_and_update_order_payment(db, order_id, "telebirr", transaction_id)
            break


async def process_cbe_birr_webhook(payload: Dict[str, Any]) -> None:
    """Process CBE Birr webhook in background."""
    from infrastructure.payments.payment_verifier import verify_and_update_order_payment
    from infrastructure.database.session import get_db_session
    
    transaction_status = payload.get("transactionStatus")
    
    if transaction_status == "SUCCESS":
        transaction_id = payload.get("transactionId")
        order_id = extract_order_id_from_ref(transaction_id)
        
        async for db in get_db_session():
            await verify_and_update_order_payment(db, order_id, "cbe_birr", transaction_id)
            break


async def process_generic_webhook(webhook_type: str, payload: Dict[str, Any]) -> None:
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


__all__ = ["router"]