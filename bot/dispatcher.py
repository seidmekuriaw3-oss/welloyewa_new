#!/usr/bin/env python3
"""Telegram bot dispatcher - registers all handlers and middlewares."""

import re
from functools import partial

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from bot.keyboards.reply import main_reply_button_actions
from bot.middlewares.auth import ensure_user_registered
from core.logger import logger


def setup_dispatcher(application: Application) -> Application:
    """Set up the dispatcher with all handlers and middlewares."""
    logger.info("Setting up bot dispatcher...")
    text_message_filter = (
        filters.UpdateType.MESSAGE & filters.TEXT & ~filters.COMMAND
    )
    non_text_message_filter = (
        filters.UpdateType.MESSAGE & filters.ALL & ~filters.COMMAND & ~filters.TEXT
    )
    main_reply_filter = filters.Regex(
        re.compile(
            "^(?:"
            + "|".join(re.escape(label) for label in main_reply_button_actions())
            + ")$"
        )
    )

    # ── Import all handler modules ──────────────────────────────────────────
    from bot.handlers import (
        account_recovery,
        broadcaster,
        cart,
        catalog,
        checkout,
        conversation_navigation,
        deep_linking,
        errors,
        feedback,
        location,
        profile,
        search,
        start,
        vendor,
        vendor_registration,
        wishlist,
    )

    # Admin handlers (optional)
    dashboard = products_admin = orders_admin = None
    admin_input = None
    try:
        from bot.handlers.admin import (
            admin_input,
            dashboard,
            orders_admin,
            products_admin,
        )
    except Exception as e:
        logger.warning(f"Admin handlers disabled: {e}")

    # ── MIDDLEWARE (group -1, runs before every other handler) ───────────────
    # ensure_user_registered creates the DB record for new users and populates
    # context.user_data["user_id"] / ["user_role"] / ["user"] for all handlers.
    application.add_handler(TypeHandler(Update, ensure_user_registered), group=-1)
    logger.info("Auth middleware registered (group -1)")

    # Register vendor onboarding before other conversations so its active step
    # receives text/documents even when another conversation was previously open.
    vendor_states = {
        step: [
            CallbackQueryHandler(
                vendor_registration.application_callback,
                pattern="^vendor_application_cancel$",
            ),
            CallbackQueryHandler(
                vendor_registration.application_navigation_callback,
                pattern="^vendor_application_back$",
            ),
            CallbackQueryHandler(
                vendor_registration.application_choice_callback,
                pattern="^vendor_choice_",
            ),
            *(
                [
                    MessageHandler(
                        filters.UpdateType.MESSAGE
                        & (filters.PHOTO | filters.Document.ALL),
                        partial(vendor_registration.handle_document, step_index=step),
                    )
                ]
                if step == 2
                else []
            ),
            MessageHandler(
                main_reply_filter,
                conversation_navigation.cancel_to_menu,
            ),
            MessageHandler(
                text_message_filter,
                partial(vendor_registration.handle_text, step_index=step),
            ),
        ]
        for step in range(vendor_registration.VENDOR_STEP_COUNT)
    }
    vendor_states[vendor_registration.VENDOR_CONFIRM_STATE] = [
        CallbackQueryHandler(
            vendor_registration.application_callback,
            pattern="^vendor_application_(confirm|cancel)$",
        ),
        CallbackQueryHandler(
            vendor_registration.application_navigation_callback,
            pattern="^vendor_application_back$",
        ),
        CallbackQueryHandler(
            vendor_registration.application_choice_callback,
            pattern="^vendor_choice_",
        ),
        MessageHandler(
            main_reply_filter,
            conversation_navigation.cancel_to_menu,
        ),
        MessageHandler(
            text_message_filter,
            partial(
                vendor_registration.handle_text,
                step_index=vendor_registration.VENDOR_CONFIRM_STATE,
            ),
        ),
    ]
    vendor_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                vendor_registration.start_application,
                pattern="^profile_become_vendor$",
            )
        ],
        states=vendor_states,
        fallbacks=[
            CommandHandler("cancel", vendor_registration.cancel_application),
        ],
        allow_reentry=True,
        name="vendor_registration_conversation",
        persistent=True,
    )
    application.add_handler(vendor_conversation, group=0)
    logger.info("Vendor registration conversation registered")

    # ── Onboarding callbacks (highest priority — before menu and catalog) ────
    # Handles language selection during new-user onboarding (Step 1)
    application.add_handler(
        CallbackQueryHandler(start.onboard_language_callback, pattern="^onboard_lang_")
    )

    # ── Command handlers ─────────────────────────────────────────────────────
    application.add_handler(CommandHandler("start", start.start_command))
    application.add_handler(CommandHandler("help", start.help_command))
    application.add_handler(
        CommandHandler("resetpassword", account_recovery.reset_password_command)
    )
    application.add_handler(CommandHandler("menu", catalog.menu_command))
    # NOTE: /search and /checkout are entry-points of ConversationHandlers below;
    # registering them again here would shadow the conversation — omitted.
    application.add_handler(CommandHandler("cart", cart.cart_command))
    application.add_handler(CommandHandler("profile", profile.profile_command))

    application.add_handler(CommandHandler("orders", profile.orders_command))
    application.add_handler(CommandHandler("wishlist", wishlist.wishlist_command))
    application.add_handler(CommandHandler("location", location.location_command))
    application.add_handler(CommandHandler("deep_link", deep_linking.deep_link_command))
    application.add_handler(CommandHandler("broadcast", broadcaster.broadcast_command))
    application.add_handler(CommandHandler("shop", start.shop_command))

    if dashboard is not None:
        application.add_handler(CommandHandler("admin", dashboard.admin_command))
        application.add_handler(CommandHandler("stats", dashboard.stats_command))
    if admin_input is not None:
        application.add_handler(CommandHandler("addphoto", admin_input.addphoto_command))

    logger.info("Command handlers registered")

    # ── Callback query handlers ───────────────────────────────────────────────
    # Category pagination (must come before generic cat_ so it matches first)
    application.add_handler(
        CallbackQueryHandler(catalog.category_page_callback, pattern="^cat_page_")
    )
    application.add_handler(CallbackQueryHandler(catalog.category_callback, pattern="^cat_"))
    # Product detail & add-to-cart / add-to-wishlist from product view
    application.add_handler(
        CallbackQueryHandler(catalog.product_callback, pattern="^prod_(?!admin_|search_)")
    )
    # Leave checkout callbacks for the Checkout ConversationHandler below.
    application.add_handler(
        CallbackQueryHandler(cart.cart_callback, pattern="^cart_(?!checkout$)")
    )
    application.add_handler(CallbackQueryHandler(cart.cart_callback, pattern="^add_to_cart_"))
    application.add_handler(CallbackQueryHandler(profile.profile_callback, pattern="^profile_"))
    application.add_handler(
        CallbackQueryHandler(profile.orders_page_callback, pattern="^orders_page_")
    )
    application.add_handler(CallbackQueryHandler(vendor.vendor_callback, pattern="^vendor_"))
    # Language change from Profile screen (lang_am / lang_en / lang_om)
    application.add_handler(CallbackQueryHandler(profile.language_callback, pattern="^lang_"))
    application.add_handler(
        CallbackQueryHandler(location.location_callback, pattern="^(share_location|enter_city)$")
    )
    application.add_handler(
        CallbackQueryHandler(
            broadcaster.broadcast_callback, pattern="^broadcast_(all|active|new|vendors|cancel)$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(broadcaster.broadcast_send_callback, pattern="^broadcast_send$")
    )
    application.add_handler(
        CallbackQueryHandler(start.noop_callback, pattern="^(noop|out_of_stock)$")
    )
    # Wishlist: both wish_ (legacy) and wishlist_ / add_to_wishlist_
    application.add_handler(CallbackQueryHandler(wishlist.wishlist_callback, pattern="^wish_"))
    application.add_handler(CallbackQueryHandler(wishlist.wishlist_callback, pattern="^wishlist_"))
    application.add_handler(
        CallbackQueryHandler(wishlist.wishlist_callback, pattern="^add_to_wishlist_")
    )
    if dashboard is not None:
        application.add_handler(CallbackQueryHandler(dashboard.admin_callback, pattern="^admin_"))
    if admin_input is not None:
        application.add_handler(
            CallbackQueryHandler(admin_input.addphoto_page_callback, pattern="^addphoto_page_")
        )
    if products_admin is not None:
        application.add_handler(
            CallbackQueryHandler(products_admin.product_admin_callback, pattern="^prod_admin_")
        )
    if orders_admin is not None:
        application.add_handler(
            CallbackQueryHandler(orders_admin.order_admin_callback, pattern="^order_admin_")
        )

    logger.info("Callback handlers registered")

    # ── Conversation handlers ─────────────────────────────────────────────────
    # Checkout conversation
    # Entry: /checkout command OR "cart_checkout" inline button
    checkout_conv = ConversationHandler(
        entry_points=[
            CommandHandler("checkout", checkout.start_checkout),
            CallbackQueryHandler(checkout.start_checkout, pattern="^cart_checkout$"),
        ],
        states={
            checkout.SELECT_ADDRESS: [
                CallbackQueryHandler(
                    conversation_navigation.cancel_to_menu,
                    pattern=conversation_navigation.MENU_BACK_CALLBACK,
                ),
                MessageHandler(
                    conversation_navigation.CANCEL_TEXT_FILTER,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    main_reply_filter,
                    conversation_navigation.cancel_to_menu,
                ),
                CallbackQueryHandler(
                    checkout.address_callback, pattern="^(addr_|checkout_cancel$)"
                ),
                MessageHandler(text_message_filter, checkout.new_address_handler),
                MessageHandler(
                    filters.UpdateType.MESSAGE & filters.LOCATION,
                    checkout.new_address_handler,
                ),
                MessageHandler(
                    non_text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
            ],
            checkout.SELECT_RECIPIENT_NAME: [
                CallbackQueryHandler(
                    conversation_navigation.cancel_to_menu,
                    pattern=conversation_navigation.MENU_BACK_CALLBACK,
                ),
                MessageHandler(
                    conversation_navigation.CANCEL_TEXT_FILTER,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    main_reply_filter,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    text_message_filter,
                    checkout.recipient_name_handler,
                ),
                MessageHandler(
                    non_text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
            ],
            checkout.SELECT_RECIPIENT_PHONE: [
                CallbackQueryHandler(
                    conversation_navigation.cancel_to_menu,
                    pattern=conversation_navigation.MENU_BACK_CALLBACK,
                ),
                MessageHandler(
                    conversation_navigation.CANCEL_TEXT_FILTER,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    main_reply_filter,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    filters.UpdateType.MESSAGE & filters.CONTACT,
                    checkout.recipient_phone_handler,
                ),
                MessageHandler(
                    text_message_filter,
                    checkout.recipient_phone_handler,
                ),
                MessageHandler(
                    non_text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
            ],
            checkout.SELECT_PAYMENT: [
                CallbackQueryHandler(
                    conversation_navigation.cancel_to_menu,
                    pattern=conversation_navigation.MENU_BACK_CALLBACK,
                ),
                MessageHandler(
                    conversation_navigation.CANCEL_TEXT_FILTER,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    main_reply_filter,
                    conversation_navigation.cancel_to_menu,
                ),
                CallbackQueryHandler(
                    checkout.payment_callback, pattern="^(pay_|checkout_cancel$)"
                ),
                MessageHandler(
                    non_text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
                MessageHandler(
                    text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
            ],
            checkout.CONFIRM_ORDER: [
                CallbackQueryHandler(
                    conversation_navigation.cancel_to_menu,
                    pattern=conversation_navigation.MENU_BACK_CALLBACK,
                ),
                MessageHandler(
                    conversation_navigation.CANCEL_TEXT_FILTER,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    main_reply_filter,
                    conversation_navigation.cancel_to_menu,
                ),
                CallbackQueryHandler(
                    checkout.confirm_callback,
                    pattern="^(confirm_|retry_payment$|checkout_cancel$)",
                ),
                MessageHandler(
                    non_text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
                MessageHandler(
                    text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", checkout.cancel_checkout)],
        name="checkout_conversation",
        persistent=True,
    )
    application.add_handler(checkout_conv)

    # Search conversation
    # menu_search is an entry point here, so the next user text is tracked by
    # the conversation and reaches search_query_handler.
    search_conv = ConversationHandler(
        entry_points=[
            CommandHandler("search", search.search_command),
            CallbackQueryHandler(search.start_search, pattern="^menu_search$"),
        ],
        states={
            search.WAITING_QUERY: [
                CallbackQueryHandler(
                    conversation_navigation.cancel_to_menu,
                    pattern=conversation_navigation.MENU_BACK_CALLBACK,
                ),
                MessageHandler(
                    conversation_navigation.CANCEL_TEXT_FILTER,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    main_reply_filter,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(text_message_filter, search.search_query_handler),
                CommandHandler("search", search.start_search),
                MessageHandler(
                    non_text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
            ],
            search.FILTER_RESULTS: [
                CallbackQueryHandler(
                    conversation_navigation.cancel_to_menu,
                    pattern=conversation_navigation.MENU_BACK_CALLBACK,
                ),
                MessageHandler(
                    conversation_navigation.CANCEL_TEXT_FILTER,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    main_reply_filter,
                    conversation_navigation.cancel_to_menu,
                ),
                CallbackQueryHandler(search.filter_callback, pattern="^filter_"),
                CallbackQueryHandler(search.filter_callback, pattern="^search_"),
                CallbackQueryHandler(search.filter_callback, pattern="^sort_"),
                CallbackQueryHandler(search.product_from_search, pattern="^prod_search_"),
                MessageHandler(
                    non_text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
                MessageHandler(
                    text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", search.cancel_search)],
        name="search_conversation",
        persistent=True,
    )
    application.add_handler(search_conv)

    # Keep these after the search conversation so active search callbacks can
    # update its state before the global fallback handles stale result buttons.
    application.add_handler(CallbackQueryHandler(search.filter_callback, pattern="^search_"))
    application.add_handler(CallbackQueryHandler(search.filter_callback, pattern="^sort_"))
    application.add_handler(CallbackQueryHandler(search.filter_callback, pattern="^filter_"))

    # Feedback conversation
    # menu_feedback and review_* are entry points here and retain feedback state.
    feedback_conv = ConversationHandler(
        entry_points=[
            CommandHandler("feedback", feedback.feedback_command),
            CallbackQueryHandler(feedback.start_feedback, pattern="^menu_feedback$"),
            CallbackQueryHandler(feedback.start_feedback, pattern="^review_"),
        ],
        states={
            feedback.WAITING_RATING: [
                CallbackQueryHandler(
                    conversation_navigation.cancel_to_menu,
                    pattern=conversation_navigation.MENU_BACK_CALLBACK,
                ),
                MessageHandler(
                    conversation_navigation.CANCEL_TEXT_FILTER,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    main_reply_filter,
                    conversation_navigation.cancel_to_menu,
                ),
                CallbackQueryHandler(
                    feedback.rating_callback, pattern="^(rate_|feedback_cancel$)"
                ),
                MessageHandler(
                    non_text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
            ],
            feedback.WAITING_MESSAGE: [
                CallbackQueryHandler(
                    conversation_navigation.cancel_to_menu,
                    pattern=conversation_navigation.MENU_BACK_CALLBACK,
                ),
                MessageHandler(
                    conversation_navigation.CANCEL_TEXT_FILTER,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(
                    main_reply_filter,
                    conversation_navigation.cancel_to_menu,
                ),
                MessageHandler(text_message_filter, feedback.message_handler),
                MessageHandler(
                    non_text_message_filter,
                    conversation_navigation.invalid_conversation_input,
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", feedback.cancel_feedback)],
        name="feedback_conversation",
        persistent=True,
    )
    application.add_handler(feedback_conv)

    # Keep this after the conversation entry points so menu_search/menu_feedback
    # are claimed by their conversations and retain their next-message state.
    application.add_handler(CallbackQueryHandler(start.menu_callback, pattern="^menu_"))
    application.add_handler(CallbackQueryHandler(start.unknown_callback))

    logger.info("Conversation handlers registered")

    # ── Message handlers (catch-all, registered last) ─────────────────────────
    # Keep location handling after checkout/search state handlers so location
    # shares meant for an active conversation are not swallowed by the global
    # profile/location fallback.
    application.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE & filters.LOCATION,
            location.location_message_handler,
        ),
        group=1,
    )
    # Contact handler: saves phone on sharing AND completes new-user onboarding
    application.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE & filters.CONTACT, profile.contact_handler
        ),
        group=1,
    )
    application.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE & filters.PHOTO,
            profile.profile_photo_handler,
        ),
        group=1,
    )
    application.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE & filters.Document.ALL,
            profile.profile_photo_handler,
        ),
        group=1,
    )

    # Admin text-input state handler — must run BEFORE the general text handler
    if admin_input is not None:
        application.add_handler(
            MessageHandler(
                text_message_filter,
                admin_input.handle_admin_text_input,
            ),
            group=0,
        )
        # Admin photo handler — intercepts photos when admin is in waiting_product_image state
        application.add_handler(
            MessageHandler(
                filters.PHOTO,
                admin_input.handle_admin_photo_input,
            ),
            group=0,
        )

    application.add_handler(
        MessageHandler(main_reply_filter, start.main_reply_handler),
        group=1,
    )
    application.add_handler(
        MessageHandler(text_message_filter, catalog.text_message_handler), group=1
    )

    logger.info("Message handlers registered")

    # ── Error handler ─────────────────────────────────────────────────────────
    application.add_error_handler(errors.error_handler)

    logger.info("Bot dispatcher setup complete ✓")
    return application


async def process_update(application: Application, update) -> None:
    """Process a Telegram update through the dispatcher."""
    await application.process_update(update)


__all__ = ["process_update", "setup_dispatcher"]
