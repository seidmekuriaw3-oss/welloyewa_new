# ============================
# WOLLOYEWA STORE BOT - WORKERS MODULE
# ============================
"""Celery workers for background task processing."""

from infrastructure.workers.celery_app import (
    celery_app,
    create_celery_app,
    get_celery_app,
)
from infrastructure.workers.tasks import (
    # Order tasks
    process_order_task,
    send_order_confirmation_task,
    update_order_status_task,
    # Notification tasks
    send_email_task,
    send_sms_task,
    send_telegram_task,
    # Payment tasks
    process_payment_task,
    verify_payment_task,
    # Analytics tasks
    update_analytics_task,
    generate_report_task,
    # Inventory tasks
    update_inventory_task,
    check_low_stock_task,
    # Maintenance tasks
    cleanup_expired_reservations_task,
    backup_database_task,
    send_health_report_task,
)
from infrastructure.workers.beat_schedule import (
    beat_schedule,
    setup_periodic_tasks,
)

__all__ = [
    # Celery app
    "celery_app",
    "create_celery_app",
    "get_celery_app",
    # Order tasks
    "process_order_task",
    "send_order_confirmation_task",
    "update_order_status_task",
    # Notification tasks
    "send_email_task",
    "send_sms_task",
    "send_telegram_task",
    # Payment tasks
    "process_payment_task",
    "verify_payment_task",
    # Analytics tasks
    "update_analytics_task",
    "generate_report_task",
    # Inventory tasks
    "update_inventory_task",
    "check_low_stock_task",
    # Maintenance tasks
    "cleanup_expired_reservations_task",
    "backup_database_task",
    "send_health_report_task",
    # Beat schedule
    "beat_schedule",
    "setup_periodic_tasks",
]