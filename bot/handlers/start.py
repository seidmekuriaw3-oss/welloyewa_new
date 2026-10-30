"""Telegram bot start command, welcome message, and main menu callback handler."""

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from apps.users.schemas import UserUpdate
from apps.users.services import UserService
from bot.handlers.callback_utils import answer_callback_query, edit_callback_message
from bot.keyboards.reply import main_reply_button_actions, main_reply_keyboard
from bot.localization import SUPPORTED_LANGUAGES, get_language, translate
from core.config import settings
from core.logger import logger
from infrastructure.database.session import get_db_session, transaction_session

# ---------------------------------------------------------------------------
# Shared UI builders
# ---------------------------------------------------------------------------


def _build_store_button(label: str) -> InlineKeyboardButton:
    """Build a Mini App button only when Telegram can reach an HTTPS URL."""
    store_url = settings.web_app_url
    if store_url.lower().startswith("https://"):
        return InlineKeyboardButton(label, web_app=WebAppInfo(url=store_url))
    return InlineKeyboardButton(label, callback_data="menu_products")


def _build_main_menu(is_admin: bool = False, lang: str = "am") -> InlineKeyboardMarkup:
    """Build the main menu inline keyboard (label changes with language)."""
    labels = {
        "am": {
            "products": "🛍️ ምርቶች",
            "search": "🔍 ፈልግ",
            "cart": "🛒 ግዢ ቅርጫት",
            "profile": "👤 ፕሮፋይል",
            "orders": "📦 ትዕዛዞቼ",
            "wishlist": "⭐ ተመራጮች",
            "help": "❓ እገዛ",
            "feedback": "💬 ግብረ መልስ",
            "admin": "🔧 አስተዳደር",
        },
        "en": {
            "products": "🛍️ Products",
            "search": "🔍 Search",
            "cart": "🛒 Cart",
            "profile": "👤 Profile",
            "orders": "📦 My Orders",
            "wishlist": "⭐ Wishlist",
            "help": "❓ Help",
            "feedback": "💬 Feedback",
            "admin": "🔧 Admin",
        },
        "om": {
            "products": "🛍️ Meeshaalee",
            "search": "🔍 Barbaadi",
            "cart": "🛒 Kuusaa",
            "profile": "👤 Profaayilii",
            "orders": "📦 Ajajawwan",
            "wishlist": "⭐ Barbaachisoo",
            "help": "❓ Gargaarsa",
            "feedback": "💬 Yaada",
            "admin": "🔧 Bulchiinsa",
        },
    }
    L = labels.get(lang, labels["am"])
    open_store_labels = {
        "am": "🛍️ ሱቁን ክፈት",
        "en": "🛍️ Open Store",
        "om": "🛍️ Suuqa Bani",
    }
    keyboard = [
        [_build_store_button(open_store_labels.get(lang, open_store_labels["en"]))],
        [
            InlineKeyboardButton(L["products"], callback_data="menu_products"),
            InlineKeyboardButton(L["search"], callback_data="menu_search"),
        ],
        [
            InlineKeyboardButton(L["cart"], callback_data="menu_cart"),
            InlineKeyboardButton(L["profile"], callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton(L["orders"], callback_data="menu_orders"),
            InlineKeyboardButton(L["wishlist"], callback_data="menu_wishlist"),
        ],
        [
            InlineKeyboardButton(L["help"], callback_data="menu_help"),
            InlineKeyboardButton(L["feedback"], callback_data="menu_feedback"),
        ],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(L["admin"], callback_data="menu_admin")])
    return InlineKeyboardMarkup(keyboard)


def _build_language_keyboard() -> InlineKeyboardMarkup:
    """Build onboarding language choices and direct store navigation actions."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="onboard_lang_am")],
            [InlineKeyboardButton("🌐 English", callback_data="onboard_lang_en")],
            [InlineKeyboardButton("🟢 Oromiffa", callback_data="onboard_lang_om")],
            [
                InlineKeyboardButton(
                    "🛍️ Browse Products / ምርቶች",
                    callback_data="menu_products",
                ),
                _build_store_button("🌐 Open Store / ሱቅ"),
            ],
            [
                InlineKeyboardButton(
                    "☰ Main Menu / ዋና ምናሌ",
                    callback_data="menu_back",
                )
            ],
        ]
    )


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


async def _send_start_welcome(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    caption: str,
    reply_markup: InlineKeyboardMarkup,
    reply_keyboard: ReplyKeyboardMarkup | None = None,
) -> None:
    """Send the welcome screen and, when provided, the persistent reply menu."""
    photo_cache_key = "start_profile_photo_file_id"
    photo_file_id = context.bot_data.get(photo_cache_key)

    if photo_cache_key not in context.bot_data:
        try:
            bot_user = await context.bot.get_me()
            profile_photos = await context.bot.get_user_profile_photos(
                bot_user.id, limit=1
            )
        except TelegramError as exc:
            logger.warning("Could not retrieve bot profile photo: %s", exc)
            profile_photos = None

        photo_file_id = (
            profile_photos.photos[0][-1].file_id
            if profile_photos and profile_photos.total_count and profile_photos.photos
            else None
        )
        context.bot_data[photo_cache_key] = photo_file_id

    if photo_file_id:
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo_file_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
            if reply_keyboard:
                await update.effective_message.reply_text(
                    translate(get_language(context), "menu_keyboard_hint"),
                    reply_markup=reply_keyboard,
                )
            return
        except TelegramError as exc:
            context.bot_data.pop(photo_cache_key, None)
            logger.warning("Could not send bot profile photo in /start: %s", exc)

    await update.effective_message.reply_text(
        caption,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )
    if reply_keyboard:
        await update.effective_message.reply_text(
            translate(get_language(context), "menu_keyboard_hint"),
            reply_markup=reply_keyboard,
        )


# ---------------------------------------------------------------------------
# /start command
# ---------------------------------------------------------------------------


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start.

    Flow for NEW users (truly never seen before, no context.user_data either):
        Step 1 → Language selection (onboard_lang_* callback)
        Step 2 → Phone sharing  (contact_handler in profile.py)
        Step 3 → Main menu

    Flow for RETURNING users (DB record found OR context.user_data has prior session):
        → Main menu directly (with a gentle nudge if phone is still missing)
    """
    tg_user = update.effective_user
    logger.info(f"User {tg_user.id} (@{tg_user.username}) started the bot")

    user = None
    db_found = False

    async with transaction_session() as db:
        user_service = UserService(db)
        existing = await user_service.get_user_by_telegram(tg_user.id)
        db_found = existing is not None
        user = await user_service.get_or_create_user(
            telegram_id=tg_user.id,
            first_name=tg_user.first_name or "User",
            username=tg_user.username,
        )
        from bot.middlewares.auth import auth_middleware

        auth_middleware.invalidate(tg_user.id)

    # --- Determine if this is truly a new user ---
    # A user is "new" only when:
    #   1. They have no DB record AND
    #   2. They have no prior context.user_data session (no saved user_id)
    # This prevents returning users from seeing the language screen again if
    # the DB row was lost between restarts (their context.user_data persists).
    has_prior_session = bool(context.user_data.get("user_id"))
    is_new_user = (not db_found) and (not has_prior_session)

    # If DB was missing but context has the user — restore it now
    if not db_found and has_prior_session:
        cached = context.user_data.get("user", {})
        lang_restore = cached.get("language", "am")
        if user:
            try:
                from apps.users.schemas import UserUpdate

                async with transaction_session() as db:
                    us = UserService(db)
                    await us.update_user(user.id, UserUpdate(language=lang_restore))
            except Exception as exc:
                logger.error("Failed to restore user language for %s: %s", tg_user.id, exc)
        logger.info(f"User {tg_user.id} restored from context.user_data (DB row was missing)")

    # Always clear the stale onboarding flag for returning users so that
    # reopening /start never loops back to language selection.
    if not is_new_user:
        context.user_data.pop("onboarding", None)

    is_admin = tg_user.id in settings.admin_ids_list

    if is_new_user:
        welcome_text = (
            "🌟 *ወሎየዋ ስቶር | Wolloyewa Store*\n\n"
            "እንኳን ደህና መጡ! በአንድ ቦታ ምርቶችን ይመልከቱ፣ ይፈልጉ፣ "
            "ወደ ቅርጫት ይጨምሩ እና ትዕዛዝዎን ይከታተሉ።\n"
            "Welcome! Discover products, search, shop your cart, and keep track of your orders.\n"
            "Baga nagaan dhuftan! Meeshaalee argadhaa, barbaadaa, bitadhaa; "
            "ajajawwan keessanis hordofaa.\n\n"
            "🌐 *ቋንቋዎን ይምረጡ | Choose your language | Afaan filadhaa*"
        )
        await _send_start_welcome(
            update,
            context,
            welcome_text,
            _build_language_keyboard(),
            main_reply_keyboard("am"),
        )
        context.user_data["onboarding"] = True

    else:
        # Returning user — go straight to the main menu
        lang = "am"
        if user and user.language:
            lang = user.language
        elif context.user_data.get("user", {}).get("language"):
            lang = context.user_data["user"]["language"]

        safe_first_name = escape_markdown(tg_user.first_name or "User", version=1)
        greetings = {
            "am": (
                f"👋 ሰላም *{safe_first_name}*፣ እንኳን ወደ ወሎየዋ ስቶር በደህና ተመለሱ!\n\n"
                "🛍️ ምርቶችን ይመልከቱ እና ይፈልጉ\n"
                "🛒 ወደ ቅርጫት ጨምረው ትዕዛዝ ያስገቡ\n"
                "📦 ትዕዛዝዎን እና ፕሮፋይልዎን ያስተዳድሩ\n\n"
                "👇 ለመቀጠል ከታች ያለውን ምናሌ ይጠቀሙ።"
            ),
            "en": (
                f"👋 Welcome back to Wolloyewa Store, *{safe_first_name}*!\n\n"
                "🛍️ Browse and search products\n"
                "🛒 Add items to your cart and place an order\n"
                "📦 Manage your orders and profile\n\n"
                "👇 Choose an option below to get started."
            ),
            "om": (
                f"👋 *{safe_first_name}*, gara Wolloyewa Store nagaan deebi'uu keessaniif baga gammaddan!\n\n"
                "🛍️ Meeshaalee ilaalaa fi barbaadaa\n"
                "🛒 Kuusaatti dabalaa, ajaja galchaa\n"
                "📦 Ajajawwan fi profaayila keessan bulchaa\n\n"
                "👇 Itti fufuuf filannoo armaan gadii tuqaa."
            ),
        }
        nudge = {
            "am": "\n\n⚠️ ስልክ ቁጥርዎ ገና አልተመዘገበም — ከፕሮፋይልዎ ሊያስገቡ ይችላሉ።",
            "en": "\n\n⚠️ Phone not saved yet — update it from your Profile.",
            "om": "\n\n⚠️ Lakkoofsi bilbilaa hin kuufamne — Profaayilii keessaa guuntaa.",
        }
        text = greetings.get(lang, greetings["am"])
        phone_missing = not user or not user.phone_number
        if phone_missing:
            text += nudge.get(lang, nudge["am"])

        await _send_start_welcome(
            update,
            context,
            text,
            _build_main_menu(is_admin, lang),
            main_reply_keyboard(lang),
        )


# ---------------------------------------------------------------------------
# Onboarding Step 1 callback: language chosen → save + ask for phone
# ---------------------------------------------------------------------------


async def onboard_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle onboard_lang_am / onboard_lang_en / onboard_lang_om.

    Saves the chosen language, then moves to Step 2 (phone sharing).
    """
    query = update.callback_query
    lang = query.data.removeprefix("onboard_lang_")
    if lang not in SUPPORTED_LANGUAGES:
        await answer_callback_query(query, "Unsupported language.", show_alert=True)
        return
    if not await answer_callback_query(query):
        return
    tg_user = update.effective_user

    # Save language to DB
    user_found = False
    async with transaction_session() as db:
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(tg_user.id)
        if user:
            await user_service.update_user(user.id, UserUpdate(language=lang))
            user_found = True
            from bot.middlewares.auth import auth_middleware

            auth_middleware.invalidate(tg_user.id)

    if not user_found:
        logger.error("Could not save onboarding language: user %s was not found", tg_user.id)
        await query.message.reply_text(translate(lang, "user_not_found"))
        return

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

    # Preserve the welcome photo while replacing its language picker with the
    # selected language's next-step instructions.
    remove_language_keyboard = InlineKeyboardMarkup(
        [], api_kwargs={"inline_keyboard": []}
    )
    if query.message.photo:
        await query.edit_message_caption(
            caption=ack.get(lang, ack["am"]),
            parse_mode="Markdown",
            reply_markup=remove_language_keyboard,
        )
    else:
        await query.edit_message_text(
            ack.get(lang, ack["am"]),
            parse_mode="Markdown",
            reply_markup=remove_language_keyboard,
        )

    await update.effective_message.reply_text(
        "⬇️",
        reply_markup=_build_phone_keyboard(lang),
    )

    # Ensure onboarding flag is set (may have been lost if user reopened the bot)
    context.user_data["onboarding"] = True
    context.user_data["onboarding_lang"] = lang
    context.user_data["language"] = lang
    context.user_data.setdefault("user", {})["language"] = lang


# ---------------------------------------------------------------------------
# Main menu callback router
# ---------------------------------------------------------------------------


async def _show_callback_text(query, text: str, **kwargs) -> None:
    """Edit a text message or reply when the callback came from a photo."""
    if query.message.text is not None:
        await edit_callback_message(query, text, **kwargs)
    else:
        await query.message.reply_text(text, **kwargs)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all menu_* callback queries to the right handler."""
    query = update.callback_query
    if not await answer_callback_query(query):
        return

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
        await _show_callback_text(
            query,
            help_texts.get(user_lang, help_texts["am"]),
            parse_mode="Markdown",
        )

    elif action == "admin":
        # admin_command expects update.message, so show the panel inline here.
        if update.effective_user.id not in settings.admin_ids_list:
            await _show_callback_text(query, "❌ ፈቃድ የለዎትም።")
        else:
            from bot.handlers.admin.dashboard import ADMIN_MENU_TEXT, _admin_main_keyboard

            await _show_callback_text(
                query,
                ADMIN_MENU_TEXT,
                parse_mode="Markdown",
                reply_markup=_admin_main_keyboard(),
            )

    elif action in ("back", "main", "start"):
        tg_user = update.effective_user
        is_admin = tg_user.id in settings.admin_ids_list
        lang = context.user_data.get("user", {}).get("language", "am")
        titles = {
            "am": "🌟 *ዎሎየዋ ስቶር* — ዋና ምናሌ\n\n📌 ከዚህ በታች ካሉት ቁልፎች ይምረጡ።",
            "en": "🌟 *Wolloyewa Store* — Main Menu\n\n📌 Choose from the buttons below.",
            "om": "🌟 *Wolloyewa Store* — Chaartii Ijoo\n\n📌 Armaan gadii keessaa filadhu.",
        }
        await _show_callback_text(
            query,
            titles.get(lang, titles["am"]),
            parse_mode="Markdown",
            reply_markup=_build_main_menu(is_admin, lang),
        )

    else:
        logger.warning(f"Unknown menu action: {action}")
        await _show_callback_text(query, "❓ /start")


async def main_reply_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Route the persistent reply-keyboard shortcuts to their existing screens."""
    text = update.effective_message.text.strip()
    action = main_reply_button_actions().get(text)
    if action is None:
        return
    context.user_data.pop("updating_field", None)

    if action == "browse_store":
        from bot.handlers.catalog import menu_command

        await menu_command(update, context)
    elif action == "cart":
        from bot.handlers.cart import cart_command

        await cart_command(update, context)
    elif action == "wishlist":
        from bot.handlers.wishlist import wishlist_command

        await wishlist_command(update, context)
    elif action == "search":
        from bot.handlers.search import search_command

        await search_command(update, context)
    elif action == "profile":
        from bot.handlers.profile import profile_command

        await profile_command(update, context)
    elif action == "vendor_panel":
        from bot.handlers.profile import show_vendor_panel

        await show_vendor_panel(update, context)
    elif action == "orders":
        from bot.handlers.profile import orders_command

        await orders_command(update, context)
    elif action == "help":
        await help_command(update, context)
    elif action == "web_app":
        await update.effective_message.reply_text(
            translate(get_language(context), "web_app_unavailable")
        )


async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Acknowledge intentionally inert/status buttons without leaving a spinner."""
    await answer_callback_query(update.callback_query)


async def unknown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Acknowledge unmatched or stale inline buttons with a recovery hint."""
    query = update.callback_query
    await answer_callback_query(
        query,
        translate(get_language(context), "stale_button"),
        show_alert=True,
    )


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
            "/resetpassword - የይለፍ ቃል መመለስ\n"
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
            "/resetpassword - Reset your password\n"
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
            "/resetpassword - Jecha darbii deebisi\n"
            "/feedback - Yaada\n/help - Gargaarsa\n\n"
            "*Gurgurtaa:* /my_products · /add_product\n"
            "*Bulchiinsa:* /admin · /stats · /broadcast"
        ),
    }
    await update.message.reply_text(
        texts.get(lang, texts["am"]),
        parse_mode="Markdown",
        reply_markup=main_reply_keyboard(lang),
    )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("user", {}).get("language", "am")
    msgs = {
        "am": "❌ የማይታወቅ ትዕዛዝ። /help ይጫኑ።",
        "en": "❌ Unknown command. Use /help.",
        "om": "❌ Ajaja hin beekamne. /help fayyadami.",
    }
    await update.message.reply_text(
        msgs.get(lang, msgs["am"]),
        reply_markup=main_reply_keyboard(lang),
    )


async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/shop — send a standalone Mini App button that opens the web store."""
    lang = context.user_data.get("user", {}).get("language", "am")
    captions = {
        "am": "👇 ከዚህ ቁልፍ ሱቁን ክፈቱ:",
        "en": "👇 Tap below to open the store:",
        "om": "👇 Suuqa banuuf armaan gadii tuqi:",
    }
    button_labels = {
        "am": "🛍️ ወሎየዋ ሱቅ ክፈት",
        "en": "🛍️ Open Wolloyewa Store",
        "om": "🛍️ Suuqa Wolloyewa Bani",
    }
    markup = InlineKeyboardMarkup(
        [
            [
                _build_store_button(button_labels.get(lang, button_labels["en"]))
            ]
        ]
    )
    await update.message.reply_text(
        captions.get(lang, captions["en"]),
        reply_markup=markup,
    )


__all__ = [
    "_build_main_menu",
    "_build_phone_keyboard",
    "help_command",
    "menu_callback",
    "main_reply_handler",
    "noop_callback",
    "onboard_language_callback",
    "shop_command",
    "start_command",
    "unknown_command",
]
