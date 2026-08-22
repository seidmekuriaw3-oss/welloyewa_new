# ============================
# WOLLOYEWA STORE BOT - STATES MODULE
# ============================
"""Conversation state definitions for bot handlers."""

from bot.states.auth_states import (
    AUTH_STATES,
    AWAITING_EMAIL,
    AWAITING_OTP,
    AWAITING_PHONE,
    AuthStates,
)
from bot.states.order_states import (
    CART_STATES,
    CONFIRM_ORDER,
    ORDER_COMPLETED,
    SELECT_ADDRESS,
    SELECT_PAYMENT,
    OrderStates,
)
from bot.states.support_states import (
    AWAITING_TICKET_CATEGORY,
    AWAITING_TICKET_MESSAGE,
    AWAITING_TICKET_SUBJECT,
    SUPPORT_STATES,
    SupportStates,
)

__all__ = [
    "AUTH_STATES",
    "AWAITING_EMAIL",
    "AWAITING_OTP",
    "AWAITING_PHONE",
    "AWAITING_TICKET_CATEGORY",
    "AWAITING_TICKET_MESSAGE",
    "AWAITING_TICKET_SUBJECT",
    "CART_STATES",
    "CONFIRM_ORDER",
    "ORDER_COMPLETED",
    "SELECT_ADDRESS",
    "SELECT_PAYMENT",
    "SUPPORT_STATES",
    # Auth states
    "AuthStates",
    # Order states
    "OrderStates",
    # Support states
    "SupportStates",
]
