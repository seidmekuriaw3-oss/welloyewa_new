# ============================
# WOLLOYEWA STORE BOT - QUEUES MODULE
# ============================
"""Message queue systems for task processing and event handling."""

from infrastructure.queues.priority_queue import (
    PriorityQueue,
    PriorityLevel,
    QueueItem,
    get_queue,
    add_to_queue,
    process_queue,
)
from infrastructure.queues.dead_letter_handler import (
    DeadLetterHandler,
    DeadLetterEntry,
    move_to_dead_letter,
    retry_dead_letter,
    get_dead_letter_stats,
)
from infrastructure.queues.scheduled_tasks import (
    ScheduledTaskManager,
    ScheduledTask,
    schedule_task,
    cancel_scheduled_task,
    process_scheduled_tasks,
)
from infrastructure.queues.batch_processor import (
    BatchProcessor,
    BatchJob,
    BatchStatus,
    create_batch_job,
    process_batch,
    get_batch_status,
)
from infrastructure.queues.task_deduplicator import (
    TaskDeduplicator,
    deduplicate_task,
    is_task_duplicate,
    clear_task_records,
)

__all__ = [
    # Priority Queue
    "PriorityQueue",
    "PriorityLevel",
    "QueueItem",
    "get_queue",
    "add_to_queue",
    "process_queue",
    # Dead Letter
    "DeadLetterHandler",
    "DeadLetterEntry",
    "move_to_dead_letter",
    "retry_dead_letter",
    "get_dead_letter_stats",
    # Scheduled Tasks
    "ScheduledTaskManager",
    "ScheduledTask",
    "schedule_task",
    "cancel_scheduled_task",
    "process_scheduled_tasks",
    # Batch Processor
    "BatchProcessor",
    "BatchJob",
    "BatchStatus",
    "create_batch_job",
    "process_batch",
    "get_batch_status",
    # Deduplicator
    "TaskDeduplicator",
    "deduplicate_task",
    "is_task_duplicate",
    "clear_task_records",
]