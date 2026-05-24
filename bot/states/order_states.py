# ============================
# WOLLOYEWA STORE BOT - ORDER STATES
# ============================
"""Conversation states for order processing."""

from enum import IntEnum


class OrderStates(IntEnum):
    """Order conversation states."""
    
    # Address selection states
    SELECT_ADDRESS = 1
    ADD_NEW_ADDRESS = 2
    EDIT_ADDRESS = 3
    
    # Payment states
    SELECT_PAYMENT = 4
    PROCESSING_PAYMENT = 5
    
    # Order confirmation states
    CONFIRM_ORDER = 6
    ORDER_PLACED = 7
    ORDER_COMPLETED = 8
    
    # Tracking states
    TRACK_ORDER = 9
    VIEW_ORDER_DETAILS = 10
    
    # Refund states
    REQUEST_REFUND = 11
    REFUND_REASON = 12
    REFUND_CONFIRM = 13


# State constants for easier imports
SELECT_ADDRESS = OrderStates.SELECT_ADDRESS
SELECT_PAYMENT = OrderStates.SELECT_PAYMENT
CONFIRM_ORDER = OrderStates.CONFIRM_ORDER
ORDER_COMPLETED = OrderStates.ORDER_COMPLETED

# Cart related states
CART_STATES = {
    "viewing": "cart_viewing",
    "editing": "cart_editing",
    "checkout": "cart_checkout",
}

__all__ = [
    "OrderStates",
    "SELECT_ADDRESS",
    "SELECT_PAYMENT",
    "CONFIRM_ORDER",
    "ORDER_COMPLETED",
    "CART_STATES",
]