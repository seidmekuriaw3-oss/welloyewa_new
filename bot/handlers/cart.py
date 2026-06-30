"""Shopping cart handler — stores cart in context.user_data (no Redis needed)."""

from decimal import Decimal

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from core.utils.currency import format_etb
from apps.products.services import ProductService
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
            "🛒 *የግዢ ቅርጫትዎ ባዶ ነው!*\n\nምርቶችን ለመግዛት /menu ይጫኑ።",
            parse_mode="Markdown",
        )
        return
    cart_text, reply_markup = await _build_cart_view(cart)
    await update.effective_message.reply_text(
        cart_text, parse_mode="Markdown", reply_markup=reply_markup
    )


async def cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cart_* callback queries."""
    query = update.callback_query
    await query.answer()

    action = query.data
    cart = _get_cart(context)

    if action.startswith("add_to_cart_"):
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
        try:
            await query.answer("✅ ወደ ቅርጫት ተጨምሯል!", show_alert=True)
        except Exception:
            pass
        return

    elif action.startswith("cart_remove_"):
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
        try:
            await query.message.edit_text(
                "🛒 *የግዢ ቅርጫትዎ ባዶ ነው!*", parse_mode="Markdown"
            )
        except Exception:
            pass
        return

    elif action == "cart_checkout":
        from bot.handlers.checkout import start_checkout
        await start_checkout(update, context)
        return

    elif action == "cart_refresh":
        pass  # fall through to refresh

    # Refresh display
    cart = _get_cart(context)
    if not cart:
        try:
            await query.message.edit_text(
                "🛒 *የግዢ ቅርጫትዎ ባዶ ነው!*", parse_mode="Markdown"
            )
        except Exception:
            pass
        return
    cart_text, reply_markup = await _build_cart_view(cart)
    try:
        await query.message.edit_text(
            cart_text, parse_mode="Markdown", reply_markup=reply_markup
        )
    except Exception:
        pass


async def _build_cart_view(cart: list):
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
                    items_text.append(
                        f"• *{product.name}*\n"
                        f"  {item['quantity']} x {format_etb(product.price)} = {format_etb(item_total)}\n"
                    )
            except Exception:
                pass
        break

    cart_text = "🛒 *የግዢ ቅርጫትዎ*\n\n"
    cart_text += "\n".join(items_text) if items_text else "_ምርቶች ሲጫኑ ይታያሉ_"
    cart_text += f"\n─────────────────\n💰 *ጠቅላላ*: {format_etb(total)}"

    keyboard = [
        [
            InlineKeyboardButton("🗑️ ቅርጫትን አጥፋ", callback_data="cart_clear"),
            InlineKeyboardButton("🔄 አድስ", callback_data="cart_refresh"),
        ],
        [
            InlineKeyboardButton("➕ ቀጥል", callback_data="menu_products"),
            InlineKeyboardButton("✅ ግዢ አጠናቅቅ", callback_data="cart_checkout"),
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


async def refresh_cart_display(
    query, user_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Refresh the cart display message."""
    cart = _get_cart(context)
    if not cart:
        await query.message.edit_text(
            "🛒 *የግዢ ቅርጫትዎ ባዶ ነው!*", parse_mode="Markdown"
        )
        return
    cart_text, reply_markup = await _build_cart_view(cart)
    await query.message.edit_text(
        cart_text, parse_mode="Markdown", reply_markup=reply_markup
    )


__all__ = ["cart_command", "cart_callback", "add_to_cart", "get_user_cart", "clear_cart"]
