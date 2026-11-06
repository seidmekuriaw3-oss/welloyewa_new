# ============================
# WOLLOYEWA STORE BOT - PROFILE HANDLER
# ============================
"""Telegram bot user profile and order history handlers — full i18n support."""

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    ReplyKeyboardRemove,
    Update,
)
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from sqlalchemy.exc import SQLAlchemyError

from apps.orders.services import OrderService
from apps.users.schemas import UserUpdate
from apps.users.services import UserService, VendorService
from bot.handlers.callback_utils import answer_callback_query
from bot.handlers.text_routing import mark_text_message_handled
from bot.localization import SUPPORTED_LANGUAGES, get_language, tr
from core.exceptions import NotFoundError
from core.logger import logger
from core.utils.currency import format_etb
from core.utils.validators import Validator
from infrastructure.database.session import get_db_session, transaction_session

# ---------------------------------------------------------------------------
# Translation tables
# ---------------------------------------------------------------------------

_T = {
    # ── Profile screen ──────────────────────────────────────────────────────
    "profile_title": {
        "am": "👤 *ፕሮፋይል*",
        "en": "👤 *Profile*",
        "om": "👤 *Profaayilii*",
    },
    "field_name": {
        "am": "🆔 *ስም:*",
        "en": "🆔 *Name:*",
        "om": "🆔 *Maqaa:*",
    },
    "field_username": {
        "am": "📝 *የተጠቃሚ ስም:*",
        "en": "📝 *Username:*",
        "om": "📝 *Maqaa fayyadamaa:*",
    },
    "field_phone": {
        "am": "📞 *ስልክ:*",
        "en": "📞 *Phone:*",
        "om": "📞 *Bilbila:*",
    },
    "field_address": {
        "am": "📍 *አድራሻ:*",
        "en": "📍 *Address:*",
        "om": "📍 *Teessoo:*",
    },
    "field_email": {
        "am": "📧 *ኢሜይል:*",
        "en": "📧 *Email:*",
        "om": "📧 *Imeelii:*",
    },
    "field_role": {
        "am": "⭐ *ሚና:*",
        "en": "⭐ *Role:*",
        "om": "⭐ *Gahee:*",
    },
    "field_joined": {
        "am": "📅 *የተመዘገበበት:*",
        "en": "📅 *Member since:*",
        "om": "📅 *Guyyaa makamumsaa:*",
    },
    "stats_title": {
        "am": "📊 *ስታቲስቲክስ:*",
        "en": "📊 *Statistics:*",
        "om": "📊 *Qabiyyee:*",
    },
    "stats_orders": {
        "am": "• 🛒 *ጠቅላላ ትዕዛዞች:*",
        "en": "• 🛒 *Total orders:*",
        "om": "• 🛒 *Ajajawwan waliigalaa:*",
    },
    "stats_spent": {
        "am": "• 💰 *ጠቅላላ ወጪ:*",
        "en": "• 💰 *Total spent:*",
        "om": "• 💰 *Gatii waliigalaa:*",
    },
    "stats_avg": {
        "am": "• 📦 *አማካይ ትዕዛዝ:*",
        "en": "• 📦 *Average order:*",
        "om": "• 📦 *Ajaja giddugaleessa:*",
    },
    # not-set placeholders
    "not_set": {
        "am": "አልተመዘገበም",
        "en": "Not set",
        "om": "Hin galmoofne",
    },
    # ── Profile buttons ──────────────────────────────────────────────────────
    "btn_update_phone": {
        "am": "📞 ስልክ አዘምን",
        "en": "📞 Update Phone",
        "om": "📞 Bilbila Haaromsi",
    },
    "btn_update_photo": {
        "am": "🖼️ ፎቶ ቀይር",
        "en": "🖼️ Update Photo",
        "om": "🖼️ Suuraa Haaromsi",
    },
    "btn_update_email": {
        "am": "📧 ኢሜይል አዘምን",
        "en": "📧 Update Email",
        "om": "📧 Imeelii Haaromsi",
    },
    "btn_change_lang": {
        "am": "🌐 ቋንቋ ቀይር",
        "en": "🌐 Change Language",
        "om": "🌐 Afaan Jijjiiri",
    },
    "btn_my_orders": {
        "am": "📦 ትዕዛዞቼ",
        "en": "📦 My Orders",
        "om": "📦 Ajajawwan Koo",
    },
    "btn_become_vendor": {
        "am": "🏪 ሻጭ ለመሆን ያመልክቱ",
        "en": "🏪 Apply to be a Vendor",
        "om": "🏪 Gurgurtaa Ta'uuf Iyyaddhu",
    },
    "btn_vendor_panel": {
        "am": "🏪 የሻጭ ፓነል",
        "en": "🏪 Vendor Panel",
        "om": "🏪 Paanelii Gurgurtaa",
    },
    "btn_back": {
        "am": "🔙 ወደ ኋላ",
        "en": "🔙 Back",
        "om": "🔙 Deebi'i",
    },
    # ── Language selection (from profile) ───────────────────────────────────
    "lang_select_title": {
        "am": "🌐 *ቋንቋ ይምረጡ*\n\nየሚፈልጉትን ቋንቋ ይምረጡ:",
        "en": "🌐 *Choose Language*\n\nSelect your preferred language:",
        "om": "🌐 *Afaan Filadhu*\n\nAfaan barbaadde filadhu:",
    },
    # ── Phone update ─────────────────────────────────────────────────────────
    "phone_prompt": {
        "am": "📞 ስልክ ቁጥርዎን ይላኩ (09XXXXXXXX):",
        "en": "📞 Send your phone number (09XXXXXXXX):",
        "om": "📞 Lakkoofsa bilbilaa ergi (09XXXXXXXX):",
    },
    # ── Email update ─────────────────────────────────────────────────────────
    "email_prompt": {
        "am": "📧 ኢሜይል አድራሻዎን ይላኩ:",
        "en": "📧 Send your email address:",
        "om": "📧 Teessoo imeelii kee ergi:",
    },
    "email_invalid": {
        "am": "❌ እባክዎ ትክክለኛ ኢሜይል ያስገቡ።",
        "en": "❌ Please enter a valid email address.",
        "om": "❌ Maaloo imeelii sirrii galchi.",
    },
    "email_saved": {
        "am": "✅ ኢሜይልዎ ተቀምጧል።",
        "en": "✅ Your email has been saved.",
        "om": "✅ Imeeliin kee olkaa'ameera.",
    },
    "email_failed": {
        "am": "❌ ኢሜይልዎን ማስቀመጥ አልተቻለም።",
        "en": "❌ We could not save your email.",
        "om": "❌ Imeelii kee olkaa'uu hin dandeenye.",
    },
    # ── Vendor panel ─────────────────────────────────────────────────────────
    "vendor_panel_title": {
        "am": "🏪 *የሻጭ ፓነል*\n\nከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        "en": "🏪 *Vendor Panel*\n\nChoose from the options below.",
        "om": "🏪 *Paanelii Gurgurtaa*\n\nFilannoo armaan gadii keessaa filadhu.",
    },
    "btn_my_products": {
        "am": "📦 ምርቶቼ",
        "en": "📦 My Products",
        "om": "📦 Meeshaalee Koo",
    },
    "btn_add_product": {
        "am": "+ ምርት ጨምር",
        "en": "+ Add Product",
        "om": "+ Meeshaa Ida'i",
    },
    "btn_vendor_orders": {
        "am": "📋 ትዕዛዞች",
        "en": "📋 Orders",
        "om": "📋 Ajajawwan",
    },
    "btn_vendor_stats": {
        "am": "📊 ስታቲስቲክስ",
        "en": "📊 Statistics",
        "om": "📊 Qabiyyee",
    },
    "btn_vendor_settings": {
        "am": "⚙️ ቅንብሮች",
        "en": "⚙️ Settings",
        "om": "⚙️ Qindaa'ina",
    },
    "btn_back_profile": {
        "am": "🔙 ወደ ፕሮፋይል",
        "en": "🔙 Back to Profile",
        "om": "🔙 Profaayiliitti Deebi'i",
    },
    # ── Orders screen ─────────────────────────────────────────────────────────
    "orders_title": {
        "am": "📦 *ትዕዛዞቼ*\n\n",
        "en": "📦 *My Orders*\n\n",
        "om": "📦 *Ajajawwan Koo*\n\n",
    },
    "orders_empty": {
        "am": "📦 *ምንም ትዕዛዞች የሉም*\n\nምርቶችን ለመግዛት /menu ይጫኑ።",
        "en": "📦 *No orders yet*\n\nBrowse products with /menu.",
        "om": "📦 *Ajajni hin jiru*\n\nMeeshaalee ilaaluuf /menu fayyadami.",
    },
    "orders_order": {
        "am": "ትዕዛዝ",
        "en": "Order",
        "om": "Ajajni",
    },
    "btn_prev": {
        "am": "◀️ ቀዳሚ",
        "en": "◀️ Previous",
        "om": "◀️ Duraa",
    },
    "btn_next": {
        "am": "ቀጣይ ▶️",
        "en": "Next ▶️",
        "om": "Itti aanaa ▶️",
    },
    "btn_back_profile2": {
        "am": "🔙 ወደ ፕሮፋይል",
        "en": "🔙 Back to Profile",
        "om": "🔙 Profaayiliitti Deebi'i",
    },
    # ── Contact handler ───────────────────────────────────────────────────────
    "phone_saved": {
        "am": "✅ ስልክ ቁጥርዎ ተመዝግቧል!",
        "en": "✅ Phone number saved!",
        "om": "✅ Lakkoofsi bilbilaa kuufame!",
    },
    "phone_failed": {
        "am": "❌ ስልክ ቁጥሩን ማስቀመጥ አልተቻለም። ቆይቶ እንደገና ይሞክሩ።",
        "en": "❌ Could not save phone number. Please try again later.",
        "om": "❌ Lakkoofsi bilbilaa hin kuufamne. Booda irra deebi'i yaali.",
    },
    "onboarding_done": {
        "am": "🌟 *ዎሎየዋ ስቶር* — ዋና ምናሌ\n\n📌 ከዚህ በታች ካሉት ቁልፎች ይምረጡ።",
        "en": "🌟 *Wolloyewa Store* — Main Menu\n\n📌 Choose from the buttons below.",
        "om": "🌟 *Wolloyewa Store* — Chaartii Ijoo\n\n📌 Armaan gadii keessaa filadhu.",
    },
    # ── Language changed confirmation ────────────────────────────────────────
    "lang_changed": {
        "am": "✅ ቋንቋ ወደ *አማርኛ* ተቀይሯል!",
        "en": "✅ Language changed to *English*!",
        "om": "✅ Afaan *Oromiffa*tti jijjiirameera!",
    },
    # ── Generic error ─────────────────────────────────────────────────────────
    "user_not_found": {
        "am": "❌ ተጠቃሚ አልተገኘም። /start ይጫኑ።",
        "en": "❌ User not found. Please /start again.",
        "om": "❌ Fayyadamaan hin argamne. /start tuqi.",
    },
    "profile_load_failed": {
        "am": "❌ የፕሮፋይል መረጃዎን ማምጣት አልተቻለም። እባክዎ ቆይተው እንደገና ይሞክሩ።",
        "en": "❌ We could not load your profile. Please try again shortly.",
        "om": "❌ Odeeffannoo profaayilii keessanii fiduu hin dandeenye. Booda irra deebi'aa yaalaa.",
    },
    "profile_update_failed": {
        "am": "❌ ለውጡን ማስቀመጥ አልተቻለም። እባክዎ ቆይተው እንደገና ይሞክሩ።",
        "en": "❌ We could not save your change. Please try again shortly.",
        "om": "❌ Jijjiirama olkaa'uu hin dandeenye. Booda irra deebi'aa yaalaa.",
    },
    "profile_photo_prompt": {
        "am": "🖼️ ፕሮፋይልዎ ላይ ለማስቀመጥ ፎቶ ይላኩ። ፋይሉ ከ5 MB በታች ይሁን።",
        "en": "🖼️ Send a photo to use on your profile. Maximum size: 5 MB.",
        "om": "🖼️ Suuraa profaayilii keessanii ta'u ergaa. Hangi isaa 5 MB gadi haa ta'u.",
    },
    "profile_photo_text_hint": {
        "am": "🖼️ እባክዎ ፎቶ ይላኩ ወይም /cancel በመጻፍ ይውጡ።",
        "en": "🖼️ Please send a photo, or tap Cancel to leave this step.",
        "om": "🖼️ Maaloo suuraa ergaa, ykn Cancel tuqaa keessaa bahaa.",
    },
    "profile_update_cancelled": {
        "am": "↩️ ማሻሻያው ተሰርዟል።",
        "en": "↩️ Profile update cancelled.",
        "om": "↩️ Haaromsi profaayilii haqameera.",
    },
    "btn_cancel_update": {
        "am": "❌ ሰርዝ",
        "en": "❌ Cancel",
        "om": "❌ Haqi",
    },
    "profile_photo_too_large": {
        "am": "❌ ፎቶው 5 MB ወይም ከዚያ በታች መሆን አለበት።",
        "en": "❌ Photo must be 5 MB or smaller.",
        "om": "❌ Suuraan 5 MB ykn isaa gadi ta'uu qaba.",
    },
    "profile_photo_saved": {
        "am": "✅ የፕሮፋይል ፎቶዎ ተዘምኗል።",
        "en": "✅ Profile photo updated.",
        "om": "✅ Suuraan profaayilii keessanii haaromfameera.",
    },
}


def t(key: str, lang: str) -> str:
    """Return translated string, falling back to 'am' if lang not found."""
    return _T[key].get(lang) or _T[key].get("am", "")


def _get_lang(context: ContextTypes.DEFAULT_TYPE, user=None) -> str:
    """Resolve display language from context cache or DB user object."""
    lang = context.user_data.get("user", {}).get("language")
    if not lang and user:
        lang = getattr(user, "language", None)
    return lang if lang in SUPPORTED_LANGUAGES else get_language(context)


def _role_label(role, lang: str) -> str:
    roles = {
        "am": {"customer": "ደንበኛ", "vendor": "ሻጭ", "admin": "አስተዳዳሪ", "super_admin": "ዋና አስተዳዳሪ"},
        "en": {
            "customer": "Customer",
            "vendor": "Vendor",
            "admin": "Admin",
            "super_admin": "Super Admin",
        },
        "om": {
            "customer": "Bitaa",
            "vendor": "Gurgurtaa",
            "admin": "Bulchaa",
            "super_admin": "Bulchaa Olaanaa",
        },
    }
    role_str = role.value if hasattr(role, "value") else str(role)
    return roles.get(lang, roles["am"]).get(role_str, role_str)


def _order_status_label(status: str, lang: str) -> str:
    labels = {
        "am": {
            "pending": "⏳ በጥበቃ ላይ",
            "confirmed": "✅ ተረጋግጧል",
            "processing": "🔄 በሂደት ላይ",
            "shipped": "🚚 ተልኳል",
            "delivered": "📦✅ ደርሷል",
            "cancelled": "❌ ተሰርዟል",
        },
        "en": {
            "pending": "⏳ Pending",
            "confirmed": "✅ Confirmed",
            "processing": "🔄 Processing",
            "shipped": "🚚 Shipped",
            "delivered": "📦✅ Delivered",
            "cancelled": "❌ Cancelled",
        },
        "om": {
            "pending": "⏳ Eegamaa",
            "confirmed": "✅ Mirkanaayeera",
            "processing": "🔄 Hojjetamaa",
            "shipped": "🚚 Ergameera",
            "delivered": "📦✅ Geenyeera",
            "cancelled": "❌ Haqameera",
        },
    }
    return labels.get(lang, labels["am"]).get(status, status.upper())


async def _telegram_profile_photo_file_id(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> str | None:
    """Return the largest Telegram profile-photo file ID when the bot can access it."""
    try:
        photos = await context.bot.get_user_profile_photos(user_id=user_id, limit=1)
    except TelegramError as exc:
        logger.warning(
            "Could not retrieve Telegram profile photo for user %s: %s",
            user_id,
            exc,
        )
        return None

    if not photos.photos or not photos.photos[0]:
        return None
    return photos.photos[0][-1].file_id


async def _store_banner_file_id(
    context: ContextTypes.DEFAULT_TYPE,
) -> str | None:
    """Return the cached bot banner photo, fetching it once when needed."""
    cache_key = "start_profile_photo_file_id"
    bot_data = context.bot_data
    if cache_key in bot_data:
        return bot_data[cache_key]

    try:
        bot_user = await context.bot.get_me()
        photos = await context.bot.get_user_profile_photos(
            user_id=bot_user.id,
            limit=1,
        )
    except TelegramError as exc:
        logger.warning("Could not retrieve the store banner photo: %s", exc)
        bot_data[cache_key] = None
        return None

    photo_id = photos.photos[0][-1].file_id if photos.photos and photos.photos[0] else None
    bot_data[cache_key] = photo_id
    return photo_id


async def _profile_photo_candidates(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    stored_photo: str | None,
) -> list[str]:
    """Build profile-photo candidates, preferring the user's Telegram avatar."""
    telegram_photo = await _telegram_profile_photo_file_id(context, user_id)
    banner_photo = await _store_banner_file_id(context)
    return list(
        dict.fromkeys(
            photo
            for photo in (telegram_photo, stored_photo, banner_photo)
            if photo
        )
    )


async def _edit_profile_message(
    query,
    text: str,
    *,
    parse_mode: str | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Edit profile navigation content on either text or media messages."""
    kwargs = {}
    if parse_mode:
        kwargs["parse_mode"] = parse_mode
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup

    try:
        message = getattr(query, "message", None)
        if message and (
            getattr(message, "photo", None) or getattr(message, "document", None)
        ):
            await query.edit_message_caption(
                caption=text,
                **kwargs,
            )
        else:
            await query.edit_message_text(text, **kwargs)
    except BadRequest as exc:
        message = str(exc).casefold()
        if "message is not modified" in message:
            return
        if "there is no text in the message" not in message:
            raise
        await query.message.reply_text(text, **kwargs)


async def _show_profile_card(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    profile_text: str,
    reply_markup: InlineKeyboardMarkup,
    photo_candidates: list[str],
) -> None:
    """Render a profile card as photo+caption when possible, otherwise as text."""
    query = update.callback_query
    message = getattr(query, "message", None) if query else None
    if message and (getattr(message, "photo", None) or getattr(message, "document", None)):
        for photo in photo_candidates:
            try:
                await query.edit_message_media(
                    media=InputMediaPhoto(
                        media=photo,
                        caption=profile_text,
                        parse_mode="Markdown",
                    ),
                    reply_markup=reply_markup,
                )
                return
            except BadRequest as exc:
                if "message is not modified" in str(exc).casefold():
                    return
                logger.warning("Could not edit profile photo message: %s", exc)
            except TelegramError as exc:
                logger.warning("Could not update profile media: %s", exc)

        await _edit_profile_message(
            query,
            profile_text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        return

    if query:
        for photo in photo_candidates:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo,
                    caption=profile_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
                try:
                    await query.message.delete()
                except BadRequest as exc:
                    logger.warning(
                        "Could not remove previous profile menu message: %s", exc
                    )
                return
            except TelegramError as exc:
                logger.warning("Could not send profile photo: %s", exc)

    elif update.effective_chat:
        for photo in photo_candidates:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo,
                    caption=profile_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
                return
            except TelegramError as exc:
                logger.warning("Could not send profile photo: %s", exc)

    if query:
        await _edit_profile_message(
            query,
            profile_text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            profile_text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )


# ---------------------------------------------------------------------------
# Profile screen
# ---------------------------------------------------------------------------


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user profile — all text and buttons in the user's saved language."""
    tg_user = update.effective_user
    if tg_user is None:
        logger.error("Cannot show profile for update without an effective user")
        return
    tg_id = tg_user.id

    user = None
    stats = {}
    vendor_is_approved = False
    vendor_application_pending = False
    try:
        async for db in get_db_session():
            user_service = UserService(db)
            user = await user_service.get_user_by_telegram(tg_id)
            if user:
                stats = await user_service.get_user_stats(user.id)
                vendor = await VendorService(db).get_vendor_by_user(user.id)
                if vendor:
                    vendor_is_approved = vendor.is_approved
                    vendor_application_pending = (
                        not vendor.is_approved and vendor.rejected_at is None
                    )
            break
    except SQLAlchemyError:
        logger.exception("Could not load profile data for Telegram user %s", tg_id)
        await update.effective_message.reply_text(
            t("profile_load_failed", _get_lang(context))
        )
        return

    if user is None:
        await update.effective_message.reply_text(
            t("user_not_found", _get_lang(context))
        )
        return

    lang = _get_lang(context, user)
    ns = t("not_set", lang)
    full_name = (
        getattr(user, "full_name", None)
        or getattr(user, "first_name", None)
        or ns
    )
    username = getattr(user, "username", None) or "N/A"
    phone_number = getattr(user, "phone_number", None) or ns
    email = getattr(user, "email", None) or ns
    role = getattr(user, "role", None)
    created_at = getattr(user, "created_at", None)
    joined = created_at.strftime("%Y-%m-%d") if created_at else ns

    addresses = getattr(user, "addresses", None) or []
    address = next(
        (item for item in addresses if getattr(item, "is_default", False)),
        addresses[0] if addresses else None,
    )
    address_parts = (
        [
            getattr(address, "address_line1", None),
            getattr(address, "address_line2", None),
            getattr(address, "subcity", None),
            getattr(address, "city", None),
            getattr(address, "woreda", None),
            getattr(address, "house_number", None),
        ]
        if address
        else []
    )
    address_text = ", ".join(
        str(part).strip() for part in address_parts if part and str(part).strip()
    ) or ns

    profile_text = (
        f"{t('profile_title', lang)}\n\n"
        f"{t('field_name', lang)} {escape_markdown(str(full_name), version=1)}\n"
        f"{t('field_username', lang)} @{escape_markdown(str(username), version=1)}\n"
        f"{t('field_phone', lang)} {escape_markdown(str(phone_number), version=1)}\n"
        f"{t('field_email', lang)} {escape_markdown(str(email), version=1)}\n"
        f"{t('field_address', lang)} {escape_markdown(address_text, version=1)}\n"
        f"{t('field_role', lang)} {_role_label(role or 'customer', lang)}\n"
        f"{t('field_joined', lang)} {joined}\n\n"
        f"{t('stats_title',  lang)}\n"
        f"{t('stats_orders', lang)} {stats.get('total_orders') or 0}\n"
        f"{t('stats_spent',  lang)} {format_etb(stats.get('total_spent') or 0)}\n"
        f"{t('stats_avg',    lang)} {format_etb(stats.get('average_order_value') or 0)}"
    )

    keyboard = [
        [InlineKeyboardButton(t("btn_update_photo", lang), callback_data="profile_update_photo")],
        [InlineKeyboardButton(t("btn_update_phone", lang), callback_data="profile_update_phone")],
        [InlineKeyboardButton(t("btn_update_email", lang), callback_data="profile_update_email")],
        [InlineKeyboardButton(t("btn_change_lang", lang), callback_data="profile_change_language")],
        [InlineKeyboardButton(t("btn_my_orders", lang), callback_data="profile_orders")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="menu_back")],
    ]

    if vendor_is_approved:
        keyboard.insert(
            0,
            [
                InlineKeyboardButton(
                    t("btn_vendor_panel", lang), callback_data="profile_vendor_panel"
                )
            ],
        )
    elif vendor_application_pending:
        keyboard.insert(
            0,
            [
                InlineKeyboardButton(
                    "⏳ Vendor application under review",
                    callback_data="profile_become_vendor",
                )
            ],
        )
    else:
        keyboard.insert(
            0,
            [InlineKeyboardButton(t("btn_become_vendor", lang), callback_data="profile_become_vendor")],
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    photo_candidates = await _profile_photo_candidates(
        context,
        tg_id,
        getattr(user, "profile_picture", None),
    )
    await _show_profile_card(
        update,
        context,
        profile_text,
        reply_markup,
        photo_candidates,
    )


# ---------------------------------------------------------------------------
# Orders screen
# ---------------------------------------------------------------------------


async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show order history — all text and buttons in the user's saved language."""
    tg_id = update.effective_user.id
    page = context.user_data.get("orders_page", 1)
    page_size = 5

    user = None
    orders = []
    total = 0
    async for db in get_db_session():
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(tg_id)
        if not user:
            await update.effective_message.reply_text(t("user_not_found", "am"))
            return
        order_service = OrderService(db)
        orders, total = await order_service.get_user_orders(
            user_id=user.id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        break

    lang = _get_lang(context, user)

    if not orders:
        await update.effective_message.reply_text(t("orders_empty", lang), parse_mode="Markdown")
        return

    orders_text = t("orders_title", lang)
    for order in orders:
        status = _order_status_label(str(order.status), lang)
        orders_text += (
            f"*{t('orders_order', lang)} #{order.order_number}*\n"
            f"   📅 {order.created_at.strftime('%Y-%m-%d')}\n"
            f"   💰 {format_etb(order.total)}\n"
            f"   {status}\n\n"
        )

    total_pages = (total + page_size - 1) // page_size
    keyboard = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(t("btn_prev", lang), callback_data=f"orders_page_{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(t("btn_next", lang), callback_data=f"orders_page_{page+1}"))
    if nav:
        keyboard.append(nav)
    keyboard.append(
        [InlineKeyboardButton(t("btn_back_profile2", lang), callback_data="menu_profile")]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await _edit_profile_message(
            update.callback_query,
            orders_text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    else:
        await update.effective_message.reply_text(
            orders_text, parse_mode="Markdown", reply_markup=reply_markup
        )


# ---------------------------------------------------------------------------
# Profile callback router
# ---------------------------------------------------------------------------


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all profile_* callback queries."""
    query = update.callback_query
    if not await answer_callback_query(query):
        return

    action = query.data
    lang = _get_lang(context)

    if action == "profile_orders":
        context.user_data["orders_page"] = 1
        await orders_command(update, context)

    elif action == "profile_update_phone":
        context.user_data["updating_field"] = "phone"
        await query.message.reply_text(
            t("phone_prompt", lang),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(t("btn_cancel_update", lang), callback_data="profile_cancel_update")]]
            ),
        )

    elif action == "profile_update_photo":
        context.user_data["updating_field"] = "profile_picture"
        await query.message.reply_text(
            t("profile_photo_prompt", lang),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(t("btn_cancel_update", lang), callback_data="profile_cancel_update")]]
            ),
        )

    elif action == "profile_update_email":
        context.user_data["updating_field"] = "email"
        await query.message.reply_text(
            t("email_prompt", lang),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(t("btn_cancel_update", lang), callback_data="profile_cancel_update")]]
            ),
        )

    elif action == "profile_cancel_update":
        context.user_data.pop("updating_field", None)
        await query.message.reply_text(t("profile_update_cancelled", lang))

    elif action == "profile_change_language":
        keyboard = [
            [InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am")],
            [InlineKeyboardButton("🌐 English", callback_data="lang_en")],
            [InlineKeyboardButton("🟢 Oromiffa", callback_data="lang_om")],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu_profile")],
        ]
        await _edit_profile_message(
            query,
            t("lang_select_title", lang),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif action == "profile_become_vendor":
        from bot.handlers.vendor_registration import start_application

        await start_application(update, context)

    elif action == "profile_vendor_panel":
        await show_vendor_panel(update, context)


async def orders_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle orders_page_<number> pagination buttons."""
    query = update.callback_query
    try:
        page = max(1, int(query.data.rsplit("_", 1)[1]))
    except (ValueError, IndexError):
        await answer_callback_query(
            query, "❌ የገጽ ቁጥሩ ልክ አይደለም፣", show_alert=True
        )
        return
    if not await answer_callback_query(query):
        return
    context.user_data["orders_page"] = page
    await orders_command(update, context)


async def vendor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle vendor dashboard buttons with a useful response instead of dead clicks."""
    query = update.callback_query
    if not await answer_callback_query(query):
        return

    action = query.data
    lang = _get_lang(context)

    if action == "vendor_products":
        await _edit_profile_message(
            query,
            "📦 *ምርቶቼ*\n\nየሻጭ ምርቶችን ለማስተዳደር የአስተዳዳሪ ፓነልን ወይም የድጋፍ ቡድንን ያግኙ።",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            t("btn_back_profile", lang), callback_data="profile_vendor_panel"
                        )
                    ]
                ]
            ),
        )
    elif action == "vendor_add_product":
        await _edit_profile_message(
            query,
            "+ *አዲስ ምርት ለመጨመር*\n\nእባክዎ ለማስገባት የምርቱን መረጃ ለአስተዳዳሪ ይላኩ።",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            t("btn_back_profile", lang), callback_data="profile_vendor_panel"
                        )
                    ]
                ]
            ),
        )
    elif action == "vendor_orders":
        await _edit_profile_message(
            query,
            "📦 *የሻጭ ትዕዛዞች*\n\nየሻጭ ትዕዛዝ መረጃ ሲኖር እዚህ ይታያል።",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            t("btn_back_profile", lang), callback_data="profile_vendor_panel"
                        )
                    ]
                ]
            ),
        )
    elif action == "vendor_stats":
        await _edit_profile_message(
            query,
            "📊 *የሽያጭ ስታቲስቲክስ*\n\nስታቲስቲክስ ለማየት የሽያጭ እንቅስቃሴ እስኪመዘገብ ይጠብቁ።",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            t("btn_back_profile", lang), callback_data="profile_vendor_panel"
                        )
                    ]
                ]
            ),
        )
    elif action == "vendor_settings":
        await _edit_profile_message(
            query,
            "⚙️ *የሻጭ ቅንብሮች*\n\nለውጦችን ለማድረግ የድጋፍ ቡድንን ያግኙ።",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            t("btn_back_profile", lang), callback_data="profile_vendor_panel"
                        )
                    ]
                ]
            ),
        )


# ---------------------------------------------------------------------------
# Language change handler  (lang_am / lang_en / lang_om from Profile)
# ---------------------------------------------------------------------------


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle lang_am / lang_en / lang_om callback from the Profile language picker.
    Saves new language to DB, refreshes the middleware cache, and re-opens Profile.
    """
    query = update.callback_query
    new_lang = query.data.removeprefix("lang_")
    if new_lang not in SUPPORTED_LANGUAGES:
        await answer_callback_query(
            query, "Unsupported language.", show_alert=True
        )
        return
    if not await answer_callback_query(query):
        return
    tg_id = update.effective_user.id

    user_found = False
    try:
        async with transaction_session() as db:
            user_service = UserService(db)
            user = await user_service.get_user_by_telegram(tg_id)
            if user:
                await user_service.update_user(user.id, UserUpdate(language=new_lang))
                user_found = True
    except SQLAlchemyError:
        logger.exception("Could not update language for Telegram user %s", tg_id)
        await query.message.reply_text(t("profile_update_failed", new_lang))
        return

    if not user_found:
        logger.error("Could not change language: user %s was not found", tg_id)
        await query.message.reply_text(t("user_not_found", new_lang))
        return

    # Refresh middleware cache so subsequent handlers see the new language
    from bot.middlewares.auth import auth_middleware

    auth_middleware.invalidate(tg_id)

    # Also update the in-memory user_data so this same message sees the change
    if "user" in context.user_data:
        context.user_data["user"]["language"] = new_lang
    context.user_data["language"] = new_lang

    # Confirm with a short toast-style message, then reopen profile
    await _edit_profile_message(query, t("lang_changed", new_lang), parse_mode="Markdown")
    # Reload the profile screen in the new language
    await profile_command(update, context)


# ---------------------------------------------------------------------------
# Vendor panel
# ---------------------------------------------------------------------------


async def show_vendor_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show vendor dashboard — buttons in the user's saved language."""
    query = update.callback_query
    lang = _get_lang(context)
    tg_user = update.effective_user
    vendor_is_approved = False
    if tg_user:
        async for db in get_db_session():
            user = await UserService(db).get_user_by_telegram(tg_user.id)
            if user:
                vendor = await VendorService(db).get_vendor_by_user(user.id)
                vendor_is_approved = bool(vendor and vendor.is_approved)
            break

    if not vendor_is_approved:
        await profile_command(update, context)
        return

    keyboard = [
        [InlineKeyboardButton(t("btn_my_products", lang), callback_data="vendor_products")],
        [InlineKeyboardButton(t("btn_add_product", lang), callback_data="vendor_add_product")],
        [InlineKeyboardButton(t("btn_vendor_orders", lang), callback_data="vendor_orders")],
        [InlineKeyboardButton(t("btn_vendor_stats", lang), callback_data="vendor_stats")],
        [InlineKeyboardButton(t("btn_vendor_settings", lang), callback_data="vendor_settings")],
        [InlineKeyboardButton(t("btn_back_profile", lang), callback_data="menu_profile")],
    ]

    if query:
        await _edit_profile_message(
            query,
            t("vendor_panel_title", lang),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await update.effective_message.reply_text(
            t("vendor_panel_title", lang),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# ---------------------------------------------------------------------------
# Contact handler — phone sharing (onboarding Step 2 OR profile update)
# ---------------------------------------------------------------------------


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle contact sharing.

    Situations:
    1. New-user onboarding — /start → lang selected → phone shared → main menu
    2. Profile update      — "📞 Update Phone" button → contact shared → stay in profile
    """
    if context.user_data.get("checkout_in_progress"):
        if not context.user_data.get("checkout_conversation_active"):
            context.user_data.pop("checkout_in_progress", None)
            await update.message.reply_text(
                tr(context, "checkout_session_expired"),
                reply_markup=ReplyKeyboardRemove(),
            )
        return

    contact = update.message.contact
    tg_user = update.effective_user
    if not contact:
        return

    lang = _get_lang(context)
    try:
        phone_number = Validator.phone(contact.phone_number, normalize=True)
    except ValueError:
        await update.message.reply_text(
            t("phone_invalid", lang),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    saved = await _save_profile_update(
        tg_user.id,
        UserUpdate(phone_number=phone_number),
        context,
    )

    await update.message.reply_text(
        t("phone_saved", lang) if saved else t("phone_failed", lang),
        reply_markup=ReplyKeyboardRemove(),
    )

    if not saved:
        return

    from bot.keyboards.reply import main_reply_keyboard

    if context.user_data.pop("onboarding", False):
        # Onboarding complete — open the main menu in the user's chosen language
        from bot.handlers.start import _build_main_menu
        from core.config import settings

        # lang may have been set during onboarding (onboarding_lang key)
        lang = context.user_data.pop("onboarding_lang", lang)
        is_admin = tg_user.id in settings.admin_ids_list
        await update.message.reply_text(
            t("onboarding_done", lang),
            parse_mode="Markdown",
            reply_markup=_build_main_menu(is_admin, lang),
        )
        await update.message.reply_text(
            tr(context, "menu_keyboard_hint"),
            reply_markup=main_reply_keyboard(lang),
        )
    else:
        await update.message.reply_text(
            tr(context, "menu_keyboard_hint"),
            reply_markup=main_reply_keyboard(lang),
        )


async def profile_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save text entered after the profile email/update prompts."""
    if "vendor_application_step" in context.user_data:
        from bot.handlers.vendor_registration import handle_text

        await handle_text(update, context)
        return

    field = context.user_data.get("updating_field")
    message_text = (update.effective_message.text or "").strip().casefold()
    if field and message_text in {
        "cancel",
        "❌ cancel",
        "ሰርዝ",
        "❌ ሰርዝ",
        "haqi",
        "❌ haqi",
        "back",
        "🔙 back",
        "deebi'i",
    }:
        mark_text_message_handled(update, context)
        context.user_data.pop("updating_field", None)
        await update.effective_message.reply_text(
            t("profile_update_cancelled", _get_lang(context))
        )
        return
    if field == "phone":
        mark_text_message_handled(update, context)
        value = (update.effective_message.text or "").strip()
        try:
            value = Validator.phone(value, normalize=True)
        except ValueError:
            await update.effective_message.reply_text(t("phone_invalid", _get_lang(context)))
            return
        saved = await _save_profile_update(
            update.effective_user.id,
            UserUpdate(phone_number=value),
            context,
        )
        if saved:
            context.user_data.pop("updating_field", None)
        await update.effective_message.reply_text(
            t("phone_saved", _get_lang(context)) if saved else t("phone_failed", _get_lang(context))
        )
        return
    if field == "profile_picture":
        mark_text_message_handled(update, context)
        await update.effective_message.reply_text(
            t("profile_photo_text_hint", _get_lang(context))
        )
        return
    if field != "email":
        return
    mark_text_message_handled(update, context)
    value = (update.effective_message.text or "").strip()
    try:
        value = Validator.email(value)
    except ValueError:
        await update.effective_message.reply_text(t("email_invalid", _get_lang(context)))
        return

    saved = await _save_profile_update(
        update.effective_user.id,
        UserUpdate(email=value),
        context,
    )
    if saved:
        context.user_data.pop("updating_field", None)
    await update.effective_message.reply_text(
        t("email_saved", _get_lang(context)) if saved else t("email_failed", _get_lang(context))
    )


async def profile_photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Save a user-uploaded Telegram photo file ID as their profile image."""
    if context.user_data.get("vendor_application_step") == 2:
        from bot.handlers.vendor_registration import handle_document

        await handle_document(update, context)
        return

    if context.user_data.get("updating_field") != "profile_picture":
        return

    message = update.effective_message
    user = update.effective_user
    photos = getattr(message, "photo", None) if message else None
    if user is None or not photos:
        if message:
            await message.reply_text(t("profile_load_failed", _get_lang(context)))
        return

    largest_photo = max(photos, key=lambda item: item.file_size or 0)
    if largest_photo.file_size and largest_photo.file_size > 5 * 1024 * 1024:
        await message.reply_text(t("profile_photo_too_large", _get_lang(context)))
        return

    saved = await _save_profile_update(
        user.id,
        UserUpdate(profile_picture=largest_photo.file_id),
        context,
    )
    if not saved:
        await message.reply_text(t("profile_update_failed", _get_lang(context)))
        return

    context.user_data.pop("updating_field", None)
    await message.reply_text(t("profile_photo_saved", _get_lang(context)))
    await profile_command(update, context)


async def _save_profile_update(
    telegram_id: int,
    data: UserUpdate,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Commit a profile update before reporting success or refreshing the user cache."""
    try:
        async with transaction_session() as db:
            user_service = UserService(db)
            user = await user_service.get_user_by_telegram(telegram_id)
            if not user:
                return False
            updated_user = await user_service.update_user(user.id, data)
    except SQLAlchemyError:
        logger.exception("Could not update profile for Telegram user %s", telegram_id)
        return False
    except NotFoundError:
        logger.warning(
            "Profile disappeared while updating Telegram user %s", telegram_id
        )
        return False

    from bot.middlewares.auth import auth_middleware

    auth_middleware.invalidate(telegram_id)
    cached_user = context.user_data.setdefault("user", {})
    for field in data.model_fields_set:
        cached_user[field] = getattr(updated_user, field)
    return True


# ---------------------------------------------------------------------------
# Legacy helper (kept for any caller that still imports it)
# ---------------------------------------------------------------------------


def get_role_amharic(role) -> str:
    return _role_label(role, "am")


__all__ = [
    "contact_handler",
    "get_role_amharic",
    "language_callback",
    "orders_command",
    "orders_page_callback",
    "profile_callback",
    "profile_command",
    "profile_photo_handler",
    "profile_text_handler",
    "show_vendor_panel",
    "vendor_callback",
]
