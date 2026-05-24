# ============================
# WOLLOYEWA STORE BOT - ADMIN DASHBOARD HANDLER
# ============================
"""Admin dashboard handlers for bot administration."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

from core.logger import logger
from core.config import settings
from apps.analytics.services import DashboardService, SalesAnalyticsService
from apps.users.services import UserService
from apps.orders.services import OrderService
from infrastructure.database.session import get_db_session


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /admin command.
    
    Shows admin dashboard.
    """
    user_id = update.effective_user.id
    
    # Check admin permission
    if user_id not in settings.admin_ids_list:
        await update.message.reply_text("❌ ይህን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም።")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 ዳሽቦርድ", callback_data="admin_dashboard")],
        [InlineKeyboardButton("📦 ምርቶች", callback_data="admin_products")],
        [InlineKeyboardButton("📋 ትዕዛዞች", callback_data="admin_orders")],
        [InlineKeyboardButton("👥 ተጠቃሚዎች", callback_data="admin_users")],
        [InlineKeyboardButton("🏪 ሻጮች", callback_data="admin_vendors")],
        [InlineKeyboardButton("📊 ሪፖርቶች", callback_data="admin_reports")],
        [InlineKeyboardButton("⚙️ ቅንብሮች", callback_data="admin_settings")],
        [InlineKeyboardButton("🔙 ወደ ምናሌ", callback_data="menu_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔧 *የአስተዳደር ፓነል*\n\n"
        "እንኳን ደህና መጡ! ከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle admin dashboard callbacks.
    """
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "admin_dashboard":
        await show_admin_dashboard(update, context)
    elif action == "admin_products":
        from bot.handlers.admin.products_admin import products_admin_panel
        await products_admin_panel(update, context)
    elif action == "admin_orders":
        from bot.handlers.admin.orders_admin import orders_admin_panel
        await orders_admin_panel(update, context)
    elif action == "admin_users":
        from bot.handlers.admin.users_admin import users_admin_panel
        await users_admin_panel(update, context)
    elif action == "admin_vendors":
        await show_vendors_list(update, context)
    elif action == "admin_reports":
        from bot.handlers.admin.reports import reports_panel
        await reports_panel(update, context)
    elif action == "admin_settings":
        await show_admin_settings(update, context)


async def show_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show admin dashboard with statistics.
    """
    query = update.callback_query
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    async for db in get_db_session():
        dashboard_service = DashboardService(db)
        sales_service = SalesAnalyticsService(db)
        user_service = UserService(db)
        order_service = OrderService(db)
        
        # Get statistics
        today_sales = await sales_service.get_sales_summary(today_start, now)
        week_sales = await sales_service.get_sales_summary(week_start, now)
        month_sales = await sales_service.get_sales_summary(month_start, now)
        
        # User stats
        total_users = await user_service.user_repo.count()
        active_users = await user_service.user_repo.count({"last_active__gte": week_start})
        vendors = await user_service.user_repo.count({"role": "vendor"})
        
        # Order stats
        pending_orders = await order_service.order_repo.count({"status": "pending"})
        processing_orders = await order_service.order_repo.count({"status": "processing"})
        
        break
    
    dashboard_text = f"""
📊 *የስርዓት ዳሽቦርድ*

💰 *ሽያጭ*
• ዛሬ: {format_etb(today_sales.get('total_revenue', 0))}
• በዚህ ሳምንት: {format_etb(week_sales.get('total_revenue', 0))}
• በዚህ ወር: {format_etb(month_sales.get('total_revenue', 0))}

👥 *ተጠቃሚዎች*
• ጠቅላላ: {total_users}
• ንቁ (7 ቀን): {active_users}
• ሻጮች: {vendors}

📦 *ትዕዛዞች*
• በመጠባበቅ ላይ: {pending_orders}
• በማቀናበር ላይ: {processing_orders}

⏱️ *የስርዓት ሁኔታ*
• ሰዓት: {now.strftime('%Y-%m-%d %H:%M')}
• አካባቢ: {settings.ENVIRONMENT}
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 አድስ", callback_data="admin_dashboard")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር", callback_data="admin_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        dashboard_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def show_vendors_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show list of vendors for admin.
    """
    query = update.callback_query
    
    async for db in get_db_session():
        user_service = UserService(db)
        vendors = await user_service.user_repo.get_all(filters={"role": "vendor"}, limit=50)
        break
    
    if not vendors:
        await query.message.edit_text("📋 ምንም ሻጮች አልተገኙም።")
        return
    
    vendors_text = "🏪 *ሻጮች*\n\n"
    
    for vendor in vendors:
        vendors_text += f"• *{vendor.full_name}* (@{vendor.username or 'N/A'})\n"
        vendors_text += f"  📞 {vendor.phone_number or 'N/A'}\n"
        vendors_text += f"  📅 {vendor.created_at.strftime('%Y-%m-%d')}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("✅ አጽድቅ", callback_data="admin_approve_vendor")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር", callback_data="admin_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        vendors_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def show_admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show admin settings panel.
    """
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("🔧 ስርዓት ቅንብሮች", callback_data="admin_system_settings")],
        [InlineKeyboardButton("💰 የክፍያ ቅንብሮች", callback_data="admin_payment_settings")],
        [InlineKeyboardButton("📧 ማሳወቂያ ቅንብሮች", callback_data="admin_notification_settings")],
        [InlineKeyboardButton("🗄️ የውሂብ ጎታ ምትኬ", callback_data="admin_backup")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር", callback_data="admin_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "⚙️ *የስርዓት ቅንብሮች*\n\n"
        "ከዚህ በታላላቅ ቅንብሮችን መቀየር ይችላሉ።",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /stats command (admin only).
    
    Shows quick statistics.
    """
    user_id = update.effective_user.id
    
    if user_id not in settings.admin_ids_list:
        await update.message.reply_text("❌ ፈቃድ የለዎትም።")
        return
    
    await show_admin_dashboard(update, context)


def format_etb(amount: float) -> str:
    """Format amount in Ethiopian Birr."""
    return f"{amount:,.2f} ብር"


__all__ = [
    "admin_command",
    "admin_callback",
    "stats_command",
]