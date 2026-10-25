"""Shared cancel/back handling for customer conversations."""

import re

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes, ConversationHandler, filters

from bot.handlers.callback_utils import answer_callback_query
from bot.localization import get_language, translate
from bot.handlers.text_routing import mark_text_message_handled
from core.config import settings

CANCEL_TEXT_FILTER = filters.UpdateType.MESSAGE & filters.Regex(
    re.compile(
        r"^\s*(?:(?:❌|🔙)\s*)?(?:cancel|back|menu|ሰርዝ|ወደ ኋላ|ወደ ምናሌ|haqi|deebi'i)\s*$",
        re.IGNORECASE,
    )
)
MENU_BACK_CALLBACK = r"^menu_(?:back|main|start)$"


def _clear_conversation_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in tuple(context.user_data):
        if key.startswith(("checkout_", "search_")) or key == "feedback_rating":
            context.user_data.pop(key, None)


async def cancel_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End the active customer flow and return to the localized main menu."""
    query = update.callback_query
    if query:
        await answer_callback_query(query)
    else:
        mark_text_message_handled(update, context)

    if context.user_data.get("checkout_order_id"):
        from bot.handlers.checkout import _cancel_created_order_if_pending

        await _cancel_created_order_if_pending(update, context)
    _clear_conversation_data(context)

    language = get_language(context)
    text = translate(language, "flow_cancelled")
    from bot.handlers.start import _build_main_menu

    reply_markup = _build_main_menu(
        is_admin=bool(update.effective_user and update.effective_user.id in settings.admin_ids_list),
        lang=language,
    )

    if query and query.message and query.message.text is not None:
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
        except BadRequest as exc:
            if "message is not modified" in str(exc).casefold():
                pass
            elif "there is no text in the message" in str(exc).casefold():
                await query.message.reply_text(text, reply_markup=reply_markup)
            else:
                raise
    elif update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=reply_markup)

    return ConversationHandler.END


async def invalid_conversation_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Give a localized recovery hint for unsupported non-text input in a flow."""
    if update.effective_message and update.effective_message.text:
        mark_text_message_handled(update, context)
    await update.effective_message.reply_text(
        translate(get_language(context), "flow_invalid_input")
    )


__all__ = [
    "CANCEL_TEXT_FILTER",
    "MENU_BACK_CALLBACK",
    "cancel_to_menu",
    "invalid_conversation_input",
]
