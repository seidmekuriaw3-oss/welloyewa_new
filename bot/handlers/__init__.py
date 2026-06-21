# ============================
# WOLLOYEWA STORE BOT - HANDLERS MODULE
# ============================
"""Telegram bot handlers for all user interactions."""

from telegram.ext import Application

from core.logger import logger

from . import (
    start,
    catalog,
    cart,
    checkout,
    profile,
    feedback,
    search,
    wishlist,
    location,
    deep_linking,
    broadcaster,
    errors,
)

try:
    from .admin import (
        dashboard,
        products_admin,
        orders_admin,
        users_admin,
        reports,
    )
except Exception as e:
    logger.warning(f"Failed to import admin handlers; admin commands disabled: {e}")
    dashboard = None
    products_admin = None
    orders_admin = None
    users_admin = None
    reports = None

async def register_handlers(application: Application) -> None:
    """
    Register all bot handlers with the Application instance.
    This ensures the dispatcher is configured before bot startup.
    """
    from bot.dispatcher import setup_dispatcher

    setup_dispatcher(application)
    return None

__all__ = [
    "register_handlers",
    "start",
    "catalog",
    "cart",
    "checkout",
    "profile",
    "feedback",
    "search",
    "wishlist",
    "location",
    "deep_linking",
    "broadcaster",
    "errors",
    # Admin
    "dashboard",
    "products_admin",
    "orders_admin",
    "users_admin",
    "reports",
]