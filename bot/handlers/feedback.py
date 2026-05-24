# ============================
# WOLLOYEWA STORE BOT - FEEDBACK HANDLER
# ============================
"""Telegram bot feedback and rating handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from core.logger import logger
from apps.support.services import TicketService
from infrastructure.database.session import get_db_session

# Conversation states
WAITING_RATING, WAITING_MESSAGE = range(2)


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /feedback command.
    
    Starts the feedback conversation.
    """
    await update.message.reply_text(
        "💬 *ግብረ መልስ ለመስጠት እንመሰግናለን!*\n\n"
        "እባክዎ አገልግሎታችንን ይገምግሙ።",
        parse_mode="Markdown"
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
        [InlineKeyboardButton("❌ ሰርዝ", callback_data="feedback_cancel")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📊 *ደረጃ ይስጡ:*\n(1 = በጣም መጥፎ, 5 = በጣም ጥሩ)",
        parse_mode="Markdown",
        reply_markup=reply_markup
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
        [InlineKeyboardButton("❌ ሰርዝ", callback_data="feedback_cancel")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "📊 *ደረጃ ይስጡ:*\n(1 = በጣም መጥፎ, 5 = በጣም ጥሩ)",
        parse_mode="Markdown",
        reply_markup=reply_markup
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
        await query.message.edit_text("❌ ግብረ መልስ ተሰርዟል።")
        return ConversationHandler.END
    
    # Extract rating
    rating = int(query.data.split("_")[1])
    context.user_data["feedback_rating"] = rating
    
    # Show rating feedback
    rating_messages = {
        1: "😞 አዝነናል አገልግሎታችን እንዳላረካዎት። እባክዎ ችግሩን ይግለጹ።",
        2: "😕 አገልግሎታችንን ማሻሻል እንደሚፈልግ ተገንዝበናል። እባክዎ ምን እንደሚሻሻል ይንገሩን።",
        3: "😐 አገልግሎታችንን በአማካይ ደረጃ ሰጥተውናል። እባክዎ ሀሳብዎን ያካፍሉን።",
        4: "🙂 አገልግሎታችንን እንደወደዱት ደስ ብሎናል! እባክዎ ተጨማሪ አስተያየት ይስጡ።",
        5: "😊 አገልግሎታችንን ስለወደዱት እናመሰግናለን! እባክዎ ልምድዎን ያጋሩን።",
    }
    
    await query.message.edit_text(
        f"{rating_messages.get(rating, 'እባክዎ አስተያየትዎን ይላኩ።')}\n\n"
        f"✏️ አስተያየትዎን ይጻፉ (በአንድ መልዕክት):",
        parse_mode="Markdown"
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
    message_text = update.message.text
    rating = context.user_data.get("feedback_rating", 0)
    user_id = update.effective_user.id
    
    # Create support ticket for feedback
    async for db in get_db_session():
        ticket_service = TicketService(db)
        
        # Create ticket
        ticket = await ticket_service.create_ticket(
            user_id=user_id,
            subject=f"User Feedback - Rating {rating}/5",
            message=f"Rating: {rating}/5\n\nFeedback: {message_text}",
            priority="low",
        )
        
        break
    
    logger.info(f"Feedback received from user {user_id}: rating {rating}/5")
    
    # Send confirmation
    await update.message.reply_text(
        "✅ *ግብረ መልስዎ ተልኳል!*\n\n"
        "አመሰግናለሁ ጊዜዎን ስለሰጡን። አስተያየትዎ አገልግሎታችንን ለማሻሻል ይረዳናል።\n\n"
        "ተጨማሪ እገዛ ከፈለጉ እባክዎ ድጋፍን ያግኙ።",
        parse_mode="Markdown"
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
    await update.message.reply_text("❌ ግብረ መልስ ተሰርዟል።")
    return ConversationHandler.END


__all__ = [
    "feedback_command",
    "start_feedback",
    "rating_callback",
    "message_handler",
    "cancel_feedback",
    "WAITING_RATING",
    "WAITING_MESSAGE",
]