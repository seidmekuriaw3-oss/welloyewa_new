# ============================
# WOLLOYEWA STORE BOT - TELEGRAM BOT MODULE
# ============================
"""Telegram bot module for customer interaction and order management."""

from bot.bot_instance import (
    bot,
    dispatcher,
    init_bot,
    shutdown_bot,
    get_bot,
    get_dispatcher,
)
from bot.webhooks import (
    webhook_router,
    set_webhook,
    remove_webhook,
    handle_telegram_update,
)
from bot.dispatcher import (
    setup_dispatcher,
    register_all_handlers,
    process_update,
)

__all__ = [
    # Bot instance
    "bot",
    "dispatcher",
    "init_bot",
    "shutdown_bot",
    "get_bot",
    "get_dispatcher",
    # Webhooks
    "webhook_router",
    "set_webhook",
    "remove_webhook",
    "handle_telegram_update",
    # Dispatcher
    "setup_dispatcher",
    "register_all_handlers",
    "process_update",
]