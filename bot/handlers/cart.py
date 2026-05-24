# ============================
# WOLLOYEWA STORE BOT - CART HANDLER
# ============================
"""Telegram bot shopping cart management handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from decimal import Decimal

from core.logger import logger
from core.utils.currency import format_etb
from apps.products.services import ProductService
from infrastructure.database.session import get_db_session
from infrastructure.redis.client import get_redis_client


async def cart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /cart command.
    
    Shows the user's shopping cart.
    """
    user_id = update.effective_user.id
    
    # Get cart from Redis
    cart = await get_user_cart(user_id)
    
    if not cart or len(cart) == 0:
        await update.message.reply_text(
            "🛒 *የግዢ ቅርጫትዎ ባዶ ነው!*\n\n"
            "ምርቶችን ለመግዛት /menu ይጫኑ።",
            parse_mode="Markdown"
        )
        return
    
    # Build cart message
    total = Decimal('0')
    items_text = []
    
    async for db in get_db_session():
        product_service = ProductService(db)
        
        for item in cart:
            product = await product_service.get_product(item["product_id"])
            if product:
                item_total = product.price * item["quantity"]
                total += item_total
                items_text.append(
                    f"• *{product.name}*\n"
                    f"  {item['quantity']} x {format_etb(product.price)} = {format_etb(item_total)}\n"
                )
        break
    
    cart_text = "🛒 *የግዢ ቅርጫትዎ*\n\n"
    cart_text += "\n".join(items_text)
    cart_text += f"\n─────────────────\n"
    cart_text += f"💰 *ጠቅላላ*: {format_etb(total)}"
    
    # Build keyboard
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
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(cart_text, parse_mode="Markdown", reply_markup=reply_markup)


async def cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle cart-related callback queries.
    
    Supports: add, remove, update quantity, clear, refresh.
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data
    
    if action.startswith("add_to_cart_"):
        # Add product to cart
        product_id = int(action.split("_")[3])
        await add_to_cart(user_id, product_id, context)
        await query.message.reply_text(f"✅ ምርቱ ወደ ቅርጫት ተጨምሯል!")
        
    elif action.startswith("cart_remove_"):
        # Remove product from cart
        product_id = int(action.split("_")[2])
        await remove_from_cart(user_id, product_id)
        await query.message.reply_text(f"🗑️ ምርቱ ከቅርጫት ተወግዷል!")
        await refresh_cart_display(query, user_id, context)
        
    elif action.startswith("cart_qty_"):
        # Update quantity
        parts = action.split("_")
        product_id = int(parts[2])
        delta = int(parts[3])
        await update_cart_quantity(user_id, product_id, delta)
        await refresh_cart_display(query, user_id, context)
        
    elif action == "cart_clear":
        # Clear cart
        await clear_cart(user_id)
        await query.message.edit_text(
            "🛒 *የግዢ ቅርጫትዎ ባዶ ነው!*",
            parse_mode="Markdown"
        )
        
    elif action == "cart_refresh":
        # Refresh cart display
        await refresh_cart_display(query, user_id, context)
        
    elif action == "cart_checkout":
        # Proceed to checkout
        from bot.handlers.checkout import start_checkout
        context.user_data["checkout_cart"] = await get_user_cart(user_id)
        await start_checkout(update, context)


async def add_to_cart(user_id: int, product_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a product to the user's cart."""
    redis = await get_redis_client()
    cart_key = f"cart:{user_id}"
    
    # Get current cart
    cart = await get_user_cart(user_id)
    
    # Find and update or add new item
    found = False
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += 1
            found = True
            break
    
    if not found:
        cart.append({"product_id": product_id, "quantity": 1})
    
    # Save to Redis (expires in 7 days)
    import json
    await redis.setex(cart_key, 604800, json.dumps(cart))
    
    logger.info(f"Added product {product_id} to cart for user {user_id}")


async def remove_from_cart(user_id: int, product_id: int) -> None:
    """Remove a product from the user's cart."""
    cart = await get_user_cart(user_id)
    cart = [item for item in cart if item["product_id"] != product_id]
    await save_user_cart(user_id, cart)


async def update_cart_quantity(user_id: int, product_id: int, delta: int) -> None:
    """Update product quantity in cart."""
    cart = await get_user_cart(user_id)
    
    for item in cart:
        if item["product_id"] == product_id:
            new_qty = item["quantity"] + delta
            if new_qty <= 0:
                cart.remove(item)
            else:
                item["quantity"] = new_qty
            break
    
    await save_user_cart(user_id, cart)


async def clear_cart(user_id: int) -> None:
    """Clear the user's cart."""
    await save_user_cart(user_id, [])


async def get_user_cart(user_id: int) -> list:
    """Get the user's cart from Redis."""
    redis = await get_redis_client()
    cart_key = f"cart:{user_id}"
    
    cart_json = await redis.get(cart_key)
    if cart_json:
        import json
        return json.loads(cart_json)
    return []


async def save_user_cart(user_id: int, cart: list) -> None:
    """Save the user's cart to Redis."""
    redis = await get_redis_client()
    cart_key = f"cart:{user_id}"
    
    import json
    await redis.setex(cart_key, 604800, json.dumps(cart))


async def refresh_cart_display(
    query,
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Refresh the cart display message."""
    cart = await get_user_cart(user_id)
    
    if not cart:
        await query.message.edit_text(
            "🛒 *የግዢ ቅርጫትዎ ባዶ ነው!*",
            parse_mode="Markdown"
        )
        return
    
    total = Decimal('0')
    items_text = []
    
    async for db in get_db_session():
        product_service = ProductService(db)
        
        for item in cart:
            product = await product_service.get_product(item["product_id"])
            if product:
                item_total = product.price * item["quantity"]
                total += item_total
                items_text.append(
                    f"• *{product.name}*\n"
                    f"  {item['quantity']} x {format_etb(product.price)} = {format_etb(item_total)}\n"
                )
        break
    
    cart_text = "🛒 *የግዢ ቅርጫትዎ*\n\n"
    cart_text += "\n".join(items_text)
    cart_text += f"\n─────────────────\n"
    cart_text += f"💰 *ጠቅላላ*: {format_etb(total)}"
    
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
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(cart_text, parse_mode="Markdown", reply_markup=reply_markup)


__all__ = [
    "cart_command",
    "cart_callback",
    "add_to_cart",
    "get_user_cart",
    "clear_cart",
]