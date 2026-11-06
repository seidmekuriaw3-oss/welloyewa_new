# ============================
# WOLLOYEWA STORE BOT - BROADCASTER HANDLER
# ============================
"""Telegram bot broadcast message handler for admin announcements."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from bot.handlers.text_routing import mark_text_message_handled
from core.config import settings
from core.logger import logger


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id in settings.admin_ids_list)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /broadcast command (admin only).

    Starts broadcast message flow.
    """
    # Check admin permission
    if not _is_admin(update):
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
        "📢 *የማሰራጨት አማራጭ*\n\n" "ለማን መልዕክት መላክ ይፈልጋሉ?\n\n" "ማስታወሻ: መልዕክቱ ለሁሉም ተመራጭ ተጠቃሚዎች ይላካል።",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle broadcast type selection.
    """
    if not _is_admin(update):
        await update.callback_query.answer("ፈቃድ የለዎትም።", show_alert=True)
        return
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
        parse_mode="Markdown",
    )

    context.user_data["awaiting_broadcast_message"] = True


async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle broadcast message input and send broadcasts.
    """
    if not _is_admin(update):
        context.user_data.pop("awaiting_broadcast_message", None)
        return
    if not context.user_data.get("awaiting_broadcast_message"):
        return

    mark_text_message_handled(update, context)
    message_text = (update.message.text or "").strip()
    if not message_text or len(message_text) > 4000:
        await update.message.reply_text(
            "መልዕክቱ ባዶ መሆን የለበትም፤ ከ4,000 ቁምፊ በታች ያድርጉት።"
        )
        return
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
        f"---\n{escape_markdown(message_text, version=1)}\n---\n\n"
        f"መልዕክቱን መላክ ይፈልጋሉ?",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )

    context.user_data["broadcast_message"] = message_text


async def broadcast_send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Confirm and send broadcast message.
    """
    if not _is_admin(update):
        await update.callback_query.answer("ፈቃድ የለዎትም።", show_alert=True)
        return
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
    if not message:
        await query.message.edit_text("❌ የማሰራጫ መልዕክት አልተገኘም። እንደገና ይጀምሩ።")
        return

    try:
        from infrastructure.workers.tasks import send_user_broadcast_task

        send_user_broadcast_task.delay(broadcast_type, message)
    except Exception as exc:
        logger.exception("Could not queue admin broadcast")
        await query.message.edit_text(
            f"❌ ማሰራጨቱን ማስጀመር አልተቻለም ({type(exc).__name__})። እንደገና ይሞክሩ።"
        )
        return

    await query.message.edit_text(
        "✅ ማሰራጨቱ በጀርባ ሂደት ተጀምሯል። ሂደቱ ሲጠናቀቅ የውጤት ማጠቃለያ በስርዓት ሎግ ይመዘገባል።"
    )

    # Clean up
    context.user_data.pop("awaiting_broadcast_message", None)
    context.user_data.pop("broadcast_message", None)
    context.user_data.pop("broadcast_type", None)


__all__ = [
    "broadcast_callback",
    "broadcast_command",
    "broadcast_message_handler",
    "broadcast_send_callback",
]
