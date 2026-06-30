# ============================
# WOLLOYEWA STORE BOT - PROFILE HANDLER
# ============================
"""Telegram bot user profile and order history handlers — full i18n support."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from core.logger import logger
from core.utils.currency import format_etb
from apps.users.services import UserService, VendorService
from apps.orders.services import OrderService
from apps.users.schemas import UserUpdate
from infrastructure.database.session import get_db_session


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
    # ── Vendor application ───────────────────────────────────────────────────
    "vendor_apply_title": {
        "am": "🏪 *ሻጅ ለመሆን ማመልከቻ*",
        "en": "🏪 *Vendor Application*",
        "om": "🏪 *Iyyannoo Gurgurtaa*",
    },
    "vendor_apply_body": {
        "am": (
            "ሻጅ ለመሆን ከዚህ በታች ያለውን ፎርም ይሙሉ:\n\n"
            "1. የንግድ ስም\n"
            "2. የንግድ ፈቃድ ቁጥር\n"
            "3. የግብር ተመዝጋቢ ቁጥር (TIN)\n"
            "4. የንግድ አድራሻ\n\n"
            "እባክዎ መረጃዎችን በመልዕክት ይላኩ።"
        ),
        "en": (
            "Fill in the form below to become a vendor:\n\n"
            "1. Business name\n"
            "2. Business license number\n"
            "3. Tax ID (TIN)\n"
            "4. Business address\n\n"
            "Please send the information as a message."
        ),
        "om": (
            "Gurgurtaa ta'uuf foormii armaan gadii guuti:\n\n"
            "1. Maqaa daldalaa\n"
            "2. Lakkoofsa hayyama daldalaa\n"
            "3. Lakkoofsa gibiraa (TIN)\n"
            "4. Teessoo daldalaa\n\n"
            "Odeeffannoo ergii."
        ),
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
        "am": "➕ ምርት ጨምር",
        "en": "➕ Add Product",
        "om": "➕ Meeshaa Ida'i",
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
}


def t(key: str, lang: str) -> str:
    """Return translated string, falling back to 'am' if lang not found."""
    return _T[key].get(lang) or _T[key].get("am", "")


def _get_lang(context: ContextTypes.DEFAULT_TYPE, user=None) -> str:
    """Resolve display language from context cache or DB user object."""
    lang = context.user_data.get("user", {}).get("language")
    if not lang and user:
        lang = getattr(user, "language", None)
    return lang or "am"


def _role_label(role, lang: str) -> str:
    roles = {
        "am": {"customer": "ደንበኛ", "vendor": "ሻጭ", "admin": "አስተዳዳሪ", "super_admin": "ዋና አስተዳዳሪ"},
        "en": {"customer": "Customer", "vendor": "Vendor", "admin": "Admin", "super_admin": "Super Admin"},
        "om": {"customer": "Bitaa", "vendor": "Gurgurtaa", "admin": "Bulchaa", "super_admin": "Bulchaa Olaanaa"},
    }
    role_str = role.value if hasattr(role, "value") else str(role)
    return roles.get(lang, roles["am"]).get(role_str, role_str)


def _order_status_label(status: str, lang: str) -> str:
    labels = {
        "am": {
            "pending": "⏳ በጥበቃ ላይ", "confirmed": "✅ ተረጋግጧል",
            "processing": "🔄 በሂደት ላይ", "shipped": "🚚 ተልኳል",
            "delivered": "📦✅ ደርሷል", "cancelled": "❌ ተሰርዟል",
        },
        "en": {
            "pending": "⏳ Pending", "confirmed": "✅ Confirmed",
            "processing": "🔄 Processing", "shipped": "🚚 Shipped",
            "delivered": "📦✅ Delivered", "cancelled": "❌ Cancelled",
        },
        "om": {
            "pending": "⏳ Eegamaa", "confirmed": "✅ Mirkanaayeera",
            "processing": "🔄 Hojjetamaa", "shipped": "🚚 Ergameera",
            "delivered": "📦✅ Geenyeera", "cancelled": "❌ Haqameera",
        },
    }
    return labels.get(lang, labels["am"]).get(status, status.upper())


# ---------------------------------------------------------------------------
# Profile screen
# ---------------------------------------------------------------------------

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user profile — all text and buttons in the user's saved language."""
    tg_id = update.effective_user.id

    user = None
    stats = {}
    async for db in get_db_session():
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(tg_id)
        if not user:
            await update.effective_message.reply_text(t("user_not_found", "am"))
            return
        stats = await user_service.get_user_stats(user.id)
        break

    lang = _get_lang(context, user)
    ns = t("not_set", lang)

    profile_text = (
        f"{t('profile_title', lang)}\n\n"
        f"{t('field_name',     lang)} {getattr(user, 'full_name', user.first_name)}\n"
        f"{t('field_username', lang)} @{user.username or 'N/A'}\n"
        f"{t('field_phone',    lang)} {user.phone_number or ns}\n"
        f"{t('field_email',    lang)} {user.email or ns}\n"
        f"{t('field_role',     lang)} {_role_label(user.role, lang)}\n"
        f"{t('field_joined',   lang)} {user.created_at.strftime('%Y-%m-%d')}\n\n"
        f"{t('stats_title',  lang)}\n"
        f"{t('stats_orders', lang)} {stats.get('total_orders', 0)}\n"
        f"{t('stats_spent',  lang)} {format_etb(stats.get('total_spent', 0))}\n"
        f"{t('stats_avg',    lang)} {format_etb(stats.get('average_order_value', 0))}"
    )

    keyboard = [
        [InlineKeyboardButton(t("btn_update_phone",   lang), callback_data="profile_update_phone")],
        [InlineKeyboardButton(t("btn_update_email",   lang), callback_data="profile_update_email")],
        [InlineKeyboardButton(t("btn_change_lang",    lang), callback_data="profile_change_language")],
        [InlineKeyboardButton(t("btn_my_orders",      lang), callback_data="profile_orders")],
        [InlineKeyboardButton(t("btn_become_vendor",  lang), callback_data="profile_become_vendor")],
        [InlineKeyboardButton(t("btn_back",           lang), callback_data="menu_back")],
    ]

    # Vendor panel shortcut
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_str == "vendor":
        async for db in get_db_session():
            vendor_service = VendorService(db)
            vendor = await vendor_service.get_vendor_by_user(user.id)
            if vendor:
                keyboard.insert(0, [InlineKeyboardButton(
                    t("btn_vendor_panel", lang), callback_data="profile_vendor_panel"
                )])
            break

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(
            profile_text, parse_mode="Markdown", reply_markup=reply_markup
        )
        await update.callback_query.answer()
    else:
        await update.effective_message.reply_text(
            profile_text, parse_mode="Markdown", reply_markup=reply_markup
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
        await update.effective_message.reply_text(
            t("orders_empty", lang), parse_mode="Markdown"
        )
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
    keyboard.append([InlineKeyboardButton(t("btn_back_profile2", lang), callback_data="menu_profile")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(
            orders_text, parse_mode="Markdown", reply_markup=reply_markup
        )
        await update.callback_query.answer()
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
    await query.answer()

    action = query.data
    lang = _get_lang(context)

    if action == "profile_orders":
        context.user_data["orders_page"] = 1
        await orders_command(update, context)

    elif action == "profile_update_phone":
        context.user_data["updating_field"] = "phone"
        await query.message.reply_text(t("phone_prompt", lang))

    elif action == "profile_update_email":
        context.user_data["updating_field"] = "email"
        await query.message.reply_text(t("email_prompt", lang))

    elif action == "profile_change_language":
        keyboard = [
            [InlineKeyboardButton("🇪🇹 አማርኛ",  callback_data="lang_am")],
            [InlineKeyboardButton("🌐 English", callback_data="lang_en")],
            [InlineKeyboardButton("🟢 Oromiffa", callback_data="lang_om")],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="menu_profile")],
        ]
        await query.message.edit_text(
            t("lang_select_title", lang),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif action == "profile_become_vendor":
        await query.message.reply_text(
            f"{t('vendor_apply_title', lang)}\n\n{t('vendor_apply_body', lang)}",
            parse_mode="Markdown",
        )
        context.user_data["vendor_application"] = True

    elif action == "profile_vendor_panel":
        await show_vendor_panel(update, context)


# ---------------------------------------------------------------------------
# Language change handler  (lang_am / lang_en / lang_om from Profile)
# ---------------------------------------------------------------------------

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle lang_am / lang_en / lang_om callback from the Profile language picker.
    Saves new language to DB, refreshes the middleware cache, and re-opens Profile.
    """
    query = update.callback_query
    await query.answer()

    new_lang = query.data.replace("lang_", "")   # "am" | "en" | "om"
    tg_id = update.effective_user.id

    async for db in get_db_session():
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(tg_id)
        if user:
            await user_service.update_user(user.id, UserUpdate(language=new_lang))
        break

    # Refresh middleware cache so subsequent handlers see the new language
    from bot.middlewares.auth import auth_middleware
    auth_middleware.invalidate(tg_id)

    # Also update the in-memory user_data so this same message sees the change
    if "user" in context.user_data:
        context.user_data["user"]["language"] = new_lang

    # Confirm with a short toast-style message, then reopen profile
    await query.edit_message_text(
        t("lang_changed", new_lang), parse_mode="Markdown"
    )
    # Reload the profile screen in the new language
    await profile_command(update, context)


# ---------------------------------------------------------------------------
# Vendor panel
# ---------------------------------------------------------------------------

async def show_vendor_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show vendor dashboard — buttons in the user's saved language."""
    query = update.callback_query
    lang = _get_lang(context)

    keyboard = [
        [InlineKeyboardButton(t("btn_my_products",    lang), callback_data="vendor_products")],
        [InlineKeyboardButton(t("btn_add_product",    lang), callback_data="vendor_add_product")],
        [InlineKeyboardButton(t("btn_vendor_orders",  lang), callback_data="vendor_orders")],
        [InlineKeyboardButton(t("btn_vendor_stats",   lang), callback_data="vendor_stats")],
        [InlineKeyboardButton(t("btn_vendor_settings",lang), callback_data="vendor_settings")],
        [InlineKeyboardButton(t("btn_back_profile",   lang), callback_data="menu_profile")],
    ]

    await query.message.edit_text(
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
    contact = update.message.contact
    tg_user = update.effective_user
    if not contact:
        return

    phone_number = contact.phone_number
    lang = _get_lang(context)

    saved = False
    async for db in get_db_session():
        try:
            user_service = UserService(db)
            user = await user_service.get_user_by_telegram(tg_user.id)
            if user:
                await user_service.update_user(user.id, UserUpdate(phone_number=phone_number))
                from bot.middlewares.auth import auth_middleware
                auth_middleware.invalidate(tg_user.id)
                if "user" in context.user_data:
                    context.user_data["user"]["phone_number"] = phone_number
                saved = True
        except Exception as e:
            logger.error(f"contact_handler: failed to save phone {phone_number} for {tg_user.id}: {e}")
        break

    await update.message.reply_text(
        t("phone_saved", lang) if saved else t("phone_failed", lang),
        reply_markup=ReplyKeyboardRemove(),
    )

    if not saved:
        return

    if context.user_data.pop("onboarding", False):
        # Onboarding complete — open the main menu in the user's chosen language
        from core.config import settings
        from bot.handlers.start import _build_main_menu

        # lang may have been set during onboarding (onboarding_lang key)
        lang = context.user_data.pop("onboarding_lang", lang)
        is_admin = tg_user.id in settings.admin_ids_list
        await update.message.reply_text(
            t("onboarding_done", lang),
            parse_mode="Markdown",
            reply_markup=_build_main_menu(is_admin, lang),
        )


# ---------------------------------------------------------------------------
# Legacy helper (kept for any caller that still imports it)
# ---------------------------------------------------------------------------

def get_role_amharic(role) -> str:
    return _role_label(role, "am")


__all__ = [
    "profile_command",
    "orders_command",
    "profile_callback",
    "language_callback",
    "contact_handler",
    "show_vendor_panel",
    "get_role_amharic",
]
