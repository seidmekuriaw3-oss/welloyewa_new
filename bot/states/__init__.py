# ============================
# WOLLOYEWA STORE BOT - STATES MODULE
# ============================
"""Conversation state definitions for bot handlers."""

from bot.states.order_states import (
    OrderStates,
    SELECT_ADDRESS,
    SELECT_PAYMENT,
    CONFIRM_ORDER,
    ORDER_COMPLETED,
    CART_STATES,
)
from bot.states.auth_states import (
    AuthStates,
    AWAITING_PHONE,
    AWAITING_OTP,
    AWAITING_EMAIL,
    AUTH_STATES,
)
from bot.states.support_states import (
    SupportStates,
    AWAITING_TICKET_SUBJECT,
    AWAITING_TICKET_MESSAGE,
    AWAITING_TICKET_CATEGORY,
    SUPPORT_STATES,
)

__all__ = [
    # Order states
    "OrderStates",
    "SELECT_ADDRESS",
    "SELECT_PAYMENT",
    "CONFIRM_ORDER",
    "ORDER_COMPLETED",
    "CART_STATES",
    # Auth states
    "AuthStates",
    "AWAITING_PHONE",
    "AWAITING_OTP",
    "AWAITING_EMAIL",
    "AUTH_STATES",
    # Support states
    "SupportStates",
    "AWAITING_TICKET_SUBJECT",
    "AWAITING_TICKET_MESSAGE",
    "AWAITING_TICKET_CATEGORY",
    "SUPPORT_STATES",
]