"""Telegram bot start command, welcome message, and main menu callback handler."""

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import ContextTypes

from core.logger import logger
from core.config import settings
from apps.users.services import UserService
from apps.users.schemas import UserUpdate
from infrastructure.database.session import get_db_session


# ---------------------------------------------------------------------------
# Shared UI builders
# ---------------------------------------------------------------------------

def _build_main_menu(is_admin: bool = False, lang: str = "am") -> InlineKeyboardMarkup:
    """Build the main menu inline keyboard (label changes with language)."""
    labels = {
        "am": {
            "products": "🛍️ ምርቶች",   "search": "🔍 ፈልግ",
            "cart":     "🛒 ግዢ ቅርጫት", "profile": "👤 ፕሮፋይል",
            "orders":   "📦 ትዕዛዞቼ",   "wishlist": "⭐ ተመራጮች",
            "help":     "❓ እገዛ",       "feedback": "💬 ግብረ መልስ",
            "admin":    "🔧 አስተዳደር",
        },
        "en": {
            "products": "🛍️ Products",  "search": "🔍 Search",
            "cart":     "🛒 Cart",       "profile": "👤 Profile",
            "orders":   "📦 My Orders", "wishlist": "⭐ Wishlist",
            "help":     "❓ Help",       "feedback": "💬 Feedback",
            "admin":    "🔧 Admin",
        },
        "om": {
            "products": "🛍️ Meeshaalee", "search": "🔍 Barbaadi",
            "cart":     "🛒 Kuusaa",      "profile": "👤 Profaayilii",
            "orders":   "📦 Ajajawwan",   "wishlist": "⭐ Barbaachisoo",
            "help":     "❓ Gargaarsa",   "feedback": "💬 Yaada",
            "admin":    "🔧 Bulchiinsa",
        },
    }
    L = labels.get(lang, labels["am"])
    keyboard = [
        [InlineKeyboardButton(L["products"], callback_data="menu_products"),
         InlineKeyboardButton(L["search"],   callback_data="menu_search")],
        [InlineKeyboardButton(L["cart"],     callback_data="menu_cart"),
         InlineKeyboardButton(L["profile"],  callback_data="menu_profile")],
        [InlineKeyboardButton(L["orders"],   callback_data="menu_orders"),
         InlineKeyboardButton(L["wishlist"], callback_data="menu_wishlist")],
        [InlineKeyboardButton(L["help"],     callback_data="menu_help"),
         InlineKeyboardButton(L["feedback"], callback_data="menu_feedback")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(L["admin"], callback_data="menu_admin")])
    return InlineKeyboardMarkup(keyboard)


def _build_language_keyboard() -> InlineKeyboardMarkup:
    """Language selection keyboard shown to brand-new users."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇪🇹 አማርኛ",  callback_data="onboard_lang_am")],
        [InlineKeyboardButton("🌐 English", callback_data="onboard_lang_en")],
        [InlineKeyboardButton("🟢 Oromiffa", callback_data="onboard_lang_om")],
    ])


def _build_phone_keyboard(lang: str = "am") -> ReplyKeyboardMarkup:
    """One-time contact-sharing keyboard shown after language selection."""
    labels = {
        "am": "📞 ስልኬን አጋራ",
        "en": "📞 Share My Phone",
        "om": "📞 Bilbila Koo Qoodi",
    }
    placeholders = {
        "am": "ቁልፉን ይጫኑ ወይም ይዝለሉ…",
        "en": "Tap the button or skip…",
        "om": "Furtuudhaan tuqi ykn darbi…",
    }
    return ReplyKeyboardMarkup(
        [[KeyboardButton(labels.get(lang, labels["am"]), request_contact=True)]],
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder=placeholders.get(lang, placeholders["am"]),
    )


# ---------------------------------------------------------------------------
# /start command
# ---------------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start.

    Flow for NEW users:
        Step 1 → Language selection (onboard_lang_* callback)
        Step 2 → Phone sharing  (contact_handler in profile.py)
        Step 3 → Main menu

    Flow for RETURNING users:
        → Main menu directly (with a gentle nudge if phone is still missing)
    """
    tg_user = update.effective_user
    logger.info(f"User {tg_user.id} (@{tg_user.username}) started the bot")

    is_new_user = False
    user = None

    async for db in get_db_session():
        user_service = UserService(db)
        existing = await user_service.get_user_by_telegram(tg_user.id)
        is_new_user = existing is None
        user = await user_service.get_or_create_user(
            telegram_id=tg_user.id,
            first_name=tg_user.first_name or "User",
            username=tg_user.username,
        )
        from bot.middlewares.auth import auth_middleware
        auth_middleware.invalidate(tg_user.id)
        break

    is_admin = tg_user.id in settings.admin_ids_list

    if is_new_user:
        # Step 1: ask language — message is written in all three so everyone understands
        await update.message.reply_text(
            "🌟 *ዎሎየዋ ስቶር* — *Wolloyewa Store* 🌟\n\n"
            "🇪🇹 እንኳን ደህና መጡ! ቋንቋዎን ይምረጡ።\n"
            "🌐 Welcome! Please choose your language.\n"
            "🟢 Baga nagaan dhufte! Afaan filadhu.\n\n"
            "⬇️  ⬇️  ⬇️",
            parse_mode="Markdown",
            reply_markup=_build_language_keyboard(),
        )
        # Mark that we are in onboarding so subsequent steps know the context
        context.user_data["onboarding"] = True

    else:
        # Returning user — go straight to the main menu
        lang = (user.language or "am") if user else "am"
        greetings = {
            "am": f"👤 ሰላም, *{tg_user.first_name}*! እንኳን ደህና መጡ 🎉",
            "en": f"👤 Hello, *{tg_user.first_name}*! Welcome back 🎉",
            "om": f"👤 Akkam, *{tg_user.first_name}*! Baga nagaan deebitee 🎉",
        }
        nudge = {
            "am": "\n\n⚠️ ስልክ ቁጥርዎ ገና አልተመዘገበም — ከፕሮፋይልዎ ሊያስገቡ ይችላሉ።",
            "en": "\n\n⚠️ Phone not saved yet — update it from your Profile.",
            "om": "\n\n⚠️ Lakkoofsi bilbilaa hin kuufamne — Profaayilii keessaa guuntaa.",
        }
        text = greetings.get(lang, greetings["am"])
        if user and not user.phone_number:
            text += nudge.get(lang, nudge["am"])

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=_build_main_menu(is_admin, lang),
        )


# ---------------------------------------------------------------------------
# Onboarding Step 1 callback: language chosen → save + ask for phone
# ---------------------------------------------------------------------------

async def onboard_language_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle onboard_lang_am / onboard_lang_en / onboard_lang_om.

    Saves the chosen language, then moves to Step 2 (phone sharing).
    """
    query = update.callback_query
    await query.answer()

    lang = query.data.replace("onboard_lang_", "")   # "am" | "en" | "om"
    tg_user = update.effective_user

    # Save language to DB
    async for db in get_db_session():
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(tg_user.id)
        if user:
            await user_service.update_user(user.id, UserUpdate(language=lang))
            from bot.middlewares.auth import auth_middleware
            auth_middleware.invalidate(tg_user.id)
        break

    # Acknowledgement messages per language
    ack = {
        "am": (
            "✅ *ቋንቋ ተመርጧል: አማርኛ*\n\n"
            "📞 *ቀጣይ: ስልክ ቁጥርዎን ያጋሩ*\n"
            "ትዕዛዞችዎን ለማረጋገጥ ስልክዎ ያስፈልጋል።\n\n"
            "ከዚህ በታች ያለውን ቁልፍ ይጫኑ ወይም ቆይቶ ከፕሮፋይልዎ ሊያስገቡ ይችላሉ።"
        ),
        "en": (
            "✅ *Language set: English*\n\n"
            "📞 *Next: Share your phone number*\n"
            "Your number is needed to confirm orders.\n\n"
            "Tap the button below, or add it later from Profile."
        ),
        "om": (
            "✅ *Afaan filatame: Oromiffa*\n\n"
            "📞 *Itti aanaa: Lakkoofsa bilbila kee qoodi*\n"
            "Lakkoofsi ajajawwan mirkaaneessuuf barbaachisaa dha.\n\n"
            "Furtuu armaan gadii tuqi, ykn booda Profaayilii keessaa guunna."
        ),
    }

    # Edit the language-selection message, then send the phone-share keyboard
    # (edit removes the language buttons, new message carries the reply keyboard)
    await query.edit_message_text(ack.get(lang, ack["am"]), parse_mode="Markdown")

    await update.effective_message.reply_text(
        "⬇️" if lang == "am" else "⬇️",
        reply_markup=_build_phone_keyboard(lang),
    )

    # Ensure onboarding flag is set (may have been lost if user reopened the bot)
    context.user_data["onboarding"] = True
    context.user_data["onboarding_lang"] = lang


# ---------------------------------------------------------------------------
# Main menu callback router
# ---------------------------------------------------------------------------

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all menu_* callback queries to the right handler."""
    query = update.callback_query
    await query.answer()

    action = query.data.removeprefix("menu_")

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
        tg_user = update.effective_user
        user_lang = context.user_data.get("user", {}).get("language", "am")
        help_texts = {
            "am": (
                "📖 *የቦት መመሪያ*\n\n"
                "/start - ቦቱን ለመጀመር\n/menu - ዋና ምናሌ\n"
                "/search - ምርቶችን ለመፈለግ\n/cart - ግዢ ቅርጫት\n"
                "/checkout - ግዢን ለማጠናቀቅ\n/profile - ፕሮፋይል\n"
                "/orders - ትዕዛዞቼ\n/wishlist - ተምሳሌቶች\n"
                "/feedback - ግብረ መልስ\n/help - እገዛ"
            ),
            "en": (
                "📖 *Bot Help*\n\n"
                "/start - Restart the bot\n/menu - Main menu\n"
                "/search - Search products\n/cart - Shopping cart\n"
                "/checkout - Complete purchase\n/profile - Your profile\n"
                "/orders - My orders\n/wishlist - Wishlist\n"
                "/feedback - Give feedback\n/help - This help"
            ),
            "om": (
                "📖 *Gargaarsa Bot*\n\n"
                "/start - Bot jalqabi\n/menu - Chaartii ijoo\n"
                "/search - Meeshaa barbaadi\n/cart - Kuusaa bitaa\n"
                "/checkout - Bitaa xumuri\n/profile - Profaayilii\n"
                "/orders - Ajajawwan koo\n/wishlist - Barbaachisoo\n"
                "/feedback - Yaada\n/help - Gargaarsa"
            ),
        }
        await query.edit_message_text(
            help_texts.get(user_lang, help_texts["am"]),
            parse_mode="Markdown",
        )

    elif action == "admin":
        await query.edit_message_text("🔧 /admin")

    elif action == "back":
        tg_user = update.effective_user
        is_admin = tg_user.id in settings.admin_ids_list
        lang = context.user_data.get("user", {}).get("language", "am")
        titles = {
            "am": "🌟 *ዎሎየዋ ስቶር* — ዋና ምናሌ\n\n📌 ከዚህ በታች ካሉት ቁልፎች ይምረጡ።",
            "en": "🌟 *Wolloyewa Store* — Main Menu\n\n📌 Choose from the buttons below.",
            "om": "🌟 *Wolloyewa Store* — Chaartii Ijoo\n\n📌 Armaan gadii keessaa filadhu.",
        }
        await query.edit_message_text(
            titles.get(lang, titles["am"]),
            parse_mode="Markdown",
            reply_markup=_build_main_menu(is_admin, lang),
        )

    else:
        logger.warning(f"Unknown menu action: {action}")
        await query.edit_message_text("❓ /start")


# ---------------------------------------------------------------------------
# /help and fallback handlers
# ---------------------------------------------------------------------------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("user", {}).get("language", "am")
    texts = {
        "am": (
            "📖 *የቦት መመሪያ*\n\n"
            "/start - ቦቱን ለመጀመር\n/menu - ዋና ምናሌ ለማየት\n"
            "/search - ምርቶችን ለመፈለግ\n/cart - የግዢ ቅርጫት\n"
            "/checkout - ግዢን ለማጠናቀቅ\n/profile - መለያዎን ለማየት\n"
            "/orders - ትዕዛዞቼ\n/wishlist - ተምሳሌቶች\n"
            "/feedback - ግብረ መልስ\n/help - ይህ እገዛ\n\n"
            "*ሻጆች:* /my_products · /add_product\n"
            "*አስተዳዳሪዎች:* /admin · /stats · /broadcast"
        ),
        "en": (
            "📖 *Bot Help*\n\n"
            "/start - Restart the bot\n/menu - Main menu\n"
            "/search - Search products\n/cart - Shopping cart\n"
            "/checkout - Complete purchase\n/profile - Your profile\n"
            "/orders - My orders\n/wishlist - Wishlist\n"
            "/feedback - Feedback\n/help - This message\n\n"
            "*Vendors:* /my_products · /add_product\n"
            "*Admins:* /admin · /stats · /broadcast"
        ),
        "om": (
            "📖 *Gargaarsa Bot*\n\n"
            "/start - Bot jalqabi\n/menu - Chaartii ijoo\n"
            "/search - Meeshaa barbaadi\n/cart - Kuusaa bitaa\n"
            "/checkout - Bitaa xumuri\n/profile - Profaayilii\n"
            "/orders - Ajajawwan\n/wishlist - Barbaachisoo\n"
            "/feedback - Yaada\n/help - Gargaarsa\n\n"
            "*Gurgurtaa:* /my_products · /add_product\n"
            "*Bulchiinsa:* /admin · /stats · /broadcast"
        ),
    }
    await update.message.reply_text(texts.get(lang, texts["am"]), parse_mode="Markdown")


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("user", {}).get("language", "am")
    msgs = {
        "am": "❌ የማይታወቅ ትዕዛዝ። /help ይጫኑ።",
        "en": "❌ Unknown command. Use /help.",
        "om": "❌ Ajaja hin beekamne. /help fayyadami.",
    }
    await update.message.reply_text(msgs.get(lang, msgs["am"]))


__all__ = [
    "start_command",
    "help_command",
    "unknown_command",
    "menu_callback",
    "onboard_language_callback",
    "_build_main_menu",
    "_build_phone_keyboard",
]
