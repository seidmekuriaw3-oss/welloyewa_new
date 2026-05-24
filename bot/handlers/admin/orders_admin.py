# ============================
# WOLLOYEWA STORE BOT - ADMIN ORDERS HANDLER
# ============================
"""Admin handlers for order management."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from core.config import settings
from core.utils.currency import format_etb
from apps.orders.services import OrderService
from apps.orders.schemas import OrderStatusUpdate
from infrastructure.database.session import get_db_session
from core.constants import OrderStatus


async def orders_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show admin orders management panel.
    """
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("📋 ሁሉንም ትዕዛዞች", callback_data="admin_list_orders")],
        [InlineKeyboardButton("⏳ በመጠባበቅ ላይ", callback_data="admin_pending_orders")],
        [InlineKeyboardButton("🔄 በማቀናበር ላይ", callback_data="admin_processing_orders")],
        [InlineKeyboardButton("🚚 የተላኩ", callback_data="admin_shipped_orders")],
        [InlineKeyboardButton("✅ የደረሱ", callback_data="admin_delivered_orders")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር", callback_data="admin_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "📋 *የትዕዛዝ አስተዳደር*\n\n"
        "ከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str = None) -> None:
    """
    List orders for admin.
    
    Args:
        update: Telegram update
        context: Callback context
        status: Filter by order status
    """
    query = update.callback_query
    page = context.user_data.get("admin_orders_page", 1)
    page_size = 10
    
    async for db in get_db_session():
        order_service = OrderService(db)
        
        filters = {}
        if status:
            filters["status"] = status
        
        orders, total = await order_service.order_repo.get_all_with_count(
            filters=filters,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        break
    
    if not orders:
        await query.message.edit_text("📋 ምንም ትዕዛዞች አልተገኙም።")
        return
    
    total_pages = (total + page_size - 1) // page_size
    
    status_text = f"({status.upper()})" if status else "(ሁሉም)"
    
    orders_text = f"📋 *ትዕዛዞች* {status_text} - ገጽ {page}/{total_pages}\n\n"
    
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
        orders_text += f"   👤 ተጠቃሚ: {order.user_id}\n"
        orders_text += f"   💰 ጠቅላላ: {format_etb(order.total)}\n"
        orders_text += f"   📅 {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        orders_text += f"   🆔 ID: {order.id}\n\n"
    
    # Build keyboard
    keyboard = []
    
    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_orders_page_prev"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_orders_page_next"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Action buttons
    keyboard.append([
        InlineKeyboardButton("🔄 ሁኔታ ቀይር", callback_data="admin_change_status"),
        InlineKeyboardButton("🔍 ዝርዝር", callback_data="admin_view_order"),
    ])
    keyboard.append([InlineKeyboardButton("🔙 ወደ ትዕዛዝ አስተዳደር", callback_data="admin_orders_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        orders_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def order_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle admin order callbacks.
    """
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "admin_list_orders":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = None
        await list_orders(update, context)
    
    elif action == "admin_pending_orders":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = "pending"
        await list_orders(update, context, status="pending")
    
    elif action == "admin_processing_orders":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = "processing"
        await list_orders(update, context, status="processing")
    
    elif action == "admin_shipped_orders":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = "shipped"
        await list_orders(update, context, status="shipped")
    
    elif action == "admin_delivered_orders":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = "delivered"
        await list_orders(update, context, status="delivered")
    
    elif action == "admin_orders_page_prev":
        context.user_data["admin_orders_page"] = context.user_data.get("admin_orders_page", 1) - 1
        filter_status = context.user_data.get("admin_orders_filter")
        await list_orders(update, context, status=filter_status)
    
    elif action == "admin_orders_page_next":
        context.user_data["admin_orders_page"] = context.user_data.get("admin_orders_page", 1) + 1
        filter_status = context.user_data.get("admin_orders_filter")
        await list_orders(update, context, status=filter_status)
    
    elif action == "admin_orders_back":
        await orders_admin_panel(update, context)


async def update_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int, new_status: str) -> None:
    """
    Update order status.
    
    Args:
        update: Telegram update
        context: Callback context
        order_id: Order ID
        new_status: New order status
    """
    async for db in get_db_session():
        order_service = OrderService(db)
        
        await order_service.update_order_status(
            order_id=order_id,
            data=OrderStatusUpdate(status=new_status),
            user_id=update.effective_user.id,
        )
        break
    
    await update.callback_query.message.reply_text(
        f"✅ ትዕዛዙ ሁኔታ ወደ {new_status.upper()} ተቀይሯል!"
    )


__all__ = [
    "orders_admin_panel",
    "order_admin_callback",
    "update_order_status",
]