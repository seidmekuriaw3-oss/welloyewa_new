# ============================
# WOLLOYEWA STORE BOT - DEAD LETTER HANDLER
# ============================
"""Dead letter queue handling for failed tasks."""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from infrastructure.redis.client import get_redis_client
from core.logger import logger


@dataclass
class DeadLetterEntry:
    """Entry in dead letter queue."""
    
    item_id: str
    task: str
    data: Dict[str, Any]
    error: str
    failed_at: datetime
    retry_count: int
    queue_name: str
    original_priority: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "item_id": self.item_id,
            "task": self.task,
            "data": self.data,
            "error": self.error,
            "failed_at": self.failed_at.isoformat(),
            "retry_count": self.retry_count,
            "queue_name": self.queue_name,
            "original_priority": self.original_priority,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeadLetterEntry":
        """Create from dictionary."""
        return cls(
            item_id=data["item_id"],
            task=data["task"],
            data=data["data"],
            error=data["error"],
            failed_at=datetime.fromisoformat(data["failed_at"]),
            retry_count=data["retry_count"],
            queue_name=data["queue_name"],
            original_priority=data["original_priority"],
        )


class DeadLetterHandler:
    """
    Handler for dead letter queue.
    
    Features:
    - Store failed tasks
    - Manual retry capability
    - Analytics on failed tasks
    - Automatic cleanup
    """
    
    def __init__(self):
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def add(
        self,
        item_id: str,
        task: str,
        data: Dict[str, Any],
        error: str,
        queue_name: str,
        original_priority: int,
        retry_count: int,
    ) -> None:
        """
        Add an item to dead letter queue.
        
        Args:
            item_id: Original item ID
            task: Task name
            data: Task data
            error: Error message
            queue_name: Original queue name
            original_priority: Original priority
            retry_count: Number of retry attempts
        """
        redis = await self._get_redis()
        
        entry = DeadLetterEntry(
            item_id=item_id,
            task=task,
            data=data,
            error=error,
            failed_at=datetime.utcnow(),
            retry_count=retry_count,
            queue_name=queue_name,
            original_priority=original_priority,
        )
        
        key = f"dead_letter:{queue_name}"
        await redis.lpush(key, json.dumps(entry.to_dict()))
        await redis.ltrim(key, 0, 999)  # Keep last 1000 entries
        
        # Add to index for analytics
        await redis.zincrby("dead_letter:stats", 1, task)
        
        logger.warning(f"Added item {item_id} to dead letter queue: {error}")
    
    async def get_all(
        self,
        queue_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[DeadLetterEntry]:
        """
        Get all dead letter entries.
        
        Args:
            queue_name: Filter by queue name
            limit: Maximum number of entries
            
        Returns:
            List of dead letter entries
        """
        redis = await self._get_redis()
        
        if queue_name:
            key = f"dead_letter:{queue_name}"
        else:
            # Get from all queues
            keys = await redis.keys("dead_letter:*")
            entries = []
            for key in keys:
                queue_entries = await redis.lrange(key, 0, limit - 1)
                for entry_json in queue_entries:
                    entries.append(DeadLetterEntry.from_dict(json.loads(entry_json)))
            return entries[:limit]
        
        entries_json = await redis.lrange(key, 0, limit - 1)
        return [DeadLetterEntry.from_dict(json.loads(e)) for e in entries_json]
    
    async def retry(
        self,
        item_id: str,
        queue_name: str,
    ) -> bool:
        """
        Retry a failed task from dead letter.
        
        Args:
            item_id: Item ID to retry
            queue_name: Original queue name
            
        Returns:
            True if retried successfully
        """
        redis = await self._get_redis()
        key = f"dead_letter:{queue_name}"
        
        # Find the entry
        entries = await redis.lrange(key, 0, -1)
        for idx, entry_json in enumerate(entries):
            entry = DeadLetterEntry.from_dict(json.loads(entry_json))
            if entry.item_id == item_id:
                # Remove from dead letter
                await redis.lset(key, idx, "__DELETED__")
                await redis.lrem(key, 1, "__DELETED__")
                
                # Re-add to original queue
                from infrastructure.queues.priority_queue import get_queue
                from infrastructure.queues.priority_queue import PriorityLevel
                
                q = get_queue(queue_name)
                await q.add(
                    task=entry.task,
                    data=entry.data,
                    priority=PriorityLevel(entry.original_priority),
                    item_id=item_id,
                    max_retries=entry.retry_count,
                )
                
                logger.info(f"Retried item {item_id} from dead letter queue")
                return True
        
        return False
    
    async def retry_all(self, queue_name: str) -> int:
        """
        Retry all failed tasks in a dead letter queue.
        
        Args:
            queue_name: Queue name
            
        Returns:
            Number of retried tasks
        """
        entries = await self.get_all(queue_name)
        retried = 0
        
        for entry in entries:
            if await self.retry(entry.item_id, queue_name):
                retried += 1
        
        return retried
    
    async def clear(self, queue_name: str, older_than_days: int = 30) -> int:
        """
        Clear old dead letter entries.
        
        Args:
            queue_name: Queue name
            older_than_days: Clear entries older than this many days
            
        Returns:
            Number of cleared entries
        """
        redis = await self._get_redis()
        key = f"dead_letter:{queue_name}"
        
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        
        entries = await redis.lrange(key, 0, -1)
        cleared = 0
        
        for entry_json in entries:
            entry = DeadLetterEntry.from_dict(json.loads(entry_json))
            if entry.failed_at < cutoff:
                await redis.lrem(key, 1, entry_json)
                cleared += 1
        
        return cleared
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about dead letter queues.
        
        Returns:
            Statistics dictionary
        """
        redis = await self._get_redis()
        
        # Get task failure counts
        stats = await redis.zrevrange("dead_letter:stats", 0, 9, withscores=True)
        
        # Get queue sizes
        keys = await redis.keys("dead_letter:*")
        queue_sizes = {}
        for key in keys:
            size = await redis.llen(key)
            queue_name = key.replace("dead_letter:", "")
            queue_sizes[queue_name] = size
        
        return {
            "total_dead_letters": sum(queue_sizes.values()),
            "queue_sizes": queue_sizes,
            "top_failed_tasks": [
                {"task": task.decode(), "failures": int(score)}
                for task, score in stats
            ],
        }


# Global dead letter handler
dead_letter_handler = DeadLetterHandler()


async def move_to_dead_letter(
    item_id: str,
    task: str,
    data: Dict[str, Any],
    error: str,
    queue_name: str,
    original_priority: int,
    retry_count: int,
) -> None:
    """Move a failed task to dead letter queue."""
    await dead_letter_handler.add(
        item_id=item_id,
        task=task,
        data=data,
        error=error,
        queue_name=queue_name,
        original_priority=original_priority,
        retry_count=retry_count,
    )


async def retry_dead_letter(item_id: str, queue_name: str) -> bool:
    """Retry a dead letter task."""
    return await dead_letter_handler.retry(item_id, queue_name)


async def get_dead_letter_stats() -> Dict[str, Any]:
    """Get dead letter statistics."""
    return await dead_letter_handler.get_stats()


__all__ = [
    "DeadLetterHandler",
    "DeadLetterEntry",
    "dead_letter_handler",
    "move_to_dead_letter",
    "retry_dead_letter",
    "get_dead_letter_stats",
]