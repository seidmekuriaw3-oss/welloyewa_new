# ============================
# WOLLOYEWA STORE BOT - OFFLINE SYNC
# ============================
"""Offline sync support for mobile apps."""

import json
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from infrastructure.redis.client import get_redis_client
from core.logger import logger


class SyncStatus(str, Enum):
    """Sync operation status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncOperation(str, Enum):
    """Sync operation types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class SyncQueue:
    """Sync queue item."""
    
    queue_id: str
    user_id: int
    entity_type: str
    entity_id: str
    operation: SyncOperation
    data: Dict[str, Any]
    status: SyncStatus = SyncStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class SyncConflictResolver:
    """
    Conflict resolver for offline sync.
    
    Strategies:
    - Server wins: Server version always takes precedence
    - Client wins: Client version always takes precedence
    - Last write wins: Most recent timestamp wins
    - Merge: Attempt to merge changes
    """
    
    def __init__(self, strategy: str = "server_wins"):
        self.strategy = strategy
    
    def resolve(
        self,
        server_data: Dict[str, Any],
        client_data: Dict[str, Any],
        server_version: datetime,
        client_version: datetime,
    ) -> Dict[str, Any]:
        """
        Resolve conflict between server and client data.
        
        Args:
            server_data: Current server data
            client_data: Client's pending changes
            server_version: Server last modified timestamp
            client_version: Client last modified timestamp
            
        Returns:
            Resolved data
        """
        if self.strategy == "server_wins":
            return server_data
        elif self.strategy == "client_wins":
            return client_data
        elif self.strategy == "last_write_wins":
            return client_data if client_version > server_version else server_data
        elif self.strategy == "merge":
            # Simple merge: client changes override server
            merged = server_data.copy()
            merged.update(client_data)
            return merged
        else:
            return server_data


class OfflineSyncManager:
    """
    Offline sync manager for mobile apps.
    
    Features:
    - Queue offline operations
    - Sync when online
    - Conflict resolution
    - Retry failed operations
    """
    
    def __init__(self):
        self._redis = None
        self._conflict_resolver = SyncConflictResolver()
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def queue_operation(
        self,
        user_id: int,
        entity_type: str,
        entity_id: str,
        operation: SyncOperation,
        data: Dict[str, Any],
    ) -> str:
        """
        Queue an offline operation.
        
        Args:
            user_id: User ID
            entity_type: Type of entity (order, product, etc.)
            entity_id: Entity ID
            operation: Operation type
            data: Operation data
            
        Returns:
            Queue ID
        """
        import uuid
        redis = await self._get_redis()
        
        queue_id = str(uuid.uuid4())
        queue_item = SyncQueue(
            queue_id=queue_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            data=data,
        )
        
        key = f"offline_sync:{user_id}:{queue_id}"
        await redis.setex(
            key,
            86400 * 7,  # 7 days TTL
            json.dumps({
                "queue_id": queue_item.queue_id,
                "user_id": queue_item.user_id,
                "entity_type": queue_item.entity_type,
                "entity_id": queue_item.entity_id,
                "operation": queue_item.operation.value,
                "data": queue_item.data,
                "status": queue_item.status.value,
                "created_at": queue_item.created_at.isoformat(),
                "retry_count": queue_item.retry_count,
                "max_retries": queue_item.max_retries,
            }, default=str),
        )
        
        # Add to user's sync list
        await redis.sadd(f"offline_sync:{user_id}:list", queue_id)
        
        logger.info(f"Queued offline operation {queue_id} for user {user_id}")
        return queue_id
    
    async def process_sync_queue(self, user_id: int) -> Dict[str, Any]:
        """
        Process all pending sync operations for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Sync results
        """
        redis = await self._get_redis()
        
        queue_ids = await redis.smembers(f"offline_sync:{user_id}:list")
        
        results = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "conflicts": 0,
            "details": [],
        }
        
        for queue_id in queue_ids:
            queue_id = queue_id.decode() if isinstance(queue_id, bytes) else queue_id
            result = await self._process_operation(user_id, queue_id)
            
            results["processed"] += 1
            if result["status"] == "success":
                results["success"] += 1
            elif result["status"] == "conflict":
                results["conflicts"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append(result)
        
        return results
    
    async def _process_operation(self, user_id: int, queue_id: str) -> Dict[str, Any]:
        """
        Process a single sync operation.
        
        Args:
            user_id: User ID
            queue_id: Queue ID
            
        Returns:
            Operation result
        """
        redis = await self._get_redis()
        
        key = f"offline_sync:{user_id}:{queue_id}"
        item_json = await redis.get(key)
        
        if not item_json:
            return {"queue_id": queue_id, "status": "not_found"}
        
        item_data = json.loads(item_json)
        
        queue_item = SyncQueue(
            queue_id=item_data["queue_id"],
            user_id=item_data["user_id"],
            entity_type=item_data["entity_type"],
            entity_id=item_data["entity_id"],
            operation=SyncOperation(item_data["operation"]),
            data=item_data["data"],
            status=SyncStatus(item_data["status"]),
            created_at=datetime.fromisoformat(item_data["created_at"]),
            retry_count=item_data.get("retry_count", 0),
            max_retries=item_data.get("max_retries", 3),
        )
        
        if queue_item.status != SyncStatus.PENDING:
            return {"queue_id": queue_id, "status": queue_item.status.value}
        
        # Update status to processing
        await self._update_queue_item_status(redis, user_id, queue_id, SyncStatus.PROCESSING)
        
        try:
            # Process based on entity type and operation
            # This would call the appropriate service
            success = await self._apply_operation(queue_item)
            
            if success:
                await self._update_queue_item_status(redis, user_id, queue_id, SyncStatus.COMPLETED)
                await redis.srem(f"offline_sync:{user_id}:list", queue_id)
                await redis.delete(key)
                return {"queue_id": queue_id, "status": "success"}
            else:
                queue_item.retry_count += 1
                if queue_item.retry_count >= queue_item.max_retries:
                    await self._update_queue_item_status(redis, user_id, queue_id, SyncStatus.FAILED)
                else:
                    await self._update_queue_item_status(redis, user_id, queue_id, SyncStatus.PENDING)
                
                return {
                    "queue_id": queue_id,
                    "status": "failed",
                    "retry_count": queue_item.retry_count,
                }
                
        except Exception as e:
            logger.error(f"Failed to process sync operation {queue_id}: {e}")
            
            queue_item.retry_count += 1
            if queue_item.retry_count >= queue_item.max_retries:
                await self._update_queue_item_status(redis, user_id, queue_id, SyncStatus.FAILED)
            else:
                await self._update_queue_item_status(redis, user_id, queue_id, SyncStatus.PENDING)
            
            return {
                "queue_id": queue_id,
                "status": "failed",
                "error": str(e),
                "retry_count": queue_item.retry_count,
            }
    
    async def _apply_operation(self, queue_item: SyncQueue) -> bool:
        """Apply the operation to the server."""
        # In production, this would call the appropriate service
        # based on entity_type and operation
        logger.info(f"Applying {queue_item.operation.value} on {queue_item.entity_type} {queue_item.entity_id}")
        
        # Mock implementation - always success
        return True
    
    async def _update_queue_item_status(
        self,
        redis,
        user_id: int,
        queue_id: str,
        status: SyncStatus,
    ) -> None:
        """Update queue item status."""
        key = f"offline_sync:{user_id}:{queue_id}"
        item_json = await redis.get(key)
        
        if item_json:
            item_data = json.loads(item_json)
            item_data["status"] = status.value
            item_data["processed_at"] = datetime.utcnow().isoformat()
            await redis.setex(key, 86400 * 7, json.dumps(item_data))
    
    async def get_pending_sync_count(self, user_id: int) -> int:
        """Get number of pending sync operations for a user."""
        redis = await self._get_redis()
        return await redis.scard(f"offline_sync:{user_id}:list")
    
    async def clear_user_sync_queue(self, user_id: int) -> int:
        """Clear all pending sync operations for a user."""
        redis = await self._get_redis()
        
        queue_ids = await redis.smembers(f"offline_sync:{user_id}:list")
        
        for queue_id in queue_ids:
            queue_id = queue_id.decode() if isinstance(queue_id, bytes) else queue_id
            key = f"offline_sync:{user_id}:{queue_id}"
            await redis.delete(key)
        
        await redis.delete(f"offline_sync:{user_id}:list")
        
        logger.info(f"Cleared sync queue for user {user_id}")
        return len(queue_ids)


# Global offline sync manager
offline_sync_manager = OfflineSyncManager()


async def queue_offline_operation(
    user_id: int,
    entity_type: str,
    entity_id: str,
    operation: str,
    data: Dict[str, Any],
) -> str:
    """Queue an offline operation."""
    return await offline_sync_manager.queue_operation(
        user_id, entity_type, entity_id, SyncOperation(operation), data
    )


async def process_sync_queue(user_id: int) -> Dict[str, Any]:
    """Process pending sync operations."""
    return await offline_sync_manager.process_sync_queue(user_id)


async def get_pending_sync_count(user_id: int) -> int:
    """Get pending sync count."""
    return await offline_sync_manager.get_pending_sync_count(user_id)


__all__ = [
    "OfflineSyncManager",
    "SyncQueue",
    "SyncOperation",
    "SyncStatus",
    "SyncConflictResolver",
    "offline_sync_manager",
    "queue_offline_operation",
    "process_sync_queue",
    "get_pending_sync_count",
]