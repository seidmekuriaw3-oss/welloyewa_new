# ============================
# WOLLOYEWA STORE BOT - START HANDLER
# ============================
"""Telegram bot start command and welcome message handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from core.config import settings
from apps.users.services import UserService
from infrastructure.database.session import get_db_session


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    
    Registers new user and shows welcome message.
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    # Register or get user in database
    async for db in get_db_session():
        user_service = UserService(db)
        db_user = await user_service.get_or_create_user(
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
        )
        break
    
    # Welcome message
    welcome_text = f"""
🌟 እንኳን ደህና መጡ ወደ *ዎሎየዋ ስቶር*! 🌟

የኢትዮጵያ የመጀመሪያው ዘመናዊ የኢ-ኮሜርስ ቴሌግራም ቦት።

✨ *ባህሪያት:*
• 🛍️ ምርቶችን ይመልከቱ እና ይግዙ
• 💳 በቀላሉ ይክፈሉ (Chapa፣ Telebirr፣ CBE Birr)
• 📦 ትዕዛዞትን ይከታተሉ
• ⭐ ግምገማ ያስቀምጡ
• 🏪 ሻጭ ለመሆን ያመልክቱ

📌 ለመጀመር ከዚህ በታች ካሉት ቁልፎች ይምረጡ።
    """
    
    # Create keyboard
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
    
    # Add admin button if user is admin
    if user.id in settings.admin_ids_list:
        keyboard.append([
            InlineKeyboardButton("🔧 አስተዳደር", callback_data="menu_admin"),
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /help command.
    
    Shows help information about bot commands.
    """
    help_text = """
📖 *የቦት መመሪያ*

*ዋና ዋና ትዕዛዞች:*

/start - ቦቱን ለመጀመር
/menu - ዋና ምናሌ ለማየት
/search - ምርቶችን ለመፈለግ
/cart - የግዢ ቅርጫትን ለማየት
/checkout - ግዢን ለማጠናቀቅ
/profile - መለያዎን ለማየት
/orders - ትዕዛዞትን ለመከታተል
/wishlist - ተመራጭ ምርቶችን ለማየት
/feedback - ግብረ መልስ ለመስጠት
/help - ይህን መመሪያ ለማየት

*ሻጆች ብቻ:*
/my_products - ምርቶቼን ለማየት
/add_product - አዲስ ምርት ለመጨመር

*አስተዳዳሪዎች ብቻ:*
/admin - የአስተዳደር ፓነል
/stats - የስርዓት ስታቲስቲክስ
/broadcast - መልዕክት ለማሰራጨት

❓ ተጨማሪ እገዛ ከፈለጉ እባክዎ ድጋፍን ያግኙ።
    """
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle unknown commands.
    
    Sends a message informing the user that the command is unknown.
    """
    await update.message.reply_text(
        "❌ የማይታወቅ ትዕዛዝ።\n"
        "እባክዎ /help በመጠቀም የሚገኙ ትዕዛዞችን ይመልከቱ።"
    )


__all__ = ["start_command", "help_command", "unknown_command"]