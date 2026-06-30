#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram bot dispatcher - registers all handlers and middlewares."""

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from core.config import settings
from core.logger import logger


def setup_dispatcher(application: Application) -> Application:
    """Set up the dispatcher with all handlers and middlewares."""
    logger.info("Setting up bot dispatcher...")

    # ── Import all handler modules ──────────────────────────────────────────
    from bot.handlers import (
        start, catalog, cart, checkout,
        profile, feedback, search, wishlist,
        location, deep_linking, broadcaster, errors,
    )

    # Admin handlers (optional)
    dashboard = products_admin = orders_admin = users_admin = reports = None
    admin_input = None
    try:
        from bot.handlers.admin import (
            dashboard, products_admin, orders_admin, users_admin, reports,
        )
        from bot.handlers.admin import admin_input
    except Exception as e:
        logger.warning(f"Admin handlers disabled: {e}")

    # ── Main menu callback (must be registered FIRST, highest priority) ──────
    application.add_handler(CallbackQueryHandler(start.menu_callback, pattern="^menu_"))

    # ── Command handlers ─────────────────────────────────────────────────────
    application.add_handler(CommandHandler("start",    start.start_command))
    application.add_handler(CommandHandler("help",     start.help_command))
    application.add_handler(CommandHandler("menu",     catalog.menu_command))
    application.add_handler(CommandHandler("search",   search.search_command))
    application.add_handler(CommandHandler("cart",     cart.cart_command))
    application.add_handler(CommandHandler("checkout", checkout.checkout_command))
    application.add_handler(CommandHandler("profile",  profile.profile_command))
    application.add_handler(CommandHandler("orders",   profile.orders_command))
    application.add_handler(CommandHandler("wishlist", wishlist.wishlist_command))
    application.add_handler(CommandHandler("feedback", feedback.feedback_command))
    application.add_handler(CommandHandler("location", location.location_command))
    application.add_handler(CommandHandler("deep_link", deep_linking.deep_link_command))
    application.add_handler(CommandHandler("broadcast", broadcaster.broadcast_command))

    if dashboard is not None:
        application.add_handler(CommandHandler("admin", dashboard.admin_command))
        application.add_handler(CommandHandler("stats", dashboard.stats_command))

    logger.info("Command handlers registered")

    # ── Callback query handlers ───────────────────────────────────────────────
    application.add_handler(CallbackQueryHandler(catalog.category_callback,  pattern="^cat_"))
    application.add_handler(CallbackQueryHandler(catalog.product_callback,   pattern="^prod_"))
    application.add_handler(CallbackQueryHandler(cart.cart_callback,         pattern="^cart_"))
    application.add_handler(CallbackQueryHandler(profile.profile_callback,   pattern="^profile_"))
    application.add_handler(CallbackQueryHandler(wishlist.wishlist_callback, pattern="^wish_"))

    if dashboard is not None:
        application.add_handler(CallbackQueryHandler(dashboard.admin_callback, pattern="^admin_"))
    if products_admin is not None:
        application.add_handler(CallbackQueryHandler(products_admin.product_admin_callback, pattern="^prod_admin_"))
    if orders_admin is not None:
        application.add_handler(CallbackQueryHandler(orders_admin.order_admin_callback, pattern="^order_admin_"))

    logger.info("Callback handlers registered")

    # ── Conversation handlers ─────────────────────────────────────────────────
    # Checkout conversation
    checkout_conv = ConversationHandler(
        entry_points=[CommandHandler("checkout", checkout.start_checkout)],
        states={
            checkout.SELECT_ADDRESS: [
                CallbackQueryHandler(checkout.address_callback, pattern="^addr_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, checkout.new_address_handler),
            ],
            checkout.SELECT_PAYMENT: [
                CallbackQueryHandler(checkout.payment_callback, pattern="^pay_"),
            ],
            checkout.CONFIRM_ORDER: [
                CallbackQueryHandler(checkout.confirm_callback, pattern="^confirm_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", checkout.cancel_checkout)],
        name="checkout_conversation",
        persistent=True,
    )
    application.add_handler(checkout_conv)

    # Search conversation
    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", search.start_search)],
        states={
            search.WAITING_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search.search_query_handler),
            ],
            search.FILTER_RESULTS: [
                CallbackQueryHandler(search.filter_callback, pattern="^filter_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", search.cancel_search)],
        name="search_conversation",
        persistent=True,
    )
    application.add_handler(search_conv)

    # Feedback conversation
    feedback_conv = ConversationHandler(
        entry_points=[CommandHandler("feedback", feedback.start_feedback)],
        states={
            feedback.WAITING_RATING: [
                CallbackQueryHandler(feedback.rating_callback, pattern="^rate_"),
            ],
            feedback.WAITING_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, feedback.message_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", feedback.cancel_feedback)],
        name="feedback_conversation",
        persistent=True,
    )
    application.add_handler(feedback_conv)

    logger.info("Conversation handlers registered")

    # ── Message handlers (catch-all, registered last) ─────────────────────────
    application.add_handler(MessageHandler(filters.LOCATION, location.location_message_handler))
    application.add_handler(MessageHandler(filters.CONTACT,  profile.contact_handler))

    # Admin text-input state handler — must run BEFORE the general text handler
    if admin_input is not None:
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                admin_input.handle_admin_text_input,
            ),
            group=0,
        )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, catalog.text_message_handler),
        group=1,
    )

    logger.info("Message handlers registered")

    # ── Error handler ─────────────────────────────────────────────────────────
    application.add_error_handler(errors.error_handler)

    logger.info("Bot dispatcher setup complete ✓")
    return application


async def process_update(application: Application, update) -> None:
    """Process a Telegram update through the dispatcher."""
    await application.process_update(update)


__all__ = ["setup_dispatcher", "process_update"]
