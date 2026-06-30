# ============================
# WOLLOYEWA STORE BOT - CATALOG HANDLER
# ============================
"""Telegram bot catalog browsing and product display handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from apps.products.services import ProductService, CategoryService
from infrastructure.database.session import get_db_session
from core.utils.currency import format_etb


# Pagination settings
PRODUCTS_PER_PAGE = 10


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /menu command.
    
    Shows the main menu with categories.
    """
    query = update.callback_query if update.callback_query else None
    chat_id = update.effective_chat.id
    
    # Get categories
    async for db in get_db_session():
        category_service = CategoryService(db)
        categories = await category_service.get_all_categories(active_only=True)
        break
    
    # Build keyboard
    keyboard = []
    row = []
    
    for i, category in enumerate(categories):
        button_text = category.name_am or category.name
        row.append(InlineKeyboardButton(button_text, callback_data=f"cat_{category.id}"))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Add menu buttons
    keyboard.append([
        InlineKeyboardButton("🔍 ፈልግ", callback_data="menu_search"),
        InlineKeyboardButton("🛒 ቅርጫት", callback_data="menu_cart"),
    ])
    keyboard.append([
        InlineKeyboardButton("⭐ ተመራጮች", callback_data="menu_wishlist"),
        InlineKeyboardButton("👤 ፕሮፋይል", callback_data="menu_profile"),
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = "📁 *ምድቦች*\n\nእባክዎ ማየት የሚፈልጉትን ምድብ ይምረጡ።"
    
    if query:
        await query.message.edit_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)
        await query.answer()
    else:
        await update.effective_message.reply_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle category selection: cat_<id>"""
    query = update.callback_query
    await query.answer()

    # Extract category ID — data is exactly "cat_<id>"
    category_id = int(query.data.split("_")[1])

    context.user_data["current_category"] = category_id
    context.user_data["current_page"] = 1

    await show_category_products(update, context, category_id, page=1)


async def category_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle category pagination: cat_page_<category_id>_<page>"""
    query = update.callback_query
    await query.answer()

    # data format: "cat_page_<category_id>_<page>"
    parts = query.data.split("_")
    category_id = int(parts[2])
    page = int(parts[3])

    context.user_data["current_category"] = category_id
    context.user_data["current_page"] = page

    await show_category_products(update, context, category_id, page=page)


async def show_category_products(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    category_id: int,
    page: int = 1,
) -> None:
    """
    Show products in a category with pagination.
    
    Args:
        update: Telegram update
        context: Callback context
        category_id: Category ID
        page: Page number
    """
    query = update.callback_query
    
    async for db in get_db_session():
        product_service = ProductService(db)
        category_service = CategoryService(db)
        
        # Get category name
        category = await category_service.get_category(category_id)
        category_name = category.name_am or category.name
        
        # Get products
        offset = (page - 1) * PRODUCTS_PER_PAGE
        products = await product_service.product_repo.get_by_category(
            category_id=category_id,
            limit=PRODUCTS_PER_PAGE,
            offset=offset,
        )
        
        # Get total count for pagination
        total = await product_service.product_repo.count({"category_id": category_id, "status": "active"})
        total_pages = (total + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
        
        break
    
    if not products:
        text = f"📁 *{category_name}*\n\nምንም ምርቶች አልተገኙም።"
        await query.message.edit_text(text, parse_mode="Markdown")
        return
    
    # Build product list message
    product_list = []
    for product in products:
        price_text = format_etb(product.price)
        if product.discounted_price:
            price_text = f"~~{format_etb(product.compare_price)}~~ {format_etb(product.price)}"
        
        stock_status = "✅ ክምችት አለ" if product.is_in_stock else "❌ ክምችት የለም"
        
        product_list.append(
            f"• *{product.name}*\n"
            f"  💰 {price_text}\n"
            f"  {stock_status}\n"
            f"  [ዝርዝር ለማየት ይጫኑ](/view_{product.id})"
        )
    
    text = f"📁 *{category_name}* - ገጽ {page}/{total_pages}\n\n"
    text += "\n".join(product_list[:5])  # Show 5 products per message
    
    # Build navigation keyboard
    keyboard = []
    
    # Product buttons
    for product in products[:5]:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {product.name[:30]}",
                callback_data=f"prod_{product.id}"
            )
        ])
    
    # Pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data=f"cat_page_{category_id}_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data=f"cat_page_{category_id}_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Back button
    keyboard.append([
        InlineKeyboardButton("🔙 ወደ ምድቦች", callback_data="menu_back"),
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle product selection: prod_<id>"""
    query = update.callback_query
    await query.answer()

    # data is "prod_<id>" — split gives ['prod', '<id>']
    product_id = int(query.data.split("_")[1])
    
    async for db in get_db_session():
        product_service = ProductService(db)
        
        try:
            product = await product_service.get_product(product_id)
        except Exception as e:
            await query.message.reply_text("❌ ምርቱ አልተገኘም።")
            return
        
        break
    
    # Build product detail message
    price_text = format_etb(product.price)
    if product.discounted_price:
        price_text = f"~~{format_etb(product.compare_price)}~~ {format_etb(product.price)}"
    
    stock_status = "✅ ክምችት አለ" if product.is_in_stock else "❌ ክምችት የለም"
    
    rating_text = "⭐" * int(product.rating) + "☆" * (5 - int(product.rating)) if product.rating > 0 else "⭐ ገና ግምገማ የለም"
    
    text = f"""
*{product.name}*

{product.description or 'ምንም መግለጫ የለም'}

💰 *ዋጋ:* {price_text}
📦 *ሁኔታ:* {stock_status}
{rating_text} ({product.reviews_count} ግምገማዎች)

👤 *ሻጭ:* {product.vendor.business_name if product.vendor else 'N/A'}
    """
    
    # Build keyboard
    keyboard = [
        [
            InlineKeyboardButton("🛒 ወደ ቅርጫት ጨምር", callback_data=f"add_to_cart_{product.id}"),
            InlineKeyboardButton("❤️ ወደ ተመራጮች", callback_data=f"add_to_wishlist_{product.id}"),
        ],
        [
            InlineKeyboardButton("📝 ግምገማ ጻፍ", callback_data=f"review_{product.id}"),
            InlineKeyboardButton("🔙 ወደ ኋላ", callback_data="menu_back"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages that aren't commands.
    
    Searches for products matching the text.
    """
    text = update.effective_message.text
    
    if len(text) < 3:
        await update.effective_message.reply_text("እባክዎ ቢያንስ 3 ፊደላት ያስገቡ።")
        return
    
    # Search for products
    async for db in get_db_session():
        product_service = ProductService(db)
        products = await product_service.search_products(text, limit=10)
        break
    
    if not products:
        await update.effective_message.reply_text(f"🔍 '{text}' የሚል ምርት አልተገኘም።")
        return
    
    # Build results message
    result_text = f"🔍 የ'*{text}*' ፍለጋ ውጤት:\n\n"
    
    for product in products[:5]:
        result_text += f"• *{product.name}* - {format_etb(product.price)}\n"
    
    result_text += "\nተጨማሪ ውጤት ለማየት /search ይጠቀሙ።"
    
    await update.effective_message.reply_text(result_text, parse_mode="Markdown")


__all__ = [
    "menu_command",
    "category_callback",
    "category_page_callback",
    "product_callback",
    "show_category_products",
    "text_message_handler",
]