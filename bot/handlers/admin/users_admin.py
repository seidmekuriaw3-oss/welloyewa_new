# ============================
# WOLLOYEWA STORE BOT - ADMIN USERS HANDLER
# ============================
"""Admin handlers for user management."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from core.config import settings
from apps.users.services import UserService, VendorService
from infrastructure.database.session import get_db_session


async def users_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show admin users management panel.
    """
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("👥 ሁሉንም ተጠቃሚዎች", callback_data="admin_list_users")],
        [InlineKeyboardButton("🏪 ሻጮች", callback_data="admin_list_vendors")],
        [InlineKeyboardButton("⏳ በመጠባበቅ ላይ ያሉ ሻጮች", callback_data="admin_pending_vendors")],
        [InlineKeyboardButton("🚫 የታገዱ", callback_data="admin_suspended_users")],
        [InlineKeyboardButton("🔍 ፈልግ", callback_data="admin_search_users")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር", callback_data="admin_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "👥 *የተጠቃሚ አስተዳደር*\n\n"
        "ከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE, role: str = None) -> None:
    """
    List users for admin.
    
    Args:
        update: Telegram update
        context: Callback context
        role: Filter by user role
    """
    query = update.callback_query
    page = context.user_data.get("admin_users_page", 1)
    page_size = 10
    
    async for db in get_db_session():
        user_service = UserService(db)
        
        filters = {}
        if role:
            filters["role"] = role
        
        users, total = await user_service.user_repo.get_all_with_count(
            filters=filters,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        break
    
    if not users:
        await query.message.edit_text("👥 ምንም ተጠቃሚዎች አልተገኙም።")
        return
    
    total_pages = (total + page_size - 1) // page_size
    
    role_text = f"({role.upper()})" if role else "(ሁሉም)"
    
    users_text = f"👥 *ተጠቃሚዎች* {role_text} - ገጽ {page}/{total_pages}\n\n"
    
    for user in users:
        status_emoji = "✅" if user.status == "active" else "⏳"
        users_text += f"{status_emoji} *{user.full_name}*\n"
        users_text += f"   🆔 ID: {user.id}\n"
        users_text += f"   📞 {user.phone_number or 'N/A'}\n"
        users_text += f"   📧 {user.email or 'N/A'}\n"
        users_text += f"   👤 @{user.username or 'N/A'}\n"
        users_text += f"   ⭐ {user.role}\n"
        users_text += f"   📅 {user.created_at.strftime('%Y-%m-%d')}\n\n"
    
    # Build keyboard
    keyboard = []
    
    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_users_page_prev"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_users_page_next"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Action buttons
    keyboard.append([
        InlineKeyboardButton("✏️ አርትዕ", callback_data="admin_edit_user"),
        InlineKeyboardButton("🚫 አግድ", callback_data="admin_suspend_user"),
    ])
    keyboard.append([InlineKeyboardButton("🔙 ወደ ተጠቃሚ አስተዳደር", callback_data="admin_users_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        users_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def list_vendors(update: Update, context: ContextTypes.DEFAULT_TYPE, pending_only: bool = False) -> None:
    """
    List vendors for admin.
    
    Args:
        update: Telegram update
        context: Callback context
        pending_only: Show only pending vendors
    """
    query = update.callback_query
    page = context.user_data.get("admin_vendors_page", 1)
    page_size = 10
    
    async for db in get_db_session():
        vendor_service = VendorService(db)
        
        if pending_only:
            vendors = await vendor_service.vendor_repo.get_pending_vendors(limit=page_size)
            total = len(vendors)
        else:
            vendors, total = await vendor_service.vendor_repo.get_all_with_count(
                limit=page_size,
                offset=(page - 1) * page_size,
            )
        break
    
    if not vendors:
        status_text = "በመጠባበቅ ላይ" if pending_only else ""
        await query.message.edit_text(f"🏪 ምንም ሻጮች {status_text} አልተገኙም።")
        return
    
    total_pages = (total + page_size - 1) // page_size
    
    status_text = "(በመጠባበቅ ላይ)" if pending_only else "(ሁሉም)"
    
    vendors_text = f"🏪 *ሻጮች* {status_text} - ገጽ {page}/{total_pages}\n\n"
    
    for vendor in vendors:
        approved_emoji = "✅" if vendor.is_approved else "⏳"
        vendors_text += f"{approved_emoji} *{vendor.business_name}*\n"
        vendors_text += f"   🆔 ID: {vendor.id}\n"
        vendors_text += f"   👤 ተጠቃሚ: {vendor.user_id}\n"
        vendors_text += f"   📞 {vendor.business_phone or 'N/A'}\n"
        vendors_text += f"   📧 {vendor.business_email or 'N/A'}\n"
        vendors_text += f"   📅 {vendor.created_at.strftime('%Y-%m-%d')}\n"
        vendors_text += f"   ⭐ ደረጃ: {vendor.rating}\n"
        vendors_text += f"   📦 ሽያጭ: {vendor.total_sales}\n\n"
    
    # Build keyboard
    keyboard = []
    
    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_vendors_page_prev"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_vendors_page_next"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Action buttons for pending vendors
    if pending_only:
        keyboard.append([
            InlineKeyboardButton("✅ አጽድቅ", callback_data="admin_approve_vendor"),
            InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data="admin_reject_vendor"),
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 ወደ ተጠቃሚ አስተዳደር", callback_data="admin_users_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        vendors_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def user_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle admin user callbacks.
    """
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "admin_list_users":
        context.user_data["admin_users_page"] = 1
        await list_users(update, context)
    
    elif action == "admin_list_vendors":
        context.user_data["admin_vendors_page"] = 1
        await list_vendors(update, context)
    
    elif action == "admin_pending_vendors":
        context.user_data["admin_vendors_page"] = 1
        await list_vendors(update, context, pending_only=True)
    
    elif action == "admin_users_page_prev":
        context.user_data["admin_users_page"] = context.user_data.get("admin_users_page", 1) - 1
        await list_users(update, context)
    
    elif action == "admin_users_page_next":
        context.user_data["admin_users_page"] = context.user_data.get("admin_users_page", 1) + 1
        await list_users(update, context)
    
    elif action == "admin_vendors_page_prev":
        context.user_data["admin_vendors_page"] = context.user_data.get("admin_vendors_page", 1) - 1
        await list_vendors(update, context)
    
    elif action == "admin_vendors_page_next":
        context.user_data["admin_vendors_page"] = context.user_data.get("admin_vendors_page", 1) + 1
        await list_vendors(update, context)
    
    elif action == "admin_users_back":
        await users_admin_panel(update, context)


__all__ = [
    "users_admin_panel",
    "user_admin_callback",
]