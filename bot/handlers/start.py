"""Telegram bot start command, welcome message, and main menu callback handler."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from core.logger import logger
from core.config import settings
from apps.users.services import UserService
from infrastructure.database.session import get_db_session


def _build_main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Build the main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🛍️ ምርቶች", callback_data="menu_products"),
            InlineKeyboardButton("🔍 ፈልግ", callback_data="menu_search"),
        ],
        [
            InlineKeyboardButton("🛒 ግዢ ቅርጫት", callback_data="menu_cart"),
            InlineKeyboardButton("👤 ፕሮፋይል", callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton("📦 ትዕዛዞቼ", callback_data="menu_orders"),
            InlineKeyboardButton("⭐ ተመራጮች", callback_data="menu_wishlist"),
        ],
        [
            InlineKeyboardButton("❓ እገዛ", callback_data="menu_help"),
            InlineKeyboardButton("💬 ግብረ መልስ", callback_data="menu_feedback"),
        ],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("🔧 አስተዳደር", callback_data="menu_admin")])
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — register user and show welcome message."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")

    async for db in get_db_session():
        user_service = UserService(db)
        await user_service.get_or_create_user(
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
        )
        break

    welcome_text = (
        "🌟 እንኳን ደህና መጡ ወደ *ዎሎየዋ ስቶር*! 🌟\n\n"
        "የኢትዮጵያ የመጀመሪያው ዘመናዊ የኢ-ኮሜርስ ቴሌግራም ቦት።\n\n"
        "✨ *ባህሪያት:*\n"
        "• 🛍️ ምርቶችን ይመልከቱ እና ይግዙ\n"
        "• 💳 በቀላሉ ይክፈሉ (Chapa፣ Telebirr፣ CBE Birr)\n"
        "• 📦 ትዕዛዞትን ይከታተሉ\n"
        "• ⭐ ግምገማ ያስቀምጡ\n"
        "• 🏪 ሻጭ ለመሆን ያመልክቱ\n\n"
        "📌 ለመጀመር ከዚህ በታች ካሉት ቁልፎች ይምረጡ።"
    )

    is_admin = user.id in settings.admin_ids_list
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=_build_main_menu(is_admin),
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all menu_* callback queries to the right handler."""
    query = update.callback_query
    await query.answer()

    data = query.data  # e.g. "menu_products"
    action = data.removeprefix("menu_")

    if action == "products":
        from bot.handlers.catalog import menu_command
        await menu_command(update, context)

    elif action == "search":
        from bot.handlers.search import search_command
        await search_command(update, context)

    elif action == "cart":
        from bot.handlers.cart import cart_command
        await cart_command(update, context)

    elif action == "profile":
        from bot.handlers.profile import profile_command
        await profile_command(update, context)

    elif action == "orders":
        from bot.handlers.profile import orders_command
        await orders_command(update, context)

    elif action == "wishlist":
        from bot.handlers.wishlist import wishlist_command
        await wishlist_command(update, context)

    elif action == "feedback":
        from bot.handlers.feedback import feedback_command
        await feedback_command(update, context)

    elif action == "help":
        help_text = (
            "📖 *የቦት መመሪያ*\n\n"
            "*ዋና ዋና ትዕዛዞች:*\n\n"
            "/start - ቦቱን ለመጀመር\n"
            "/menu - ዋና ምናሌ ለማየት\n"
            "/search - ምርቶችን ለመፈለግ\n"
            "/cart - የግዢ ቅርጫትን ለማየት\n"
            "/checkout - ግዢን ለማጠናቀቅ\n"
            "/profile - መለያዎን ለማየት\n"
            "/orders - ትዕዛዞትን ለመከታተል\n"
            "/wishlist - ተመራጭ ምርቶችን ለማየት\n"
            "/feedback - ግብረ መልስ ለመስጠት\n"
            "/help - ይህን መመሪያ ለማየት\n\n"
            "❓ ተጨማሪ እገዛ ከፈለጉ እባክዎ ድጋፍን ያግኙ።"
        )
        await query.edit_message_text(help_text, parse_mode="Markdown")

    elif action == "admin":
        await query.edit_message_text("🔧 የአስተዳደር ፓነል ለማስጀመር /admin ይጠቀሙ።")

    elif action == "back":
        user = update.effective_user
        is_admin = user.id in settings.admin_ids_list
        welcome_text = (
            "🌟 *ዎሎየዋ ስቶር* — ዋና ምናሌ\n\n"
            "📌 ከዚህ በታች ካሉት ቁልፎች ይምረጡ።"
        )
        await query.edit_message_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=_build_main_menu(is_admin),
        )

    else:
        logger.warning(f"Unknown menu action: {action}")
        await query.edit_message_text("❓ ያልታወቀ ምርጫ። /start ለማስጀመር ይጠቀሙ።")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "📖 *የቦት መመሪያ*\n\n"
        "*ዋና ዋና ትዕዛዞች:*\n\n"
        "/start - ቦቱን ለመጀመር\n"
        "/menu - ዋና ምናሌ ለማየት\n"
        "/search - ምርቶችን ለመፈለግ\n"
        "/cart - የግዢ ቅርጫትን ለማየት\n"
        "/checkout - ግዢን ለማጠናቀቅ\n"
        "/profile - መለያዎን ለማየት\n"
        "/orders - ትዕዛዞትን ለመከታተል\n"
        "/wishlist - ተምሳሌት ምርቶችን ለማየት\n"
        "/feedback - ግብረ መልስ ለመስጠት\n"
        "/help - ይህን መመሪያ ለማየት\n\n"
        "*ሻጆች ብቻ:*\n"
        "/my_products - ምርቶቼን ለማየት\n"
        "/add_product - አዲስ ምርት ለመጨመር\n\n"
        "*አስተዳዳሪዎች ብቻ:*\n"
        "/admin - የአስተዳደር ፓነል\n"
        "/stats - የስርዓት ስታቲስቲክስ\n"
        "/broadcast - መልዕክት ለማሰራጨት\n\n"
        "❓ ተጨማሪ እገዛ ከፈለጉ እባክዎ ድጋፍን ያግኙ።"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands."""
    await update.message.reply_text(
        "❌ የማይታወቅ ትዕዛዝ።\n"
        "እባክዎ /help በመጠቀም የሚገኙ ትዕዛዞችን ይመልከቱ።"
    )


__all__ = ["start_command", "help_command", "unknown_command", "menu_callback", "_build_main_menu"]
