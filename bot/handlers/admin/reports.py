# ============================
# WOLLOYEWA STORE BOT - ADMIN REPORTS HANDLER
# ============================
"""Admin handlers for generating and viewing reports."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

from core.logger import logger
from core.config import settings
from core.utils.currency import format_etb
from apps.analytics.services import SalesAnalyticsService, UserAnalyticsService
from apps.orders.services import OrderService
from infrastructure.database.session import get_db_session


async def reports_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show admin reports panel.
    """
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("💰 የሽያጭ ሪፖርት", callback_data="admin_sales_report")],
        [InlineKeyboardButton("👥 የተጠቃሚ ሪፖርት", callback_data="admin_user_report")],
        [InlineKeyboardButton("📦 የምርት ሪፖርት", callback_data="admin_product_report")],
        [InlineKeyboardButton("🏪 የሻጭ ሪፖርት", callback_data="admin_vendor_report")],
        [InlineKeyboardButton("📊 ዕለታዊ ሪፖርት", callback_data="admin_daily_report")],
        [InlineKeyboardButton("📈 ሳምንታዊ ሪፖርት", callback_data="admin_weekly_report")],
        [InlineKeyboardButton("📅 ወርሃዊ ሪፖርት", callback_data="admin_monthly_report")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር", callback_data="admin_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "📊 *ሪፖርቶች*\n\n"
        "ከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def generate_sales_report(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int = 30) -> None:
    """
    Generate and display sales report.
    
    Args:
        update: Telegram update
        context: Callback context
        days: Number of days to report
    """
    query = update.callback_query
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    async for db in get_db_session():
        sales_service = SalesAnalyticsService(db)
        order_service = OrderService(db)
        
        # Get sales summary
        summary = await sales_service.get_sales_summary(start_date, end_date)
        
        # Get daily sales
        daily_sales = await sales_service.get_daily_sales(days)
        
        # Get top products
        top_products = await sales_service.get_top_products(limit=5, days=days)
        
        break
    
    # Build report
    report_text = f"""
📊 *የሽያጭ ሪፖርት* - የቀናት: {days}

📅 *ጊዜ:* {start_date.strftime('%Y-%m-%d')} እስከ {end_date.strftime('%Y-%m-%d')}

💰 *ጠቅላላ ሽያጭ:* {format_etb(summary.get('total_revenue', 0))}
📦 *ጠቅላላ ትዕዛዞች:* {summary.get('total_orders', 0)}
📊 *አማካይ ትዕዛዝ:* {format_etb(summary.get('avg_order_value', 0))}

🏆 *ከፍተኛ ምርቶች:*
"""
    for product in top_products[:3]:
        report_text += f"• {product.get('product_name', 'N/A')}: {format_etb(product.get('revenue', 0))}\n"
    
    # Daily breakdown
    report_text += f"\n📈 *ዕለታዊ ክፍፍል:*\n"
    for day in daily_sales[-7:]:  # Last 7 days
        report_text += f"• {day['date']}: {format_etb(day['total_sales'])} ({day['order_count']} ትዕዛዞች)\n"
    
    keyboard = [
        [InlineKeyboardButton("📥 ሪፖርቱን አውርድ", callback_data="admin_export_sales")],
        [InlineKeyboardButton("🔙 ወደ ሪፖርቶች", callback_data="admin_reports_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        report_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def generate_user_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Generate and display user report.
    """
    query = update.callback_query
    
    async for db in get_db_session():
        user_service = UserService(db)
        user_analytics = UserAnalyticsService(db)
        
        # User stats
        total_users = await user_service.user_repo.count()
        active_users = await user_analytics.get_active_users(days=30)
        new_users_last_30d = await user_service.user_repo.count({"created_at__gte": datetime.utcnow() - timedelta(days=30)})
        vendors = await user_service.user_repo.count({"role": "vendor"})
        
        # User growth
        user_growth = await user_analytics.get_user_growth(days=30)
        
        break
    
    report_text = f"""
👥 *የተጠቃሚ ሪፖርት*

📊 *አጠቃላይ ስታቲስቲክስ:*
• ጠቅላላ ተጠቃሚዎች: {total_users}
• ንቁ ተጠቃሚዎች (30 ቀን): {active_users}
• አዳዲስ ተጠቃሚዎች (30 ቀን): {new_users_last_30d}
• ሻጮች: {vendors}

📈 *የተጠቃሚ እድገት (የመጨረሻ 30 ቀናት):*
"""
    for growth in user_growth[-7:]:  # Last 7 days
        report_text += f"• {growth['date']}: +{growth['new_users']} አዳዲስ\n"
    
    keyboard = [
        [InlineKeyboardButton("📥 ሪፖርቱን አውርድ", callback_data="admin_export_users")],
        [InlineKeyboardButton("🔙 ወደ ሪፖርቶች", callback_data="admin_reports_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        report_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def generate_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Generate daily report.
    """
    query = update.callback_query
    await generate_sales_report(update, context, days=1)


async def generate_weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Generate weekly report.
    """
    query = update.callback_query
    await generate_sales_report(update, context, days=7)


async def generate_monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Generate monthly report.
    """
    query = update.callback_query
    await generate_sales_report(update, context, days=30)


async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle report callbacks.
    """
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "admin_sales_report":
        await generate_sales_report(update, context)
    elif action == "admin_user_report":
        await generate_user_report(update, context)
    elif action == "admin_daily_report":
        await generate_daily_report(update, context)
    elif action == "admin_weekly_report":
        await generate_weekly_report(update, context)
    elif action == "admin_monthly_report":
        await generate_monthly_report(update, context)
    elif action == "admin_reports_back":
        await reports_panel(update, context)


__all__ = [
    "reports_panel",
    "report_callback",
]