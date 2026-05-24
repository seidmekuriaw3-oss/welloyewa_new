# ============================
# WOLLOYEWA STORE BOT - WISHLIST HANDLER
# ============================
"""Telegram bot wishlist management handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.logger import logger
from core.utils.currency import format_etb
from apps.products.services import ProductService
from infrastructure.database.session import get_db_session
from infrastructure.redis.client import get_redis_client


async def wishlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /wishlist command.
    
    Shows the user's wishlist.
    """
    user_id = update.effective_user.id
    
    # Get wishlist from Redis
    wishlist = await get_user_wishlist(user_id)
    
    if not wishlist:
        await update.message.reply_text(
            "⭐ *ተመራጭ ምርቶችዎ ባዶ ነው!*\n\n"
            "ምርቶችን ለመጨመር /menu ይጫኑ።",
            parse_mode="Markdown"
        )
        return
    
    # Build wishlist message
    wishlist_text = "⭐ *ተመራጭ ምርቶች*\n\n"
    products_info = []
    
    async for db in get_db_session():
        product_service = ProductService(db)
        
        for item in wishlist:
            product = await product_service.get_product(item["product_id"])
            if product:
                products_info.append({
                    "product": product,
                    "added_at": item.get("added_at", ""),
                })
        break
    
    for info in products_info[:10]:  # Show first 10
        product = info["product"]
        price_text = format_etb(product.price)
        if product.discounted_price:
            price_text = f"~~{format_etb(product.compare_price)}~~ {format_etb(product.price)}"
        
        wishlist_text += f"• *{product.name}*\n"
        wishlist_text += f"  💰 {price_text}\n"
        wishlist_text += f"  [ዝርዝር ለማየት ይጫኑ](/view_{product.id})\n\n"
    
    # Build keyboard
    keyboard = [
        [
            InlineKeyboardButton("🛒 ሁሉንም ወደ ቅርጫት ጨምር", callback_data="wishlist_add_all"),
            InlineKeyboardButton("🗑️ ሁሉንም አጥፋ", callback_data="wishlist_clear"),
        ],
        [InlineKeyboardButton("🔙 ወደ ምናሌ", callback_data="menu_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            wishlist_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_text(
            wishlist_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def wishlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle wishlist-related callback queries.
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data
    
    if action.startswith("add_to_wishlist_"):
        # Add product to wishlist
        product_id = int(action.split("_")[3])
        await add_to_wishlist(user_id, product_id)
        await query.message.reply_text(f"⭐ ምርቱ ወደ ተመራጮች ተጨምሯል!")
        
    elif action.startswith("wishlist_remove_"):
        # Remove from wishlist
        product_id = int(action.split("_")[2])
        await remove_from_wishlist(user_id, product_id)
        await query.message.reply_text(f"🗑️ ምርቱ ከተመራጮች ተወግዷል!")
        await refresh_wishlist_display(query, user_id)
        
    elif action == "wishlist_add_all":
        # Add all to cart
        wishlist = await get_user_wishlist(user_id)
        from bot.handlers.cart import add_to_cart
        
        for item in wishlist:
            await add_to_cart(user_id, item["product_id"], context)
        
        await query.message.reply_text(f"✅ {len(wishlist)} ምርቶች ወደ ቅርጫት ተጨምረዋል!")
        
    elif action == "wishlist_clear":
        # Clear wishlist
        await clear_wishlist(user_id)
        await query.message.edit_text("⭐ *ተመራጭ ምርቶችዎ ባዶ ነው!*", parse_mode="Markdown")
        
    elif action == "wishlist_refresh":
        # Refresh wishlist display
        await refresh_wishlist_display(query, user_id)


async def add_to_wishlist(user_id: int, product_id: int) -> None:
    """Add a product to the user's wishlist."""
    redis = await get_redis_client()
    wishlist_key = f"wishlist:{user_id}"
    
    # Get current wishlist
    wishlist = await get_user_wishlist(user_id)
    
    # Check if already exists
    for item in wishlist:
        if item["product_id"] == product_id:
            return
    
    # Add new item
    import json
    from datetime import datetime
    
    wishlist.append({
        "product_id": product_id,
        "added_at": datetime.utcnow().isoformat(),
    })
    
    # Save to Redis (expires in 30 days)
    await redis.setex(wishlist_key, 2592000, json.dumps(wishlist))
    
    logger.info(f"Added product {product_id} to wishlist for user {user_id}")


async def remove_from_wishlist(user_id: int, product_id: int) -> None:
    """Remove a product from the user's wishlist."""
    wishlist = await get_user_wishlist(user_id)
    wishlist = [item for item in wishlist if item["product_id"] != product_id]
    await save_user_wishlist(user_id, wishlist)


async def clear_wishlist(user_id: int) -> None:
    """Clear the user's wishlist."""
    await save_user_wishlist(user_id, [])


async def get_user_wishlist(user_id: int) -> list:
    """Get the user's wishlist from Redis."""
    redis = await get_redis_client()
    wishlist_key = f"wishlist:{user_id}"
    
    wishlist_json = await redis.get(wishlist_key)
    if wishlist_json:
        import json
        return json.loads(wishlist_json)
    return []


async def save_user_wishlist(user_id: int, wishlist: list) -> None:
    """Save the user's wishlist to Redis."""
    redis = await get_redis_client()
    wishlist_key = f"wishlist:{user_id}"
    
    import json
    await redis.setex(wishlist_key, 2592000, json.dumps(wishlist))


async def refresh_wishlist_display(query, user_id: int) -> None:
    """Refresh the wishlist display message."""
    wishlist = await get_user_wishlist(user_id)
    
    if not wishlist:
        await query.message.edit_text(
            "⭐ *ተመራጭ ምርቶችዎ ባዶ ነው!*",
            parse_mode="Markdown"
        )
        return
    
    wishlist_text = "⭐ *ተመራጭ ምርቶች*\n\n"
    
    async for db in get_db_session():
        product_service = ProductService(db)
        
        for item in wishlist[:10]:
            product = await product_service.get_product(item["product_id"])
            if product:
                price_text = format_etb(product.price)
                if product.discounted_price:
                    price_text = f"~~{format_etb(product.compare_price)}~~ {format_etb(product.price)}"
                
                wishlist_text += f"• *{product.name}*\n"
                wishlist_text += f"  💰 {price_text}\n\n"
        break
    
    keyboard = [
        [
            InlineKeyboardButton("🛒 ሁሉንም ወደ ቅርጫት ጨምር", callback_data="wishlist_add_all"),
            InlineKeyboardButton("🗑️ ሁሉንም አጥፋ", callback_data="wishlist_clear"),
        ],
        [InlineKeyboardButton("🔄 አድስ", callback_data="wishlist_refresh")],
        [InlineKeyboardButton("🔙 ወደ ምናሌ", callback_data="menu_back")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        wishlist_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


__all__ = [
    "wishlist_command",
    "wishlist_callback",
    "add_to_wishlist",
    "get_user_wishlist",
    "clear_wishlist",
]