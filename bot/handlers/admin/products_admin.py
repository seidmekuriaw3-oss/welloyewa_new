# ============================
# WOLLOYEWA STORE BOT - ADMIN PRODUCTS HANDLER
# ============================
"""Admin handlers for product management."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime

from core.logger import logger
from core.config import settings
from apps.products.services import ProductService, CategoryService
from infrastructure.database.session import get_db_session


async def products_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show admin products management panel.
    """
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("📋 ሁሉንም ምርቶች", callback_data="admin_list_products")],
        [InlineKeyboardButton("➕ አዲስ ምርት", callback_data="admin_add_product")],
        [InlineKeyboardButton("📁 ምድቦች", callback_data="admin_categories")],
        [InlineKeyboardButton("⏳ በመጠባበቅ ላይ", callback_data="admin_pending_products")],
        [InlineKeyboardButton("🔙 ወደ አስተዳደር", callback_data="admin_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "📦 *የምርት አስተዳደር*\n\n"
        "ከዚህ በታች ያሉትን አማራጮች ይምረጡ።",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    List all products for admin.
    """
    query = update.callback_query
    page = context.user_data.get("admin_products_page", 1)
    page_size = 10
    
    async for db in get_db_session():
        product_service = ProductService(db)
        products, total = await product_service.product_repo.get_all_with_count(
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        break
    
    if not products:
        await query.message.edit_text("📦 ምንም ምርቶች አልተገኙም።")
        return
    
    total_pages = (total + page_size - 1) // page_size
    
    products_text = "📦 *ሁሉም ምርቶች*\n\n"
    
    for product in products:
        status_emoji = "✅" if product.status == "active" else "⏳"
        products_text += f"{status_emoji} *{product.name}*\n"
        products_text += f"   🆔 ID: {product.id}\n"
        products_text += f"   👤 ሻጭ: {product.vendor_id}\n"
        products_text += f"   💰 ዋጋ: {product.price}\n"
        products_text += f"   📦 ክምችት: {product.stock_quantity}\n\n"
    
    # Pagination
    keyboard = []
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="admin_products_page_prev"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="admin_products_page_next"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        products_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def product_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle admin product callbacks.
    """
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "admin_list_products":
        context.user_data["admin_products_page"] = 1
        await list_products(update, context)
    
    elif action == "admin_products_page_prev":
        context.user_data["admin_products_page"] = context.user_data.get("admin_products_page", 1) - 1
        await list_products(update, context)
    
    elif action == "admin_products_page_next":
        context.user_data["admin_products_page"] = context.user_data.get("admin_products_page", 1) + 1
        await list_products(update, context)
    
    elif action == "admin_products_back":
        await products_admin_panel(update, context)
    
    elif action == "admin_categories":
        await manage_categories(update, context)
    
    elif action == "admin_pending_products":
        await list_pending_products(update, context)


async def manage_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manage product categories (admin).
    """
    query = update.callback_query
    
    async for db in get_db_session():
        category_service = CategoryService(db)
        categories = await category_service.get_all_categories()
        break
    
    categories_text = "📁 *ምድቦች*\n\n"
    
    for cat in categories:
        categories_text += f"• *{cat.name}* (ID: {cat.id})\n"
        categories_text += f"  📦 ምርቶች: {cat.product_count}\n"
        categories_text += f"  🆔 ስልክ: {cat.slug}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ አዲስ ምድብ", callback_data="admin_add_category")],
        [InlineKeyboardButton("✏️ አርትዕ", callback_data="admin_edit_category")],
        [InlineKeyboardButton("🗑️ ሰርዝ", callback_data="admin_delete_category")],
        [InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        categories_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def list_pending_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    List products pending approval.
    """
    query = update.callback_query
    
    async for db in get_db_session():
        product_service = ProductService(db)
        products = await product_service.product_repo.get_all(filters={"status": "pending"})
        break
    
    if not products:
        await query.message.edit_text("📦 ምንም በመጠባበቅ ላይ ያሉ ምርቶች የሉም።")
        return
    
    products_text = "⏳ *በመጠባበቅ ላይ ያሉ ምርቶች*\n\n"
    
    for product in products:
        products_text += f"• *{product.name}*\n"
        products_text += f"  🆔 ID: {product.id}\n"
        products_text += f"  👤 ሻጭ: {product.vendor_id}\n"
        products_text += f"  📅 {product.created_at.strftime('%Y-%m-%d')}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("✅ አጽድቅ", callback_data="admin_approve_product")],
        [InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data="admin_reject_product")],
        [InlineKeyboardButton("🔙 ወደ ምርት አስተዳደር", callback_data="admin_products_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        products_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


__all__ = [
    "products_admin_panel",
    "product_admin_callback",
]