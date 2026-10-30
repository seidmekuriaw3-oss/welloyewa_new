# ============================
# WOLLOYEWA STORE BOT - TELEGRAM WEBHOOKS
# ============================
"""Webhook handling for Telegram bot updates."""

import json
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from telegram import Update

from bot.bot_instance import get_dispatcher
from core.config import settings
from core.dependencies import verify_webhook_signature
from core.logger import logger
from core.security import verify_telegram_webhook

router = APIRouter()


@router.post("/telegram", dependencies=[Depends(verify_webhook_signature)])
async def telegram_webhook(
    request: Request,
) -> dict[str, str]:
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

        await handle_telegram_update(body)

        return {"status": "ok"}

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON") from e
    except Exception as e:
        logger.exception("Webhook processing failed")
        raise HTTPException(status_code=500, detail="Webhook processing failed") from e


async def process_update(update_data: dict[str, Any]) -> None:
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

    except Exception:
        logger.exception(
            "Telegram update processing failed (update_id=%s)",
            update_data.get("update_id"),
        )
        raise


async def set_webhook() -> bool:
    """
    Set the webhook URL for the bot.

    Returns:
        True if successful
    """
    from bot.bot_instance import get_bot

    webhook_base_url = (settings.TELEGRAM_WEBHOOK_URL or "").strip()
    if not webhook_base_url:
        logger.warning("TELEGRAM_WEBHOOK_URL not set, using polling mode")
        return False

    if "://" not in webhook_base_url:
        webhook_base_url = f"https://{webhook_base_url}"

    parsed = urlsplit(webhook_base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        logger.error(
            "Invalid TELEGRAM_WEBHOOK_URL %r. Use a full HTTPS URL like https://your-domain.example",
            settings.TELEGRAM_WEBHOOK_URL,
        )
        return False

    bot = get_bot()
    path = parsed.path.rstrip("/")
    webhook_suffix = "/api/v1/webhook/telegram"
    if path.endswith(webhook_suffix):
        pass
    elif path.endswith("/webhook/telegram"):
        path = f"{path[:-len('/webhook/telegram')]}{webhook_suffix}"
    elif path.endswith("/api/v1"):
        path = f"{path}/webhook/telegram"
    elif path.endswith("/webhook"):
        path = f"{path[:-len('/webhook')]}{webhook_suffix}"
    else:
        path = f"{path}{webhook_suffix}"
    webhook_url = parsed._replace(path=path, query="", fragment="").geturl()

    try:
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
        logger.info("Telegram webhook configured at %s", webhook_url)
        return True

    except Exception as e:
        logger.error(
            "Failed to set Telegram webhook for %s: %s (%s)",
            webhook_url,
            type(e).__name__,
            e,
        )
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


async def handle_telegram_update(update_data: dict[str, Any]) -> None:
    """
    Handle a Telegram update directly (without FastAPI).

    Args:
        update_data: Raw update data from Telegram
    """
    await process_update(update_data)


webhook_router = router

__all__ = [
    "handle_telegram_update",
    "process_update",
    "remove_webhook",
    "router",
    "set_webhook",
    "webhook_router",
]
