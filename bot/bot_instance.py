# ============================
# WOLLOYEWA STORE BOT - TELEGRAM BOT INSTANCE
# ============================
"""Telegram bot initialization and configuration."""

import logging
from typing import Optional

from telegram import Bot, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    PicklePersistence,
)

from core.config import settings
from core.logger import logger

# Global bot instances
_bot: Optional[Bot] = None
_application: Optional[Application] = None


async def init_bot() -> Application:
    """
    Initialize the Telegram bot application.
    
    Returns:
        Configured Application instance
    """
    global _application, _bot
    
    if _application is not None:
        return _application
    
    logger.info("Initializing Telegram bot...")
    
    # Configure persistence for conversation states
    persistence = PicklePersistence(
        filepath="bot_data.pickle",
        store_bot_data=True,
        store_user_data=True,
        store_chat_data=True,
    )
    
    # Build application
    _application = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .persistence(persistence)
        .build()
    )
    
    _bot = _application.bot
    
    logger.info(f"Bot initialized: {await _bot.get_me()}")
    
    return _application


async def shutdown_bot() -> None:
    """Shutdown the Telegram bot gracefully."""
    global _application
    
    if _application:
        logger.info("Shutting down bot...")
        await _application.shutdown()
        _application = None
        logger.info("Bot shutdown complete")


def get_bot() -> Bot:
    """Get the bot instance."""
    if _bot is None:
        raise RuntimeError("Bot not initialized. Call init_bot() first.")
    return _bot


def get_dispatcher():
    """Get the dispatcher instance."""
    if _application is None:
        raise RuntimeError("Bot not initialized. Call init_bot() first.")
    return _application


__all__ = ["init_bot", "shutdown_bot", "get_bot", "get_dispatcher"]