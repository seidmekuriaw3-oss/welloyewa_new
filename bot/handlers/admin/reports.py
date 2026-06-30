# ============================
# WOLLOYEWA STORE BOT - ADMIN REPORTS HANDLER
# ============================
"""Admin handlers for generating and viewing reports, including CSV export."""

import io
import csv
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
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


# ── Panels ────────────────────────────────────────────────────────────────────

async def reports_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin reports panel."""
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("💰 የሽያጭ ሪፖርት",  callback_data="admin_sales_report")],
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


# ── Report generators ─────────────────────────────────────────────────────────

async def generate_sales_report(
    update: Update, context: ContextTypes.DEFAULT_TYPE, days: int = 30
) -> None:
    """Generate and display a sales report."""
    query = update.callback_query
    end_date   = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    try:
        async for db in get_db_session():
            sales_service = SalesAnalyticsService(db)
            summary      = await sales_service.get_sales_summary(start_date, end_date)
            daily_sales  = await sales_service.get_daily_sales(days)
            top_products = await sales_service.get_top_products(limit=5, days=days)
            break
    except Exception as exc:
        logger.error("Sales report error: %s", exc)
        summary = {}
        daily_sales  = []
        top_products = []

    report_text = (
        f"📊 *የሽያጭ ሪፖርት* — {days} ቀናት\n\n"
        f"📅 {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}\n\n"
        f"💰 ጠቅላላ ሽያጭ: *{format_etb(summary.get('total_revenue', 0))}*\n"
        f"📦 ጠቅላላ ትዕዛዞች: *{summary.get('total_orders', 0)}*\n"
        f"📊 አማካይ ትዕዛዝ: *{format_etb(summary.get('avg_order_value', 0))}*\n\n"
        "🏆 *ከፍተኛ ምርቶች:*\n"
    )
    for p in top_products[:3]:
        report_text += f"• {p.get('product_name', 'N/A')}: {format_etb(p.get('revenue', 0))}\n"

    report_text += "\n📈 *ዕለታዊ (ባለፉ 7 ቀናት):*\n"
    for day in daily_sales[-7:]:
        report_text += (
            f"• {day.get('date', 'N/A')}: "
            f"{format_etb(day.get('total_sales', 0))} "
            f"({day.get('order_count', 0)} ትዕዛዞች)\n"
        )

    keyboard = [
        [InlineKeyboardButton("📥 CSV ሪፖርት አውርድ", callback_data="admin_export_sales")],
        [InlineKeyboardButton("🔙 ወደ ሪፖርቶች",      callback_data="admin_reports_back")],
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
            vendors   = await user_service.user_repo.count({"role": "vendor"})
            user_growth = await user_analytics.get_user_growth(days=30)
            break
    except Exception as exc:
        logger.error("User report error: %s", exc)
        total_users = active_users = new_users_last_30d = vendors = 0
        user_growth = []

    report_text = (
        "👥 *የተጠቃሚ ሪፖርት*\n\n"
        f"• ጠቅላላ ተጠቃሚዎች: *{total_users}*\n"
        f"• ንቁ ተጠቃሚዎች (30 ቀን): *{active_users}*\n"
        f"• አዳዲስ ተጠቃሚዎች (30 ቀን): *{new_users_last_30d}*\n"
        f"• ሻጮች: *{vendors}*\n\n"
        "📈 *የተጠቃሚ እድገት (ባለፉ 7 ቀናት):*\n"
    )
    for g in user_growth[-7:]:
        report_text += f"• {g.get('date', 'N/A')}: +{g.get('new_users', 0)} አዳዲስ\n"

    keyboard = [
        [InlineKeyboardButton("📥 CSV ሪፖርት አውርድ", callback_data="admin_export_users")],
        [InlineKeyboardButton("🔙 ወደ ሪፖርቶች",      callback_data="admin_reports_back")],
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
            total_products = await product_service.product_repo.count()
            pending_count  = await product_service.product_repo.count({"status": "pending"})
            active_count   = await product_service.product_repo.count({"status": "active"})
            categories     = await category_service.get_all_categories()
            break
    except Exception as exc:
        logger.error("Product report error: %s", exc)
        total_products = pending_count = active_count = 0
        categories = []

    report_text = (
        "📦 *የምርት ሪፖርት*\n\n"
        f"• ጠቅላላ ምርቶች: *{total_products}*\n"
        f"• ንቁ ምርቶች: *{active_count}*\n"
        f"• በመጠባበቅ ላይ: *{pending_count}*\n"
        f"• ምድቦች: *{len(categories)}*\n\n"
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
            user_service  = UserService(db)
            total_vendors  = await user_service.user_repo.count({"role": "vendor"})
            active_vendors = await user_service.user_repo.count({"role": "vendor", "status": "active"})
            break
    except Exception as exc:
        logger.error("Vendor report error: %s", exc)
        total_vendors = active_vendors = 0

    report_text = (
        "🏪 *የሻጭ ሪፖርት*\n\n"
        f"• ጠቅላላ ሻጮች: *{total_vendors}*\n"
        f"• ንቁ ሻጮች: *{active_vendors}*\n"
        f"• ያልነቁ ሻጮች: *{total_vendors - active_vendors}*\n"
    )

    await query.message.edit_text(
        report_text, parse_mode="Markdown",
        reply_markup=_back_keyboard("admin_reports_back"),
    )


# ── CSV exports ───────────────────────────────────────────────────────────────

async def export_sales_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a sales CSV and send it as a document."""
    query = update.callback_query
    await query.answer("📊 ሪፖርቱ ዝግጁ ነው...")

    end_date   = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    try:
        async for db in get_db_session():
            order_service = OrderService(db)
            orders = await order_service.order_repo.get_all(
                filters={"created_at__gte": start_date},
                order_by="created_at",
                order_desc=True,
                limit=1000,
            )
            break
    except Exception as exc:
        logger.error("Export sales CSV error: %s", exc)
        orders = []

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Order ID", "Order Number", "User ID",
        "Total (ETB)", "Status", "Payment Status", "Created At",
    ])
    for o in orders:
        writer.writerow([
            o.id,
            getattr(o, "order_number", o.id),
            o.user_id,
            float(o.total),
            str(o.status),
            str(getattr(o, "payment_status", "")),
            o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])

    filename = f"sales_report_{end_date.strftime('%Y%m%d')}.csv"
    bio = io.BytesIO(buf.getvalue().encode("utf-8-sig"))  # BOM for Excel
    bio.name = filename

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=bio,
        filename=filename,
        caption=f"📥 *የሽያጭ ሪፖርት* — {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}\n"
                f"ጠቅላላ ትዕዛዞች: {len(orders)}",
        parse_mode="Markdown",
    )


async def export_users_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a users CSV and send it as a document."""
    query = update.callback_query
    await query.answer("👥 ሪፖርቱ ዝግጁ ነው...")

    try:
        async for db in get_db_session():
            user_service = UserService(db)
            users = await user_service.user_repo.get_all(
                order_by="created_at",
                order_desc=True,
                limit=2000,
            )
            break
    except Exception as exc:
        logger.error("Export users CSV error: %s", exc)
        users = []

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "User ID", "Username", "Full Name",
        "Phone", "Email", "Role", "Status",
        "Telegram ID", "Joined At",
    ])
    for u in users:
        writer.writerow([
            u.id,
            u.username or "",
            u.full_name or "",
            u.phone_number or "",
            u.email or "",
            str(u.role),
            str(u.status),
            getattr(u, "telegram_id", ""),
            u.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])

    now = datetime.utcnow()
    filename = f"users_report_{now.strftime('%Y%m%d')}.csv"
    bio = io.BytesIO(buf.getvalue().encode("utf-8-sig"))
    bio.name = filename

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=bio,
        filename=filename,
        caption=f"📥 *የተጠቃሚ ሪፖርት*\nጠቅላላ ተጠቃሚዎች: {len(users)}",
        parse_mode="Markdown",
    )


# ── legacy stub ───────────────────────────────────────────────────────────────

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
    "export_sales_csv",
    "export_users_csv",
]
