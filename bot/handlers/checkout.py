# ============================
# WOLLOYEWA STORE BOT - CHECKOUT HANDLER
# ============================
"""Telegram bot checkout and order confirmation handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from decimal import Decimal

from core.logger import logger
from core.utils.currency import format_etb
from apps.orders.services import OrderService
from apps.orders.schemas import OrderCreate, OrderItemCreate
from apps.users.services import UserService, UserAddress
from infrastructure.database.session import get_db_session
from infrastructure.payments.factory import process_payment
from bot.handlers.cart import get_user_cart, clear_cart

# Conversation states
SELECT_ADDRESS, SELECT_PAYMENT, CONFIRM_ORDER = range(3)


async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start the checkout process.
    
    Shows address selection or address entry form.
    """
    user_id = update.effective_user.id
    
    # Get user's saved addresses
    async for db in get_db_session():
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(user_id)
        
        if user:
            addresses = user.addresses
        else:
            addresses = []
        break
    
    if addresses:
        # Show address selection
        keyboard = []
        for addr in addresses:
            address_text = f"{addr.address_line1}, {addr.city}"
            keyboard.append([
                InlineKeyboardButton(
                    f"📍 {address_text[:40]}",
                    callback_data=f"addr_{addr.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("➕ አዲስ አድራሻ", callback_data="addr_new"),
            InlineKeyboardButton("❌ ሰርዝ", callback_data="checkout_cancel"),
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(
            "📍 *የማድረሻ አድራሻ ምረጡ*\n\n"
            "እባክዎ የሚፈልጉትን አድራሻ ይምረጡ ወይም አዲስ ይጨምሩ።",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        # Ask for new address
        await update.callback_query.message.edit_text(
            "📍 *አዲስ አድራሻ ያስገቡ*\n\n"
            "እባክዎ ሙሉ አድራሻዎን ይላኩ።\n\n"
            "ለምሳሌ: ቢትዉድ አካባቢ፣ ቤት ቁጥር 123፣ አዲስ አበባ",
            parse_mode="Markdown"
        )
        return SELECT_ADDRESS
    
    return SELECT_ADDRESS


async def address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle address selection callback.
    
    Stores selected address and moves to payment method selection.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "addr_new":
        await query.message.edit_text(
            "📍 *አዲስ አድራሻ ያስገቡ*\n\n"
            "እባክዎ ሙሉ አድራሻዎን ይላኩ።",
            parse_mode="Markdown"
        )
        return SELECT_ADDRESS
    
    elif query.data == "checkout_cancel":
        await query.message.edit_text("❌ ግዢው ተሰርዟል።")
        return ConversationHandler.END
    
    # Selected existing address
    address_id = int(query.data.split("_")[1])
    context.user_data["checkout_address_id"] = address_id
    
    # Show payment methods
    return await show_payment_methods(update, context)


async def new_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle new address input.
    
    Saves the new address and moves to payment method selection.
    """
    address_text = update.message.text
    user_id = update.effective_user.id
    
    # Save address to database
    async for db in get_db_session():
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(user_id)
        
        if user:
            # Create new address
            new_address = UserAddress(
                user_id=user.id,
                address_line1=address_text,
                city="Addis Ababa",  # Default
                recipient_name=user.full_name,
                recipient_phone=user.phone_number or "",
            )
            db.add(new_address)
            await db.flush()
            context.user_data["checkout_address_id"] = new_address.id
        break
    
    # Show payment methods
    return await show_payment_methods(update, context)


async def show_payment_methods(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Show available payment methods."""
    keyboard = [
        [InlineKeyboardButton("💳 Chapa", callback_data="pay_chapa")],
        [InlineKeyboardButton("📱 Telebirr", callback_data="pay_telebirr")],
        [InlineKeyboardButton("🏦 CBE Birr", callback_data="pay_cbe_birr")],
        [InlineKeyboardButton("💵 በአደራ ክፍያ", callback_data="pay_cod")],
        [InlineKeyboardButton("🔙 ወደ ኋላ", callback_data="pay_back")],
        [InlineKeyboardButton("❌ ሰርዝ", callback_data="checkout_cancel")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            "💳 *የክፍያ መንገድ ምረጡ*\n\n"
            "እባክዎ የሚፈልጉትን የክፍያ መንገድ ይምረጡ።",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "💳 *የክፍያ መንገድ ምረጡ*\n\n"
            "እባክዎ የሚፈልጉትን የክፍያ መንገድ ይምረጡ።",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    return SELECT_PAYMENT


async def payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle payment method selection.
    
    Stores payment method and shows order confirmation.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "pay_back":
        # Go back to address selection
        return await start_checkout(update, context)
    
    elif query.data == "checkout_cancel":
        await query.message.edit_text("❌ ግዢው ተሰርዟል።")
        return ConversationHandler.END
    
    # Store payment method
    payment_method = query.data.split("_")[1]
    context.user_data["checkout_payment_method"] = payment_method
    
    # Show order confirmation
    return await show_order_confirmation(update, context)


async def show_order_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Show order confirmation with total and details."""
    user_id = update.effective_user.id
    cart = await get_user_cart(user_id)
    
    if not cart:
        await update.callback_query.message.edit_text("🛒 ቅርጫትዎ ባዶ ነው!")
        return ConversationHandler.END
    
    # Calculate totals
    subtotal = Decimal('0')
    items_text = []
    
    async for db in get_db_session():
        product_service = ProductService(db)
        
        for item in cart:
            product = await product_service.get_product(item["product_id"])
            if product:
                item_total = product.price * item["quantity"]
                subtotal += item_total
                items_text.append(
                    f"• {product.name} x{item['quantity']} = {format_etb(item_total)}"
                )
        break
    
    shipping_fee = Decimal('0') if subtotal >= 1000 else Decimal('50')
    tax = subtotal * Decimal('0.15')
    total = subtotal + shipping_fee + tax
    
    confirmation_text = f"""
✅ *የትዕዛዝ ማረጋገጫ*

*ምርቶች:*
{chr(10).join(items_text)}

─────────────────
💰 *ንኡስ ድምር:* {format_etb(subtotal)}
🚚 *የማድረስ ክፍያ:* {format_etb(shipping_fee)}
📊 *ቀረጥ (15% VAT):* {format_etb(tax)}
─────────────────
💎 *ጠቅላላ:* {format_etb(total)}

💳 *የክፍያ መንገድ:* {context.user_data.get('checkout_payment_method', 'N/A')}

ትዕዛዙን ለማረጋገጥ "✅ አረጋግጥ" ይጫኑ።
    """
    
    keyboard = [
        [
            InlineKeyboardButton("✅ አረጋግጥ", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ ሰርዝ", callback_data="confirm_no"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        confirmation_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return CONFIRM_ORDER


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle order confirmation.
    
    Creates the order and processes payment.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_no":
        await query.message.edit_text("❌ ግዢው ተሰርዟል።")
        return ConversationHandler.END
    
    # Create order
    user_id = update.effective_user.id
    cart = await get_user_cart(user_id)
    address_id = context.user_data.get("checkout_address_id")
    payment_method = context.user_data.get("checkout_payment_method")
    
    if not cart or not address_id or not payment_method:
        await query.message.edit_text("❌ የትዕዛዝ መረጃ ጠፍቷል። እባክዎ እንደገና ይሞክሩ።")
        return ConversationHandler.END
    
    async for db in get_db_session():
        order_service = OrderService(db)
        
        # Get user
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(user_id)
        
        # Get address
        address = await db.get(UserAddress, address_id)
        
        # Prepare order items
        order_items = []
        for item in cart:
            order_items.append(OrderItemCreate(
                product_id=item["product_id"],
                quantity=item["quantity"],
            ))
        
        # Create order
        order_create = OrderCreate(
            items=order_items,
            payment_method=payment_method,
            shipping_address=f"{address.address_line1}, {address.city}",
            shipping_city=address.city,
            shipping_phone=address.recipient_phone,
            customer_notes=None,
        )
        
        order = await order_service.create_order(user.id, order_create)
        
        # Clear cart
        await clear_cart(user_id)
        
        # Process payment
        payment_response = await process_payment(
            method=payment_method,
            amount=order.total,
            order_id=order.id,
            order_number=order.order_number,
            customer_name=user.full_name,
            customer_email=user.email or "",
            customer_phone=user.phone_number or "",
        )
        
        break
    
    # Send confirmation
    if payment_response.success:
        await query.message.edit_text(
            f"✅ *ትዕዛዝዎ ተረጋግጧል!*\n\n"
            f"🆔 ትዕዛዝ ቁጥር: `{order.order_number}`\n"
            f"💰 ጠቅላላ: {format_etb(order.total)}\n\n"
            f"የክፍያ ማስረጃ: {payment_response.payment_url or 'በቅርቡ ይደርስዎታል'}\n\n"
            f"ትዕዛዝዎን ለመከታተል /orders ይጫኑ።",
            parse_mode="Markdown"
        )
    else:
        await query.message.edit_text(
            f"❌ *ክፍያው አልተሳካም*\n\n"
            f"እባክዎ እንደገና ይሞክሩ ወይም ሌላ የክፍያ መንገድ ይምረጡ።\n\n"
            f"ችግሩ ከቀጠለ ድጋፍን ያግኙን።",
            parse_mode="Markdown"
        )
    
    return ConversationHandler.END


async def cancel_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the checkout process."""
    await update.message.reply_text("❌ ግዢው ተሰርዟል።")
    return ConversationHandler.END


from apps.products.services import ProductService

__all__ = [
    "start_checkout",
    "address_callback",
    "new_address_handler",
    "payment_callback",
    "confirm_callback",
    "cancel_checkout",
    "SELECT_ADDRESS",
    "SELECT_PAYMENT",
    "CONFIRM_ORDER",
]