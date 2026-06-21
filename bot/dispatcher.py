# ============================
# WOLLOYEWA STORE BOT - BOT DISPATCHER
# ============================
"""Telegram bot dispatcher and handler registration."""

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

from bot.middlewares import (
    auth_middleware,
    analytics_middleware,
    throttling_middleware,
    i18n_middleware,
    logging_middleware,
    role_check_middleware,
)


def setup_dispatcher(application: Application) -> Application:
    """
    Set up the dispatcher with all handlers and middlewares.
    
    Args:
        application: Telegram Application instance
        
    Returns:
        Configured Application instance
    """
    logger.info("Setting up bot dispatcher...")
    
    # Import handlers lazily to avoid package import cycles
    from bot.handlers import (
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

    dashboard = products_admin = orders_admin = users_admin = reports = None
    try:
        from bot.handlers.admin import (
            dashboard,
            products_admin,
            orders_admin,
            users_admin,
            reports,
        )
    except Exception as e:
        logger.warning(f"Failed to import admin handlers; admin commands disabled: {e}")

    # Register middlewares
    _register_middlewares(application)
    
    # Register command handlers
    _register_command_handlers(application, start, catalog, cart, checkout, profile, feedback, search, wishlist, location, deep_linking, broadcaster, errors)
    
    # Register callback query handlers
    _register_callback_handlers(application, catalog, cart, checkout, profile, wishlist, search, dashboard, products_admin, orders_admin)
    
    # Register message handlers
    _register_message_handlers(application)
    
    # Register conversation handlers
    _register_conversation_handlers(application)
    
    # Register error handler
    application.add_error_handler(errors.error_handler)
    
    logger.info("Bot dispatcher setup complete")
    
    return application


def _register_middlewares(application: Application) -> None:
    """Register middleware handlers."""
    # Note: python-telegram-bot doesn't have built-in middleware
    # We implement middleware logic within handlers or use decorators
    
    # Logging middleware is applied via error handler and custom decorators
    logger.info("Middlewares registered")


def _register_command_handlers(application: Application, start, catalog, cart, checkout, profile, feedback, search, wishlist, location, deep_linking, broadcaster, errors) -> None:
    """Register command handlers."""
    
    # Public commands
    application.add_handler(CommandHandler("start", start.start_command))
    application.add_handler(CommandHandler("help", start.help_command))
    application.add_handler(CommandHandler("menu", catalog.menu_command))
    application.add_handler(CommandHandler("search", search.search_command))
    application.add_handler(CommandHandler("cart", cart.cart_command))
    application.add_handler(CommandHandler("checkout", checkout.checkout_command))
    application.add_handler(CommandHandler("profile", profile.profile_command))
    application.add_handler(CommandHandler("orders", profile.orders_command))
    application.add_handler(CommandHandler("wishlist", wishlist.wishlist_command))
    application.add_handler(CommandHandler("feedback", feedback.feedback_command))
    application.add_handler(CommandHandler("location", location.location_command))
    application.add_handler(CommandHandler("deep_link", deep_linking.deep_link_command))
    
    # Admin commands
    if dashboard is not None:
        application.add_handler(CommandHandler("admin", dashboard.admin_command))
        application.add_handler(CommandHandler("stats", dashboard.stats_command))
    application.add_handler(CommandHandler("broadcast", broadcaster.broadcast_command))
    
    logger.info("Command handlers registered")


def _register_callback_handlers(application: Application, catalog, cart, checkout, profile, wishlist, search, dashboard, products_admin, orders_admin) -> None:
    """Register callback query handlers."""
    
    application.add_handler(CallbackQueryHandler(catalog.category_callback, pattern="^cat_"))
    application.add_handler(CallbackQueryHandler(catalog.product_callback, pattern="^prod_"))
    application.add_handler(CallbackQueryHandler(cart.cart_callback, pattern="^cart_"))
    application.add_handler(CallbackQueryHandler(checkout.checkout_callback, pattern="^checkout_"))
    application.add_handler(CallbackQueryHandler(profile.profile_callback, pattern="^profile_"))
    application.add_handler(CallbackQueryHandler(wishlist.wishlist_callback, pattern="^wish_"))
    application.add_handler(CallbackQueryHandler(search.search_callback, pattern="^search_"))
    
    # Admin callbacks
    if dashboard is not None:
        application.add_handler(CallbackQueryHandler(dashboard.admin_callback, pattern="^admin_"))
    if products_admin is not None:
        application.add_handler(CallbackQueryHandler(products_admin.product_admin_callback, pattern="^prod_admin_"))
    if orders_admin is not None:
        application.add_handler(CallbackQueryHandler(orders_admin.order_admin_callback, pattern="^order_admin_"))
    
    logger.info("Callback handlers registered")


def _register_message_handlers(application: Application) -> None:
    """Register message handlers."""
    
    # Text message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, catalog.text_message_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^/'), start.unknown_command))
    
    # Location handler
    application.add_handler(MessageHandler(filters.LOCATION, location.location_message_handler))
    
    # Contact handler
    application.add_handler(MessageHandler(filters.CONTACT, profile.contact_handler))
    
    logger.info("Message handlers registered")


def _register_conversation_handlers(application: Application) -> None:
    """Register conversation handlers."""
    
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


def register_all_handlers(application: Application) -> None:
    """Alias for setup_dispatcher."""
    return setup_dispatcher(application)


async def process_update(application: Application, update) -> None:
    """
    Process an update through the dispatcher.
    
    Args:
        application: Application instance
        update: Update object
    """
    await application.process_update(update)


__all__ = ["setup_dispatcher", "register_all_handlers", "process_update"]