# ============================
# WOLLOYEWA STORE BOT - CATALOG HANDLER
# ============================
"""Telegram bot catalog browsing and product display handlers."""

import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from apps.products.services import CategoryService, ProductService
from bot.handlers.callback_utils import answer_callback_query
from bot.handlers.text_routing import consume_handled_text
from bot.localization import get_language, tr
from core.config import settings
from core.logger import logger
from core.utils.currency import format_etb
from infrastructure.database.session import get_db_session

# Pagination settings
PRODUCTS_PER_PAGE = 5
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ETHIOPIAN_PHONE_PATTERN = re.compile(r"^(?:\+?251|0)?[79]\d{8}$")


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /menu command. Shows the main menu with categories."""
    query = update.callback_query if update.callback_query else None

    if update.effective_user and update.effective_user.id in settings.admin_ids_list:
        from bot.handlers.admin.dashboard import ADMIN_MENU_TEXT, _admin_main_keyboard

        if query:
            await query.message.edit_text(
                ADMIN_MENU_TEXT,
                parse_mode="Markdown",
                reply_markup=_admin_main_keyboard(),
            )
        else:
            await update.effective_message.reply_text(
                ADMIN_MENU_TEXT,
                parse_mode="Markdown",
                reply_markup=_admin_main_keyboard(),
            )
        return

    async for db in get_db_session():
        category_service = CategoryService(db)
        categories = await category_service.get_all_categories(active_only=True)
        break

    keyboard = []
    row = []
    language = get_language(context)
    for _i, category in enumerate(categories):
        button_text = category.name_am if language == "am" else category.name
        button_text = button_text or category.name
        row.append(InlineKeyboardButton(button_text, callback_data=f"cat_{category.id}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append(
        [
            InlineKeyboardButton(tr(context, "search"), callback_data="menu_search"),
            InlineKeyboardButton(tr(context, "cart"), callback_data="menu_cart"),
        ]
    )
    keyboard.append(
        [
            InlineKeyboardButton(tr(context, "wishlist"), callback_data="menu_wishlist"),
            InlineKeyboardButton(tr(context, "profile"), callback_data="menu_profile"),
        ]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = tr(context, "categories_title")

    if query:
        if query.message.text is not None:
            await query.message.edit_text(
                message_text, parse_mode="Markdown", reply_markup=reply_markup
            )
        else:
            await query.message.reply_text(
                message_text, parse_mode="Markdown", reply_markup=reply_markup
            )
    else:
        await update.effective_message.reply_text(
            message_text, parse_mode="Markdown", reply_markup=reply_markup
        )


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle category selection: cat_<id>"""
    query = update.callback_query
    if not await answer_callback_query(query):
        return
    category_id = int(query.data.split("_")[1])
    context.user_data["current_category"] = category_id
    context.user_data["current_page"] = 1
    await show_category_products(update, context, category_id, page=1)


async def category_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle category pagination: cat_page_<category_id>_<page>"""
    query = update.callback_query
    if not await answer_callback_query(query):
        return
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
    """Show products in a category with pagination."""
    query = update.callback_query

    async for db in get_db_session():
        product_service = ProductService(db)
        category_service = CategoryService(db)
        category = await category_service.get_category(category_id)
        language = get_language(context)
        category_name = category.name_am if language == "am" else category.name
        category_name = category_name or category.name
        offset = (page - 1) * PRODUCTS_PER_PAGE
        products = await product_service.product_repo.get_by_category(
            category_id=category_id,
            limit=PRODUCTS_PER_PAGE,
            offset=offset,
        )
        total = await product_service.product_repo.count(
            {"category_id": category_id, "status": "active"}
        )
        total_pages = max(1, (total + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE)
        break

    if not products:
        text = f"📁 *{category_name}*\n\n{tr(context, 'products_empty')}"
        keyboard = [[InlineKeyboardButton(tr(context, "back_categories"), callback_data="menu_back")]]
        await query.message.edit_text(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Build product list text
    product_list = []
    for product in products:
        price_text = format_etb(product.price)
        stock_icon = "✅" if product.is_in_stock else "❌"
        language = get_language(context)
        product_name = product.name_am if language == "am" else product.name
        product_list.append(f"{stock_icon} *{product_name or product.name}*\n   💰 {price_text}")

    text = f"📦 *{category_name}* — {tr(context, 'page')} {page}/{total_pages}\n\n"
    text += "\n\n".join(product_list)

    # Product buttons (one per row, with photo indicator)
    keyboard = []
    for product in products:
        has_img = bool(product.images)
        icon = "🖼️" if has_img else "📦"
        language = get_language(context)
        product_name = product.name_am if language == "am" else product.name
        btn_name = (product_name or product.name)[:35]
        keyboard.append(
            [InlineKeyboardButton(f"{icon} {btn_name}", callback_data=f"prod_{product.id}")]
        )

    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(f"◀️ {tr(context, 'previous')}", callback_data=f"cat_page_{category_id}_{page-1}")
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(f"{tr(context, 'next')} ▶️", callback_data=f"cat_page_{category_id}_{page+1}")
        )
    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton(tr(context, "back_categories"), callback_data="menu_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    except BadRequest:
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle product selection: prod_<id>
    Shows product photo (if available) + full details + action buttons.
    """
    query = update.callback_query
    if not await answer_callback_query(query):
        return

    product_id = int(query.data.split("_")[1])

    async for db in get_db_session():
        product_service = ProductService(db)
        try:
            product = await product_service.get_product(product_id)
        except Exception:
            await query.message.reply_text(tr(context, "product_not_found"))
            return
        break

    # ── Format detail text (keep under 1024 chars for photo captions) ─────
    price_text = format_etb(product.price)
    if product.is_on_sale and product.compare_price:
        price_text = f"~~{format_etb(product.compare_price)}~~ {format_etb(product.price)}"

    stock_icon = (
        tr(context, "stock_available")
        if product.is_in_stock
        else tr(context, "stock_unavailable")
    )

    stars = ""
    if product.rating and product.rating > 0:
        full = int(product.rating)
        stars = (
            "⭐" * full
            + ("½" if product.rating - full >= 0.5 else "")
            + f" ({product.reviews_count})"
        )
    else:
        stars = tr(context, "no_reviews")

    vendor_name = product.vendor.business_name if product.vendor else tr(context, "store_name")

    language = get_language(context)
    title = (product.name_am if language == "am" else product.name) or product.name
    desc = (
        product.description_am if language == "am" else product.description
    ) or product.description or ""
    desc = desc[:300]
    caption = (
        f"🛍️ *{title}*\n\n"
        f"{desc}\n\n"
        f"💰 *{tr(context, 'price')}:* {price_text}\n"
        f"📦 *{tr(context, 'status')}:* {stock_icon}\n"
        f"{stars}\n"
        f"🏪 *{tr(context, 'seller')}:* {vendor_name}"
    )

    # ── Keyboard ────────────────────────────────────────────────────────────
    from core.config import settings

    is_admin = update.effective_user.id in settings.admin_ids_list

    keyboard = [
        [
            InlineKeyboardButton(tr(context, "add_to_cart"), callback_data=f"add_to_cart_{product.id}"),
        ],
        [
            InlineKeyboardButton(tr(context, "add_to_wishlist"), callback_data=f"add_to_wishlist_{product.id}"),
            InlineKeyboardButton(tr(context, "write_review"), callback_data=f"review_{product.id}"),
        ],
    ]

    if is_admin:
        keyboard.append(
            [
                InlineKeyboardButton(tr(context, "admin_add_photo"), callback_data=f"admin_prompt_image_{product.id}"),
                InlineKeyboardButton(tr(context, "admin_view_photos"), callback_data=f"admin_add_image_{product.id}"),
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(tr(context, "back"), callback_data="menu_back"),
            InlineKeyboardButton(tr(context, "home"), callback_data="menu_main"),
        ]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ── Decide: photo or text ───────────────────────────────────────────────
    image_url = None
    if product.images and len(product.images) > 0:
        image_url = str(product.images[0]).strip()

    if image_url:
        await _send_product_photo(query, context, image_url, caption, reply_markup)
    else:
        try:
            await query.message.edit_text(caption, parse_mode="Markdown", reply_markup=reply_markup)
        except BadRequest:
            await query.message.reply_text(
                caption, parse_mode="Markdown", reply_markup=reply_markup
            )


async def _send_product_photo(query, context, image_url: str, caption: str, reply_markup) -> None:
    """
    Try to show a product photo.
    1. If current message IS a photo → edit_message_media (seamless swap)
    2. Otherwise → delete text message, send new photo message
    Falls back to text if Telegram rejects the URL.
    """
    chat_id = query.message.chat.id

    # Case 1: current message already has a photo — edit media in place
    if query.message.photo or query.message.document:
        try:
            from bot.product_media import telegram_photo_source

            with telegram_photo_source(image_url) as photo:
                await query.message.edit_media(
                    media=InputMediaPhoto(
                        media=photo, caption=caption, parse_mode="Markdown"
                    ),
                    reply_markup=reply_markup,
                )
            return
        except (BadRequest, OSError, ValueError) as e:
            logger.warning(f"edit_media failed ({e}), falling back to send_photo")

    # Case 2: current message is text → delete it and send fresh photo
    try:
        await query.message.delete()
    except BadRequest:
        pass  # Cannot delete — ignore

    try:
        from bot.product_media import telegram_photo_source

        with telegram_photo_source(image_url) as photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
    except (BadRequest, OSError, ValueError) as e:
        logger.warning(f"send_photo failed ({e}), sending text instead")
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages — search for matching products."""
    if consume_handled_text(update, context):
        return

    if context.user_data.get("checkout_in_progress"):
        if not context.user_data.get("checkout_conversation_active"):
            context.user_data.pop("checkout_in_progress", None)
            await update.effective_message.reply_text(
                tr(context, "checkout_session_expired")
            )
        return

    if context.user_data.get("updating_field") or context.user_data.get(
        "vendor_application"
    ):
        from bot.handlers.profile import profile_text_handler

        await profile_text_handler(update, context)
        return

    text = update.effective_message.text.strip()
    normalized_phone = re.sub(r"[\s().-]", "", text)
    if _EMAIL_PATTERN.fullmatch(text) or _ETHIOPIAN_PHONE_PATTERN.fullmatch(
        normalized_phone
    ):
        await update.effective_message.reply_text(tr(context, "contact_input_hint"))
        return

    if len(text) < 2:
        await update.effective_message.reply_text(tr(context, "search_min_length"))
        return

    async for db in get_db_session():
        product_service = ProductService(db)
        products = await product_service.search_products(text, limit=8)
        break

    if not products:
        await update.effective_message.reply_text(
            tr(context, "no_search_results", query=escape_markdown(text, version=1)),
            parse_mode="Markdown",
        )
        return

    result_text = tr(
        context,
        "search_results",
        query=escape_markdown(text, version=1),
        page=1,
        total_pages=1,
    ) + "\n\n"
    keyboard = []
    for product in products[:5]:
        has_img = bool(product.images)
        icon = "🖼️" if has_img else "📦"
        language = get_language(context)
        product_name = product.name_am if language == "am" else product.name
        name = (product_name or product.name)[:35]
        result_text += (
            f"• {icon} *{escape_markdown(str(name), version=1)}* — "
            f"{format_etb(product.price)}\n"
        )
        keyboard.append(
            [InlineKeyboardButton(f"{icon} {name}", callback_data=f"prod_{product.id}")]
        )

    keyboard.append([InlineKeyboardButton(tr(context, "home"), callback_data="menu_main")])

    await update.effective_message.reply_text(
        result_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


__all__ = [
    "category_callback",
    "category_page_callback",
    "menu_command",
    "product_callback",
    "show_category_products",
    "text_message_handler",
]
