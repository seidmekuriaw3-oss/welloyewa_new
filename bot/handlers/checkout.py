# ============================
# WOLLOYEWA STORE BOT - CHECKOUT HANDLER
# ============================
"""Telegram bot checkout and order confirmation handlers."""

from decimal import Decimal

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes, ConversationHandler
from telegram.helpers import escape_markdown

from apps.orders.schemas import OrderCreate, OrderItemCreate
from apps.orders.services import OrderService
from apps.products.services import ProductService
from apps.users.models import UserAddress
from apps.users.services import UserService
from bot.handlers.cart import clear_cart, get_user_cart
from bot.handlers.location import reverse_geocode
from bot.handlers.text_routing import mark_text_message_handled
from bot.localization import get_language, tr
from core.constants import PaymentStatus
from core.logger import logger
from core.utils.currency import format_etb
from core.utils.location import format_delivery_address
from core.utils.validators import Validator
from infrastructure.database.session import get_db_session, transaction_session
from infrastructure.payments.factory import process_payment

# Conversation states
SELECT_ADDRESS, SELECT_PAYMENT, CONFIRM_ORDER = range(3)
SELECT_RECIPIENT_NAME, SELECT_RECIPIENT_PHONE = range(3, 5)


async def _prompt_new_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    location_prompt = (
        f"{tr(context, 'checkout_new_address')}\n\n"
        f"{tr(context, 'checkout_address_example')}"
    )
    location_markup = ReplyKeyboardMarkup(
        [[KeyboardButton(tr(context, "location_share"), request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
    await update.effective_message.reply_text(
        location_prompt,
        parse_mode="Markdown",
        reply_markup=location_markup,
    )
    return SELECT_ADDRESS


async def _prompt_recipient_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    await update.effective_message.reply_text(
        tr(context, "checkout_recipient_name_prompt"),
        reply_markup=ReplyKeyboardRemove(),
    )
    return SELECT_RECIPIENT_NAME


async def _prompt_recipient_phone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    markup = ReplyKeyboardMarkup(
        [[KeyboardButton(tr(context, "checkout_share_phone"), request_contact=True)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
    await update.effective_message.reply_text(
        tr(context, "checkout_recipient_phone_prompt"),
        reply_markup=markup,
    )
    return SELECT_RECIPIENT_PHONE


async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start the checkout process.

    Shows address selection or address entry form.
    """
    user_id = update.effective_user.id
    context.user_data["checkout_in_progress"] = True
    context.user_data["checkout_conversation_active"] = True

    if update.callback_query:
        await update.callback_query.answer()
        target_message = update.callback_query.message
    else:
        target_message = update.message

    context.user_data.pop("checkout_address_id", None)
    context.user_data.pop("checkout_pending_address", None)
    context.user_data.pop("checkout_recipient_name", None)
    context.user_data.pop("checkout_recipient_phone", None)
    context.user_data.pop("checkout_resume_confirmation", None)
    context.user_data.pop("checkout_payment_method", None)
    context.user_data.pop("checkout_order_id", None)

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
            keyboard.append(
                [InlineKeyboardButton(f"📍 {address_text[:40]}", callback_data=f"addr_{addr.id}")]
            )

        keyboard.append(
            [
                InlineKeyboardButton(tr(context, "checkout_add_address"), callback_data="addr_new"),
                InlineKeyboardButton(tr(context, "cancel"), callback_data="checkout_cancel"),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await target_message.edit_text(
                f"{tr(context, 'checkout_address_title')}\n\n{tr(context, 'checkout_address_prompt')}",
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
        else:
            await target_message.reply_text(
                f"{tr(context, 'checkout_address_title')}\n\n{tr(context, 'checkout_address_prompt')}",
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
    else:
        if update.callback_query:
            await target_message.edit_text(
                tr(context, "checkout_address_title"),
                parse_mode="Markdown",
            )
        return await _prompt_new_address(update, context)

    return SELECT_ADDRESS


async def checkout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Command entrypoint for checkout."""
    return await start_checkout(update, context)


async def address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle address selection callback.

    Stores selected address and asks for delivery recipient details.
    """
    query = update.callback_query
    await query.answer()
    context.user_data["checkout_conversation_active"] = True

    if query.data == "addr_new":
        context.user_data["checkout_in_progress"] = True
        await query.message.edit_text(
            tr(context, "checkout_address_title"), parse_mode="Markdown"
        )
        return await _prompt_new_address(update, context)

    elif query.data == "checkout_cancel":
        await query.message.edit_text(tr(context, "order_cancelled"))
        _clear_checkout_state(context)
        return ConversationHandler.END

    # Selected existing address
    address_id = int(query.data.split("_")[1])
    context.user_data["checkout_address_id"] = address_id
    context.user_data["checkout_in_progress"] = True

    return await _prompt_recipient_name(update, context)


async def new_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle new address input.

    Temporarily stores a new address and asks for delivery recipient details.
    """
    context.user_data["checkout_conversation_active"] = True
    if getattr(update.message, "text", None):
        mark_text_message_handled(update, context)

    address_text = (getattr(update.message, "text", None) or "").strip() or None
    city = "Addis Ababa"
    latitude = None
    longitude = None

    if getattr(update.message, "location", None):
        location = update.message.location
        latitude = location.latitude
        longitude = location.longitude
        city = await reverse_geocode(location.latitude, location.longitude) or city
        address_text = "Shared location"

    if not address_text:
        await update.effective_message.reply_text(
            tr(context, "checkout_new_address"),
        )
        return SELECT_ADDRESS
    if len(address_text) > 255:
        await update.effective_message.reply_text(
            tr(context, "checkout_invalid_address")
        )
        return SELECT_ADDRESS

    context.user_data["checkout_pending_address"] = {
        "address_line1": address_text,
        "city": city,
        "latitude": latitude,
        "longitude": longitude,
    }
    context.user_data.pop("checkout_address_id", None)
    return await _prompt_recipient_name(update, context)


async def recipient_name_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Collect the name to put on the delivery."""
    context.user_data["checkout_conversation_active"] = True
    mark_text_message_handled(update, context)
    recipient_name = (update.effective_message.text or "").strip()
    if not recipient_name or len(recipient_name) > 100:
        await update.effective_message.reply_text(
            tr(context, "checkout_invalid_name")
        )
        return SELECT_RECIPIENT_NAME

    context.user_data["checkout_recipient_name"] = recipient_name
    if context.user_data.get("checkout_resume_confirmation") and context.user_data.get(
        "checkout_recipient_phone"
    ):
        context.user_data.pop("checkout_resume_confirmation", None)
        return await show_order_confirmation(update, context)
    return await _prompt_recipient_phone(update, context)


async def recipient_phone_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Collect and validate the delivery recipient's phone number."""
    context.user_data["checkout_conversation_active"] = True
    contact = getattr(update.effective_message, "contact", None)
    phone_input = contact.phone_number if contact else update.effective_message.text
    if not contact:
        mark_text_message_handled(update, context)

    try:
        recipient_phone = Validator.phone((phone_input or "").strip(), normalize=True)
    except ValueError:
        markup = ReplyKeyboardMarkup(
            [[KeyboardButton(tr(context, "checkout_share_phone"), request_contact=True)]],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await update.effective_message.reply_text(
            tr(context, "checkout_invalid_phone"),
            reply_markup=markup,
        )
        return SELECT_RECIPIENT_PHONE

    context.user_data["checkout_recipient_phone"] = recipient_phone
    pending_address = context.user_data.get("checkout_pending_address")
    if pending_address:
        address_id = None
        try:
            async with transaction_session() as db:
                user_service = UserService(db)
                user = await user_service.get_user_by_telegram(
                    update.effective_user.id
                )
                if user:
                    new_address = UserAddress(
                        user_id=user.id,
                        address_line1=pending_address["address_line1"],
                        city=pending_address["city"],
                        recipient_name=context.user_data["checkout_recipient_name"],
                        recipient_phone=recipient_phone,
                        latitude=pending_address["latitude"],
                        longitude=pending_address["longitude"],
                    )
                    db.add(new_address)
                    await db.flush()
                    address_id = new_address.id
        except Exception:
            logger.exception(
                "Failed to save checkout address for Telegram user %s",
                update.effective_user.id,
            )
            await update.effective_message.reply_text(
                tr(context, "checkout_save_failed"),
                reply_markup=ReplyKeyboardRemove(),
            )
            _clear_checkout_state(context)
            return ConversationHandler.END

        if address_id is None:
            await update.effective_message.reply_text(
                tr(context, "checkout_missing"),
                reply_markup=ReplyKeyboardRemove(),
            )
            _clear_checkout_state(context)
            return ConversationHandler.END
        context.user_data["checkout_address_id"] = address_id
        context.user_data.pop("checkout_pending_address", None)

    await update.effective_message.reply_text(
        tr(context, "checkout_delivery_details_saved"),
        reply_markup=ReplyKeyboardRemove(),
    )
    if context.user_data.pop("checkout_resume_confirmation", False):
        return await show_order_confirmation(update, context)
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
        [InlineKeyboardButton(tr(context, "pay_cash"), callback_data="pay_cod")],
        [InlineKeyboardButton(tr(context, "back"), callback_data="pay_back")],
        [InlineKeyboardButton(tr(context, "cancel"), callback_data="checkout_cancel")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(
            f"{tr(context, 'checkout_payment_title')}\n\n{tr(context, 'checkout_payment_prompt')}",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text(
            f"{tr(context, 'checkout_payment_title')}\n\n{tr(context, 'checkout_payment_prompt')}",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

    return SELECT_PAYMENT


async def payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle payment method selection.

    Stores payment method and shows order confirmation.
    """
    query = update.callback_query
    await query.answer()
    context.user_data["checkout_conversation_active"] = True

    if query.data == "pay_back":
        # Go back to address selection
        return await start_checkout(update, context)

    elif query.data == "checkout_cancel":
        await query.message.edit_text(tr(context, "order_cancelled"))
        _clear_checkout_state(context)
        return ConversationHandler.END

    # Store payment method
    payment_method = {
        "pay_cbe_birr": "cbe_birr",
        "pay_cod": "cash_on_delivery",
    }.get(query.data, query.data.removeprefix("pay_"))
    context.user_data["checkout_payment_method"] = payment_method
    if not context.user_data.get("checkout_recipient_name"):
        context.user_data["checkout_resume_confirmation"] = True
        return await _prompt_recipient_name(update, context)
    if not context.user_data.get("checkout_recipient_phone"):
        context.user_data["checkout_resume_confirmation"] = True
        return await _prompt_recipient_phone(update, context)

    # Show order confirmation
    return await show_order_confirmation(update, context)


async def show_order_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Show order confirmation with total and details."""
    user_id = update.effective_user.id
    cart = await get_user_cart(user_id, context)
    if not cart:
        await update.effective_message.reply_text(
            tr(context, "cart_empty"),
            parse_mode="Markdown",
        )
        _clear_checkout_state(context)
        return ConversationHandler.END

    # Calculate totals
    subtotal = Decimal("0")
    items_text = []
    delivery_address = None

    async for db in get_db_session():
        product_service = ProductService(db)
        address_id = context.user_data.get("checkout_address_id")
        address = await db.get(UserAddress, address_id) if address_id else None
        if address:
            delivery_address = format_delivery_address(
                f"{address.address_line1}, {address.city}",
                address.latitude,
                address.longitude,
            )

        for item in cart:
            product = await product_service.get_product(item["product_id"])
            if product:
                item_total = product.price * item["quantity"]
                subtotal += item_total
                language = get_language(context)
                name = (
                    product.name_am if language == "am" else product.name
                ) or product.name
                items_text.append(f"• {name} x{item['quantity']} = {format_etb(item_total)}")
        break

    shipping_fee = Decimal("0") if subtotal >= 1000 else Decimal("50")
    tax = subtotal * Decimal("0.15")
    total = subtotal + shipping_fee + tax

    payment_method = context.user_data.get("checkout_payment_method", "N/A")
    if payment_method == "cash_on_delivery":
        payment_label = tr(context, "pay_cash")
    else:
        payment_label = payment_method.replace("_", " ").title()
    recipient_name = context.user_data.get("checkout_recipient_name")
    recipient_phone = context.user_data.get("checkout_recipient_phone")
    if not recipient_name or not recipient_phone or not delivery_address:
        await update.callback_query.message.edit_text(tr(context, "checkout_missing"))
        _clear_checkout_state(context)
        return ConversationHandler.END

    recipient_name = escape_markdown(recipient_name, version=1)
    delivery_address = escape_markdown(delivery_address, version=1)
    confirmation_text = (
        f"{tr(context, 'checkout_confirm_title')}\n\n"
        f"{tr(context, 'checkout_delivery_to')} {recipient_name}\n"
        f"{tr(context, 'checkout_phone_summary')} {recipient_phone}\n"
        f"{tr(context, 'checkout_address_summary')} {delivery_address}\n\n"
        f"{tr(context, 'checkout_products')}\n{chr(10).join(items_text)}\n\n"
        "─────────────────\n"
        f"{tr(context, 'checkout_subtotal')} {format_etb(subtotal)}\n"
        f"{tr(context, 'checkout_shipping')} {format_etb(shipping_fee)}\n"
        f"{tr(context, 'checkout_tax')} {format_etb(tax)}\n"
        "─────────────────\n"
        f"{tr(context, 'checkout_total')} {format_etb(total)}\n\n"
        f"{tr(context, 'checkout_method')} {payment_label}\n\n"
        f"{tr(context, 'checkout_confirm_prompt')}"
    )

    keyboard = [
        [
            InlineKeyboardButton(tr(context, "confirm"), callback_data="confirm_yes"),
            InlineKeyboardButton(tr(context, "cancel"), callback_data="confirm_no"),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(
            confirmation_text, parse_mode="Markdown", reply_markup=reply_markup
        )
    else:
        await update.effective_message.reply_text(
            confirmation_text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

    return CONFIRM_ORDER


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle order confirmation.

    Creates the order and processes payment.
    """
    query = update.callback_query
    await query.answer()

    if query.data in {"confirm_no", "checkout_cancel"}:
        await query.message.edit_text(tr(context, "order_cancelled"))
        await _cancel_created_order_if_pending(update, context)
        _clear_checkout_state(context)
        return ConversationHandler.END

    user_id = update.effective_user.id
    if query.data == "retry_payment":
        order_id = context.user_data.get("checkout_order_id")
        if not order_id:
            await query.message.edit_text(tr(context, "checkout_missing"))
            _clear_checkout_state(context)
            return ConversationHandler.END

        order = None
        user = None
        async for db in get_db_session():
            order = await OrderService(db).get_order(order_id, user_id)
            user = await UserService(db).get_user_by_telegram(user_id)
            break
        if not order or not user:
            await query.message.edit_text(tr(context, "checkout_missing"))
            _clear_checkout_state(context)
            return ConversationHandler.END
        return await _process_order_payment(
            update,
            context,
            order,
            user,
            context.user_data.get("checkout_payment_method"),
        )

    return await _create_and_process_order(update, context)


async def _create_and_process_order(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Create an order and start payment after the order is committed."""
    query = update.callback_query
    user_id = update.effective_user.id
    cart = await get_user_cart(user_id, context)
    address_id = context.user_data.get("checkout_address_id")
    payment_method = context.user_data.get("checkout_payment_method")
    recipient_name = context.user_data.get("checkout_recipient_name")
    recipient_phone = context.user_data.get("checkout_recipient_phone")

    if not cart or not address_id or not payment_method or not recipient_name or not recipient_phone:
        await query.message.edit_text(tr(context, "checkout_missing"))
        _clear_checkout_state(context)
        return ConversationHandler.END

    user = None
    order = None
    async with transaction_session() as db:
        order_service = OrderService(db)

        # Get user
        user_service = UserService(db)
        user = await user_service.get_user_by_telegram(user_id)
        if not user:
            raise ValueError("Checkout user no longer exists")

        # Get address
        address = await db.get(UserAddress, address_id)
        if not address or address.user_id != user.id:
            raise ValueError("Shipping address does not belong to this user")

        # Prepare order items
        order_items = []
        for item in cart:
            order_items.append(
                OrderItemCreate(
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                )
            )
        subtotal = Decimal("0")
        for item in cart:
            product = await order_service.product_service.get_product(item["product_id"])
            subtotal += product.price * item["quantity"]

        # Create order
        order_create = OrderCreate(
            items=order_items,
            payment_method=payment_method,
            shipping_fee=Decimal("0") if subtotal >= 1000 else Decimal("50"),
            shipping_address=format_delivery_address(
                f"{address.address_line1}, {address.city}",
                address.latitude,
                address.longitude,
            ),
            shipping_city=address.city,
            shipping_phone=recipient_phone,
            customer_notes=f"Delivery recipient: {recipient_name}",
        )

        order = await order_service.create_order(user.id, order_create)

    context.user_data["checkout_order_id"] = order.id
    return await _process_order_payment(update, context, order, user, payment_method)


async def _process_order_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    order,
    user,
    payment_method: str | None,
) -> int:
    """Process an online payment or complete a cash-on-delivery order."""
    query = update.callback_query
    user_id = update.effective_user.id

    if payment_method == "cash_on_delivery":
        await clear_cart(user_id, context)
        await query.message.edit_text(
            f"{tr(context, 'order_success')}\n\n"
            f"{tr(context, 'order_number')} `{order.order_number}`\n"
            f"{tr(context, 'checkout_total')} {format_etb(order.total)}\n\n"
            f"{tr(context, 'cod_payment_at_delivery')}\n\n"
            f"{tr(context, 'order_track')}",
            parse_mode="Markdown",
        )
        _clear_checkout_state(context)
        return ConversationHandler.END

    try:
        payment_response = await process_payment(
            method=payment_method or "",
            amount=order.total,
            order_id=order.id,
            order_number=order.order_number,
            customer_name=context.user_data.get("checkout_recipient_name") or user.full_name,
            customer_email=user.email or "",
            customer_phone=context.user_data.get("checkout_recipient_phone") or user.phone_number or "",
        )
    except Exception:
        logger.exception("Checkout payment initialization failed for order %s", order.id)
        payment_response = None

    if payment_response and payment_response.success and payment_response.transaction_id:
        async with transaction_session() as db:
            await OrderService(db).update_payment_status(
                order.id,
                PaymentStatus.PENDING.value,
                payment_response.transaction_id,
            )
        await clear_cart(user_id, context)
        payment_url = payment_response.payment_url or payment_response.redirect_url
        await query.message.edit_text(
            f"{tr(context, 'order_success')}\n\n"
            f"{tr(context, 'order_number')} `{order.order_number}`\n"
            f"{tr(context, 'checkout_total')} {format_etb(order.total)}\n\n"
            f"{tr(context, 'payment_receipt')} "
            f"{payment_url or tr(context, 'payment_receipt_later')}\n\n"
            f"{tr(context, 'order_track')}",
            parse_mode="Markdown",
        )
        _clear_checkout_state(context)
        return ConversationHandler.END

    async with transaction_session() as db:
        await OrderService(db).update_payment_status(order.id, PaymentStatus.FAILED.value)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    tr(context, "retry_payment_button"), callback_data="retry_payment"
                )
            ],
            [InlineKeyboardButton(tr(context, "cancel"), callback_data="checkout_cancel")],
        ]
    )
    await query.message.edit_text(
        f"{tr(context, 'payment_failed')}\n\n"
        f"{tr(context, 'payment_retry')}\n\n"
        f"{tr(context, 'payment_support')}",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    context.user_data["checkout_order_id"] = order.id
    return CONFIRM_ORDER


def _clear_checkout_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        "checkout_in_progress",
        "checkout_conversation_active",
        "checkout_address_id",
        "checkout_pending_address",
        "checkout_recipient_name",
        "checkout_recipient_phone",
        "checkout_resume_confirmation",
        "checkout_payment_method",
        "checkout_order_id",
    ):
        context.user_data.pop(key, None)


async def _cancel_created_order_if_pending(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    order_id = context.user_data.get("checkout_order_id")
    user = update.effective_user
    if not order_id or not user:
        return

    try:
        async with transaction_session() as db:
            await OrderService(db).cancel_order(
                order_id,
                user.id,
                reason="Checkout cancelled by customer",
            )
    except Exception:
        logger.exception("Could not cancel checkout order %s", order_id)


async def cancel_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the checkout process."""
    await update.message.reply_text(tr(context, "order_cancelled"))
    await _cancel_created_order_if_pending(update, context)
    _clear_checkout_state(context)
    return ConversationHandler.END


__all__ = [
    "CONFIRM_ORDER",
    "SELECT_ADDRESS",
    "SELECT_PAYMENT",
    "SELECT_RECIPIENT_NAME",
    "SELECT_RECIPIENT_PHONE",
    "address_callback",
    "cancel_checkout",
    "checkout_command",
    "confirm_callback",
    "new_address_handler",
    "payment_callback",
    "recipient_name_handler",
    "recipient_phone_handler",
    "start_checkout",
]
