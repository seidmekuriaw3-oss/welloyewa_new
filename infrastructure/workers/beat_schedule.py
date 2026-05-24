# ============================
# WOLLOYEWA STORE BOT - CELERY BEAT SCHEDULE
# ============================
"""Periodic task schedule for Celery Beat."""

from celery.schedules import crontab
from datetime import timedelta

# Beat schedule configuration
beat_schedule = {
    # Analytics tasks
    "update-analytics-hourly": {
        "task": "update_analytics",
        "schedule": crontab(minute=0),  # Every hour at minute 0
        "options": {"queue": "analytics"},
    },
    "generate-daily-report": {
        "task": "generate_report",
        "schedule": crontab(minute=0, hour=1),  # Daily at 1:00 AM
        "args": ("daily_sales",),
        "options": {"queue": "analytics"},
    },
    "generate-weekly-report": {
        "task": "generate_report",
        "schedule": crontab(minute=0, hour=2, day_of_week=1),  # Monday at 2:00 AM
        "args": ("weekly_sales",),
        "options": {"queue": "analytics"},
    },
    "generate-monthly-report": {
        "task": "generate_report",
        "schedule": crontab(minute=0, hour=3, day_of_month=1),  # 1st day of month at 3:00 AM
        "args": ("monthly_sales",),
        "options": {"queue": "analytics"},
    },
    
    # Inventory tasks
    "check-low-stock": {
        "task": "check_low_stock",
        "schedule": crontab(minute=0, hour=9, day_of_week="mon,wed,fri"),  # MWF at 9:00 AM
        "options": {"queue": "maintenance"},
    },
    "update-inventory-sync": {
        "task": "update_inventory",
        "schedule": crontab(minute=30, hour=2),  # Daily at 2:30 AM
        "options": {"queue": "maintenance"},
    },
    
    # Maintenance tasks
    "cleanup-expired-reservations": {
        "task": "cleanup_expired_reservations",
        "schedule": timedelta(minutes=30),  # Every 30 minutes
        "options": {"queue": "maintenance"},
    },
    "backup-database-daily": {
        "task": "backup_database",
        "schedule": crontab(minute=0, hour=0),  # Daily at midnight
        "options": {"queue": "maintenance"},
    },
    "cleanup-old-sessions": {
        "task": "cleanup_old_sessions",
        "schedule": crontab(minute=0, hour=4),  # Daily at 4:00 AM
        "options": {"queue": "maintenance"},
    },
    "cleanup-old-audit-logs": {
        "task": "cleanup_old_audit_logs",
        "schedule": crontab(minute=0, hour=5, day_of_month=1),  # Monthly on 1st day
        "options": {"queue": "maintenance"},
    },
    
    # Health checks
    "send-health-report": {
        "task": "send_health_report",
        "schedule": crontab(minute=0, hour=8, day_of_week="mon"),  # Monday at 8:00 AM
        "options": {"queue": "maintenance"},
    },
    
    # Payment tasks
    "verify-pending-payments": {
        "task": "verify_pending_payments",
        "schedule": timedelta(minutes=15),  # Every 15 minutes
        "options": {"queue": "payment"},
    },
    "process-recurring-payments": {
        "task": "process_recurring_payments",
        "schedule": crontab(minute=0, hour=6),  # Daily at 6:00 AM
        "options": {"queue": "payment"},
    },
    
    # Email tasks
    "send-pending-newsletters": {
        "task": "send_pending_newsletters",
        "schedule": crontab(minute=0, hour=10),  # Daily at 10:00 AM
        "options": {"queue": "email"},
    },
    
    # Cart cleanup
    "cleanup-abandoned-carts": {
        "task": "cleanup_abandoned_carts",
        "schedule": timedelta(hours=1),  # Every hour
        "options": {"queue": "maintenance"},
    },
    "send-cart-reminders": {
        "task": "send_cart_reminders",
        "schedule": crontab(minute=0, hour=18),  # Daily at 6:00 PM
        "options": {"queue": "email"},
    },
}


def setup_periodic_tasks(app):
    """
    Set up periodic tasks for the Celery app.
    
    Args:
        app: Celery app instance
    """
    app.conf.beat_schedule = beat_schedule
    logger.info("Periodic tasks configured")
    
    # Optional: Add dynamic tasks from database
    # This could be extended to support admin-configurable schedules


__all__ = [
    "beat_schedule",
    "setup_periodic_tasks",
]