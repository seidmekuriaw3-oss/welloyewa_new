# ============================
# WOLLOYEWA STORE BOT - TASK DEDUPLICATOR
# ============================
"""Task deduplication to prevent duplicate processing."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from infrastructure.redis.client import get_redis_client
from core.logger import logger


@dataclass
class TaskRecord:
    """Record of a processed task."""
    
    task_id: str
    task_hash: str
    processed_at: datetime
    status: str  # processing, completed, failed
    result: Optional[Dict[str, Any]] = None


class TaskDeduplicator:
    """
    Task deduplication service.
    
    Features:
    - Generate unique hash for task content
    - Track processed tasks
    - Prevent duplicate processing
    - Configurable retention period
    """
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    def _generate_hash(self, task_name: str, data: Dict[str, Any]) -> str:
        """
        Generate unique hash for a task.
        
        Args:
            task_name: Task name
            data: Task data
            
        Returns:
            SHA256 hash string
        """
        # Create deterministic string representation
        content = json.dumps({
            "task": task_name,
            "data": data,
        }, sort_keys=True)
        
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def is_duplicate(
        self,
        task_name: str,
        data: Dict[str, Any],
        window_seconds: Optional[int] = None,
    ) -> bool:
        """
        Check if a task is a duplicate of a recently processed task.
        
        Args:
            task_name: Task name
            data: Task data
            window_seconds: Time window to check (default retention_hours)
            
        Returns:
            True if duplicate found
        """
        redis = await self._get_redis()
        task_hash = self._generate_hash(task_name, data)
        
        key = f"task_dedup:{task_hash}"
        window = window_seconds or (self.retention_hours * 3600)
        
        # Check if task exists and not expired
        exists = await redis.exists(key)
        
        if exists:
            # Get task record
            record_json = await redis.get(key)
            if record_json:
                record = json.loads(record_json)
                logger.debug(f"Duplicate task detected: {task_name} (hash: {task_hash[:8]})")
                return True
        
        return False
    
    async def register_task(
        self,
        task_name: str,
        data: Dict[str, Any],
        status: str = "processing",
        result: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """
        Register a task as being processed.
        
        Args:
            task_name: Task name
            data: Task data
            status: Task status
            result: Task result (for completed tasks)
            ttl_seconds: Time to live in seconds
            
        Returns:
            Task hash
        """
        redis = await self._get_redis()
        task_hash = self._generate_hash(task_name, data)
        
        ttl = ttl_seconds or (self.retention_hours * 3600)
        
        record = TaskRecord(
            task_id=f"{task_name}:{task_hash[:8]}",
            task_hash=task_hash,
            processed_at=datetime.utcnow(),
            status=status,
            result=result,
        )
        
        await redis.setex(
            f"task_dedup:{task_hash}",
            ttl,
            json.dumps({
                "task_id": record.task_id,
                "task_hash": record.task_hash,
                "processed_at": record.processed_at.isoformat(),
                "status": record.status,
                "result": record.result,
            }, default=str),
        )
        
        logger.debug(f"Registered task: {task_name} (hash: {task_hash[:8]})")
        return task_hash
    
    async def complete_task(
        self,
        task_name: str,
        data: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark a task as completed.
        
        Args:
            task_name: Task name
            data: Task data
            result: Task result
            
        Returns:
            True if task was updated
        """
        redis = await self._get_redis()
        task_hash = self._generate_hash(task_name, data)
        
        key = f"task_dedup:{task_hash}"
        record_json = await redis.get(key)
        
        if record_json:
            record = json.loads(record_json)
            record["status"] = "completed"
            record["result"] = result
            
            ttl = await redis.ttl(key)
            await redis.setex(key, ttl, json.dumps(record, default=str))
            
            logger.debug(f"Completed task: {task_name} (hash: {task_hash[:8]})")
            return True
        
        return False
    
    async def fail_task(
        self,
        task_name: str,
        data: Dict[str, Any],
        error: str,
    ) -> bool:
        """
        Mark a task as failed.
        
        Args:
            task_name: Task name
            data: Task data
            error: Error message
            
        Returns:
            True if task was updated
        """
        redis = await self._get_redis()
        task_hash = self._generate_hash(task_name, data)
        
        key = f"task_dedup:{task_hash}"
        record_json = await redis.get(key)
        
        if record_json:
            record = json.loads(record_json)
            record["status"] = "failed"
            record["result"] = {"error": error}
            
            ttl = await redis.ttl(key)
            await redis.setex(key, ttl, json.dumps(record, default=str))
            
            logger.debug(f"Failed task: {task_name} (hash: {task_hash[:8]}): {error}")
            return True
        
        return False
    
    async def get_task_record(
        self,
        task_name: str,
        data: Dict[str, Any],
    ) -> Optional[TaskRecord]:
        """
        Get record of a task.
        
        Args:
            task_name: Task name
            data: Task data
            
        Returns:
            TaskRecord or None
        """
        redis = await self._get_redis()
        task_hash = self._generate_hash(task_name, data)
        
        key = f"task_dedup:{task_hash}"
        record_json = await redis.get(key)
        
        if not record_json:
            return None
        
        record = json.loads(record_json)
        return TaskRecord(
            task_id=record["task_id"],
            task_hash=record["task_hash"],
            processed_at=datetime.fromisoformat(record["processed_at"]),
            status=record["status"],
            result=record.get("result"),
        )
    
    async def cleanup_expired(self) -> int:
        """
        Clean up expired task records.
        
        Returns:
            Number of records cleaned
        """
        # Redis handles expiration automatically with TTL
        # This method is for manual cleanup if needed
        redis = await self._get_redis()
        
        keys = await redis.keys("task_dedup:*")
        cleaned = 0
        
        for key in keys:
            ttl = await redis.ttl(key)
            if ttl <= 0:
                await redis.delete(key)
                cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} expired task records")
        return cleaned
    
    async def clear_all(self) -> int:
        """Clear all task records."""
        redis = await self._get_redis()
        keys = await redis.keys("task_dedup:*")
        
        if keys:
            await redis.delete(*keys)
            logger.info(f"Cleared {len(keys)} task records")
            return len(keys)
        
        return 0


# Global deduplicator instance
task_deduplicator = TaskDeduplicator()


async def deduplicate_task(
    task_name: str,
    data: Dict[str, Any],
    window_seconds: Optional[int] = None,
) -> bool:
    """
    Check if a task is a duplicate.
    
    Args:
        task_name: Task name
        data: Task data
        window_seconds: Time window to check
        
    Returns:
        True if duplicate (should skip processing)
    """
    return await task_deduplicator.is_duplicate(task_name, data, window_seconds)


async def is_task_duplicate(task_name: str, data: Dict[str, Any]) -> bool:
    """Alias for deduplicate_task."""
    return await deduplicate_task(task_name, data)


async def clear_task_records() -> int:
    """Clear all task records."""
    return await task_deduplicator.clear_all()


__all__ = [
    "TaskDeduplicator",
    "TaskRecord",
    "task_deduplicator",
    "deduplicate_task",
    "is_task_duplicate",
    "clear_task_records",
]