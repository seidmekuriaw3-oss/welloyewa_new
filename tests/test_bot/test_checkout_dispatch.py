"""Regression tests for Telegram checkout conversation routing."""

from unittest.mock import Mock

from telegram.ext import CallbackQueryHandler, ConversationHandler, MessageHandler

from bot.dispatcher import setup_dispatcher
from bot.handlers import cart, checkout


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
