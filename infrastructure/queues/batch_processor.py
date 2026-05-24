# ============================
# WOLLOYEWA STORE BOT - BATCH PROCESSOR
# ============================
"""Batch processing for handling large volumes of similar tasks."""

import json
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from infrastructure.redis.client import get_redis_client
from core.logger import logger


class BatchStatus(str, Enum):
    """Status of a batch job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class BatchJob:
    """Batch job definition."""
    
    batch_id: str
    job_type: str
    items: List[Dict[str, Any]]
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processed_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "job_type": self.job_type,
            "items": self.items,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "errors": self.errors,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchJob":
        """Create from dictionary."""
        return cls(
            batch_id=data["batch_id"],
            job_type=data["job_type"],
            items=data["items"],
            status=BatchStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            processed_count=data.get("processed_count", 0),
            success_count=data.get("success_count", 0),
            failed_count=data.get("failed_count", 0),
            errors=data.get("errors", []),
            metadata=data.get("metadata", {}),
        )


class BatchProcessor:
    """
    Batch processor for handling bulk operations.
    
    Features:
    - Process large batches of items
    - Track progress per batch
    - Partial failure handling
    - Batch status monitoring
    - Retry failed items
    """
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self._redis = None
        self._handlers: Dict[str, Callable] = {}
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    def register_handler(self, job_type: str, handler: Callable) -> None:
        """
        Register a handler for a job type.
        
        Args:
            job_type: Job type identifier
            handler: Async function to process each item
        """
        self._handlers[job_type] = handler
        logger.info(f"Registered handler for batch job type: {job_type}")
    
    async def create_batch(
        self,
        job_type: str,
        items: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new batch job.
        
        Args:
            job_type: Type of job
            items: List of items to process
            metadata: Additional metadata
            
        Returns:
            Batch ID
        """
        import uuid
        redis = await self._get_redis()
        
        batch_id = str(uuid.uuid4())
        batch = BatchJob(
            batch_id=batch_id,
            job_type=job_type,
            items=items,
            metadata=metadata or {},
        )
        
        # Store batch
        await redis.setex(
            f"batch:{batch_id}",
            86400,  # 24 hours TTL
            json.dumps(batch.to_dict()),
        )
        
        logger.info(f"Created batch {batch_id} with {len(items)} items")
        return batch_id
    
    async def get_batch(self, batch_id: str) -> Optional[BatchJob]:
        """Get batch by ID."""
        redis = await self._get_redis()
        
        batch_json = await redis.get(f"batch:{batch_id}")
        if not batch_json:
            return None
        
        return BatchJob.from_dict(json.loads(batch_json))
    
    async def process_batch(
        self,
        batch_id: str,
        concurrency: int = 5,
    ) -> BatchJob:
        """
        Process a batch job.
        
        Args:
            batch_id: Batch ID
            concurrency: Number of concurrent items to process
            
        Returns:
            Updated batch job
        """
        batch = await self.get_batch(batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")
        
        if batch.status != BatchStatus.PENDING:
            logger.warning(f"Batch {batch_id} already in status {batch.status}")
            return batch
        
        handler = self._handlers.get(batch.job_type)
        if not handler:
            raise ValueError(f"No handler for job type: {batch.job_type}")
        
        # Update status
        batch.status = BatchStatus.PROCESSING
        batch.started_at = datetime.utcnow()
        await self._update_batch(batch)
        
        # Process items
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_item(item: Dict[str, Any], index: int):
            async with semaphore:
                try:
                    result = await handler(item)
                    batch.success_count += 1
                    return True
                except Exception as e:
                    batch.failed_count += 1
                    batch.errors.append({
                        "index": index,
                        "item": item,
                        "error": str(e),
                    })
                    logger.error(f"Failed to process item {index} in batch {batch_id}: {e}")
                    return False
        
        tasks = [process_item(item, i) for i, item in enumerate(batch.items)]
        await asyncio.gather(*tasks)
        
        batch.processed_count = len(batch.items)
        
        # Determine final status
        if batch.failed_count == 0:
            batch.status = BatchStatus.COMPLETED
        elif batch.success_count > 0:
            batch.status = BatchStatus.PARTIAL
        else:
            batch.status = BatchStatus.FAILED
        
        batch.completed_at = datetime.utcnow()
        await self._update_batch(batch)
        
        logger.info(
            f"Batch {batch_id} completed: {batch.success_count} success, "
            f"{batch.failed_count} failed"
        )
        
        return batch
    
    async def retry_failed(self, batch_id: str) -> BatchJob:
        """
        Retry failed items in a batch.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Updated batch job
        """
        batch = await self.get_batch(batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")
        
        if not batch.errors:
            logger.info(f"No failed items in batch {batch_id}")
            return batch
        
        # Create new batch with failed items
        failed_items = [e["item"] for e in batch.errors]
        
        new_batch_id = await self.create_batch(
            job_type=batch.job_type,
            items=failed_items,
            metadata={"original_batch": batch_id, "retry": True},
        )
        
        logger.info(f"Created retry batch {new_batch_id} with {len(failed_items)} items")
        return await self.process_batch(new_batch_id)
    
    async def _update_batch(self, batch: BatchJob) -> None:
        """Update batch in storage."""
        redis = await self._get_redis()
        await redis.setex(
            f"batch:{batch.batch_id}",
            86400,
            json.dumps(batch.to_dict()),
        )
    
    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get batch status summary."""
        batch = await self.get_batch(batch_id)
        if not batch:
            return {"error": "Batch not found"}
        
        return {
            "batch_id": batch.batch_id,
            "job_type": batch.job_type,
            "status": batch.status.value,
            "total_items": len(batch.items),
            "processed": batch.processed_count,
            "success": batch.success_count,
            "failed": batch.failed_count,
            "created_at": batch.created_at.isoformat(),
            "started_at": batch.started_at.isoformat() if batch.started_at else None,
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
        }


# Global batch processor
batch_processor = BatchProcessor()


async def create_batch_job(
    job_type: str,
    items: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a batch job."""
    return await batch_processor.create_batch(job_type, items, metadata)


async def process_batch(batch_id: str) -> BatchJob:
    """Process a batch job."""
    return await batch_processor.process_batch(batch_id)


async def get_batch_status(batch_id: str) -> Dict[str, Any]:
    """Get batch status."""
    return await batch_processor.get_batch_status(batch_id)


__all__ = [
    "BatchProcessor",
    "BatchJob",
    "BatchStatus",
    "batch_processor",
    "create_batch_job",
    "process_batch",
    "get_batch_status",
]