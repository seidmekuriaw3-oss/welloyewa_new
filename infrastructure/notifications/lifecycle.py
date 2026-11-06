"""Asynchronous notifications for persisted customer, vendor, and catalog events."""

import asyncio
import html
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.config import settings
from core.events import (
    ORDER_CANCELLED,
    ORDER_CONFIRMED,
    ORDER_CREATED,
    ORDER_DELIVERED,
    ORDER_PROCESSING,
    ORDER_REFUNDED,
    ORDER_SHIPPED,
    PAYMENT_COMPLETED,
    PAYMENT_FAILED,
    PRODUCT_APPROVED,
    PRODUCT_CREATED,
    PRODUCT_REJECTED,
    PRODUCT_STOCK_LOW,
    PRODUCT_STOCK_OUT,
    TICKET_CREATED,
    TICKET_MESSAGE_ADDED,
    TICKET_STATUS_CHANGED,
    USER_UPDATED,
    VENDOR_APPROVED,
    VENDOR_REGISTERED,
    VENDOR_REJECTED,
    Event,
    event_bus,
)
from core.logger import logger

_EVENT_NAMES = (
    ORDER_CREATED,
    ORDER_CONFIRMED,
    ORDER_PROCESSING,
    ORDER_SHIPPED,
    ORDER_DELIVERED,
    ORDER_CANCELLED,
    ORDER_REFUNDED,
    PAYMENT_COMPLETED,
    PAYMENT_FAILED,
    VENDOR_REGISTERED,
    VENDOR_APPROVED,
    VENDOR_REJECTED,
    PRODUCT_CREATED,
    PRODUCT_APPROVED,
    PRODUCT_REJECTED,
    PRODUCT_STOCK_LOW,
    PRODUCT_STOCK_OUT,
    USER_UPDATED,
    TICKET_CREATED,
    TICKET_STATUS_CHANGED,
    TICKET_MESSAGE_ADDED,
)
_registered = False
_fallback_tasks: set[asyncio.Task[None]] = set()

_ORDER_STATUS = {
    ORDER_CONFIRMED: ("ትዕዛዙ ተረጋግጧል", "Your order is confirmed"),
    ORDER_PROCESSING: ("ትዕዛዙ በሂደት ላይ ነው", "Your order is being prepared"),
    ORDER_SHIPPED: ("ትዕዛዙ ተልኳል", "Your order has shipped"),
    ORDER_DELIVERED: ("ትዕዛዙ ደርሷል", "Your order has been delivered"),
    ORDER_CANCELLED: ("ትዕዛዙ ተሰርዟል", "Your order has been cancelled"),
    ORDER_REFUNDED: ("ክፍያው ተመልሷል", "Your order has been refunded"),
}


def _language(user: Any) -> str:
    return str(
        getattr(user, "preferred_language", None) or getattr(user, "language", None) or "am"
    ).lower()


def _html(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _format_money(amount: Any) -> str:
    try:
        return f"ETB {float(amount):,.2f}"
    except (TypeError, ValueError):
        return "ETB 0.00"


def _order_message(
    event_name: str,
    order: Any,
    user: Any,
    event_data: dict[str, Any],
) -> tuple[str, str]:
    order_number = _html(order.order_number)
    if event_name == ORDER_CREATED:
        if _language(user).startswith("am"):
            return (
                f"✅ <b>ትዕዛዝዎ ተቀብሏል!</b>\n"
                f"ቁጥር: <b>#{order_number}</b>\n"
                f"ጠቅላላ: <b>{_format_money(order.total)}</b>",
                f"የትዕዛዝ ማረጋገጫ #{order.order_number}",
            )
        return (
            f"✅ <b>Order received</b>\n"
            f"Order: <b>#{order_number}</b>\n"
            f"Total: <b>{_format_money(order.total)}</b>",
            f"Order confirmation #{order.order_number}",
        )

    if event_name in {PAYMENT_COMPLETED, PAYMENT_FAILED}:
        is_paid = event_name == PAYMENT_COMPLETED
        if _language(user).startswith("am"):
            title = "ክፍያዎ ተሳክቷል" if is_paid else "ክፍያው አልተሳካም"
        else:
            title = "Payment received" if is_paid else "Payment could not be completed"
        return (
            f"{'✅' if is_paid else '⚠️'} <b>{title}</b>\n"
            f"Order: <b>#{order_number}</b>\n"
            f"Amount: <b>{_format_money(order.total)}</b>",
            f"{title} — #{order.order_number}",
        )

    status_am, status_en = _ORDER_STATUS.get(
        event_name, ("ትዕዛዝ ተዘምኗል", "Your order has been updated")
    )
    status = status_am if _language(user).startswith("am") else status_en
    tracking = getattr(order, "tracking_number", None)
    reason = event_data.get("reason") or getattr(order, "cancelled_reason", None)
    extra = ""
    if tracking:
        extra = (
            f"\nየመከታተያ ቁጥር: <b>{_html(tracking)}</b>"
            if _language(user).startswith("am")
            else f"\nTracking number: <b>{_html(tracking)}</b>"
        )
    if reason and event_name == ORDER_CANCELLED:
        extra += (
            f"\nምክንያት: {_html(reason)}"
            if _language(user).startswith("am")
            else f"\nReason: {_html(reason)}"
        )
    return (
        f"📦 <b>{status}</b>\nOrder: <b>#{order_number}</b>{extra}",
        f"Order update — #{order.order_number}",
    )


def _vendor_message(
    event_name: str,
    vendor: Any,
    event_data: dict[str, Any],
    language: str,
) -> tuple[str, str]:
    name = _html(vendor.business_name)
    if event_name == VENDOR_REGISTERED:
        if language.startswith("am"):
            return (
                f"✅ የሻጭ ማመልከቻዎ ለ<b>{name}</b> ተቀብሏል። አስተዳደሩ እየገመገመው ነው።",
                "የሻጭ ማመልከቻ ተቀብሏል",
            )
        return (
            f"✅ Your application for <b>{name}</b> was received and is under review.",
            "Vendor application received",
        )
    if event_name == VENDOR_APPROVED:
        if language.startswith("am"):
            return f"🎉 የ<b>{name}</b> ሻጭ መለያዎ ጸድቋል። አሁን ምርቶችን ማቅረብ ይችላሉ።", "የሻጭ መለያ ጸድቋል"
        return (
            f"🎉 Your vendor account for <b>{name}</b> has been approved. You can now list products.",
            "Vendor account approved",
        )
    reason = event_data.get("reason") or getattr(vendor, "rejection_reason", None)
    if language.startswith("am"):
        text = f"የ<b>{name}</b> የሻጭ ማመልከቻዎ ውድቅ ሆኗል።"
        if reason:
            text += f"\nምክንያት: {_html(reason)}"
        return f"⚠️ {text}", "የሻጭ ማመልከቻ ውሳኔ"
    text = f"Your vendor application for <b>{name}</b> was declined."
    if reason:
        text += f"\nReason: {_html(reason)}"
    return f"⚠️ {text}", "Vendor application decision"


async def _deliver_user(user: Any, message: str, subject: str) -> None:
    """Deliver independently over supported channels without raising to callers."""
    if user is None:
        return
    if user.telegram_id:
        try:
            from infrastructure.notifications.telegram_notifier import send_telegram_message

            if not await send_telegram_message(user.telegram_id, message):
                logger.warning("Telegram notification delivery failed for user %s", user.id)
        except Exception:
            logger.exception("Telegram notification dispatch failed for user %s", user.id)
    if user.email:
        try:
            from infrastructure.notifications.email_service import send_email

            plain_text = re.sub(r"<[^>]*>", "", message)
            if not await send_email(user.email, subject, html.unescape(plain_text)):
                logger.warning("Email notification delivery failed for user %s", user.id)
        except Exception:
            logger.exception("Email notification dispatch failed for user %s", user.id)


async def _send_admins(message: str) -> None:
    from infrastructure.notifications.telegram_notifier import send_telegram_message

    for admin_id in settings.admin_ids_list:
        try:
            if not await send_telegram_message(admin_id, message):
                logger.warning("Admin notification delivery failed")
        except Exception:
            logger.exception("Admin notification dispatch failed")


async def dispatch_lifecycle_notification(event_name: str, event_data: dict[str, Any]) -> None:
    """Load committed domain data and send localized messages outside request transactions."""
    from apps.orders.models import Order
    from apps.products.models import Product
    from apps.store_settings.models import StoreSettings
    from apps.users.models import User, Vendor
    from infrastructure.database.session import transaction_session

    user_messages: list[tuple[Any, str, str]] = []
    admin_messages: list[str] = []

    notification_settings = {
        "customer_orders": True,
        "vendor_updates": True,
        "admin_alerts": True,
        "support_updates": True,
    }
    async with transaction_session() as db:
        if event_name.startswith("order.") or event_name in {PAYMENT_COMPLETED, PAYMENT_FAILED}:
            order_id = event_data.get("order_id")
            order = await db.scalar(
                select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
            )
            if order is None:
                raise LookupError(f"Order {order_id} is not visible for notification dispatch")
            user = await db.get(User, order.user_id)
            if event_name == ORDER_CREATED:
                if user:
                    message, subject = _order_message(event_name, order, user, event_data)
                    user_messages.append((user, message, subject))
                admin_messages.append(
                    f"🛍️ New order <b>#{_html(order.order_number)}</b> · {_format_money(order.total)}"
                )
                vendor_ids = {item.vendor_id for item in order.items if item.vendor_id is not None}
                if order.vendor_id:
                    vendor_ids.add(order.vendor_id)
                if vendor_ids:
                    vendors = (
                        await db.scalars(select(Vendor).where(Vendor.id.in_(vendor_ids)))
                    ).all()
                    for vendor in vendors:
                        vendor_user = await db.get(User, vendor.user_id)
                        if vendor_user:
                            message = (
                                f"🛍️ <b>New order</b> #{_html(order.order_number)} "
                                f"contains items from <b>{_html(vendor.business_name)}</b>."
                            )
                            user_messages.append(
                                (vendor_user, message, f"New order #{order.order_number}")
                            )
            elif user:
                message, subject = _order_message(event_name, order, user, event_data)
                user_messages.append((user, message, subject))

        elif event_name in {VENDOR_REGISTERED, VENDOR_APPROVED, VENDOR_REJECTED}:
            vendor_id = event_data.get("vendor_id")
            vendor = await db.get(Vendor, vendor_id) if vendor_id else None
            if vendor is not None:
                user = await db.get(User, vendor.user_id)
                if user:
                    message, subject = _vendor_message(
                        event_name, vendor, event_data, _language(user)
                    )
                    user_messages.append((user, message, subject))
                if event_name == VENDOR_REGISTERED and event_data.get("notify_admins", True):
                    admin_messages.append(
                        f"🏪 Vendor application: <b>{_html(vendor.business_name)}</b> "
                        f"(ID {vendor.id})"
                    )

        elif event_name in {
            PRODUCT_CREATED,
            PRODUCT_APPROVED,
            PRODUCT_REJECTED,
            PRODUCT_STOCK_LOW,
            PRODUCT_STOCK_OUT,
        }:
            product_id = event_data.get("product_id")
            product = await db.get(Product, product_id) if product_id else None
            if product is not None:
                vendor = await db.get(Vendor, product.vendor_id) if product.vendor_id else None
                vendor_user = await db.get(User, vendor.user_id) if vendor else None
                if event_name == PRODUCT_CREATED and str(product.status).lower().endswith(
                    "pending"
                ):
                    admin_messages.append(
                        f"📦 Product awaiting review: <b>{_html(product.name)}</b> (ID {product.id})"
                    )
                elif vendor_user:
                    language = _language(vendor_user)
                    if event_name == PRODUCT_APPROVED:
                        message = (
                            f"✅ ምርትዎ <b>{_html(product.name)}</b> ጸድቋል።"
                            if language.startswith("am")
                            else f"✅ Your product <b>{_html(product.name)}</b> has been approved."
                        )
                        subject = "Product approved"
                    elif event_name == PRODUCT_REJECTED:
                        reason = event_data.get("reason")
                        message = (
                            f"⚠️ ምርትዎ <b>{_html(product.name)}</b> ውድቅ ሆኗል።"
                            if language.startswith("am")
                            else f"⚠️ Your product <b>{_html(product.name)}</b> was declined."
                        )
                        if reason:
                            message += (
                                f"\nምክንያት: {_html(reason)}"
                                if language.startswith("am")
                                else f"\nReason: {_html(reason)}"
                            )
                        subject = "Product decision"
                    else:
                        stock = event_data.get("current_stock", product.stock_quantity)
                        message = (
                            f"⚠️ <b>{_html(product.name)}</b> ዝቅተኛ ክምችት አለው: {stock}"
                            if event_name == PRODUCT_STOCK_LOW and language.startswith("am")
                            else (
                                f"⚠️ <b>{_html(product.name)}</b> is low on stock: {stock}"
                                if event_name == PRODUCT_STOCK_LOW
                                else (
                                    f"🚫 <b>{_html(product.name)}</b> ክምችት አልቋል: {stock}"
                                    if language.startswith("am")
                                    else f"🚫 <b>{_html(product.name)}</b> is out of stock: {stock}"
                                )
                            )
                        )
                        subject = "Stock alert"
                    user_messages.append((vendor_user, message, subject))

        elif event_name == USER_UPDATED and "status" in event_data.get("updated_fields", []):
            user_id = event_data.get("user_id")
            user = await db.get(User, user_id) if user_id else None
            status = str(getattr(user.status, "value", user.status)).lower() if user else ""
            if (
                user
                and (user.telegram_id or user.email)
                and status
                in {
                    "active",
                    "inactive",
                    "suspended",
                    "banned",
                }
            ):
                if _language(user).startswith("am"):
                    message = (
                        "✅ የመለያዎ እገዳ ተነስቷል።"
                        if status == "active"
                        else (
                            "⚠️ መለያዎ በአሁኑ ጊዜ ንቁ አይደለም።" if status == "inactive" else "⚠️ መለያዎ ታግዷል።"
                        )
                    )
                else:
                    message = (
                        "✅ Your account is active again."
                        if status == "active"
                        else (
                            "⚠️ Your account is inactive."
                            if status == "inactive"
                            else (
                                "⚠️ Your account has been banned."
                                if status == "banned"
                                else "⚠️ Your account has been suspended."
                            )
                        )
                    )
                user_messages.append((user, message, "Account status update"))

        elif event_name in {TICKET_CREATED, TICKET_STATUS_CHANGED, TICKET_MESSAGE_ADDED}:
            from apps.support.models import Ticket

            ticket_id = event_data.get("ticket_id")
            ticket = await db.get(Ticket, ticket_id) if ticket_id else None
            user = await db.get(User, ticket.user_id) if ticket else None
            ticket_number = _html(getattr(ticket, "ticket_number", event_data.get("ticket_number")))
            subject = _html(getattr(ticket, "subject", event_data.get("subject")))
            if event_name == TICKET_CREATED:
                if user:
                    if _language(user).startswith("am"):
                        message = f"✅ የድጋፍ ጥያቄዎ <b>#{ticket_number}</b> ተቀብሏል።"
                    else:
                        message = (
                            f"✅ Your support request <b>#{ticket_number}</b> has been received."
                        )
                    user_messages.append((user, message, f"Support request #{ticket_number}"))
                admin_messages.append(f"🎫 New support request <b>#{ticket_number}</b>: {subject}")
            elif event_name == TICKET_STATUS_CHANGED and user:
                status = str(event_data.get("status", "updated")).replace("_", " ")
                if _language(user).startswith("am"):
                    message = f"🎫 የድጋፍ ጥያቄዎ <b>#{ticket_number}</b> ሁኔታ ተዘምኗል: {_html(status)}"
                    if event_data.get("resolution_note"):
                        message += f"\nመፍትሔ: {_html(event_data['resolution_note'])}"
                else:
                    message = f"🎫 Support request <b>#{ticket_number}</b> status: {_html(status)}"
                    if event_data.get("resolution_note"):
                        message += f"\nResolution: {_html(event_data['resolution_note'])}"
                user_messages.append((user, message, f"Support request update #{ticket_number}"))
            elif event_name == TICKET_MESSAGE_ADDED:
                if event_data.get("is_staff_reply") and user:
                    message = (
                        f"💬 ለድጋፍ ጥያቄዎ <b>#{ticket_number}</b> አዲስ ምላሽ አለ።"
                        if _language(user).startswith("am")
                        else f"💬 There is a new reply to support request <b>#{ticket_number}</b>."
                    )
                    user_messages.append((user, message, f"Support reply #{ticket_number}"))
                elif not event_data.get("is_staff_reply"):
                    admin_messages.append(
                        f"💬 Customer replied to support request <b>#{ticket_number}</b>."
                    )

        store_settings = await db.get(StoreSettings, 1)
        if store_settings and store_settings.notification_settings:
            notification_settings.update(store_settings.notification_settings)

    if event_name.startswith("order.") or event_name in {PAYMENT_COMPLETED, PAYMENT_FAILED}:
        customer_id = getattr(order, "user_id", None)
        user_messages = [
            entry
            for entry in user_messages
            if (
                entry[0].id == customer_id
                and notification_settings["customer_orders"]
            )
            or (
                entry[0].id != customer_id
                and notification_settings["vendor_updates"]
            )
        ]
    elif event_name in {VENDOR_REGISTERED, VENDOR_APPROVED, VENDOR_REJECTED,
                        PRODUCT_CREATED, PRODUCT_APPROVED, PRODUCT_REJECTED,
                        PRODUCT_STOCK_LOW, PRODUCT_STOCK_OUT}:
        if not notification_settings["vendor_updates"]:
            user_messages.clear()
    elif event_name in {TICKET_CREATED, TICKET_STATUS_CHANGED, TICKET_MESSAGE_ADDED}:
        if not notification_settings["support_updates"]:
            user_messages.clear()
    elif event_name == USER_UPDATED and not notification_settings["customer_orders"]:
        user_messages.clear()

    if not notification_settings["admin_alerts"]:
        admin_messages.clear()

    for user, message, subject in user_messages:
        await _deliver_user(user, message, subject)
    for message in admin_messages:
        await _send_admins(message)


async def _enqueue_notification(event: Event) -> None:
    """Queue notification delivery in Celery, falling back off-request if unavailable."""
    try:
        from infrastructure.workers.tasks import send_lifecycle_notification_task

        send_lifecycle_notification_task.delay(event.name, event.data)
    except Exception as exc:
        logger.warning(
            "Could not queue notification event %s (%s); dispatching asynchronously in-process",
            event.name,
            type(exc).__name__,
        )

        async def fallback() -> None:
            await asyncio.sleep(0.25)
            try:
                await dispatch_lifecycle_notification(event.name, event.data)
            except Exception:
                logger.exception("Notification event %s failed", event.name)

        task = asyncio.create_task(fallback(), name=f"notify-{event.name}")
        _fallback_tasks.add(task)
        task.add_done_callback(_fallback_tasks.discard)


def register_notification_handlers() -> None:
    """Register lifecycle notification handlers once per application process."""
    global _registered
    if _registered:
        return
    for event_name in _EVENT_NAMES:
        event_bus.subscribe(event_name, _enqueue_notification)
    _registered = True


__all__ = [
    "dispatch_lifecycle_notification",
    "register_notification_handlers",
]
