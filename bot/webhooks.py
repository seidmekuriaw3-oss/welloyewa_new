# ============================
# WOLLOYEWA STORE BOT - TELEGRAM WEBHOOKS
# ============================
"""Webhook handling for Telegram bot updates."""

import json
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from telegram import Update

from core.config import settings
from core.logger import logger
from core.security import verify_telegram_webhook
from bot.bot_instance import get_dispatcher

router = APIRouter()


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Dict[str, str]:
    """
    Handle incoming Telegram webhook updates.
    
    Receives updates from Telegram Bot API and processes them.
    """
    try:
        # Get request body
        body = await request.json()
        
        # Verify secret token if configured
        if settings.TELEGRAM_WEBHOOK_SECRET:
            token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if not verify_telegram_webhook(
                {"secret_token": token}, settings.TELEGRAM_WEBHOOK_SECRET
            ):
                logger.warning("Invalid webhook secret token")
                raise HTTPException(status_code=403, detail="Invalid token")
        
        # Process update in background
        background_tasks.add_task(process_update, body)
        
        return {"status": "ok"}
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_update(update_data: Dict[str, Any]) -> None:
    """
    Process a Telegram update.
    
    Args:
        update_data: Raw update data from Telegram
    """
    try:
        # Create Update object
        update = Update.de_json(update_data, get_dispatcher().bot)
        
        # Process the update
        await get_dispatcher().process_update(update)
        
        logger.debug(f"Processed update: {update.update_id}")
        
    except Exception as e:
        logger.error(f"Error processing update: {e}")


async def set_webhook() -> bool:
    """
    Set the webhook URL for the bot.
    
    Returns:
        True if successful
    """
    from bot.bot_instance import get_bot
    
    webhook_url = settings.TELEGRAM_WEBHOOK_URL
    if not webhook_url:
        logger.warning("TELEGRAM_WEBHOOK_URL not set, using polling mode")
        return False
    
    bot = get_bot()
    
    try:
        # Set webhook
        await bot.set_webhook(
            url=f"{webhook_url}/webhook/telegram",
            secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
        logger.info(f"Webhook set to {webhook_url}/webhook/telegram")
        return True
        
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        return False


async def remove_webhook() -> bool:
    """
    Remove the webhook for the bot.
    
    Returns:
        True if successful
    """
    from bot.bot_instance import get_bot
    
    bot = get_bot()
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook removed")
        return True
    except Exception as e:
        logger.error(f"Failed to remove webhook: {e}")
        return False


async def handle_telegram_update(update_data: Dict[str, Any]) -> None:
    """
    Handle a Telegram update directly (without FastAPI).
    
    Args:
        update_data: Raw update data from Telegram
    """
    await process_update(update_data)


__all__ = ["router", "set_webhook", "remove_webhook", "handle_telegram_update"]