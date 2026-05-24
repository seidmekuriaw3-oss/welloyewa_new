# ============================
# WOLLOYEWA STORE BOT - SCHEDULED TASKS
# ============================
"""Scheduled task management for future execution."""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from infrastructure.redis.client import get_redis_client
from core.logger import logger


class TaskStatus(str, Enum):
    """Status of scheduled task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """Scheduled task definition."""
    
    task_id: str
    task_name: str
    data: Dict[str, Any]
    scheduled_time: datetime
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    error: Optional[str] = None
    recurrence: Optional[str] = None  # cron expression or interval
    max_retries: int = 3
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "data": self.data,
            "scheduled_time": self.scheduled_time.isoformat(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "error": self.error,
            "recurrence": self.recurrence,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            task_name=data["task_name"],
            data=data["data"],
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]),
            status=TaskStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            executed_at=datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else None,
            error=data.get("error"),
            recurrence=data.get("recurrence"),
            max_retries=data.get("max_retries", 3),
            retry_count=data.get("retry_count", 0),
        )


class ScheduledTaskManager:
    """
    Manager for scheduled tasks.
    
    Features:
    - Schedule tasks for future execution
    - Recurring tasks (cron-style)
    - Task status tracking
    - Automatic retry on failure
    """
    
    def __init__(self):
        self._redis = None
        self._handlers: Dict[str, Callable] = {}
        self._running = False
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    def register_handler(self, task_name: str, handler: Callable) -> None:
        """
        Register a handler for a task.
        
        Args:
            task_name: Task name
            handler: Async function to handle the task
        """
        self._handlers[task_name] = handler
        logger.info(f"Registered handler for task: {task_name}")
    
    async def schedule(
        self,
        task_name: str,
        data: Dict[str, Any],
        run_at: datetime,
        recurrence: Optional[str] = None,
        max_retries: int = 3,
    ) -> str:
        """
        Schedule a task for future execution.
        
        Args:
            task_name: Task name
            data: Task data
            run_at: When to run the task
            recurrence: Recurrence pattern (cron or interval)
            max_retries: Maximum retry attempts
            
        Returns:
            Task ID
        """
        import uuid
        redis = await self._get_redis()
        
        task_id = str(uuid.uuid4())
        task = ScheduledTask(
            task_id=task_id,
            task_name=task_name,
            data=data,
            scheduled_time=run_at,
            recurrence=recurrence,
            max_retries=max_retries,
        )
        
        # Add to sorted set with timestamp as score
        score = run_at.timestamp()
        await redis.zadd("scheduled_tasks", {task.to_dict(): score})
        
        logger.info(f"Scheduled task {task_id} for {run_at.isoformat()}")
        return task_id
    
    async def schedule_delay(
        self,
        task_name: str,
        data: Dict[str, Any],
        delay_seconds: int,
    ) -> str:
        """
        Schedule a task after a delay.
        
        Args:
            task_name: Task name
            data: Task data
            delay_seconds: Delay in seconds
            
        Returns:
            Task ID
        """
        run_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        return await self.schedule(task_name, data, run_at)
    
    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a scheduled task.
        
        Args:
            task_id: Task ID
            
        Returns:
            True if cancelled
        """
        redis = await self._get_redis()
        
        # Find and remove the task
        tasks = await redis.zrange("scheduled_tasks", 0, -1)
        for task_dict in tasks:
            task = ScheduledTask.from_dict(json.loads(task_dict))
            if task.task_id == task_id:
                await redis.zrem("scheduled_tasks", task_dict)
                logger.info(f"Cancelled scheduled task {task_id}")
                return True
        
        return False
    
    async def get_pending_tasks(self, limit: int = 100) -> List[ScheduledTask]:
        """
        Get pending scheduled tasks.
        
        Args:
            limit: Maximum number of tasks
            
        Returns:
            List of pending tasks
        """
        redis = await self._get_redis()
        
        now = datetime.utcnow().timestamp()
        tasks_json = await redis.zrangebyscore("scheduled_tasks", 0, now, limit=limit)
        
        return [ScheduledTask.from_dict(json.loads(t)) for t in tasks_json]
    
    async def process_due_tasks(self) -> int:
        """
        Process all tasks that are due for execution.
        
        Returns:
            Number of tasks processed
        """
        redis = await self._get_redis()
        processed = 0
        
        due_tasks = await self.get_pending_tasks()
        
        for task in due_tasks:
            # Remove from queue
            await redis.zrem("scheduled_tasks", task.to_dict())
            
            # Process task
            success = await self._execute_task(task)
            
            if success:
                processed += 1
            
            # Handle recurrence
            if task.recurrence and success:
                next_run = self._calculate_next_run(task)
                if next_run:
                    await self.schedule(
                        task.task_name,
                        task.data,
                        next_run,
                        recurrence=task.recurrence,
                        max_retries=task.max_retries,
                    )
        
        return processed
    
    async def _execute_task(self, task: ScheduledTask) -> bool:
        """
        Execute a scheduled task.
        
        Args:
            task: Task to execute
            
        Returns:
            True if successful
        """
        handler = self._handlers.get(task.task_name)
        
        if not handler:
            logger.error(f"No handler registered for task: {task.task_name}")
            return False
        
        try:
            task.status = TaskStatus.PROCESSING
            await handler(task.data)
            task.status = TaskStatus.COMPLETED
            task.executed_at = datetime.utcnow()
            
            logger.info(f"Executed scheduled task {task.task_id}: {task.task_name}")
            return True
            
        except Exception as e:
            task.retry_count += 1
            task.error = str(e)
            
            if task.retry_count < task.max_retries:
                # Retry with backoff
                backoff_seconds = 2 ** task.retry_count
                retry_time = datetime.utcnow() + timedelta(seconds=backoff_seconds)
                await self.schedule(
                    task.task_name,
                    task.data,
                    retry_time,
                    recurrence=task.recurrence,
                    max_retries=task.max_retries,
                )
                logger.warning(f"Task {task.task_id} failed, retry {task.retry_count}/{task.max_retries}")
            else:
                task.status = TaskStatus.FAILED
                logger.error(f"Task {task.task_id} failed permanently: {e}")
            
            return False
    
    def _calculate_next_run(self, task: ScheduledTask) -> Optional[datetime]:
        """
        Calculate next run time for recurring task.
        
        Args:
            task: Task with recurrence pattern
            
        Returns:
            Next run datetime or None
        """
        if not task.recurrence:
            return None
        
        # Simple interval-based recurrence
        if task.recurrence.startswith("interval:"):
            seconds = int(task.recurrence.split(":")[1])
            return datetime.utcnow() + timedelta(seconds=seconds)
        
        # Cron-based recurrence would go here
        # For production, use a library like croniter
        
        return None
    
    async def start_processor(self, interval_seconds: int = 10):
        """
        Start the background task processor.
        
        Args:
            interval_seconds: How often to check for due tasks
        """
        self._running = True
        
        while self._running:
            try:
                processed = await self.process_due_tasks()
                if processed > 0:
                    logger.debug(f"Processed {processed} scheduled tasks")
            except Exception as e:
                logger.error(f"Error processing scheduled tasks: {e}")
            
            await asyncio.sleep(interval_seconds)
    
    async def stop_processor(self):
        """Stop the background task processor."""
        self._running = False
        logger.info("Scheduled task processor stopped")


# Global manager
scheduled_task_manager = ScheduledTaskManager()


async def schedule_task(
    task_name: str,
    data: Dict[str, Any],
    run_at: datetime,
    recurrence: Optional[str] = None,
) -> str:
    """Schedule a task."""
    return await scheduled_task_manager.schedule(task_name, data, run_at, recurrence)


async def cancel_scheduled_task(task_id: str) -> bool:
    """Cancel a scheduled task."""
    return await scheduled_task_manager.cancel(task_id)


async def process_scheduled_tasks() -> int:
    """Process due scheduled tasks."""
    return await scheduled_task_manager.process_due_tasks()


__all__ = [
    "ScheduledTaskManager",
    "ScheduledTask",
    "TaskStatus",
    "scheduled_task_manager",
    "schedule_task",
    "cancel_scheduled_task",
    "process_scheduled_tasks",
]