# ============================
# WOLLOYEWA STORE BOT - PRIORITY QUEUE
# ============================
"""Priority queue implementation for task processing with different priority levels."""

import json
import asyncio
from enum import IntEnum
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

from infrastructure.redis.client import get_redis_client
from core.logger import logger


class PriorityLevel(IntEnum):
    """Priority levels for queue items."""
    
    CRITICAL = 0  # Highest priority
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4  # Lowest priority


@dataclass
class QueueItem:
    """Item in the priority queue."""
    
    id: str
    task: str
    data: Dict[str, Any]
    priority: PriorityLevel
    created_at: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 3
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            "id": self.id,
            "task": self.task,
            "data": self.data,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "QueueItem":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls(
            id=data["id"],
            task=data["task"],
            data=data["data"],
            priority=PriorityLevel(data["priority"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )


class PriorityQueue:
    """
    Priority queue using Redis sorted sets.
    
    Features:
    - Multiple priority levels
    - Item deduplication
    - Retry mechanism
    - Queue monitoring
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._redis = None
        self._key = f"queue:{name}"
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def add(
        self,
        task: str,
        data: Dict[str, Any],
        priority: PriorityLevel = PriorityLevel.NORMAL,
        item_id: Optional[str] = None,
        max_retries: int = 3,
    ) -> str:
        """
        Add an item to the queue.
        
        Args:
            task: Task name/identifier
            data: Task data
            priority: Priority level
            item_id: Optional custom ID (for deduplication)
            max_retries: Maximum retry attempts
            
        Returns:
            Item ID
        """
        import uuid
        redis = await self._get_redis()
        
        item_id = item_id or str(uuid.uuid4())
        
        # Check if item already exists (deduplication)
        if await redis.hexists(f"{self._key}:ids", item_id):
            logger.debug(f"Item {item_id} already in queue, skipping")
            return item_id
        
        item = QueueItem(
            id=item_id,
            task=task,
            data=data,
            priority=priority,
            max_retries=max_retries,
        )
        
        # Add to sorted set with priority score
        # Lower score = higher priority
        score = priority.value * 1_000_000 + int(datetime.utcnow().timestamp())
        
        await redis.zadd(self._key, {item.to_json(): score})
        await redis.hset(f"{self._key}:ids", item_id, item.to_json())
        
        logger.debug(f"Added item {item_id} to queue {self.name} with priority {priority.name}")
        return item_id
    
    async def pop(self) -> Optional[QueueItem]:
        """
        Pop the highest priority item from the queue.
        
        Returns:
            QueueItem or None if queue is empty
        """
        redis = await self._get_redis()
        
        # Get item with smallest score (highest priority)
        result = await redis.zpopmin(self._key, 1)
        
        if not result:
            return None
        
        item_json = result[0][0]
        item = QueueItem.from_json(item_json)
        
        return item
    
    async def peek(self) -> Optional[QueueItem]:
        """
        Peek at the highest priority item without removing it.
        
        Returns:
            QueueItem or None
        """
        redis = await self._get_redis()
        
        # Get first item without popping
        result = await redis.zrange(self._key, 0, 0)
        
        if not result:
            return None
        
        return QueueItem.from_json(result[0])
    
    async def complete(self, item_id: str) -> bool:
        """
        Mark an item as completed and remove it.
        
        Args:
            item_id: Item ID
            
        Returns:
            True if completed successfully
        """
        redis = await self._get_redis()
        
        await redis.hdel(f"{self._key}:ids", item_id)
        return True
    
    async def fail(self, item_id: str, error: str) -> bool:
        """
        Mark an item as failed (will retry if retries left).
        
        Args:
            item_id: Item ID
            error: Error message
            
        Returns:
            True if requeued, False if max retries exceeded
        """
        redis = await self._get_redis()
        
        # Get item data
        item_json = await redis.hget(f"{self._key}:ids", item_id)
        if not item_json:
            return False
        
        item = QueueItem.from_json(item_json)
        item.retry_count += 1
        
        if item.retry_count >= item.max_retries:
            # Move to dead letter queue
            await self._move_to_dead_letter(item, error)
            await redis.hdel(f"{self._key}:ids", item_id)
            logger.error(f"Item {item_id} failed after {item.retry_count} retries: {error}")
            return False
        
        # Requeue with backoff
        backoff_seconds = 2 ** item.retry_count  # Exponential backoff
        score = item.priority.value * 1_000_000 + int(
            (datetime.utcnow() + timedelta(seconds=backoff_seconds)).timestamp()
        )
        
        await redis.zadd(self._key, {item.to_json(): score})
        await redis.hset(f"{self._key}:ids", item_id, item.to_json())
        
        logger.warning(f"Item {item_id} failed, retry {item.retry_count}/{item.max_retries}: {error}")
        return True
    
    async def _move_to_dead_letter(self, item: QueueItem, error: str) -> None:
        """Move failed item to dead letter queue."""
        dl_key = f"{self._key}:dead_letter"
        redis = await self._get_redis()
        
        dead_entry = {
            "item": item.to_json(),
            "error": error,
            "failed_at": datetime.utcnow().isoformat(),
        }
        
        await redis.lpush(dl_key, json.dumps(dead_entry))
    
    async def size(self) -> int:
        """Get queue size."""
        redis = await self._get_redis()
        return await redis.zcard(self._key)
    
    async def clear(self) -> int:
        """Clear all items from the queue."""
        redis = await self._get_redis()
        count = await self.size()
        await redis.delete(self._key)
        await redis.delete(f"{self._key}:ids")
        return count


# Queue instances for different purposes
_queues: Dict[str, PriorityQueue] = {}


def get_queue(name: str = "default") -> PriorityQueue:
    """Get or create a queue instance."""
    if name not in _queues:
        _queues[name] = PriorityQueue(name)
    return _queues[name]


async def add_to_queue(
    task: str,
    data: Dict[str, Any],
    priority: PriorityLevel = PriorityLevel.NORMAL,
    queue: str = "default",
) -> str:
    """Add a task to a queue."""
    q = get_queue(queue)
    return await q.add(task, data, priority)


async def process_queue(
    queue_name: str,
    handler: Callable,
    batch_size: int = 10,
) -> int:
    """
    Process items from a queue.
    
    Args:
        queue_name: Queue name
        handler: Async function to process each item
        batch_size: Number of items to process
        
    Returns:
        Number of items processed
    """
    q = get_queue(queue_name)
    processed = 0
    
    for _ in range(batch_size):
        item = await q.pop()
        if not item:
            break
        
        try:
            await handler(item)
            await q.complete(item.id)
            processed += 1
        except Exception as e:
            await q.fail(item.id, str(e))
    
    return processed


__all__ = [
    "PriorityQueue",
    "PriorityLevel",
    "QueueItem",
    "get_queue",
    "add_to_queue",
    "process_queue",
]