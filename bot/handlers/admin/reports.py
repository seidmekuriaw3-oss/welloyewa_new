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
from apps.users.services import UserService
from apps.products.services import ProductService, CategoryService
from infrastructure.database.session import get_db_session


def _back_keyboard(callback: str = "admin_reports") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 ወደ ሪፖርቶች", callback_data=callback)],
    ])


async def reports_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin reports panel."""
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("💰 የሽያጭ ሪፖርት", callback_data="admin_sales_report")],
        [InlineKeyboardButton("👥 የተጠቃሚ ሪፖርት", callback_data="admin_user_report")],
        [InlineKeyboardButton("📦 የምርት ሪፖርት",  callback_data="admin_product_report")],
        [InlineKeyboardButton("🏪 የሻጭ ሪፖርት",   callback_data="admin_vendor_report")],
        [InlineKeyboardButton("📊 ዕለታዊ ሪፖርት",  callback_data="admin_daily_report")],
        [InlineKeyboardButton("📈 ሳምንታዊ ሪፖርት", callback_data="admin_weekly_report")],
        [InlineKeyboardButton("📅 ወርሃዊ ሪፖርት",  callback_data="admin_monthly_report")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር",   callback_data="admin_back")],
    ]

    await query.message.edit_text(
        "📊 *ሪፖርቶች*\n\nከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def generate_sales_report(
    update: Update, context: ContextTypes.DEFAULT_TYPE, days: int = 30
) -> None:
    """Generate and display a sales report."""
    query = update.callback_query
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    try:
        async for db in get_db_session():
            sales_service = SalesAnalyticsService(db)
            summary    = await sales_service.get_sales_summary(start_date, end_date)
            daily_sales = await sales_service.get_daily_sales(days)
            top_products = await sales_service.get_top_products(limit=5, days=days)
            break
    except Exception as exc:
        logger.error("Sales report error: %s", exc)
        summary = {}
        daily_sales = []
        top_products = []

    report_text = (
        f"📊 *የሽያጭ ሪፖርት* — {days} ቀናት\n\n"
        f"📅 *ጊዜ:* {start_date.strftime('%Y-%m-%d')} እስከ {end_date.strftime('%Y-%m-%d')}\n\n"
        f"💰 *ጠቅላላ ሽያጭ:* {format_etb(summary.get('total_revenue', 0))}\n"
        f"📦 *ጠቅላላ ትዕዛዞች:* {summary.get('total_orders', 0)}\n"
        f"📊 *አማካይ ትዕዛዝ:* {format_etb(summary.get('avg_order_value', 0))}\n\n"
        "🏆 *ከፍተኛ ምርቶች:*\n"
    )
    for product in top_products[:3]:
        report_text += (
            f"• {product.get('product_name', 'N/A')}: "
            f"{format_etb(product.get('revenue', 0))}\n"
        )

    report_text += "\n📈 *ዕለታዊ ክፍፍል (ባለፉ 7 ቀናት):*\n"
    for day in daily_sales[-7:]:
        report_text += (
            f"• {day.get('date', 'N/A')}: "
            f"{format_etb(day.get('total_sales', 0))} "
            f"({day.get('order_count', 0)} ትዕዛዞች)\n"
        )

    keyboard = [
        [InlineKeyboardButton("📥 ሪፖርቱን አውርድ", callback_data="admin_export_sales")],
        [InlineKeyboardButton("🔙 ወደ ሪፖርቶች",   callback_data="admin_reports_back")],
    ]
    await query.message.edit_text(
        report_text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def generate_user_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and display a user report."""
    query = update.callback_query

    try:
        async for db in get_db_session():
            user_service   = UserService(db)
            user_analytics = UserAnalyticsService(db)

            total_users        = await user_service.user_repo.count()
            active_users       = await user_analytics.get_active_users(days=30)
            new_users_last_30d = await user_service.user_repo.count(
                {"created_at__gte": datetime.utcnow() - timedelta(days=30)}
            )
            vendors            = await user_service.user_repo.count({"role": "vendor"})
            user_growth        = await user_analytics.get_user_growth(days=30)
            break
    except Exception as exc:
        logger.error("User report error: %s", exc)
        total_users = active_users = new_users_last_30d = vendors = 0
        user_growth = []

    report_text = (
        "👥 *የተጠቃሚ ሪፖርት*\n\n"
        "📊 *አጠቃላይ ስታቲስቲክስ:*\n"
        f"• ጠቅላላ ተጠቃሚዎች: {total_users}\n"
        f"• ንቁ ተጠቃሚዎች (30 ቀን): {active_users}\n"
        f"• አዳዲስ ተጠቃሚዎች (30 ቀን): {new_users_last_30d}\n"
        f"• ሻጮች: {vendors}\n\n"
        "📈 *የተጠቃሚ እድገት (ባለፉ 7 ቀናት):*\n"
    )
    for growth in user_growth[-7:]:
        report_text += f"• {growth.get('date', 'N/A')}: +{growth.get('new_users', 0)} አዳዲስ\n"

    keyboard = [
        [InlineKeyboardButton("📥 ሪፖርቱን አውርድ", callback_data="admin_export_users")],
        [InlineKeyboardButton("🔙 ወደ ሪፖርቶች",   callback_data="admin_reports_back")],
    ]
    await query.message.edit_text(
        report_text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def generate_product_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and display a product/category report."""
    query = update.callback_query

    try:
        async for db in get_db_session():
            product_service  = ProductService(db)
            category_service = CategoryService(db)

            total_products, _ = await product_service.product_repo.get_all_with_count()
            pending_products  = await product_service.product_repo.get_all(
                filters={"status": "pending"}
            )
            categories        = await category_service.get_all_categories()
            break
    except Exception as exc:
        logger.error("Product report error: %s", exc)
        total_products = 0
        pending_products = []
        categories = []

    report_text = (
        "📦 *የምርት ሪፖርት*\n\n"
        f"• ጠቅላላ ምርቶች: {total_products}\n"
        f"• በመጠባበቅ ላይ: {len(pending_products)}\n"
        f"• ምድቦች: {len(categories)}\n\n"
        "📁 *ምድቦች:*\n"
    )
    for cat in categories[:10]:
        report_text += f"• {cat.name}: {getattr(cat, 'product_count', 0)} ምርቶች\n"

    await query.message.edit_text(
        report_text, parse_mode="Markdown",
        reply_markup=_back_keyboard("admin_reports_back"),
    )


async def generate_vendor_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and display a vendor report."""
    query = update.callback_query

    try:
        async for db in get_db_session():
            user_service = UserService(db)
            total_vendors   = await user_service.user_repo.count({"role": "vendor"})
            active_vendors  = await user_service.user_repo.count(
                {"role": "vendor", "status": "active"}
            )
            break
    except Exception as exc:
        logger.error("Vendor report error: %s", exc)
        total_vendors = active_vendors = 0

    report_text = (
        "🏪 *የሻጭ ሪፖርት*\n\n"
        f"• ጠቅላላ ሻጮች: {total_vendors}\n"
        f"• ንቁ ሻጮች: {active_vendors}\n"
        f"• ያልነቁ ሻጮች: {total_vendors - active_vendors}\n"
    )

    await query.message.edit_text(
        report_text, parse_mode="Markdown",
        reply_markup=_back_keyboard("admin_reports_back"),
    )


# kept for backward-compat (dispatcher.py references it via __all__)
async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy entry point — all routing now done in dashboard.admin_callback."""
    pass


__all__ = [
    "reports_panel",
    "report_callback",
    "generate_sales_report",
    "generate_user_report",
    "generate_product_report",
    "generate_vendor_report",
]
