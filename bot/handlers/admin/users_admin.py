# ============================
# WOLLOYEWA STORE BOT - ADMIN USERS HANDLER
# ============================
"""Admin handlers for user management."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from apps.users.services import UserService, VendorService
from apps.users.schemas import UserUpdate
from infrastructure.database.session import get_db_session


# ── helpers ───────────────────────────────────────────────────────────────────

def _users_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 ወደ ተጠቃሚ አስተዳደር", callback_data="admin_users_back")]
    ])


STATUS_EMOJI = {"active": "✅", "suspended": "🚫", "banned": "⛔", "inactive": "⚪"}


# ── Panels ────────────────────────────────────────────────────────────────────

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
    """List users with optional role/status filter and per-user action buttons."""
    query = update.callback_query
    page = context.user_data.get("admin_users_page", 1)
    page_size = 5  # smaller page so per-user buttons fit

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
        await query.message.edit_text("❌ ተጠቃሚዎችን ለማምጣት ስህተት ተፈጥሯል።", reply_markup=_users_back_keyboard())
        return

    if not users:
        label = ("(የታገዱ)" if status_filter == "suspended" else f"({role})" if role else "(ሁሉም)")
        await query.message.edit_text(
            f"👥 ምንም ተጠቃሚዎች {label} አልተገኙም።",
            reply_markup=_users_back_keyboard(),
        )
        return

    total_pages = max(1, (total + page_size - 1) // page_size)
    role_text = ("(የታገዱ)" if status_filter == "suspended" else f"({role.upper()})" if role else "(ሁሉም)")
    text = f"👥 *ተጠቃሚዎች* {role_text} — ገጽ {page}/{total_pages}\n\n"

    keyboard = []
    for user in users:
        emoji = STATUS_EMOJI.get(str(user.status), "👤")
        text += (
            f"{emoji} *{user.full_name}* (ID:{user.id})\n"
            f"   @{user.username or 'N/A'} | 📞 {user.phone_number or 'N/A'}\n"
            f"   ⭐ {user.role} | 📅 {user.created_at.strftime('%Y-%m-%d')}\n\n"
        )
        row = []
        if str(user.status) != "suspended":
            row.append(InlineKeyboardButton(
                f"🚫 አግድ ({user.id})", callback_data=f"admin_suspend_user_{user.id}"
            ))
        else:
            row.append(InlineKeyboardButton(
                f"✅ ፍቅ ({user.id})", callback_data=f"admin_unsuspend_user_{user.id}"
            ))
        keyboard.append(row)

    # Pagination
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_users_page_prev"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_users_page_next"))
    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton("🔙 ወደ ተጠቃሚ አስተዳደር", callback_data="admin_users_back")])

    await query.message.edit_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def list_suspended_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List suspended users."""
    context.user_data["admin_users_page"] = 1
    await list_users(update, context, status_filter="suspended")


async def prompt_search_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask admin to type a search query."""
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
    page_size = 8

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
        await query.message.edit_text("❌ ሻጮችን ለማምጣት ስህተት ተፈጥሯል።", reply_markup=_users_back_keyboard())
        return

    if not vendors:
        label = "በመጠባበቅ ላይ" if pending_only else ""
        await query.message.edit_text(
            f"🏪 ምንም ሻጮች {label} አልተገኙም።",
            reply_markup=_users_back_keyboard(),
        )
        return

    total_pages = max(1, (total + page_size - 1) // page_size)
    status_text = "(በመጠባበቅ ላይ)" if pending_only else "(ሁሉም)"
    text = f"🏪 *ሻጮች* {status_text} — ገጽ {page}/{total_pages}\n\n"

    keyboard = []
    for vendor in vendors:
        approved_emoji = "✅" if vendor.is_approved else "⏳"
        text += (
            f"{approved_emoji} *{vendor.business_name}* (ID:{vendor.id})\n"
            f"   👤 ተጠቃሚ: {vendor.user_id} | ⭐ {vendor.rating}\n"
            f"   📞 {vendor.business_phone or 'N/A'}\n\n"
        )
        if not vendor.is_approved:
            keyboard.append([
                InlineKeyboardButton(f"✅ አጽድቅ ({vendor.id})", callback_data=f"admin_approve_vendor_{vendor.id}"),
                InlineKeyboardButton(f"❌ ውድቅ ({vendor.id})", callback_data=f"admin_reject_vendor_{vendor.id}"),
            ])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_vendors_page_prev"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_vendors_page_next"))
    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton("🔙 ወደ ተጠቃሚ አስተዳደር", callback_data="admin_users_back")])

    await query.message.edit_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ── Action functions (called by dashboard router) ─────────────────────────────

async def confirm_suspend_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> None:
    """Show suspend-user confirmation panel."""
    query = update.callback_query
    await query.message.edit_text(
        f"🚫 *ተጠቃሚውን (ID: {user_id}) ማገድ ይፈልጋሉ?*\n\n"
        "ተጠቃሚው ሱቁን ሊጠቀም አይችልም።",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ አዎ፣ አግድ",  callback_data=f"admin_confirm_suspend_{user_id}"),
                InlineKeyboardButton("❌ አይ",         callback_data="admin_users"),
            ]
        ]),
    )


async def do_suspend_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> None:
    """Suspend a user."""
    query = update.callback_query
    try:
        async for db in get_db_session():
            user_service = UserService(db)
            await user_service.user_repo.update(user_id, {"status": "suspended"})
            break
        await query.message.edit_text(
            f"🚫 ተጠቃሚው (ID: {user_id}) ታግዷል።",
            reply_markup=_users_back_keyboard(),
        )
    except Exception as exc:
        logger.error("Suspend user %s error: %s", user_id, exc)
        await query.message.edit_text("❌ ተጠቃሚውን ለማገድ ስህተት ተፈጥሯል።", reply_markup=_users_back_keyboard())


async def do_unsuspend_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> None:
    """Lift a user suspension."""
    query = update.callback_query
    try:
        async for db in get_db_session():
            user_service = UserService(db)
            await user_service.user_repo.update(user_id, {"status": "active"})
            break
        await query.message.edit_text(
            f"✅ ተጠቃሚው (ID: {user_id}) ታደሰ።",
            reply_markup=_users_back_keyboard(),
        )
    except Exception as exc:
        logger.error("Unsuspend user %s error: %s", user_id, exc)
        await query.message.edit_text("❌ ተጠቃሚውን ለማፈታት ስህተት ተፈጥሯል።", reply_markup=_users_back_keyboard())


async def do_approve_vendor(
    update: Update, context: ContextTypes.DEFAULT_TYPE, vendor_id: int
) -> None:
    """Approve a vendor by DB vendor ID."""
    query = update.callback_query
    admin_id = update.effective_user.id
    try:
        async for db in get_db_session():
            vendor_service = VendorService(db)
            await vendor_service.approve_vendor(vendor_id, admin_id)
            break
        await query.message.edit_text(
            f"✅ ሻጩ (ID: {vendor_id}) ፀድቋል!",
            reply_markup=_users_back_keyboard(),
        )
    except Exception as exc:
        logger.error("Approve vendor %s error: %s", vendor_id, exc)
        await query.message.edit_text("❌ ሻጩን ለማጽደቅ ስህተት ተፈጥሯል።", reply_markup=_users_back_keyboard())


async def do_reject_vendor(
    update: Update, context: ContextTypes.DEFAULT_TYPE, vendor_id: int
) -> None:
    """Reject a vendor by DB vendor ID."""
    query = update.callback_query
    try:
        async for db in get_db_session():
            vendor_service = VendorService(db)
            await vendor_service.reject_vendor(vendor_id, reason="Admin rejection")
            break
        await query.message.edit_text(
            f"❌ ሻጩ (ID: {vendor_id}) ውድቅ ሆኗል።",
            reply_markup=_users_back_keyboard(),
        )
    except Exception as exc:
        logger.error("Reject vendor %s error: %s", vendor_id, exc)
        await query.message.edit_text("❌ ሻጩን ውድቅ ለማድረግ ስህተት ተፈጥሯል።", reply_markup=_users_back_keyboard())


# ── legacy stub ───────────────────────────────────────────────────────────────

async def user_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy entry point — all routing now done in dashboard.admin_callback."""
    pass


__all__ = [
    "users_admin_panel",
    "list_users",
    "list_vendors",
    "list_suspended_users",
    "prompt_search_users",
    "confirm_suspend_user",
    "do_suspend_user",
    "do_unsuspend_user",
    "do_approve_vendor",
    "do_reject_vendor",
    "user_admin_callback",
]
