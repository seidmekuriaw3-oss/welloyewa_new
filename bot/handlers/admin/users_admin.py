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
    """Show admin users management panel."""
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("👥 ሁሉንም ተጠቃሚዎች",    callback_data="admin_list_users")],
        [InlineKeyboardButton("🏪 ሻጮች",              callback_data="admin_list_vendors")],
        [InlineKeyboardButton("⏳ በመጠባበቅ ላይ ያሉ ሻጮች", callback_data="admin_pending_vendors")],
        [InlineKeyboardButton("🚫 የታገዱ",             callback_data="admin_suspended_users")],
        [InlineKeyboardButton("🔍 ፈልግ",              callback_data="admin_search_users")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር",        callback_data="admin_back")],
    ]

    await query.message.edit_text(
        "👥 *የተጠቃሚ አስተዳደር*\n\nከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def list_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    role: str = None,
    status_filter: str = None,
) -> None:
    """List users for admin with optional role/status filter."""
    query = update.callback_query
    page = context.user_data.get("admin_users_page", 1)
    page_size = 10

    try:
        async for db in get_db_session():
            user_service = UserService(db)
            filters = {}
            if role:
                filters["role"] = role
            if status_filter:
                filters["status"] = status_filter

            users, total = await user_service.user_repo.get_all_with_count(
                filters=filters,
                limit=page_size,
                offset=(page - 1) * page_size,
            )
            break
    except Exception as exc:
        logger.error("list_users error: %s", exc)
        await query.message.edit_text("❌ ተጠቃሚዎችን ለማምጣት ስህተት ተፈጥሯል።")
        return

    if not users:
        label = "ያለ" if not (role or status_filter) else f"({role or status_filter})"
        await query.message.edit_text(
            f"👥 ምንም ተጠቃሚዎች {label} አልተገኙም።",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 ወደ ተጠቃሚ አስተዳደር", callback_data="admin_users_back")]]
            ),
        )
        return

    total_pages = max(1, (total + page_size - 1) // page_size)
    role_text = f"({role.upper()})" if role else ("(የታገዱ)" if status_filter == "suspended" else "(ሁሉም)")
    users_text = f"👥 *ተጠቃሚዎች* {role_text} — ገጽ {page}/{total_pages}\n\n"

    for user in users:
        status_emoji = "✅" if user.status == "active" else ("🚫" if user.status == "suspended" else "⏳")
        users_text += (
            f"{status_emoji} *{user.full_name}*\n"
            f"   🆔 ID: {user.id}\n"
            f"   📞 {user.phone_number or 'N/A'}\n"
            f"   📧 {user.email or 'N/A'}\n"
            f"   👤 @{user.username or 'N/A'}\n"
            f"   ⭐ {user.role}\n"
            f"   📅 {user.created_at.strftime('%Y-%m-%d')}\n\n"
        )

    keyboard = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_users_page_prev"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_users_page_next"))
    if nav:
        keyboard.append(nav)

    keyboard.append([
        InlineKeyboardButton("✏️ አርትዕ",  callback_data="admin_edit_user"),
        InlineKeyboardButton("🚫 አግድ",   callback_data="admin_suspend_user"),
    ])
    keyboard.append([InlineKeyboardButton("🔙 ወደ ተጠቃሚ አስተዳደር", callback_data="admin_users_back")])

    await query.message.edit_text(
        users_text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def list_suspended_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List suspended users."""
    context.user_data["admin_users_page"] = 1
    await list_users(update, context, status_filter="suspended")


async def prompt_search_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask admin to type a search query for users."""
    query = update.callback_query
    context.user_data["admin_awaiting_user_search"] = True
    await query.message.reply_text(
        "🔍 ለመፈለግ ስም፣ ስልክ ወይም @username ይላኩ።"
    )


async def list_vendors(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    pending_only: bool = False,
) -> None:
    """List vendors for admin."""
    query = update.callback_query
    page = context.user_data.get("admin_vendors_page", 1)
    page_size = 10

    try:
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
    except Exception as exc:
        logger.error("list_vendors error: %s", exc)
        await query.message.edit_text("❌ ሻጮችን ለማምጣት ስህተት ተፈጥሯል።")
        return

    if not vendors:
        label = "በመጠባበቅ ላይ" if pending_only else ""
        await query.message.edit_text(
            f"🏪 ምንም ሻጮች {label} አልተገኙም።",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 ወደ ተጠቃሚ አስተዳደር", callback_data="admin_users_back")]]
            ),
        )
        return

    total_pages = max(1, (total + page_size - 1) // page_size)
    status_text = "(በመጠባበቅ ላይ)" if pending_only else "(ሁሉም)"
    vendors_text = f"🏪 *ሻጮች* {status_text} — ገጽ {page}/{total_pages}\n\n"

    for vendor in vendors:
        approved_emoji = "✅" if vendor.is_approved else "⏳"
        vendors_text += (
            f"{approved_emoji} *{vendor.business_name}*\n"
            f"   🆔 ID: {vendor.id}\n"
            f"   👤 ተጠቃሚ: {vendor.user_id}\n"
            f"   📞 {vendor.business_phone or 'N/A'}\n"
            f"   📧 {vendor.business_email or 'N/A'}\n"
            f"   📅 {vendor.created_at.strftime('%Y-%m-%d')}\n"
            f"   ⭐ ደረጃ: {vendor.rating}\n"
            f"   📦 ሽያጭ: {vendor.total_sales}\n\n"
        )

    keyboard = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_vendors_page_prev"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_vendors_page_next"))
    if nav:
        keyboard.append(nav)

    if pending_only:
        keyboard.append([
            InlineKeyboardButton("✅ አጽድቅ",      callback_data="admin_approve_vendor"),
            InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data="admin_reject_vendor"),
        ])

    keyboard.append([InlineKeyboardButton("🔙 ወደ ተጠቃሚ አስተዳደር", callback_data="admin_users_back")])

    await query.message.edit_text(
        vendors_text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# kept for backward-compat
async def user_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy entry point — all routing now done in dashboard.admin_callback."""
    pass


__all__ = [
    "users_admin_panel",
    "list_users",
    "list_vendors",
    "list_suspended_users",
    "prompt_search_users",
    "user_admin_callback",
]
