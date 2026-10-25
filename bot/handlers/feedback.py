# ============================
# WOLLOYEWA STORE BOT - FEEDBACK HANDLER
# ============================
"""Telegram bot feedback and rating handlers."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.support.services import TicketService
from apps.users.services import UserService
from bot.handlers.text_routing import mark_text_message_handled
from bot.localization import tr
from core.exceptions import NotFoundError
from core.logger import logger
from infrastructure.database.session import transaction_session

# Conversation states
WAITING_RATING, WAITING_MESSAGE = range(2)


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /feedback command.

    Starts the feedback conversation.
    """
    await update.effective_message.reply_text(
        tr(context, "feedback_thanks"), parse_mode="Markdown"
    )

    # Show rating buttons
    keyboard = [
        [
            InlineKeyboardButton("⭐ 1", callback_data="rate_1"),
            InlineKeyboardButton("⭐⭐ 2", callback_data="rate_2"),
            InlineKeyboardButton("⭐⭐⭐ 3", callback_data="rate_3"),
            InlineKeyboardButton("⭐⭐⭐⭐ 4", callback_data="rate_4"),
            InlineKeyboardButton("⭐⭐⭐⭐⭐ 5", callback_data="rate_5"),
        ],
        [InlineKeyboardButton(tr(context, "cancel"), callback_data="feedback_cancel")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        tr(context, "feedback_rate_prompt"), parse_mode="Markdown", reply_markup=reply_markup
    )


async def start_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start the feedback conversation from callback.

    Returns:
        Next conversation state
    """
    query = update.callback_query
    await query.answer()

    # Show rating buttons
    keyboard = [
        [
            InlineKeyboardButton("⭐ 1", callback_data="rate_1"),
            InlineKeyboardButton("⭐⭐ 2", callback_data="rate_2"),
            InlineKeyboardButton("⭐⭐⭐ 3", callback_data="rate_3"),
            InlineKeyboardButton("⭐⭐⭐⭐ 4", callback_data="rate_4"),
            InlineKeyboardButton("⭐⭐⭐⭐⭐ 5", callback_data="rate_5"),
        ],
        [InlineKeyboardButton(tr(context, "cancel"), callback_data="feedback_cancel")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    rating_prompt = tr(context, "feedback_rate_prompt")
    if query.message.text is not None:
        await query.message.edit_text(
            rating_prompt, parse_mode="Markdown", reply_markup=reply_markup
        )
    else:
        await query.message.reply_text(
            rating_prompt, parse_mode="Markdown", reply_markup=reply_markup
        )

    return WAITING_RATING


async def rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle rating selection.

    Args:
        update: Telegram update
        context: Callback context

    Returns:
        Next conversation state
    """
    query = update.callback_query
    await query.answer()

    if query.data == "feedback_cancel":
        await query.message.edit_text(tr(context, "feedback_cancelled"))
        return ConversationHandler.END

    # Extract rating
    rating = int(query.data.split("_")[1])
    if rating not in range(1, 6):
        await query.message.edit_text(tr(context, "feedback_default_prompt"))
        return WAITING_RATING
    context.user_data["feedback_rating"] = rating

    # Show rating feedback
    await query.message.edit_text(
        f"{tr(context, f'feedback_rating_{rating}')}\n\n"
        f"{tr(context, 'feedback_message_prompt')}",
        parse_mode="Markdown",
    )

    return WAITING_MESSAGE


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle feedback message.

    Args:
        update: Telegram update
        context: Callback context

    Returns:
        Next conversation state (END)
    """
    mark_text_message_handled(update, context)
    message_text = update.effective_message.text
    rating = context.user_data.get("feedback_rating", 0)
    telegram_id = update.effective_user.id

    # Create support ticket for feedback
    async with transaction_session() as db:
        user = await UserService(db).get_user_by_telegram(telegram_id)
        if not user:
            raise NotFoundError("User", telegram_id)
        ticket_service = TicketService(db)

        # Create ticket
        await ticket_service.create_ticket(
            user_id=user.id,
            subject=f"User Feedback - Rating {rating}/5",
            message=f"Rating: {rating}/5\n\nFeedback: {message_text}",
            priority="low",
        )

    logger.info(f"Feedback received from user {telegram_id}: rating {rating}/5")

    # Send confirmation
    await update.effective_message.reply_text(
        tr(context, "feedback_sent"),
        parse_mode="Markdown",
    )

    # Clear user data
    context.user_data.pop("feedback_rating", None)

    return ConversationHandler.END


async def cancel_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel the feedback conversation.

    Args:
        update: Telegram update
        context: Callback context

    Returns:
        Next conversation state (END)
    """
    await update.effective_message.reply_text(tr(context, "feedback_cancelled"))
    return ConversationHandler.END


__all__ = [
    "WAITING_MESSAGE",
    "WAITING_RATING",
    "cancel_feedback",
    "feedback_command",
    "message_handler",
    "rating_callback",
    "start_feedback",
]
