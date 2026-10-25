# ============================
# WOLLOYEWA STORE BOT - SEARCH HANDLER
# ============================
"""Telegram bot product search and filtering handlers."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes, ConversationHandler
from telegram.helpers import escape_markdown

from apps.products.search_engine import ProductSearchEngine
from bot.handlers.text_routing import mark_text_message_handled
from bot.localization import get_language, tr
from core.constants import CATEGORY_NAMES_AMHARIC, ProductCategory
from core.logger import logger
from core.utils.currency import format_etb
from infrastructure.database.session import get_db_session

# Conversation states
WAITING_QUERY, FILTER_RESULTS = range(2)

# Search settings
SEARCH_RESULTS_PER_PAGE = 10


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle the /search command.

    Starts the search conversation.
    """
    mark_text_message_handled(update, context)
    await update.effective_message.reply_text(
        tr(context, "search_prompt"),
        parse_mode="Markdown",
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
        tr(context, "search_prompt"), parse_mode="Markdown"
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
    mark_text_message_handled(update, context)
    query_text = update.effective_message.text.strip()

    if len(query_text) < 2:
        await update.effective_message.reply_text(tr(context, "search_min_length"))
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
            tr(context, "no_search_results", query=escape_markdown(query, version=1)),
            parse_mode="Markdown",
        )
        return

    # Build results message
    total_pages = (total + SEARCH_RESULTS_PER_PAGE - 1) // SEARCH_RESULTS_PER_PAGE

    results_text = tr(
        context,
        "search_results",
        query=escape_markdown(query, version=1),
        page=page,
        total_pages=total_pages,
    ) + "\n\n"

    for product in products:
        price_text = format_etb(product.price)
        if product.discounted_price:
            price_text = f"~~{format_etb(product.compare_price)}~~ {format_etb(product.price)}"

        stock_icon = "✅" if product.is_in_stock else "❌"

        language = get_language(context)
        product_name = (
            product.name_am if language == "am" else product.name
        ) or product.name
        product_name = escape_markdown(str(product_name), version=1)
        results_text += f"{stock_icon} *{product_name}*\n"
        results_text += f"   💰 {price_text}\n"
        results_text += f"   ⭐ {product.rating:.1f}/5\n"
        results_text += f"   {tr(context, 'view_product', id=product.id)}\n\n"

    # Build keyboard
    keyboard = []

    # Pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(f"◀️ {tr(context, 'previous')}", callback_data="search_page_prev"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(f"{tr(context, 'next')} ▶️", callback_data="search_page_next"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Filter and sort buttons
    keyboard.append(
        [
            InlineKeyboardButton(tr(context, "search_filter"), callback_data="search_filter"),
            InlineKeyboardButton(tr(context, "search_sort"), callback_data="search_sort"),
        ]
    )

    # Product buttons (limited to 5)
    for product in products[:5]:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"📦 {((product.name_am if get_language(context) == 'am' else product.name) or product.name)[:30]}",
                    callback_data=f"prod_{product.id}",
                )
            ]
        )

    # Back button
    keyboard.append([InlineKeyboardButton(tr(context, "search_new"), callback_data="search_new")])
    keyboard.append([InlineKeyboardButton(tr(context, "menu_back"), callback_data="menu_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(
            results_text, parse_mode="Markdown", reply_markup=reply_markup
        )
    else:
        await update.effective_message.reply_text(
            results_text, parse_mode="Markdown", reply_markup=reply_markup
        )


async def filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle search filter callback.

    Shows filter options.
    """
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest as exc:
        message = str(exc).lower()
        if "query is too old" not in message and "query id is invalid" not in message:
            raise
        logger.debug("Ignoring expired search callback query: %s", query.id)

    if query.data == "search_filter":
        # Show filter options
        keyboard = [
            [InlineKeyboardButton(tr(context, "filter_category"), callback_data="filter_category")],
            [InlineKeyboardButton(tr(context, "filter_price"), callback_data="filter_price")],
            [InlineKeyboardButton(tr(context, "filter_rating"), callback_data="filter_rating")],
            [InlineKeyboardButton(tr(context, "filter_stock"), callback_data="filter_in_stock")],
            [InlineKeyboardButton(tr(context, "filter_sale"), callback_data="filter_on_sale")],
            [InlineKeyboardButton(tr(context, "filter_clear"), callback_data="filter_clear")],
            [InlineKeyboardButton(tr(context, "back_results"), callback_data="search_back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            tr(context, "filter_title"), parse_mode="Markdown", reply_markup=reply_markup
        )

    elif query.data == "search_sort":
        # Show sort options
        keyboard = [
            [InlineKeyboardButton(tr(context, "sort_relevance"), callback_data="sort_relevance")],
            [InlineKeyboardButton(tr(context, "sort_price_desc"), callback_data="sort_price_desc")],
            [InlineKeyboardButton(tr(context, "sort_price_asc"), callback_data="sort_price_asc")],
            [InlineKeyboardButton(tr(context, "sort_rating"), callback_data="sort_rating")],
            [InlineKeyboardButton(tr(context, "sort_newest"), callback_data="sort_newest")],
            [InlineKeyboardButton(tr(context, "back_results"), callback_data="search_back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            tr(context, "sort_title"), parse_mode="Markdown", reply_markup=reply_markup
        )

    elif query.data == "filter_category":
        language = get_language(context)
        keyboard = [
            [
                InlineKeyboardButton(
                    CATEGORY_NAMES_AMHARIC.get(category, category.value)
                    if language == "am"
                    else category.value.replace("_", " ").title(),
                    callback_data=f"filter_category_{category.value}",
                )
            ]
            for category in ProductCategory
        ]
        keyboard.append(
            [InlineKeyboardButton(tr(context, "back_results"), callback_data="search_filter")]
        )
        await query.message.edit_text(
            tr(context, "filter_category"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "filter_price":
        keyboard = [
            [InlineKeyboardButton("< 500 ETB", callback_data="filter_price_under_500")],
            [InlineKeyboardButton("500-1,999.99 ETB", callback_data="filter_price_500_2000")],
            [InlineKeyboardButton("≥ 2,000 ETB", callback_data="filter_price_over_2000")],
            [InlineKeyboardButton(tr(context, "back_results"), callback_data="search_filter")],
        ]
        await query.message.edit_text(
            tr(context, "filter_price"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "filter_rating":
        keyboard = [
            [InlineKeyboardButton("⭐ 3+", callback_data="filter_rating_3")],
            [InlineKeyboardButton("⭐ 4+", callback_data="filter_rating_4")],
            [InlineKeyboardButton("⭐ 4.5+", callback_data="filter_rating_4_5")],
            [InlineKeyboardButton(tr(context, "back_results"), callback_data="search_filter")],
        ]
        await query.message.edit_text(
            tr(context, "filter_rating"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data.startswith("filter_category_"):
        context.user_data.setdefault("search_filters", {})["category"] = query.data.removeprefix(
            "filter_category_"
        )
        context.user_data["search_page"] = 1
        await perform_search(update, context)

    elif query.data.startswith("filter_price_"):
        filters = context.user_data.setdefault("search_filters", {})
        price_range = query.data.removeprefix("filter_price_")
        if price_range == "under_500":
            filters["min_price"], filters["max_price"] = None, 499.99
        elif price_range == "500_2000":
            filters["min_price"], filters["max_price"] = 500, 1999.99
        elif price_range == "over_2000":
            filters["min_price"], filters["max_price"] = 2000, None
        context.user_data["search_page"] = 1
        await perform_search(update, context)

    elif query.data.startswith("filter_rating_"):
        rating = query.data.removeprefix("filter_rating_").replace("_", ".")
        context.user_data.setdefault("search_filters", {})["min_rating"] = float(rating)
        context.user_data["search_page"] = 1
        await perform_search(update, context)

    elif query.data in {"filter_in_stock", "filter_on_sale"}:
        filters = context.user_data.setdefault("search_filters", {})
        key = "in_stock_only" if query.data == "filter_in_stock" else "on_sale_only"
        filters[key] = not filters.get(key, False)
        context.user_data["search_page"] = 1
        await perform_search(update, context)

    elif query.data == "filter_clear":
        context.user_data["search_filters"] = {}
        context.user_data["search_page"] = 1
        await perform_search(update, context)

    elif query.data in {
        "sort_relevance",
        "sort_price_desc",
        "sort_price_asc",
        "sort_rating",
        "sort_newest",
    }:
        sort_options = {
            "sort_relevance": ("relevance", True),
            "sort_price_desc": ("price", True),
            "sort_price_asc": ("price", False),
            "sort_rating": ("rating", True),
            "sort_newest": ("newest", True),
        }
        context.user_data.setdefault("search_filters", {})["sort_by"], context.user_data[
            "search_filters"
        ]["sort_desc"] = sort_options[query.data]
        context.user_data["search_page"] = 1
        await perform_search(update, context)

    elif query.data == "search_back":
        # Go back to search results
        await perform_search(update, context)

    elif query.data == "search_page_prev":
        # Previous page
        context.user_data["search_page"] = max(
            1, context.user_data.get("search_page", 1) - 1
        )
        await perform_search(update, context)

    elif query.data == "search_page_next":
        # Next page
        context.user_data["search_page"] = context.user_data.get("search_page", 1) + 1
        await perform_search(update, context)

    elif query.data == "search_new":
        await query.message.edit_text(
            tr(context, "search_prompt"), parse_mode="Markdown"
        )
        return WAITING_QUERY

    return FILTER_RESULTS


async def product_from_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle prod_search_<id> — view a product from within a search result."""
    query = update.callback_query
    await query.answer()
    # Delegate to catalog product_callback (import here to avoid circular)
    from bot.handlers.catalog import product_callback

    # Rewrite callback data so catalog can parse it normally: prod_<id>
    product_id = query.data.split("_")[2]
    query.data = f"prod_{product_id}"
    await product_callback(update, context)
    return FILTER_RESULTS


async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel the search conversation.

    Args:
        update: Telegram update
        context: Callback context

    Returns:
        Next conversation state (END)
    """
    await update.effective_message.reply_text(tr(context, "search_cancelled"))
    return ConversationHandler.END


__all__ = [
    "FILTER_RESULTS",
    "WAITING_QUERY",
    "cancel_search",
    "filter_callback",
    "product_from_search",
    "search_command",
    "search_query_handler",
    "start_search",
]
