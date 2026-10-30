"""Regression tests for Telegram checkout conversation routing."""

from functools import partial
from types import SimpleNamespace
from unittest.mock import Mock

from telegram import Update
from telegram.ext import CallbackQueryHandler, ConversationHandler, MessageHandler

from bot.dispatcher import setup_dispatcher
from bot.handlers import cart, checkout, start, vendor_registration
from bot.keyboards.reply import main_reply_button_actions


def test_cart_checkout_button_enters_checkout_conversation():
    application = Mock()
    setup_dispatcher(application)
    handlers = [call.args[0] for call in application.add_handler.call_args_list]

    cart_callback_handler = next(
        handler
        for handler in handlers
        if isinstance(handler, CallbackQueryHandler)
        and handler.callback == cart.cart_callback
        and handler.pattern.pattern.startswith("^cart_")
    )
    checkout_conversation = next(
        handler for handler in handlers if isinstance(handler, ConversationHandler)
        and handler.name == "checkout_conversation"
    )

    assert cart_callback_handler.pattern.match("cart_checkout") is None
    assert any(
        isinstance(handler, CallbackQueryHandler)
        and handler.pattern.match("cart_checkout")
        for handler in checkout_conversation.entry_points
    )
    assert any(
        isinstance(handler, MessageHandler)
        and handler.callback == checkout.recipient_phone_handler
        for handler in checkout_conversation.states[checkout.SELECT_RECIPIENT_PHONE]
    )


def test_vendor_conversation_precedes_other_conversations_and_routes_step_one_text():
    application = Mock()
    setup_dispatcher(application)
    handler_calls = application.add_handler.call_args_list
    handlers = [call.args[0] for call in handler_calls]

    vendor_conversation = next(
        handler
        for handler in handlers
        if isinstance(handler, ConversationHandler)
        and handler.name == "vendor_registration_conversation"
    )
    checkout_conversation = next(
        handler
        for handler in handlers
        if isinstance(handler, ConversationHandler)
        and handler.name == "checkout_conversation"
    )

    assert handlers.index(vendor_conversation) < handlers.index(checkout_conversation)
    assert any(
        isinstance(handler, MessageHandler)
        and isinstance(handler.callback, partial)
        and handler.callback.func == vendor_registration.handle_text
        and handler.callback.keywords["step_index"] == 0
        for handler in vendor_conversation.states[0]
    )

    assert any(
        isinstance(handler, MessageHandler)
        and isinstance(handler.callback, partial)
        and handler.callback.func == vendor_registration.handle_text
        and handler.callback.keywords["step_index"] == 1
        for handler in vendor_conversation.states[1]
    )
    assert any(
        isinstance(handler, CallbackQueryHandler)
        and handler.pattern.match("vendor_choice_category_electronics")
        for handler in vendor_conversation.states[4]
    )
    assert any(
        isinstance(handler, CallbackQueryHandler)
        and handler.pattern.match("vendor_application_back")
        for handler in vendor_conversation.states[vendor_registration.VENDOR_CONFIRM_STATE]
    )
    assert any(
        isinstance(handler, MessageHandler)
        and handler.callback == start.main_reply_handler
        for handler in handlers
    )


def test_dispatcher_routes_every_localized_home_button():
    application = Mock()
    setup_dispatcher(application)
    main_menu_handler = next(
        call.args[0]
        for call in application.add_handler.call_args_list
        if isinstance(call.args[0], MessageHandler)
        and call.args[0].callback == start.main_reply_handler
    )

    for label in main_reply_button_actions():
        update = Mock(spec=Update)
        update.effective_message = SimpleNamespace(text=label)
        assert main_menu_handler.check_update(update) is not None
