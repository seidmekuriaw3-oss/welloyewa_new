# ============================
# WOLLOYEWA STORE BOT - CELERY TASKS
# ============================
"""Background task definitions for Celery workers."""

import asyncio
from datetime import datetime
from typing import Any

from core.logger import logger
from infrastructure.workers.celery_app import celery_app


def _run_async(coroutine):
    """Run an asynchronous notification inside a synchronous worker task."""
    return asyncio.run(coroutine)


# ============================
# Order Tasks
# ============================


@celery_app.task(name="process_order", bind=True, max_retries=3)
def process_order_task(self, order_id: int) -> dict[str, Any]:
    """
    Process an order after creation.

    Args:
        order_id: Order ID

    Returns:
        Processing result
    """
    logger.info(f"Processing order {order_id}")

    try:
        # This would contain actual order processing logic
        # - Update inventory
        # - Process payment
        # - Send notifications
        # - Update analytics

        return {
            "order_id": order_id,
            "status": "processed",
            "processed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to process order {order_id}: {e}")
        # Retry with exponential backoff
        self.retry(exc=e, countdown=60 * (2**self.request.retries))
        raise


@celery_app.task(name="send_order_confirmation", bind=True, max_retries=3)
def send_order_confirmation_task(self, order_id: int, user_id: int) -> bool:
    """
    Send order confirmation notification.

    Args:
        order_id: Order ID
        user_id: User ID

    Returns:
        True if sent successfully
    """
    logger.info(f"Sending order confirmation for order {order_id} to user {user_id}")

    try:
        # Fetch order details
        # Send email and Telegram notification

        return True

    except Exception as e:
        logger.error(f"Failed to send order confirmation: {e}")
        self.retry(exc=e, countdown=60)
        return False


@celery_app.task(name="update_order_status", bind=True, max_retries=3)
def update_order_status_task(
    self, order_id: int, new_status: str, reason: str | None = None
) -> bool:
    """
    Update order status.

    Args:
        order_id: Order ID
        new_status: New order status
        reason: Status change reason

    Returns:
        True if updated successfully
    """
    logger.info(f"Updating order {order_id} status to {new_status}")

    try:
        # Update order status in database
        # Send notifications

        return True

    except Exception as e:
        logger.error(f"Failed to update order status: {e}")
        self.retry(exc=e, countdown=30)
        return False


# ============================
# Notification Tasks
# ============================


@celery_app.task(name="send_email", bind=True, max_retries=3)
def send_email_task(
    self,
    to: str,
    subject: str,
    content: str,
    template: str | None = None,
    template_data: dict | None = None,
) -> bool:
    """
    Send email asynchronously.

    Args:
        to: Recipient email
        subject: Email subject
        content: Email content
        template: Template name
        template_data: Template data

    Returns:
        True if sent successfully
    """
    logger.info(f"Sending email to {to}")

    try:
        from infrastructure.notifications.email_service import send_email

        return _run_async(send_email(to, subject, content, template, template_data))

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        self.retry(exc=e, countdown=60)
        return False


@celery_app.task(name="send_sms", bind=True, max_retries=3)
def send_sms_task(self, to: str, message: str) -> bool:
    """
    Send SMS asynchronously.

    Args:
        to: Recipient phone number
        message: SMS content

    Returns:
        True if sent successfully
    """
    logger.info(f"Sending SMS to {to}")

    try:
        from infrastructure.notifications.sms_gateway import send_sms

        return _run_async(send_sms(to, message))

    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        self.retry(exc=e, countdown=30)
        return False


@celery_app.task(name="send_telegram", bind=True, max_retries=3)
def send_telegram_task(self, chat_id: int, message: str) -> bool:
    """
    Send Telegram message asynchronously.

    Args:
        chat_id: Telegram chat ID
        message: Message content

    Returns:
        True if sent successfully
    """
    logger.info(f"Sending Telegram message to {chat_id}")

    try:
        from infrastructure.notifications.telegram_notifier import send_telegram_message

        return _run_async(send_telegram_message(chat_id, message))

    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        self.retry(exc=e, countdown=30)
        return False


@celery_app.task(name="send_lifecycle_notification", bind=True, max_retries=5)
def send_lifecycle_notification_task(
    self,
    event_name: str,
    event_data: dict[str, Any],
) -> bool:
    """Deliver a domain-event notification after its transaction has committed."""
    try:
        from infrastructure.notifications.lifecycle import dispatch_lifecycle_notification

        _run_async(dispatch_lifecycle_notification(event_name, event_data))
        return True
    except Exception as exc:
        logger.exception("Lifecycle notification task failed for %s", event_name)
        raise self.retry(
            exc=exc,
            countdown=min(300, 15 * (2**self.request.retries)),
        ) from exc


@celery_app.task(name="send_user_broadcast", bind=True, max_retries=3)
def send_user_broadcast_task(self, broadcast_type: str, message: str) -> dict[str, int]:
    """Deliver an approved user broadcast outside the Telegram update handler."""
    try:
        return _run_async(_dispatch_user_broadcast(broadcast_type, message))
    except Exception as exc:
        logger.exception("Broadcast delivery failed")
        raise self.retry(exc=exc, countdown=30) from exc


@celery_app.task(name="send_vendor_application_review", bind=True, max_retries=5)
def send_vendor_application_review_task(self, vendor_id: int) -> bool:
    """Send the vendor application and license document to admins asynchronously."""
    try:
        return _run_async(_dispatch_vendor_application_review(vendor_id))
    except Exception as exc:
        logger.exception("Vendor application notification failed for vendor %s", vendor_id)
        raise self.retry(exc=exc, countdown=min(300, 15 * (2**self.request.retries))) from exc


async def _dispatch_vendor_application_review(vendor_id: int) -> bool:
    from telegram import Bot

    from apps.users.models import User, Vendor
    from bot.handlers.vendor_registration import notify_admins
    from core.config import settings
    from infrastructure.database.session import transaction_session

    async with transaction_session() as db:
        vendor = await db.get(Vendor, vendor_id)
        if vendor is None:
            raise LookupError(f"Vendor application {vendor_id} is not available")
        user = await db.get(User, vendor.user_id)
        if user is None:
            raise LookupError(f"Vendor applicant for application {vendor_id} is not available")
        applicant = user.full_name
        username = user.username
        telegram_id = user.telegram_id
        application = {
            "business_name": vendor.business_name,
            "business_license": vendor.business_license or "",
            "tin_number": vendor.tin_number or "",
            "license_document_type": vendor.license_document_type or "document",
            "license_document_file_id": vendor.license_document_file_id,
            "business_category": vendor.business_category or "",
            "business_address": vendor.business_address or "",
            "region": vendor.region or "",
            "city": vendor.city or "",
            "subcity": vendor.subcity or "",
            "specific_location": vendor.specific_location or "",
            "maps_link": vendor.maps_link,
            "business_phone": vendor.business_phone or "",
            "bank_name": vendor.bank_name or "",
            "bank_account_name": vendor.bank_account_name or "",
            "bank_account_number": vendor.bank_account_number or "",
        }
    async with Bot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
        delivered = await notify_admins(
            bot,
            vendor_id=vendor_id,
            applicant=applicant,
            telegram_username=username,
            telegram_id=telegram_id,
            application=application,
        )
    if not delivered:
        raise RuntimeError("No administrators received the vendor application")
    return True


async def _dispatch_user_broadcast(broadcast_type: str, message: str) -> dict[str, int]:
    """Resolve eligible users and send a rate-limited Telegram broadcast."""
    from datetime import datetime, timedelta

    from apps.users.services import UserService
    from infrastructure.database.session import get_db_session
    from infrastructure.notifications.telegram_notifier import TelegramNotifier

    users = []
    async for db in get_db_session():
        user_service = UserService(db)
        if broadcast_type == "all":
            users = await user_service.user_repo.get_all(filters={"is_active": True})
        elif broadcast_type == "active":
            users = await user_service.user_repo.get_active_users(limit=10000)
        elif broadcast_type == "new":
            cutoff = datetime.utcnow() - timedelta(days=30)
            users = await user_service.user_repo.get_all(filters={"created_at__gte": cutoff})
        elif broadcast_type == "vendors":
            users = await user_service.user_repo.get_all(
                filters={"role": "vendor", "is_active": True}
            )
        break

    telegram_ids = list(
        dict.fromkeys(user.telegram_id for user in users if getattr(user, "telegram_id", None))
    )
    result = await TelegramNotifier().broadcast_to_users(telegram_ids, message)
    logger.info(
        "User broadcast completed: type=%s sent=%s failed=%s",
        broadcast_type,
        result["success"],
        result["failed"],
    )
    return result


# ============================
# Payment Tasks
# ============================


@celery_app.task(name="process_payment", bind=True, max_retries=3)
def process_payment_task(
    self,
    order_id: int,
    payment_method: str,
    amount: float,
) -> dict[str, Any]:
    """
    Process payment asynchronously.

    Args:
        order_id: Order ID
        payment_method: Payment method
        amount: Payment amount

    Returns:
        Payment result
    """
    logger.info(f"Processing payment for order {order_id}: {amount} ETB via {payment_method}")

    try:
        # Process payment through gateway
        # Update payment status
        # Update order status

        return {
            "order_id": order_id,
            "success": True,
            "transaction_id": f"txn_{order_id}",
            "processed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Payment processing failed for order {order_id}: {e}")
        self.retry(exc=e, countdown=120)
        raise


@celery_app.task(name="verify_payment", bind=True, max_retries=3)
def verify_payment_task(self, transaction_id: str) -> dict[str, Any]:
    """
    Verify payment status.

    Args:
        transaction_id: Payment transaction ID

    Returns:
        Verification result
    """
    logger.info(f"Verifying payment {transaction_id}")

    try:
        # Call payment gateway to verify
        # Update payment status in database

        return {
            "transaction_id": transaction_id,
            "verified": True,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Payment verification failed: {e}")
        self.retry(exc=e, countdown=60)
        raise


# ============================
# Analytics Tasks
# ============================


@celery_app.task(name="update_analytics", bind=True)
def update_analytics_task(self) -> bool:
    """
    Update analytics data.
    """
    logger.info("Updating analytics data")

    try:
        # Aggregate sales data
        # Update user activity metrics
        # Update product performance metrics

        return True

    except Exception as e:
        logger.error(f"Failed to update analytics: {e}")
        return False


@celery_app.task(name="generate_report", bind=True)
def generate_report_task(
    self,
    report_type: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """
    Generate report asynchronously.

    Args:
        report_type: Type of report (sales, users, products)
        start_date: Start date
        end_date: End date

    Returns:
        Report data
    """
    logger.info(f"Generating {report_type} report from {start_date} to {end_date}")

    try:
        # Generate report based on type
        # Store report in database or file

        return {
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        return {
            "report_type": report_type,
            "status": "failed",
            "error": str(e),
        }


# ============================
# Inventory Tasks
# ============================


@celery_app.task(name="update_inventory", bind=True)
def update_inventory_task(self, product_id: int, quantity_change: int) -> bool:
    """
    Update inventory asynchronously.

    Args:
        product_id: Product ID
        quantity_change: Change in quantity (positive or negative)

    Returns:
        True if updated successfully
    """
    logger.info(f"Updating inventory for product {product_id}: {quantity_change}")

    try:
        # Update inventory in database
        # Check low stock alert

        return True

    except Exception as e:
        logger.error(f"Failed to update inventory: {e}")
        return False


@celery_app.task(name="check_low_stock", bind=True)
def check_low_stock_task(self) -> dict[str, Any]:
    """
    Check for low stock products and send alerts.

    Returns:
        Alert results
    """
    logger.info("Checking low stock products")

    try:
        # Find products below threshold
        # Send notifications to vendors

        return {
            "checked_at": datetime.utcnow().isoformat(),
            "low_stock_count": 0,
            "alerts_sent": 0,
        }

    except Exception as e:
        logger.error(f"Low stock check failed: {e}")
        return {
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat(),
        }


# ============================
# Maintenance Tasks
# ============================


@celery_app.task(name="cleanup_expired_reservations")
def cleanup_expired_reservations_task(self) -> int:
    """
    Clean up expired stock reservations.

    Returns:
        Number of cleaned reservations
    """
    logger.info("Cleaning up expired reservations")

    try:
        # Find and expire old reservations
        # Release reserved stock

        return 0

    except Exception as e:
        logger.error(f"Failed to clean up reservations: {e}")
        return 0


@celery_app.task(name="backup_database")
def backup_database_task(self) -> bool:
    """
    Create database backup.

    Returns:
        True if backup successful
    """
    logger.info("Creating database backup")

    try:
        # Run pg_dump or similar
        # Upload to backup storage

        return True

    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        return False


@celery_app.task(name="send_health_report")
def send_health_report_task(self) -> bool:
    """
    Send system health report to admins.

    Returns:
        True if sent successfully
    """
    logger.info("Sending health report")

    try:
        # Collect system metrics
        # Format report
        # Send to admins

        return True

    except Exception as e:
        logger.error(f"Failed to send health report: {e}")
        return False


__all__ = [
    "backup_database_task",
    "check_low_stock_task",
    "cleanup_expired_reservations_task",
    "generate_report_task",
    "process_order_task",
    "process_payment_task",
    "send_email_task",
    "send_health_report_task",
    "send_order_confirmation_task",
    "send_sms_task",
    "send_telegram_task",
    "update_analytics_task",
    "update_inventory_task",
    "update_order_status_task",
    "verify_payment_task",
]
