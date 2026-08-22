# ============================
# WOLLOYEWA STORE BOT - NOTIFICATIONS MODULE
# ============================
"""Multi-channel notification system for emails, SMS, and Telegram."""

from infrastructure.notifications.base import (
    NotificationError,
    NotificationPriority,
    NotificationProvider,
    NotificationRequest,
    NotificationResponse,
    NotificationType,
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
    send_order_update_sms,
    send_sms,
    send_verification_code,
)
from infrastructure.notifications.telegram_notifier import (
    TelegramNotifier,
    notify_vendor,
    send_order_notification,
    send_telegram_message,
    send_to_admin,
)

__all__ = [
    # Email
    "EmailService",
    "NotificationError",
    "NotificationPriority",
    # Base
    "NotificationProvider",
    "NotificationRequest",
    "NotificationResponse",
    "NotificationType",
    # SMS
    "SMSGateway",
    # Telegram
    "TelegramNotifier",
    "notify_vendor",
    "send_email",
    "send_order_confirmation_email",
    "send_order_notification",
    "send_order_update_sms",
    "send_password_reset_email",
    "send_sms",
    "send_telegram_message",
    "send_to_admin",
    "send_verification_code",
    "send_welcome_email",
]
