# ============================
# WOLLOYEWA STORE BOT - DEEP LINKING HANDLER
# ============================
"""Telegram bot deep linking handlers for referral and product links."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from urllib.parse import parse_qs, urlparse

from core.logger import logger
from apps.products.services import ProductService
from apps.marketing.services import CouponService
from infrastructure.database.session import get_db_session


async def deep_link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for the /deep_link command."""
    await deep_link_handler(update, context)


async def deep_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle deep linking URLs (start parameter).
    
    Supports:
    - Product deep links: start=product_123
    - Coupon deep links: start=coupon_SAVE20
    - Referral deep links: start=ref_12345
    """
    user_id = update.effective_user.id
    start_param = context.args[0] if context.args else None
    
    if not start_param:
        # Regular start
        from bot.handlers.start import start_command
        await start_command(update, context)
        return
    
    logger.info(f"Deep link from user {user_id}: {start_param}")
    
    # Parse deep link
    if start_param.startswith("product_"):
        await handle_product_deep_link(update, context, start_param)
    elif start_param.startswith("coupon_"):
        await handle_coupon_deep_link(update, context, start_param)
    elif start_param.startswith("ref_"):
        await handle_referral_deep_link(update, context, start_param)
    else:
        await handle_unknown_deep_link(update, context, start_param)


async def handle_product_deep_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    param: str,
) -> None:
    """
    Handle product deep link.
    
    Shows product details directly.
    """
    try:
        product_id = int(param.split("_")[1])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ የማይሰራ ሊንክ።")
        return
    
    async for db in get_db_session():
        product_service = ProductService(db)
        
        try:
            product = await product_service.get_product(product_id)
        except Exception:
            await update.message.reply_text("❌ ምርቱ አልተገኘም።")
            return
        
        break
    
    # Build product detail message
    from core.utils.currency import format_etb
    
    price_text = format_etb(product.price)
    if product.discounted_price:
        price_text = f"~~{format_etb(product.compare_price)}~~ {format_etb(product.price)}"
    
    stock_status = "✅ ክምችት አለ" if product.is_in_stock else "❌ ክምችት የለም"
    
    text = f"""
🔗 *የተጋራ ምርት*

*{product.name}*

💰 *ዋጋ:* {price_text}
📦 *ሁኔታ:* {stock_status}

{product.short_description or 'ምርቱን ለማየት ከዚህ በታች ያለውን ቁልፍ ይጫኑ።'}
    """
    
    keyboard = [
        [InlineKeyboardButton("📦 ምርቱን ይመልከቱ", callback_data=f"prod_{product.id}")],
        [InlineKeyboardButton("🔙 ወደ መጀመሪያ", callback_data="menu_start")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def handle_coupon_deep_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    param: str,
) -> None:
    """
    Handle coupon deep link.
    
    Applies coupon code automatically.
    """
    try:
        coupon_code = param.split("_", 1)[1]
    except IndexError:
        await update.message.reply_text("❌ የማይሰራ ሊንክ።")
        return
    
    async for db in get_db_session():
        coupon_service = CouponService(db)
        
        # Validate coupon
        coupon = await coupon_service.get_coupon_by_code(coupon_code)
        
        if not coupon or not coupon.is_valid:
            await update.message.reply_text(
                f"❌ ኩፖኑ '{coupon_code}' ልክ አይደለም ወይም ጊዜው አልፎበታል።"
            )
            return
        
        break
    
    # Store coupon in user context
    context.user_data["pending_coupon"] = coupon_code
    
    text = f"""
🎫 *ኩፖን ተገኝቷል!*

የኩፖን ኮድ: `{coupon_code}`
{discount_text(coupon)}

ኩፖኑን ለመጠቀም ወደ ግዢ ቅርጫት ሄደው በቼክአውት ጊዜ ይጠቀሙበት።

🛒 ወደ ግዢ ቅርጫት ለመሄድ /cart ይጫኑ።
    """
    
    keyboard = [
        [InlineKeyboardButton("🛒 ወደ ቅርጫት", callback_data="menu_cart")],
        [InlineKeyboardButton("🔙 ወደ መጀመሪያ", callback_data="menu_start")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def handle_referral_deep_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    param: str,
) -> None:
    """
    Handle referral deep link.
    
    Tracks referral source.
    """
    try:
        referrer_id = int(param.split("_")[1])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ የማይሰራ ሊንክ።")
        return
    
    user_id = update.effective_user.id
    
    # Don't track self-referrals
    if referrer_id == user_id:
        await update.message.reply_text("👋 እንኳን ደህና መጡ!")
        return
    
    # Track referral
    async for db in get_db_session():
        # In production, save referral to database
        logger.info(f"User {user_id} referred by {referrer_id}")
        break
    
    text = f"""
👋 *እንኳን ደህና መጡ!*

በ{referrer_id} ተጋብዘዋል።

የምንሰጠውን ልዩ ቅናሽ ለማግኘት በቅርቡ ይመዝገቡ!

/start ይጫኑ
    """
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_unknown_deep_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    param: str,
) -> None:
    """
    Handle unknown deep link type.
    """
    await update.message.reply_text(
        f"❌ የማይታወቅ ሊንክ: {param}\n\n"
        f"እባክዎ ትክክለኛ ሊንክ መጠቀምዎን ያረጋግጡ።"
    )


def discount_text(coupon) -> str:
    """Format discount text for display."""
    if coupon.discount_type == "percentage":
        return f"🎉 *{coupon.discount_value}% ቅናሽ*"
    else:
        return f"🎉 *{coupon.discount_value} ብር ቅናሽ*"


__all__ = ["deep_link_handler"]