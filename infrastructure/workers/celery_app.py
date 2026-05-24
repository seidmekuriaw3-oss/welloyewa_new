# ============================
# WOLLOYEWA STORE BOT - CELERY APP
# ============================
"""Celery application configuration for background task processing."""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

from core.config import settings
from core.logger import logger


def create_celery_app() -> Celery:
    """
    Create and configure Celery application.
    
    Returns:
        Configured Celery app instance
    """
    # Create Celery app
    app = Celery(
        "wolloyewa",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=[
            "infrastructure.workers.tasks",
        ],
    )
    
    # Configure Celery
    app.conf.update(
        # Task settings
        task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
        task_eager_propagates=True,
        task_ignore_result=False,
        task_store_errors_even_if_ignored=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        
        # Result settings
        result_expires=3600,  # 1 hour
        result_backend_transport_options={
            "visibility_timeout": 3600,
        },
        
        # Worker settings
        worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=200,
        worker_max_memory_per_child=200 * 1024 * 1024,  # 200 MB
        
        # Task queues
        task_queues=(
            Queue("default", Exchange("default"), routing_key="default"),
            Queue("high_priority", Exchange("high_priority"), routing_key="high_priority"),
            Queue("low_priority", Exchange("low_priority"), routing_key="low_priority"),
            Queue("email", Exchange("email"), routing_key="email"),
            Queue("sms", Exchange("sms"), routing_key="sms"),
            Queue("payment", Exchange("payment"), routing_key="payment"),
            Queue("analytics", Exchange("analytics"), routing_key="analytics"),
            Queue("maintenance", Exchange("maintenance"), routing_key="maintenance"),
        ),
        
        # Task routes
        task_routes={
            "infrastructure.workers.tasks.send_email_task": {"queue": "email"},
            "infrastructure.workers.tasks.send_sms_task": {"queue": "sms"},
            "infrastructure.workers.tasks.process_payment_task": {"queue": "payment"},
            "infrastructure.workers.tasks.update_analytics_task": {"queue": "analytics"},
            "infrastructure.workers.tasks.cleanup_expired_reservations_task": {"queue": "maintenance"},
            "infrastructure.workers.tasks.backup_database_task": {"queue": "maintenance"},
        },
        
        # Task rate limits
        task_annotations={
            "infrastructure.workers.tasks.send_email_task": {"rate_limit": "10/m"},
            "infrastructure.workers.tasks.send_sms_task": {"rate_limit": "5/m"},
        },
        
        # Beat schedule (will be defined in beat_schedule.py)
        beat_schedule={},
        
        # Timezone
        timezone=settings.TIMEZONE,
        enable_utc=True,
        
        # Error handling
        task_reject_on_worker_lost=True,
        task_acks_late=True,
        task_default_priority=5,
        task_queue_max_priority=10,
        
        # Logging
        worker_redirect_stdouts=False,
        worker_hijack_root_logger=False,
        
        # Security
        task_protocol=2,
    )
    
    # Set up custom error handling
    @app.task(bind=True, max_retries=3)
    def debug_task(self):
        """Debug task for testing."""
        logger.debug(f"Request: {self.request!r}")
    
    logger.info("Celery app configured successfully")
    return app


# Create global Celery app instance
celery_app = create_celery_app()


def get_celery_app() -> Celery:
    """Get the Celery app instance."""
    return celery_app


__all__ = [
    "celery_app",
    "create_celery_app",
    "get_celery_app",
]