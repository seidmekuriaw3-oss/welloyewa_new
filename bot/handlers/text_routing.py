"""Helpers for coordinating text handlers registered in different groups."""

from telegram import Update
from telegram.ext import ContextTypes

_HANDLED_TEXT_UPDATE_ID = "_handled_text_update_id"


def mark_text_message_handled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prevent the later product-search fallback from reprocessing this text."""
    message = getattr(update, "effective_message", None)
    if (
        getattr(update, "callback_query", None) is not None
        or message is None
        or not message.text
        or message.text.startswith("/")
        or getattr(update, "update_id", None) is None
    ):
        return
    context.user_data[_HANDLED_TEXT_UPDATE_ID] = update.update_id


def consume_handled_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Return whether an earlier handler already processed this text update."""
    update_id = getattr(update, "update_id", None)
    handled_update_id = context.user_data.pop(_HANDLED_TEXT_UPDATE_ID, None)
    return update_id is not None and handled_update_id == update_id


__all__ = ["consume_handled_text", "mark_text_message_handled"]
