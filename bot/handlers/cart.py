"""Shopping cart handler — stores cart in context.user_data (no Redis needed)."""

from decimal import Decimal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from apps.products.services import ProductService
from bot.handlers.callback_utils import answer_callback_query, edit_callback_message
from bot.localization import get_language, tr, translate
from core.logger import logger
from core.utils.currency import format_etb
from infrastructure.database.session import get_db_session

CART_KEY = "cart"


def _get_cart(context: ContextTypes.DEFAULT_TYPE) -> list:
    return context.user_data.get(CART_KEY, [])


def _save_cart(context: ContextTypes.DEFAULT_TYPE, cart: list) -> None:
    context.user_data[CART_KEY] = cart


async def cart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's shopping cart."""
    cart = _get_cart(context)
    if not cart:
        await update.effective_message.reply_text(
            tr(context, "cart_empty"),
            parse_mode="Markdown",
        )
        return
    cart_text, reply_markup = await _build_cart_view(cart, context)
    await update.effective_message.reply_text(
        cart_text, parse_mode="Markdown", reply_markup=reply_markup
    )


async def cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cart_* callback queries."""
    query = update.callback_query
    action = query.data
    cart = _get_cart(context)

    if action.startswith("add_to_cart_"):
        if not await answer_callback_query(query, tr(context, "cart_added")):
            return
        product_id = int(action.split("_")[3])
        found = False
        for item in cart:
            if item["product_id"] == product_id:
                item["quantity"] += 1
                found = True
                break
        if not found:
            cart.append({"product_id": product_id, "quantity": 1})
        _save_cart(context, cart)
        return

    if not await answer_callback_query(query):
        return

    if action.startswith("cart_remove_"):
        product_id = int(action.split("_")[2])
        cart = [i for i in cart if i["product_id"] != product_id]
        _save_cart(context, cart)

    elif action.startswith("cart_qty_"):
        parts = action.split("_")
        product_id = int(parts[2])
        delta = int(parts[3])
        for item in cart:
            if item["product_id"] == product_id:
                new_qty = item["quantity"] + delta
                if new_qty <= 0:
                    cart.remove(item)
                else:
                    item["quantity"] = new_qty
                break
        _save_cart(context, cart)

    elif action == "cart_clear":
        _save_cart(context, [])
        await edit_callback_message(query, tr(context, "cart_empty"), parse_mode="Markdown")
        return

    elif action == "cart_refresh":
        pass  # fall through to refresh

    # Refresh display
    cart = _get_cart(context)
    if not cart:
        await edit_callback_message(query, tr(context, "cart_empty"), parse_mode="Markdown")
        return
    cart_text, reply_markup = await _build_cart_view(cart, context)
    await edit_callback_message(
        query, cart_text, parse_mode="Markdown", reply_markup=reply_markup
    )


async def _build_cart_view(cart: list, context: ContextTypes.DEFAULT_TYPE = None):
    """Build cart display text and keyboard."""
    total = Decimal("0")
    items_text = []

    async for db in get_db_session():
        product_service = ProductService(db)
        for item in cart:
            try:
                product = await product_service.get_product(item["product_id"])
                if product:
                    item_total = product.price * item["quantity"]
                    total += item_total
                    language = get_language(context) if context else "am"
                    name = (
                        product.name_am if language == "am" else product.name
                    ) or product.name
                    items_text.append(
                        translate(
                            language,
                            "cart_item",
                            name=name,
                            quantity=item["quantity"],
                            price=format_etb(product.price),
                            total=format_etb(item_total),
                        )
                    )
            except Exception:
                pass
        break

    language = get_language(context) if context else "am"
    cart_text = translate(language, "cart_title") + "\n\n"
    cart_text += "\n".join(items_text) if items_text else translate(language, "cart_no_items")
    cart_text += f"\n─────────────────\n{translate(language, 'cart_total')}: {format_etb(total)}"

    keyboard = [
        [
            InlineKeyboardButton(translate(language, "cart_clear"), callback_data="cart_clear"),
            InlineKeyboardButton(translate(language, "refresh"), callback_data="cart_refresh"),
        ],
        [
            InlineKeyboardButton(translate(language, "continue_shopping"), callback_data="menu_products"),
            InlineKeyboardButton(translate(language, "checkout"), callback_data="cart_checkout"),
        ],
    ]
    return cart_text, InlineKeyboardMarkup(keyboard)


async def add_to_cart(user_id: int, product_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a product to the cart."""
    cart = _get_cart(context)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += 1
            _save_cart(context, cart)
            return
    cart.append({"product_id": product_id, "quantity": 1})
    _save_cart(context, cart)
    logger.info(f"Added product {product_id} to cart for user {user_id}")


async def get_user_cart(user_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> list:
    """Get user cart from context.user_data."""
    if context is not None:
        return _get_cart(context)
    return []


async def clear_cart(user_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    """Clear the user's cart."""
    if context is not None:
        _save_cart(context, [])


async def refresh_cart_display(query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refresh the cart display message."""
    cart = _get_cart(context)
    if not cart:
        await query.message.edit_text(tr(context, "cart_empty"), parse_mode="Markdown")
        return
    cart_text, reply_markup = await _build_cart_view(cart, context)
    await query.message.edit_text(cart_text, parse_mode="Markdown", reply_markup=reply_markup)


__all__ = ["add_to_cart", "cart_callback", "cart_command", "clear_cart", "get_user_cart"]
