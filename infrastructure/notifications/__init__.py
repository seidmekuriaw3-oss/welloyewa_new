# ============================
# WOLLOYEWA STORE BOT - NOTIFICATIONS MODULE
# ============================
"""Multi-channel notification system for emails, SMS, and Telegram."""

from infrastructure.notifications.base import (
    NotificationProvider,
    NotificationRequest,
    NotificationResponse,
    NotificationType,
    NotificationPriority,
    NotificationError,
)
from infrastructure.notifications.email_service import (
    EmailService,
    send_email,
    send_order_confirmation_email,
    send_password_reset_email,
    send_welcome_email,
)
from infrastructure.notifications.sms_gateway import (
    SMSGateway,
    send_sms,
    send_verification_code,
    send_order_update_sms,
)
from infrastructure.notifications.telegram_notifier import (
    TelegramNotifier,
    send_telegram_message,
    send_to_admin,
    send_order_notification,
    notify_vendor,
)

__all__ = [
    # Base
    "NotificationProvider",
    "NotificationRequest",
    "NotificationResponse",
    "NotificationType",
    "NotificationPriority",
    "NotificationError",
    # Email
    "EmailService",
    "send_email",
    "send_order_confirmation_email",
    "send_password_reset_email",
    "send_welcome_email",
    # SMS
    "SMSGateway",
    "send_sms",
    "send_verification_code",
    "send_order_update_sms",
    # Telegram
    "TelegramNotifier",
    "send_telegram_message",
    "send_to_admin",
    "send_order_notification",
    "notify_vendor",
]