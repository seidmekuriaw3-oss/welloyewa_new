"""Telegram bot start command, welcome message, and main menu callback handler."""

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import ContextTypes

from core.logger import logger
from core.config import settings
from apps.users.services import UserService
from infrastructure.database.session import get_db_session


def _build_main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Build the main menu inline keyboard."""
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


def _build_phone_keyboard() -> ReplyKeyboardMarkup:
    """
    Build the one-time keyboard that lets a new user share their phone number.
    This keyboard disappears automatically after the user taps the button.
    """
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📞 ስልኬን አጋራ", request_contact=True)]],
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="ቁልፉን ይጫኑ ወይም ይዝለሉ…",
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start — auto-register the user and show welcome message.

    Flow:
    • New user (no phone yet)  → Welcome + ask for phone number
    • Returning user           → Welcome + main menu directly
    """
    tg_user = update.effective_user
    logger.info(f"User {tg_user.id} ({tg_user.username}) started the bot")

    is_new_user = False
    user = None

    async for db in get_db_session():
        user_service = UserService(db)

        # Check if user already existed
        existing = await user_service.get_user_by_telegram(tg_user.id)
        is_new_user = existing is None

        # get_or_create guarantees a DB record exists after this call
        user = await user_service.get_or_create_user(
            telegram_id=tg_user.id,
            first_name=tg_user.first_name or "ተጠቃሚ",
            username=tg_user.username,
        )

        # Invalidate middleware cache so updated data is picked up
        from bot.middlewares.auth import auth_middleware
        auth_middleware.invalidate(tg_user.id)
        break

    is_admin = tg_user.id in settings.admin_ids_list

    if is_new_user:
        # ── Onboarding: new user — greet and request phone number ────────────
        welcome_text = (
            f"🌟 እንኳን ደህና መጡ ወደ *ዎሎየዋ ስቶር*, {tg_user.first_name}! 🌟\n\n"
            "የኢትዮጵያ ዘመናዊ የኢ-ኮሜርስ ቴሌግራም ቦት — ምርቶችን ይግዙ፣ ሻጭ ይሁኑ!\n\n"
            "✅ *መለያዎ ተፈጥሯል!*\n\n"
            "📞 *ቀጣይ ደረጃ: ስልክ ቁጥርዎን ያስመዝግቡ*\n"
            "ትዕዛዞችዎን ለመከታተልና ለማረጋገጥ ስልክ ቁጥርዎ ያስፈልጋል።\n\n"
            "ከዚህ በታች ያለውን ቁልፍ ይጫኑ ወይም ቆይቶ ከፕሮፋይልዎ ሊያስገቡ ይችላሉ።"
        )
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=_build_phone_keyboard(),
        )
        # Remember that this user is in onboarding so the contact_handler
        # can show the main menu after they share their number.
        context.user_data["onboarding"] = True

    else:
        # ── Returning user — show main menu directly ─────────────────────────
        has_phone = user and user.phone_number
        returning_text = (
            f"🌟 እንኳን ደህና መጡ *ዎሎየዋ ስቶር*! 🌟\n\n"
            f"👤 ሰላም, *{tg_user.first_name}*!\n\n"
            "📌 ከዚህ በታች ካሉት ቁልፎች ይምረጡ።"
        )
        if not has_phone:
            returning_text += "\n\n⚠️ ስልክ ቁጥርዎ ገና አልተመዘገበም — ከፕሮፋይልዎ ሊያስገቡ ይችላሉ።"

        await update.message.reply_text(
            returning_text,
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
            "/wishlist - ተምሳሌት ምርቶችን ለማየት\n"
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
