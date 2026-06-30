# ============================
# WOLLOYEWA STORE BOT - SEARCH HANDLER
# ============================
"""Telegram bot product search and filtering handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from core.logger import logger
from core.utils.currency import format_etb
from apps.products.services import ProductService
from apps.products.search_engine import ProductSearchEngine
from infrastructure.database.session import get_db_session

# Conversation states
WAITING_QUERY, FILTER_RESULTS = range(2)

# Search settings
SEARCH_RESULTS_PER_PAGE = 10


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /search command.
    
    Starts the search conversation.
    """
    await update.effective_message.reply_text(
        "🔍 *ምርቶችን ይፈልጉ*\n\n"
        "እባክዎ ማግኘት የሚፈልጉትን ምርት ስም ወይም ቁልፍ ቃል ይጻፉ።\n\n"
        "ለምሳሌ: 'ስልክ', 'ልብስ', 'ኮምፒውተር'",
        parse_mode="Markdown"
    )
    return WAITING_QUERY


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start search from callback.
    
    Returns:
        Next conversation state
    """
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "🔍 *ምርቶችን ይፈልጉ*\n\n"
        "እባክዎ ማግኘት የሚፈልጉትን ምርት ስም ወይም ቁልፍ ቃል ይጻፉ።",
        parse_mode="Markdown"
    )
    
    return WAITING_QUERY


async def search_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle search query input.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        Next conversation state
    """
    query_text = update.effective_message.text.strip()
    
    if len(query_text) < 2:
        await update.effective_message.reply_text("❌ እባክዎ ቢያንስ 2 ፊደላት ያስገቡ።")
        return WAITING_QUERY
    
    context.user_data["search_query"] = query_text
    context.user_data["search_page"] = 1
    context.user_data["search_filters"] = {}
    
    # Perform search
    await perform_search(update, context)
    
    return FILTER_RESULTS


async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Perform product search with current filters.
    
    Args:
        update: Telegram update
        context: Callback context
    """
    query = context.user_data.get("search_query", "")
    page = context.user_data.get("search_page", 1)
    filters = context.user_data.get("search_filters", {})
    
    async for db in get_db_session():
        search_engine = ProductSearchEngine(db)
        
        products, total = await search_engine.search(
            query=query,
            category=filters.get("category"),
            min_price=filters.get("min_price"),
            max_price=filters.get("max_price"),
            min_rating=filters.get("min_rating"),
            in_stock_only=filters.get("in_stock_only", False),
            on_sale_only=filters.get("on_sale_only", False),
            sort_by=filters.get("sort_by", "relevance"),
            page=page,
            page_size=SEARCH_RESULTS_PER_PAGE,
        )
        break
    
    if not products:
        await update.effective_message.reply_text(
            f"🔍 *'{query}'* የሚል ምርት አልተገኘም።\n\n"
            f"እባክዎ ሌላ ቃል ይሞክሩ ወይም /menu በመጠቀም ምድቦችን ይመልከቱ።",
            parse_mode="Markdown"
        )
        return
    
    # Build results message
    total_pages = (total + SEARCH_RESULTS_PER_PAGE - 1) // SEARCH_RESULTS_PER_PAGE
    
    results_text = f"🔍 *'{query}'* የፍለጋ ውጤት - ገጽ {page}/{total_pages}\n\n"
    
    for product in products:
        price_text = format_etb(product.price)
        if product.discounted_price:
            price_text = f"~~{format_etb(product.compare_price)}~~ {format_etb(product.price)}"
        
        stock_icon = "✅" if product.is_in_stock else "❌"
        
        results_text += f"{stock_icon} *{product.name}*\n"
        results_text += f"   💰 {price_text}\n"
        results_text += f"   ⭐ {product.rating:.1f}/5\n"
        results_text += f"   [ዝርዝር ለማየት ይጫኑ](/view_{product.id})\n\n"
    
    # Build keyboard
    keyboard = []
    
    # Pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data="search_page_prev"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data="search_page_next"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Filter and sort buttons
    keyboard.append([
        InlineKeyboardButton("🔧 ማጣሪያ", callback_data="search_filter"),
        InlineKeyboardButton("📊 ደርድር", callback_data="search_sort"),
    ])
    
    # Product buttons (limited to 5)
    for product in products[:5]:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {product.name[:30]}",
                callback_data=f"prod_{product.id}"
            )
        ])
    
    # Back button
    keyboard.append([InlineKeyboardButton("🔍 አዲስ ፍለጋ", callback_data="search_new")])
    keyboard.append([InlineKeyboardButton("🔙 ወደ ምናሌ", callback_data="menu_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            results_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        await update.callback_query.answer()
    else:
        await update.effective_message.reply_text(
            results_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle search filter callback.
    
    Shows filter options.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "search_filter":
        # Show filter options
        keyboard = [
            [InlineKeyboardButton("📁 ምድብ", callback_data="filter_category")],
            [InlineKeyboardButton("💰 የዋጋ ክልል", callback_data="filter_price")],
            [InlineKeyboardButton("⭐ ዝቅተኛ ደረጃ", callback_data="filter_rating")],
            [InlineKeyboardButton("✅ ክምችት ያለው ብቻ", callback_data="filter_in_stock")],
            [InlineKeyboardButton("🏷️ በሽያጭ ላይ ያሉ", callback_data="filter_on_sale")],
            [InlineKeyboardButton("🗑️ ማጣሪያ አጥፋ", callback_data="filter_clear")],
            [InlineKeyboardButton("🔙 ወደ ውጤቶች", callback_data="search_back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "🔧 *ማጣሪያ አማራጮች*\n\n"
            "ምርጫዎችዎን ይምረጡ።",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif query.data == "search_sort":
        # Show sort options
        keyboard = [
            [InlineKeyboardButton("📊 በተዛማጅነት", callback_data="sort_relevance")],
            [InlineKeyboardButton("💰 ዋጋ ወጪ ወደ ታች", callback_data="sort_price_desc")],
            [InlineKeyboardButton("💰 ዋጋ ወጪ ወደ ላይ", callback_data="sort_price_asc")],
            [InlineKeyboardButton("⭐ በደረጃ", callback_data="sort_rating")],
            [InlineKeyboardButton("🆕 በአዲስነት", callback_data="sort_newest")],
            [InlineKeyboardButton("🔙 ወደ ውጤቶች", callback_data="search_back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "📊 *ደርድር አማራጮች*\n\n"
            "ምርጫዎችዎን ይምረጡ።",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif query.data == "search_back":
        # Go back to search results
        await perform_search(update, context)
    
    elif query.data == "search_page_prev":
        # Previous page
        context.user_data["search_page"] = context.user_data.get("search_page", 1) - 1
        await perform_search(update, context)
    
    elif query.data == "search_page_next":
        # Next page
        context.user_data["search_page"] = context.user_data.get("search_page", 1) + 1
        await perform_search(update, context)
    
    elif query.data == "search_new":
        # New search
        await search_command(update, context)


async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel the search conversation.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        Next conversation state (END)
    """
    await update.effective_message.reply_text("❌ ፍለጋ ተሰርዟል።")
    return ConversationHandler.END


__all__ = [
    "search_command",
    "start_search",
    "search_query_handler",
    "filter_callback",
    "cancel_search",
    "WAITING_QUERY",
    "FILTER_RESULTS",
]