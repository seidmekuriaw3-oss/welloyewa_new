# ============================
# WOLLOYEWA STORE BOT - QUEUES MODULE
# ============================
"""Message queue systems for task processing and event handling."""

from infrastructure.queues.batch_processor import (
    BatchJob,
    BatchProcessor,
    BatchStatus,
    create_batch_job,
    get_batch_status,
    process_batch,
)
from infrastructure.queues.dead_letter_handler import (
    DeadLetterEntry,
    DeadLetterHandler,
    get_dead_letter_stats,
    move_to_dead_letter,
    retry_dead_letter,
)
from infrastructure.queues.priority_queue import (
    PriorityLevel,
    PriorityQueue,
    QueueItem,
    add_to_queue,
    get_queue,
    process_queue,
)
from infrastructure.queues.scheduled_tasks import (
    ScheduledTask,
    ScheduledTaskManager,
    cancel_scheduled_task,
    process_scheduled_tasks,
    schedule_task,
)
from infrastructure.queues.task_deduplicator import (
    TaskDeduplicator,
    clear_task_records,
    deduplicate_task,
    is_task_duplicate,
)

__all__ = [
    "BatchJob",
    # Batch Processor
    "BatchProcessor",
    "BatchStatus",
    "DeadLetterEntry",
    # Dead Letter
    "DeadLetterHandler",
    "PriorityLevel",
    # Priority Queue
    "PriorityQueue",
    "QueueItem",
    "ScheduledTask",
    # Scheduled Tasks
    "ScheduledTaskManager",
    # Deduplicator
    "TaskDeduplicator",
    "add_to_queue",
    "cancel_scheduled_task",
    "clear_task_records",
    "create_batch_job",
    "deduplicate_task",
    "get_batch_status",
    "get_dead_letter_stats",
    "get_queue",
    "is_task_duplicate",
    "move_to_dead_letter",
    "process_batch",
    "process_queue",
    "process_scheduled_tasks",
    "retry_dead_letter",
    "schedule_task",
]
