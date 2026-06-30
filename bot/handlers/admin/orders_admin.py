# ============================
# WOLLOYEWA STORE BOT - ADMIN ORDERS HANDLER
# ============================
"""Admin handlers for order management."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from core.utils.currency import format_etb
from apps.orders.services import OrderService
from apps.orders.schemas import OrderStatusUpdate
from infrastructure.database.session import get_db_session
from core.constants import OrderStatus


# ── helpers ───────────────────────────────────────────────────────────────────

def _orders_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 ወደ ትዕዛዝ አስተዳደር", callback_data="admin_orders_back")]
    ])


STATUS_EMOJI = {
    "pending":    "⏳",
    "confirmed":  "✅",
    "processing": "🔄",
    "shipped":    "🚚",
    "delivered":  "📦✅",
    "cancelled":  "❌",
    "refunded":   "↩️",
}

STATUS_TRANSITIONS = {
    "pending":    ["confirmed", "cancelled"],
    "confirmed":  ["processing", "cancelled"],
    "processing": ["shipped", "cancelled"],
    "shipped":    ["delivered", "cancelled"],
    "delivered":  [],
    "cancelled":  [],
    "refunded":   [],
}

STATUS_LABELS = {
    "confirmed":  "✅ ያረጋገጠ",
    "processing": "🔄 በማቀናበር",
    "shipped":    "🚚 ተላከ",
    "delivered":  "📦 ደረሰ",
    "cancelled":  "❌ ተሰረዘ",
}


# ── Panels ────────────────────────────────────────────────────────────────────

async def orders_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin orders management panel."""
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("📋 ሁሉንም ትዕዛዞች",  callback_data="admin_list_orders")],
        [InlineKeyboardButton("⏳ በመጠባበቅ ላይ",   callback_data="admin_pending_orders")],
        [InlineKeyboardButton("🔄 በማቀናበር ላይ",   callback_data="admin_processing_orders")],
        [InlineKeyboardButton("🚚 የተላኩ",         callback_data="admin_shipped_orders")],
        [InlineKeyboardButton("✅ የደረሱ",          callback_data="admin_delivered_orders")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር",    callback_data="admin_back")],
    ]

    await query.message.edit_text(
        "📋 *የትዕዛዝ አስተዳደር*\n\nከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def list_orders(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    status: str = None,
) -> None:
    """List orders with per-row 'View Details' buttons."""
    query = update.callback_query
    page = context.user_data.get("admin_orders_page", 1)
    page_size = 5  # smaller page so per-order buttons fit

    try:
        async for db in get_db_session():
            order_service = OrderService(db)
            filters = {}
            if status:
                filters["status"] = status

            orders, total = await order_service.order_repo.get_all_with_count(
                filters=filters,
                limit=page_size,
                offset=(page - 1) * page_size,
                order_by="created_at",
                order_desc=True,
            )
            break
    except Exception as exc:
        logger.error("list_orders error: %s", exc)
        await query.message.edit_text("❌ ትዕዛዞችን ለማምጣት ስህተት ተፈጥሯል።", reply_markup=_orders_back_keyboard())
        return

    if not orders:
        await query.message.edit_text(
            "📋 ምንም ትዕዛዞች አልተገኙም።",
            reply_markup=_orders_back_keyboard(),
        )
        return

    total_pages = max(1, (total + page_size - 1) // page_size)
    status_text = f"({status.upper()})" if status else "(ሁሉም)"
    text = f"📋 *ትዕዛዞች* {status_text} — ገጽ {page}/{total_pages}\n\n"

    keyboard = []
    for order in orders:
        emoji = STATUS_EMOJI.get(str(order.status), "📋")
        order_num = getattr(order, "order_number", order.id)
        text += (
            f"{emoji} *#{order_num}* (ID:{order.id})\n"
            f"   👤 ተጠቃሚ: {order.user_id} | 💰 {format_etb(order.total)}\n"
            f"   📅 {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        )
        keyboard.append([
            InlineKeyboardButton(
                f"🔍 #{order_num}", callback_data=f"admin_view_order_{order.id}"
            )
        ])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_orders_page_prev"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_orders_page_next"))
    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton("🔙 ወደ ትዕዛዝ አስተዳደር", callback_data="admin_orders_back")])

    await query.message.edit_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ── Action functions (called by dashboard router) ─────────────────────────────

async def show_order_detail(
    update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int
) -> None:
    """Show full order detail with status-change buttons."""
    query = update.callback_query

    try:
        async for db in get_db_session():
            order_service = OrderService(db)
            order = await order_service.get_order(order_id)
            break
    except Exception as exc:
        logger.error("show_order_detail %s error: %s", order_id, exc)
        order = None

    if not order:
        await query.message.edit_text(
            f"❌ ትዕዛዝ (ID: {order_id}) አልተገኘም።",
            reply_markup=_orders_back_keyboard(),
        )
        return

    order_num = getattr(order, "order_number", order.id)
    status = str(order.status)
    emoji = STATUS_EMOJI.get(status, "📋")

    text = (
        f"📋 *ትዕዛዝ #{order_num}*\n\n"
        f"🆔 ID: {order.id}\n"
        f"👤 ተጠቃሚ: {order.user_id}\n"
        f"💰 ጠቅላላ: {format_etb(order.total)}\n"
        f"{emoji} ሁኔታ: *{status.upper()}*\n"
        f"💳 ክፍያ: {getattr(order, 'payment_status', 'N/A')}\n"
        f"📅 {order.created_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
    )

    if hasattr(order, "shipping_address") and order.shipping_address:
        text += f"🏠 አድራሻ: {order.shipping_address}\n"

    keyboard = []
    next_statuses = STATUS_TRANSITIONS.get(status, [])
    if next_statuses:
        text += "\n📌 *ሁኔታ ቀይር:*\n"
        row = []
        for ns in next_statuses:
            label = STATUS_LABELS.get(ns, ns)
            row.append(InlineKeyboardButton(
                label, callback_data=f"admin_set_status_{order_id}_{ns}"
            ))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 ወደ ትዕዛዞች", callback_data="admin_list_orders")])

    await query.message.edit_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def do_change_order_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int, new_status: str
) -> None:
    """Change an order's status."""
    query = update.callback_query

    try:
        async for db in get_db_session():
            order_service = OrderService(db)
            await order_service.update_order_status(
                order_id=order_id,
                data=OrderStatusUpdate(status=new_status),
                user_id=update.effective_user.id,
            )
            break
        status_label = STATUS_LABELS.get(new_status, new_status.upper())
        await query.message.edit_text(
            f"✅ ትዕዛዝ (ID: {order_id}) ሁኔታ ወደ *{status_label}* ተቀይሯል!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 ዝርዝር ይዩ", callback_data=f"admin_view_order_{order_id}")],
                [InlineKeyboardButton("🔙 ወደ ትዕዛዞች", callback_data="admin_list_orders")],
            ]),
        )
    except Exception as exc:
        logger.error("Change order %s status to %s error: %s", order_id, new_status, exc)
        await query.message.edit_text(
            "❌ ሁኔታ ለመቀየር ስህተት ተፈጥሯል።",
            reply_markup=_orders_back_keyboard(),
        )


# ── legacy stub ───────────────────────────────────────────────────────────────

async def order_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy entry point — all routing now done in dashboard.admin_callback."""
    pass


async def update_order_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int, new_status: str
) -> None:
    """Backward-compat wrapper."""
    await do_change_order_status(update, context, order_id, new_status)


__all__ = [
    "orders_admin_panel",
    "list_orders",
    "show_order_detail",
    "do_change_order_status",
    "order_admin_callback",
    "update_order_status",
]
