# ============================
# WOLLOYEWA STORE BOT - PROFILE HANDLER
# ============================
"""Telegram bot user profile and order history handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from core.logger import logger
from core.utils.currency import format_etb
from apps.users.services import UserService, VendorService
from apps.orders.services import OrderService
from apps.users.schemas import UserUpdate
from infrastructure.database.session import get_db_session


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /profile command.
    
    Shows user profile information.
    """
    user_id = update.effective_user.id
    
    async for db in get_db_session():
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(user_id)
        
        if not user:
            await update.effective_message.reply_text("❌ ተጠቃሚ አልተገኘም።")
            return
        
        # Get user stats
        stats = await user_service.get_user_stats(user.id)
        
        break
    
    # Build profile message
    profile_text = f"""
👤 *ፕሮፋይል*

🆔 *ስም:* {user.full_name}
📝 *የተጠቃሚ ስም:* @{user.username or 'N/A'}
📞 *ስልክ:* {user.phone_number or 'አልተመዘገበም'}
📧 *ኢሜይል:* {user.email or 'አልተመዘገበም'}
⭐ *ሚና:* {get_role_amharic(user.role)}
📅 *የተመዘገበበት:* {user.created_at.strftime('%Y-%m-%d')}

📊 *ስታቲስቲክስ:*
• 🛒 *ጠቅላላ ትዕዛዞች:* {stats.get('total_orders', 0)}
• 💰 *ጠቅላላ ወጪ:* {format_etb(stats.get('total_spent', 0))}
• 📦 *አማካይ ትዕዛዝ:* {format_etb(stats.get('average_order_value', 0))}
    """
    
    # Build keyboard
    keyboard = [
        [InlineKeyboardButton("📞 ስልክ አዘምን", callback_data="profile_update_phone")],
        [InlineKeyboardButton("📧 ኢሜይል አዘምን", callback_data="profile_update_email")],
        [InlineKeyboardButton("🌐 ቋንቋ ቀይር", callback_data="profile_change_language")],
        [InlineKeyboardButton("📦 ትዕዛዞቼ", callback_data="profile_orders")],
        [InlineKeyboardButton("🏪 ሻጭ ለመሆን ያመልክቱ", callback_data="profile_become_vendor")],
        [InlineKeyboardButton("🔙 ወደ ኋላ", callback_data="menu_back")],
    ]
    
    # Add vendor stats if user is vendor
    if user.role == "vendor":
        async for db in get_db_session():
            vendor_service = VendorService(db)
            vendor = await vendor_service.get_vendor_by_user(user.id)
            if vendor:
                keyboard.insert(2, [InlineKeyboardButton("🏪 የሻጭ ፓነል", callback_data="profile_vendor_panel")])
            break
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            profile_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        await update.callback_query.answer()
    else:
        await update.effective_message.reply_text(
            profile_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /orders command.
    
    Shows user's order history.
    """
    user_id = update.effective_user.id
    page = context.user_data.get("orders_page", 1)
    page_size = 5
    
    async for db in get_db_session():
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(user_id)
        
        if not user:
            await update.effective_message.reply_text("❌ ተጠቃሚ አልተገኘም።")
            return
        
        order_service = OrderService(db)
        orders, total = await order_service.get_user_orders(
            user_id=user.id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        
        break
    
    if not orders:
        await update.effective_message.reply_text(
            "📦 *ምንም ትዕዛዞች የሉም*\n\n"
            "ምርቶችን ለመግዛት /menu ይጫኑ።",
            parse_mode="Markdown"
        )
        return
    
    # Build orders message
    orders_text = "📦 *ትዕዛዞቼ*\n\n"
    
    for order in orders:
        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "processing": "🔄",
            "shipped": "🚚",
            "delivered": "📦✅",
            "cancelled": "❌",
        }.get(order.status, "📋")
        
        orders_text += f"{status_emoji} *ትዕዛዝ #{order.order_number}*\n"
        orders_text += f"   📅 {order.created_at.strftime('%Y-%m-%d')}\n"
        orders_text += f"   💰 {format_etb(order.total)}\n"
        orders_text += f"   📍 {order.status.upper()}\n\n"
    
    # Pagination
    total_pages = (total + page_size - 1) // page_size
    keyboard = []
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data=f"orders_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data=f"orders_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 ወደ ፕሮፋይል", callback_data="menu_profile")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            orders_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        await update.callback_query.answer()
    else:
        await update.effective_message.reply_text(
            orders_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle profile-related callback queries.
    """
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "profile_orders":
        context.user_data["orders_page"] = 1
        await orders_command(update, context)
    
    elif action == "profile_update_phone":
        context.user_data["updating_field"] = "phone"
        await query.message.reply_text(
            "📞 እባክዎ ስልክ ቁጥርዎን ይላኩ (ቅርጸት: 09XXXXXXXX):"
        )
    
    elif action == "profile_update_email":
        context.user_data["updating_field"] = "email"
        await query.message.reply_text(
            "📧 እባክዎ ኢሜይል አድራሻዎን ይላኩ:"
        )
    
    elif action == "profile_change_language":
        keyboard = [
            [InlineKeyboardButton("አማርኛ", callback_data="lang_am")],
            [InlineKeyboardButton("English", callback_data="lang_en")],
            [InlineKeyboardButton("Oromiffa", callback_data="lang_om")],
            [InlineKeyboardButton("🔙 ወደ ኋላ", callback_data="menu_profile")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "🌐 *ቋንቋ ይምረጡ*\n\nእባክዎ የሚፈልጉትን ቋንቋ ይምረጡ።",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif action == "profile_become_vendor":
        await query.message.reply_text(
            "🏪 *ሻጅ ለመሆን ማመልከቻ*\n\n"
            "ሻጅ ለመሆን ከዚህ በታች ያለውን ፎርም ይሙሉ:\n\n"
            "1. የንግድ ስም\n"
            "2. የንግድ ፈቃድ ቁጥር\n"
            "3. የግብር ተመዝጋቢ ቁጥር (TIN)\n"
            "4. የንግድ አድራሻ\n\n"
            "እባክዎ መረጃዎችን በመልዕክት ይላኩ።",
            parse_mode="Markdown"
        )
        context.user_data["vendor_application"] = True
    
    elif action == "profile_vendor_panel":
        await show_vendor_panel(update, context)


async def show_vendor_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show vendor panel for vendor users."""
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("📦 ምርቶቼ", callback_data="vendor_products")],
        [InlineKeyboardButton("➕ ምርት ጨምር", callback_data="vendor_add_product")],
        [InlineKeyboardButton("📋 ትዕዛዞች", callback_data="vendor_orders")],
        [InlineKeyboardButton("📊 ስታቲስቲክስ", callback_data="vendor_stats")],
        [InlineKeyboardButton("⚙️ ቅንብሮች", callback_data="vendor_settings")],
        [InlineKeyboardButton("🔙 ወደ ፕሮፋይል", callback_data="menu_profile")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🏪 *የሻጭ ፓነል*\n\n"
        "እንኳን ደህና መጡ! ከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle contact sharing.

    Works in two situations:
    1. New-user onboarding  — started from /start phone-sharing prompt
    2. Profile update       — started from "📞 ስልክ አዘምን" profile button

    After saving the number we:
    - Remove the ReplyKeyboard (clean UI)
    - If onboarding: confirm and show the main menu
    - Otherwise: just confirm
    """
    contact = update.message.contact
    tg_user = update.effective_user

    if not contact:
        return

    phone_number = contact.phone_number

    saved = False
    async for db in get_db_session():
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(tg_user.id)

        if user:
            await user_service.update_user(
                user.id,
                UserUpdate(phone_number=phone_number),
            )
            # Invalidate the middleware cache so next request sees updated phone
            from bot.middlewares.auth import auth_middleware
            auth_middleware.invalidate(tg_user.id)
            saved = True
        break

    # Always remove the phone-sharing keyboard
    await update.message.reply_text(
        "✅ ስልክ ቁጥርዎ ተመዝግቧል!" if saved else "❌ ስልክ ቁጥሩን ማስቀመጥ አልተቻለም። ቆይቶ እንደገና ይሞክሩ።",
        reply_markup=ReplyKeyboardRemove(),
    )

    if not saved:
        return

    # If this was the new-user onboarding flow, show the main menu now
    if context.user_data.pop("onboarding", False):
        from core.config import settings
        from bot.handlers.start import _build_main_menu

        is_admin = tg_user.id in settings.admin_ids_list
        await update.message.reply_text(
            "🌟 *ዎሎየዋ ስቶር* — ዋና ምናሌ\n\n"
            "📌 ከዚህ በታች ካሉት ቁልፎች ይምረጡ።",
            parse_mode="Markdown",
            reply_markup=_build_main_menu(is_admin),
        )


def get_role_amharic(role: str) -> str:
    """Convert role to Amharic."""
    roles = {
        "customer": "ደንበኛ",
        "vendor": "ሻጭ",
        "admin": "አስተዳዳሪ",
        "super_admin": "ዋና አስተዳዳሪ",
    }
    return roles.get(role, role)


__all__ = [
    "profile_command",
    "orders_command",
    "profile_callback",
    "contact_handler",
]