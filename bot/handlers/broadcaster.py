# ============================
# WOLLOYEWA STORE BOT - BROADCASTER HANDLER
# ============================
"""Telegram bot broadcast message handler for admin announcements."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from core.config import settings
from apps.users.services import UserService
from infrastructure.database.session import get_db_session
from infrastructure.queues.task_deduplicator import deduplicate_task


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /broadcast command (admin only).
    
    Starts broadcast message flow.
    """
    user_id = update.effective_user.id
    
    # Check admin permission
    if user_id not in settings.admin_ids_list:
        await update.message.reply_text("❌ ይህን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም።")
        return
    
    keyboard = [
        [InlineKeyboardButton("📢 ለሁሉም ተጠቃሚዎች", callback_data="broadcast_all")],
        [InlineKeyboardButton("👥 ለንቁ ተጠቃሚዎች", callback_data="broadcast_active")],
        [InlineKeyboardButton("🆕 ለአዳዲስ ተጠቃሚዎች", callback_data="broadcast_new")],
        [InlineKeyboardButton("🏪 ለሻጮች", callback_data="broadcast_vendors")],
        [InlineKeyboardButton("❌ ሰርዝ", callback_data="broadcast_cancel")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📢 *የማሰራጨት አማራጭ*\n\n"
        "ለማን መልዕክት መላክ ይፈልጋሉ?\n\n"
        "ማስታወሻ: መልዕክቱ ለሁሉም ተመራጭ ተጠቃሚዎች ይላካል።",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle broadcast type selection.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast_cancel":
        await query.message.edit_text("❌ ማሰራጨት ተሰርዟል።")
        return
    
    # Store broadcast type
    context.user_data["broadcast_type"] = query.data.replace("broadcast_", "")
    
    await query.message.edit_text(
        "📢 *መልዕክት ያስገቡ*\n\n"
        "እባክዎ ለማሰራጨት የሚፈልጉትን መልዕክት ይላኩ።\n\n"
        "ማስታወሻ: መልዕክቱ ለሁሉም ተመራጭ ተጠቃሚዎች በአንድ ጊዜ ይላካል።",
        parse_mode="Markdown"
    )
    
    context.user_data["awaiting_broadcast_message"] = True


async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle broadcast message input and send broadcasts.
    """
    if not context.user_data.get("awaiting_broadcast_message"):
        return
    
    message_text = update.message.text
    broadcast_type = context.user_data.get("broadcast_type", "all")
    
    # Confirm before sending
    keyboard = [
        [InlineKeyboardButton("✅ አዎ, ላክ", callback_data="broadcast_send")],
        [InlineKeyboardButton("❌ አይ, ሰርዝ", callback_data="broadcast_cancel")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📢 *ማሰራጨት ማረጋገጫ*\n\n"
        f"ወደ *{broadcast_type.upper()}* ተጠቃሚዎች የሚላክ መልዕክት:\n\n"
        f"---\n{message_text}\n---\n\n"
        f"መልዕክቱን መላክ ይፈልጋሉ?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    context.user_data["broadcast_message"] = message_text


async def broadcast_send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Confirm and send broadcast message.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data != "broadcast_send":
        await query.message.edit_text("❌ ማሰራጨት ተሰርዟል።")
        context.user_data.pop("awaiting_broadcast_message", None)
        context.user_data.pop("broadcast_message", None)
        context.user_data.pop("broadcast_type", None)
        return
    
    message = context.user_data.get("broadcast_message")
    broadcast_type = context.user_data.get("broadcast_type", "all")
    
    await query.message.edit_text("📢 መልዕክቱ በማሰራጨት ላይ... እባክዎ ይጠብቁ...")
    
    # Get target users
    async for db in get_db_session():
        user_service = UserService(db)
        
        if broadcast_type == "all":
            users = await user_service.user_repo.get_all(filters={"is_active": True})
        elif broadcast_type == "active":
            users = await user_service.user_repo.get_active_users(limit=10000)
        elif broadcast_type == "new":
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=30)
            users = await user_service.user_repo.get_all(filters={"created_at__gte": cutoff})
        elif broadcast_type == "vendors":
            users = await user_service.user_repo.get_all(filters={"role": "vendor", "is_active": True})
        else:
            users = []
        
        break
    
    # Send messages
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="Markdown"
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user.telegram_id}: {e}")
            fail_count += 1
        
        # Rate limiting delay
        await asyncio.sleep(0.05)
    
    # Send summary
    summary = f"""
📢 *ማሰራጨት ተጠናቋል!*

📊 *ውጤት:*
• ✅ የተሳካ: {success_count}
• ❌ ያልተሳካ: {fail_count}
• 👥 ጠቅላላ: {len(users)}

📝 *ተጠቃሚዎች:* {broadcast_type.upper()}
    """
    
    await query.message.edit_text(summary, parse_mode="Markdown")
    
    # Clean up
    context.user_data.pop("awaiting_broadcast_message", None)
    context.user_data.pop("broadcast_message", None)
    context.user_data.pop("broadcast_type", None)


import asyncio

__all__ = [
    "broadcast_command",
    "broadcast_callback",
    "broadcast_message_handler",
    "broadcast_send_callback",
]