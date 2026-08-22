# ============================
# WOLLOYEWA STORE BOT - WORKERS MODULE
# ============================
"""Celery workers for background task processing."""

from infrastructure.workers.beat_schedule import (
    beat_schedule,
    setup_periodic_tasks,
)
from infrastructure.workers.celery_app import (
    celery_app,
    create_celery_app,
    get_celery_app,
)
from infrastructure.workers.tasks import (
    backup_database_task,
    check_low_stock_task,
    # Maintenance tasks
    cleanup_expired_reservations_task,
    generate_report_task,
    # Order tasks
    process_order_task,
    # Payment tasks
    process_payment_task,
    # Notification tasks
    send_email_task,
    send_health_report_task,
    send_order_confirmation_task,
    send_sms_task,
    send_telegram_task,
    # Analytics tasks
    update_analytics_task,
    # Inventory tasks
    update_inventory_task,
    update_order_status_task,
    verify_payment_task,
)

__all__ = [
    "backup_database_task",
    # Beat schedule
    "beat_schedule",
    # Celery app
    "celery_app",
    "check_low_stock_task",
    # Maintenance tasks
    "cleanup_expired_reservations_task",
    "create_celery_app",
    "generate_report_task",
    "get_celery_app",
    # Order tasks
    "process_order_task",
    # Payment tasks
    "process_payment_task",
    # Notification tasks
    "send_email_task",
    "send_health_report_task",
    "send_order_confirmation_task",
    "send_sms_task",
    "send_telegram_task",
    "setup_periodic_tasks",
    # Analytics tasks
    "update_analytics_task",
    # Inventory tasks
    "update_inventory_task",
    "update_order_status_task",
    "verify_payment_task",
]
