"""Wishlist handler — stores wishlist in context.user_data (no Redis needed)."""

from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from core.utils.currency import format_etb
from apps.products.services import ProductService
from infrastructure.database.session import get_db_session

WISHLIST_KEY = "wishlist"


def _get_wishlist(context: ContextTypes.DEFAULT_TYPE) -> list:
    return context.user_data.get(WISHLIST_KEY, [])


def _save_wishlist(context: ContextTypes.DEFAULT_TYPE, wishlist: list) -> None:
    context.user_data[WISHLIST_KEY] = wishlist


async def wishlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's wishlist."""
    wishlist = _get_wishlist(context)

    if not wishlist:
        msg = "⭐ *ተመራጭ ምርቶችዎ ባዶ ነው!*\n\nምርቶችን ለመጨመር /menu ይጫኑ።"
        if update.callback_query:
            await update.callback_query.message.edit_text(msg, parse_mode="Markdown")
            await update.callback_query.answer()
        else:
            await update.effective_message.reply_text(msg, parse_mode="Markdown")
        return

    wishlist_text, reply_markup = await _build_wishlist_view(wishlist)

    if update.callback_query:
        await update.callback_query.message.edit_text(
            wishlist_text, parse_mode="Markdown", reply_markup=reply_markup
        )
        await update.callback_query.answer()
    else:
        await update.effective_message.reply_text(
            wishlist_text, parse_mode="Markdown", reply_markup=reply_markup
        )


async def wishlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle wish_* and wishlist_* callback queries."""
    query = update.callback_query
    await query.answer()

    action = query.data
    wishlist = _get_wishlist(context)

    if action.startswith("add_to_wishlist_"):
        product_id = int(action.split("_")[3])
        if not any(i["product_id"] == product_id for i in wishlist):
            wishlist.append({"product_id": product_id, "added_at": datetime.utcnow().isoformat()})
            _save_wishlist(context, wishlist)
        try:
            await query.answer("⭐ ወደ ተመራጮች ተጨምሯል!", show_alert=True)
        except Exception:
            pass
        return

    elif action.startswith("wishlist_remove_"):
        product_id = int(action.split("_")[2])
        wishlist = [i for i in wishlist if i["product_id"] != product_id]
        _save_wishlist(context, wishlist)

    elif action == "wishlist_add_all":
        from bot.handlers.cart import add_to_cart
        user_id = update.effective_user.id
        for item in wishlist:
            await add_to_cart(user_id, item["product_id"], context)
        await query.message.reply_text(f"✅ {len(wishlist)} ምርቶች ወደ ቅርጫት ተጨምረዋል!")
        return

    elif action == "wishlist_clear":
        _save_wishlist(context, [])
        try:
            await query.message.edit_text(
                "⭐ *ተመራጭ ምርቶችዎ ባዶ ነው!*", parse_mode="Markdown"
            )
        except Exception:
            pass
        return

    # Refresh display
    wishlist = _get_wishlist(context)
    if not wishlist:
        try:
            await query.message.edit_text(
                "⭐ *ተመራጭ ምርቶችዎ ባዶ ነው!*", parse_mode="Markdown"
            )
        except Exception:
            pass
        return

    wishlist_text, reply_markup = await _build_wishlist_view(wishlist)
    try:
        await query.message.edit_text(
            wishlist_text, parse_mode="Markdown", reply_markup=reply_markup
        )
    except Exception:
        pass


async def _build_wishlist_view(wishlist: list):
    """Build wishlist display text and keyboard."""
    wishlist_text = "⭐ *ተመራጭ ምርቶች*\n\n"

    async for db in get_db_session():
        product_service = ProductService(db)
        for item in wishlist[:10]:
            try:
                product = await product_service.get_product(item["product_id"])
                if product:
                    price_text = format_etb(product.price)
                    if getattr(product, "compare_price", None) and product.compare_price > product.price:
                        price_text = f"~~{format_etb(product.compare_price)}~~ {format_etb(product.price)}"
                    wishlist_text += f"• *{product.name}*\n  💰 {price_text}\n\n"
            except Exception:
                pass
        break

    keyboard = [
        [
            InlineKeyboardButton("🛒 ሁሉንም ወደ ቅርጫት ጨምር", callback_data="wishlist_add_all"),
            InlineKeyboardButton("🗑️ ሁሉንም አጥፋ", callback_data="wishlist_clear"),
        ],
        [InlineKeyboardButton("🔙 ወደ ምናሌ", callback_data="menu_back")],
    ]
    return wishlist_text, InlineKeyboardMarkup(keyboard)


async def add_to_wishlist(user_id: int, product_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    """Add a product to the wishlist."""
    if context is None:
        return
    wishlist = _get_wishlist(context)
    if not any(i["product_id"] == product_id for i in wishlist):
        wishlist.append({"product_id": product_id, "added_at": datetime.utcnow().isoformat()})
        _save_wishlist(context, wishlist)
    logger.info(f"Added product {product_id} to wishlist for user {user_id}")


async def remove_from_wishlist(user_id: int, product_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    """Remove a product from the wishlist."""
    if context is None:
        return
    wishlist = _get_wishlist(context)
    wishlist = [i for i in wishlist if i["product_id"] != product_id]
    _save_wishlist(context, wishlist)


async def clear_wishlist(user_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    """Clear the wishlist."""
    if context is None:
        return
    _save_wishlist(context, [])


async def get_user_wishlist(user_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> list:
    """Get user wishlist from context."""
    if context is not None:
        return _get_wishlist(context)
    return []


async def refresh_wishlist_display(query, user_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    """Refresh the wishlist display."""
    wishlist = _get_wishlist(context) if context else []
    if not wishlist:
        await query.message.edit_text(
            "⭐ *ተመራጭ ምርቶችዎ ባዶ ነው!*", parse_mode="Markdown"
        )
        return
    wishlist_text, reply_markup = await _build_wishlist_view(wishlist)
    await query.message.edit_text(
        wishlist_text, parse_mode="Markdown", reply_markup=reply_markup
    )


__all__ = [
    "wishlist_command", "wishlist_callback",
    "add_to_wishlist", "get_user_wishlist", "clear_wishlist",
]
