# ============================
# WOLLOYEWA STORE BOT - ADMIN DASHBOARD HANDLER
# ============================
"""
Admin dashboard — central router for ALL admin_* callbacks.

New callback patterns handled here (in addition to the originals):
  admin_cat_edit_<id>          → start edit-category text flow
  admin_cat_del_<id>           → confirm-delete panel
  admin_cat_del_confirm_<id>   → actually delete category
  admin_cat_pick_<id>          → finish add-product flow (category chosen)
  admin_approve_product_<id>   → approve a specific product
  admin_reject_product_<id>    → reject a specific product
  admin_suspend_user_<id>      → confirm-suspend panel
  admin_unsuspend_user_<id>    → lift suspension immediately
  admin_confirm_suspend_<id>   → actually suspend user
  admin_approve_vendor_<id>    → approve specific vendor
  admin_reject_vendor_<id>     → reject specific vendor
  admin_view_order_<id>        → show full order detail
  admin_set_status_<oid>_<st>  → change order status
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

from core.logger import logger
from core.config import settings
from core.utils.currency import format_etb
from apps.analytics.services import DashboardService, SalesAnalyticsService
from apps.users.services import UserService
from apps.orders.services import OrderService
from infrastructure.database.session import get_db_session


# ── Helpers ──────────────────────────────────────────────────────────────────

def _admin_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📊 ዳሽቦርድ",   callback_data="admin_dashboard")],
        [InlineKeyboardButton("📦 ምርቶች",    callback_data="admin_products")],
        [InlineKeyboardButton("📋 ትዕዛዞች",   callback_data="admin_orders")],
        [InlineKeyboardButton("👥 ተጠቃሚዎች", callback_data="admin_users")],
        [InlineKeyboardButton("🏪 ሻጮች",     callback_data="admin_vendors")],
        [InlineKeyboardButton("📊 ሪፖርቶች",  callback_data="admin_reports")],
        [InlineKeyboardButton("⚙️ ቅንብሮች",  callback_data="admin_settings")],
    ]
    return InlineKeyboardMarkup(keyboard)


ADMIN_MENU_TEXT = (
    "🔧 *የአስተዳደር ፓነል*\n\n"
    "እንኳን ደህና መጡ! ከዚህ በታች ያሉትን አማራጮች ይምረጡ።"
)


# ── Commands ─────────────────────────────────────────────────────────────────

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin."""
    if update.effective_user.id not in settings.admin_ids_list:
        await update.message.reply_text("❌ ይህን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም።")
        return
    await update.message.reply_text(
        ADMIN_MENU_TEXT, parse_mode="Markdown", reply_markup=_admin_main_keyboard()
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats."""
    if update.effective_user.id not in settings.admin_ids_list:
        await update.message.reply_text("❌ ፈቃድ የለዎትም።")
        return
    await _send_dashboard_text(update, context, via_command=True)


# ── Dashboard stats ───────────────────────────────────────────────────────────

async def _send_dashboard_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    via_command: bool = False,
) -> None:
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start  = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    try:
        async for db in get_db_session():
            sales_service = SalesAnalyticsService(db)
            user_service  = UserService(db)
            order_service = OrderService(db)

            today_sales  = await sales_service.get_sales_summary(today_start, now)
            week_sales   = await sales_service.get_sales_summary(week_start, now)
            month_sales  = await sales_service.get_sales_summary(month_start, now)
            total_users  = await user_service.user_repo.count()
            active_users = await user_service.user_repo.count({"last_active__gte": week_start})
            vendors      = await user_service.user_repo.count({"role": "vendor"})
            pending_orders    = await order_service.order_repo.count({"status": "pending"})
            processing_orders = await order_service.order_repo.count({"status": "processing"})
            break
    except Exception as exc:
        logger.error("Dashboard stats error: %s", exc)
        today_sales = week_sales = month_sales = {}
        total_users = active_users = vendors = pending_orders = processing_orders = 0

    dashboard_text = (
        "📊 *የስርዓት ዳሽቦርድ*\n\n"
        "💰 *ሽያጭ*\n"
        f"• ዛሬ: {format_etb(today_sales.get('total_revenue', 0))}\n"
        f"• በዚህ ሳምንት: {format_etb(week_sales.get('total_revenue', 0))}\n"
        f"• በዚህ ወር: {format_etb(month_sales.get('total_revenue', 0))}\n\n"
        "👥 *ተጠቃሚዎች*\n"
        f"• ጠቅላላ: {total_users}\n"
        f"• ንቁ (7 ቀን): {active_users}\n"
        f"• ሻጮች: {vendors}\n\n"
        "📦 *ትዕዛዞች*\n"
        f"• በመጠባበቅ ላይ: {pending_orders}\n"
        f"• በማቀናበር ላይ: {processing_orders}\n\n"
        "⏱️ *የስርዓት ሁኔታ*\n"
        f"• ሰዓት: {now.strftime('%Y-%m-%d %H:%M')}\n"
        f"• አካባቢ: {settings.ENVIRONMENT}"
    )

    keyboard = [
        [InlineKeyboardButton("🔄 አድስ",           callback_data="admin_dashboard")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር",    callback_data="admin_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if via_command:
        await update.message.reply_text(dashboard_text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text(dashboard_text, parse_mode="Markdown", reply_markup=reply_markup)


async def show_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_dashboard_text(update, context, via_command=False)


# ── Sub-panels ────────────────────────────────────────────────────────────────

async def show_admin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.message.edit_text(
        ADMIN_MENU_TEXT, parse_mode="Markdown", reply_markup=_admin_main_keyboard()
    )


async def show_vendors_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Vendors entry from main menu — delegate to users_admin.list_vendors."""
    from bot.handlers.admin.users_admin import list_vendors
    context.user_data["admin_vendors_page"] = 1
    await list_vendors(update, context)


async def show_admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("🔧 ስርዓት ቅንብሮች",  callback_data="admin_system_settings")],
        [InlineKeyboardButton("💰 የክፍያ ቅንብሮች",  callback_data="admin_payment_settings")],
        [InlineKeyboardButton("📧 ማሳወቂያ ቅንብሮች", callback_data="admin_notification_settings")],
        [InlineKeyboardButton("🗄️ የውሂብ ጎታ ምትኬ", callback_data="admin_backup")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር",    callback_data="admin_back")],
    ]
    await query.message.edit_text(
        "⚙️ *የስርዓት ቅንብሮች*\n\nከዚህ በታች ያሉትን ቅንብሮች ይቀይሩ።",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_system_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.message.edit_text(
        f"🔧 *ስርዓት ቅንብሮች*\n\n"
        f"• አካባቢ: `{settings.ENVIRONMENT}`\n"
        f"• ዲቡግ: `{settings.DEBUG}`\n"
        f"• ስሪት: `{settings.VERSION}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ወደ ቅንብሮች", callback_data="admin_settings")]
        ]),
    )


async def show_payment_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.message.edit_text(
        "💰 *የክፍያ ቅንብሮች*\n\n"
        "• Chapa: ✅ ንቁ\n"
        "• Telebirr: ✅ ንቁ\n"
        "• CBE Birr: ✅ ንቁ\n\n"
        "⚠️ ቅንብሮችን ለመቀየር `.env` ፋይሉ ያስተካክሉ።",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ወደ ቅንብሮች", callback_data="admin_settings")]
        ]),
    )


async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.message.edit_text(
        "📧 *ማሳወቂያ ቅንብሮች*\n\n"
        "• ትዕዛዝ ማሳወቂያ: ✅ ንቁ\n"
        "• ክምችት ማሳወቂያ: ✅ ንቁ\n"
        "• ሪፖርት ማሳወቂያ: ✅ ንቁ",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ወደ ቅንብሮች", callback_data="admin_settings")]
        ]),
    )


async def show_backup_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    now = datetime.utcnow()
    await query.message.edit_text(
        "🗄️ *የውሂብ ጎታ ምትኬ*\n\n"
        f"• ሰዓት: {now.strftime('%Y-%m-%d %H:%M UTC')}\n"
        "• ሁኔታ: ✅ ንቁ (በራስ-ሰር)\n\n"
        "⚠️ ምትኬ ለማስጀመር DevOps ቡድን ያነጋግሩ።",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ወደ ቅንብሮች", callback_data="admin_settings")]
        ]),
    )


# ── Master callback router ────────────────────────────────────────────────────

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Central router for ALL admin_* callbacks.
    Registered once in dispatcher.py with pattern ^admin_.
    """
    query = update.callback_query
    await query.answer()

    action  = query.data
    user_id = update.effective_user.id

    if user_id not in settings.admin_ids_list:
        await query.message.reply_text("❌ ፈቃድ የለዎትም።")
        return

    # ════════════════════════════════════════════════════════════════
    # Dynamic patterns  (check BEFORE the long elif chain)
    # ════════════════════════════════════════════════════════════════

    # admin_cat_edit_<id>
    if action.startswith("admin_cat_edit_"):
        cat_id = int(action.split("_")[-1])
        from bot.handlers.admin.products_admin import start_edit_category
        await start_edit_category(update, context, cat_id)
        return

    # admin_cat_del_<id>  (confirmation panel)
    if action.startswith("admin_cat_del_confirm_"):
        cat_id = int(action.split("_")[-1])
        from bot.handlers.admin.products_admin import do_delete_category
        await do_delete_category(update, context, cat_id)
        return

    if action.startswith("admin_cat_del_"):
        cat_id = int(action.split("_")[-1])
        from bot.handlers.admin.products_admin import confirm_delete_category
        await confirm_delete_category(update, context, cat_id)
        return

    # admin_cat_pick_<id>  (finish add-product flow)
    if action.startswith("admin_cat_pick_"):
        cat_id = int(action.split("_")[-1])
        from bot.handlers.admin.products_admin import do_create_product_with_category
        await do_create_product_with_category(update, context, cat_id)
        return

    # admin_approve_product_<id>
    if action.startswith("admin_approve_product_"):
        product_id = int(action.split("_")[-1])
        from bot.handlers.admin.products_admin import do_approve_product
        await do_approve_product(update, context, product_id)
        return

    # admin_reject_product_<id>
    if action.startswith("admin_reject_product_"):
        product_id = int(action.split("_")[-1])
        from bot.handlers.admin.products_admin import do_reject_product
        await do_reject_product(update, context, product_id)
        return

    # admin_suspend_user_<id>  (confirmation panel)
    if action.startswith("admin_suspend_user_"):
        uid = int(action.split("_")[-1])
        from bot.handlers.admin.users_admin import confirm_suspend_user
        await confirm_suspend_user(update, context, uid)
        return

    # admin_confirm_suspend_<id>  (actually suspend)
    if action.startswith("admin_confirm_suspend_"):
        uid = int(action.split("_")[-1])
        from bot.handlers.admin.users_admin import do_suspend_user
        await do_suspend_user(update, context, uid)
        return

    # admin_unsuspend_user_<id>
    if action.startswith("admin_unsuspend_user_"):
        uid = int(action.split("_")[-1])
        from bot.handlers.admin.users_admin import do_unsuspend_user
        await do_unsuspend_user(update, context, uid)
        return

    # admin_approve_vendor_<id>
    if action.startswith("admin_approve_vendor_"):
        vid = int(action.split("_")[-1])
        from bot.handlers.admin.users_admin import do_approve_vendor
        await do_approve_vendor(update, context, vid)
        return

    # admin_reject_vendor_<id>
    if action.startswith("admin_reject_vendor_"):
        vid = int(action.split("_")[-1])
        from bot.handlers.admin.users_admin import do_reject_vendor
        await do_reject_vendor(update, context, vid)
        return

    # admin_view_order_<id>
    if action.startswith("admin_view_order_"):
        oid = int(action.split("_")[-1])
        from bot.handlers.admin.orders_admin import show_order_detail
        await show_order_detail(update, context, oid)
        return

    # admin_set_status_<order_id>_<new_status>
    if action.startswith("admin_set_status_"):
        # format: admin_set_status_<oid>_<status>
        # status may contain underscores (none currently, but be safe)
        parts = action[len("admin_set_status_"):].split("_", 1)
        oid, new_status = int(parts[0]), parts[1]
        from bot.handlers.admin.orders_admin import do_change_order_status
        await do_change_order_status(update, context, oid, new_status)
        return

    # ════════════════════════════════════════════════════════════════
    # Static routes
    # ════════════════════════════════════════════════════════════════

    # ── Top-level navigation ────────────────────────────────────────
    if action == "admin_dashboard":
        await show_admin_dashboard(update, context)

    elif action == "admin_back":
        await show_admin_menu_callback(update, context)

    # ── Settings ────────────────────────────────────────────────────
    elif action == "admin_settings":
        await show_admin_settings(update, context)

    elif action == "admin_system_settings":
        await show_system_settings(update, context)

    elif action == "admin_payment_settings":
        await show_payment_settings(update, context)

    elif action == "admin_notification_settings":
        await show_notification_settings(update, context)

    elif action == "admin_backup":
        await show_backup_info(update, context)

    # ── Products ────────────────────────────────────────────────────
    elif action == "admin_products":
        from bot.handlers.admin.products_admin import products_admin_panel
        await products_admin_panel(update, context)

    elif action == "admin_list_products":
        context.user_data["admin_products_page"] = 1
        from bot.handlers.admin.products_admin import list_products
        await list_products(update, context)

    elif action == "admin_products_page_prev":
        context.user_data["admin_products_page"] = max(
            1, context.user_data.get("admin_products_page", 1) - 1
        )
        from bot.handlers.admin.products_admin import list_products
        await list_products(update, context)

    elif action == "admin_products_page_next":
        context.user_data["admin_products_page"] = (
            context.user_data.get("admin_products_page", 1) + 1
        )
        from bot.handlers.admin.products_admin import list_products
        await list_products(update, context)

    elif action == "admin_products_back":
        from bot.handlers.admin.products_admin import products_admin_panel
        await products_admin_panel(update, context)

    elif action == "admin_categories":
        from bot.handlers.admin.products_admin import manage_categories
        await manage_categories(update, context)

    elif action == "admin_pending_products":
        from bot.handlers.admin.products_admin import list_pending_products
        await list_pending_products(update, context)

    elif action == "admin_add_product":
        from bot.handlers.admin.products_admin import start_add_product
        await start_add_product(update, context)

    elif action == "admin_add_category":
        from bot.handlers.admin.products_admin import start_add_category
        await start_add_category(update, context)

    # admin_edit_category / admin_delete_category with no id → show category list
    elif action == "admin_edit_category":
        from bot.handlers.admin.products_admin import manage_categories
        await manage_categories(update, context)   # user picks from the list

    elif action == "admin_delete_category":
        from bot.handlers.admin.products_admin import manage_categories
        await manage_categories(update, context)   # user picks from the list

    elif action == "admin_approve_product":
        # bare (no ID) → go to pending list so admin can pick
        from bot.handlers.admin.products_admin import list_pending_products
        await list_pending_products(update, context)

    elif action == "admin_reject_product":
        from bot.handlers.admin.products_admin import list_pending_products
        await list_pending_products(update, context)

    # ── Orders ──────────────────────────────────────────────────────
    elif action == "admin_orders":
        from bot.handlers.admin.orders_admin import orders_admin_panel
        await orders_admin_panel(update, context)

    elif action == "admin_list_orders":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = None
        from bot.handlers.admin.orders_admin import list_orders
        await list_orders(update, context)

    elif action == "admin_pending_orders":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = "pending"
        from bot.handlers.admin.orders_admin import list_orders
        await list_orders(update, context, status="pending")

    elif action == "admin_processing_orders":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = "processing"
        from bot.handlers.admin.orders_admin import list_orders
        await list_orders(update, context, status="processing")

    elif action == "admin_shipped_orders":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = "shipped"
        from bot.handlers.admin.orders_admin import list_orders
        await list_orders(update, context, status="shipped")

    elif action == "admin_delivered_orders":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = "delivered"
        from bot.handlers.admin.orders_admin import list_orders
        await list_orders(update, context, status="delivered")

    elif action == "admin_orders_page_prev":
        context.user_data["admin_orders_page"] = max(
            1, context.user_data.get("admin_orders_page", 1) - 1
        )
        from bot.handlers.admin.orders_admin import list_orders
        await list_orders(update, context, status=context.user_data.get("admin_orders_filter"))

    elif action == "admin_orders_page_next":
        context.user_data["admin_orders_page"] = (
            context.user_data.get("admin_orders_page", 1) + 1
        )
        from bot.handlers.admin.orders_admin import list_orders
        await list_orders(update, context, status=context.user_data.get("admin_orders_filter"))

    elif action == "admin_orders_back":
        from bot.handlers.admin.orders_admin import orders_admin_panel
        await orders_admin_panel(update, context)

    # bare change_status / view_order (no ID) → show order list to pick from
    elif action == "admin_change_status":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = None
        from bot.handlers.admin.orders_admin import list_orders
        await list_orders(update, context)

    elif action == "admin_view_order":
        context.user_data["admin_orders_page"] = 1
        context.user_data["admin_orders_filter"] = None
        from bot.handlers.admin.orders_admin import list_orders
        await list_orders(update, context)

    # ── Users ───────────────────────────────────────────────────────
    elif action == "admin_users":
        from bot.handlers.admin.users_admin import users_admin_panel
        await users_admin_panel(update, context)

    elif action == "admin_list_users":
        context.user_data["admin_users_page"] = 1
        from bot.handlers.admin.users_admin import list_users
        await list_users(update, context)

    elif action == "admin_users_page_prev":
        context.user_data["admin_users_page"] = max(
            1, context.user_data.get("admin_users_page", 1) - 1
        )
        from bot.handlers.admin.users_admin import list_users
        await list_users(update, context)

    elif action == "admin_users_page_next":
        context.user_data["admin_users_page"] = (
            context.user_data.get("admin_users_page", 1) + 1
        )
        from bot.handlers.admin.users_admin import list_users
        await list_users(update, context)

    elif action == "admin_users_back":
        from bot.handlers.admin.users_admin import users_admin_panel
        await users_admin_panel(update, context)

    elif action == "admin_suspended_users":
        from bot.handlers.admin.users_admin import list_suspended_users
        await list_suspended_users(update, context)

    elif action == "admin_search_users":
        from bot.handlers.admin.users_admin import prompt_search_users
        await prompt_search_users(update, context)

    # bare edit_user / suspend_user (no ID) → show user list so admin can pick
    elif action == "admin_edit_user":
        context.user_data["admin_users_page"] = 1
        from bot.handlers.admin.users_admin import list_users
        await list_users(update, context)

    elif action == "admin_suspend_user":
        context.user_data["admin_users_page"] = 1
        from bot.handlers.admin.users_admin import list_users
        await list_users(update, context)

    # ── Vendors ─────────────────────────────────────────────────────
    elif action == "admin_vendors":
        await show_vendors_list(update, context)

    elif action == "admin_list_vendors":
        context.user_data["admin_vendors_page"] = 1
        from bot.handlers.admin.users_admin import list_vendors
        await list_vendors(update, context)

    elif action == "admin_pending_vendors":
        context.user_data["admin_vendors_page"] = 1
        from bot.handlers.admin.users_admin import list_vendors
        await list_vendors(update, context, pending_only=True)

    elif action == "admin_vendors_page_prev":
        context.user_data["admin_vendors_page"] = max(
            1, context.user_data.get("admin_vendors_page", 1) - 1
        )
        from bot.handlers.admin.users_admin import list_vendors
        await list_vendors(update, context)

    elif action == "admin_vendors_page_next":
        context.user_data["admin_vendors_page"] = (
            context.user_data.get("admin_vendors_page", 1) + 1
        )
        from bot.handlers.admin.users_admin import list_vendors
        await list_vendors(update, context)

    # bare approve/reject vendor (no ID) → pending vendors list
    elif action == "admin_approve_vendor":
        context.user_data["admin_vendors_page"] = 1
        from bot.handlers.admin.users_admin import list_vendors
        await list_vendors(update, context, pending_only=True)

    elif action == "admin_reject_vendor":
        context.user_data["admin_vendors_page"] = 1
        from bot.handlers.admin.users_admin import list_vendors
        await list_vendors(update, context, pending_only=True)

    # ── Reports ─────────────────────────────────────────────────────
    elif action == "admin_reports":
        from bot.handlers.admin.reports import reports_panel
        await reports_panel(update, context)

    elif action == "admin_sales_report":
        from bot.handlers.admin.reports import generate_sales_report
        await generate_sales_report(update, context)

    elif action == "admin_user_report":
        from bot.handlers.admin.reports import generate_user_report
        await generate_user_report(update, context)

    elif action == "admin_product_report":
        from bot.handlers.admin.reports import generate_product_report
        await generate_product_report(update, context)

    elif action == "admin_vendor_report":
        from bot.handlers.admin.reports import generate_vendor_report
        await generate_vendor_report(update, context)

    elif action == "admin_daily_report":
        from bot.handlers.admin.reports import generate_sales_report
        await generate_sales_report(update, context, days=1)

    elif action == "admin_weekly_report":
        from bot.handlers.admin.reports import generate_sales_report
        await generate_sales_report(update, context, days=7)

    elif action == "admin_monthly_report":
        from bot.handlers.admin.reports import generate_sales_report
        await generate_sales_report(update, context, days=30)

    elif action == "admin_reports_back":
        from bot.handlers.admin.reports import reports_panel
        await reports_panel(update, context)

    elif action == "admin_export_sales":
        from bot.handlers.admin.reports import export_sales_csv
        await export_sales_csv(update, context)

    elif action == "admin_export_users":
        from bot.handlers.admin.reports import export_users_csv
        await export_users_csv(update, context)

    else:
        logger.warning("Unhandled admin callback: %s", action)
        await query.message.reply_text(
            f"⚠️ ያልታወቀ ትዕዛዝ: `{action}`", parse_mode="Markdown"
        )


__all__ = [
    "admin_command",
    "admin_callback",
    "stats_command",
]
