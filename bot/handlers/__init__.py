# ============================
# WOLLOYEWA STORE BOT - HANDLERS MODULE
# ============================
"""Telegram bot handlers for all user interactions."""

from telegram.ext import Application

from core.logger import logger

from . import (
    broadcaster,
    cart,
    catalog,
    checkout,
    deep_linking,
    errors,
    feedback,
    location,
    profile,
    search,
    start,
    wishlist,
)

try:
    from .admin import (
        dashboard,
        orders_admin,
        products_admin,
        reports,
        users_admin,
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
    "broadcaster",
    "cart",
    "catalog",
    "checkout",
    # Admin
    "dashboard",
    "deep_linking",
    "errors",
    "feedback",
    "location",
    "orders_admin",
    "products_admin",
    "profile",
    "register_handlers",
    "reports",
    "search",
    "start",
    "users_admin",
    "wishlist",
]
