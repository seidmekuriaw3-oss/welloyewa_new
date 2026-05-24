# ============================
# WOLLOYEWA STORE BOT - ORDER TRACKING
# ============================
"""Order tracking with real-time status updates and carrier integration."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from core.logger import logger
from core.exceptions import NotFoundError
from core.redis.client import get_redis_client


class TrackingStatus(str, Enum):
    """Tracking status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"


@dataclass
class TrackingUpdate:
    """Individual tracking update."""
    
    status: TrackingStatus
    location: Optional[str]
    timestamp: datetime
    description: Optional[str] = None
    carrier_data: Optional[Dict[str, Any]] = None


class OrderTracker:
    """
    Order tracking manager.
    
    Features:
    - Real-time tracking status updates
    - Carrier integration (Ethiopian Postal Service, etc.)
    - Webhook support for carrier updates
    - Tracking history
    """
    
    def __init__(self):
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def update_tracking(
        self,
        order_id: int,
        tracking_number: str,
        carrier: str,
        status: TrackingStatus,
        location: Optional[str] = None,
        description: Optional[str] = None,
        carrier_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update tracking information for an order.
        
        Args:
            order_id: Order ID
            tracking_number: Tracking number
            carrier: Shipping carrier name
            status: Current tracking status
            location: Current location
            description: Status description
            carrier_data: Additional carrier data
        """
        redis = await self._get_redis()
        key = f"tracking:{order_id}"
        
        update = TrackingUpdate(
            status=status,
            location=location,
            timestamp=datetime.utcnow(),
            description=description,
            carrier_data=carrier_data,
        )
        
        # Store in Redis
        await redis.hset(key, "tracking_number", tracking_number)
        await redis.hset(key, "carrier", carrier)
        await redis.hset(key, "status", status.value)
        await redis.hset(key, "last_update", update.timestamp.isoformat())
        
        # Add to history
        history_key = f"tracking:{order_id}:history"
        await redis.lpush(history_key, self._serialize_update(update))
        await redis.ltrim(history_key, 0, 99)  # Keep last 100 updates
        
        # Set expiration (30 days)
        await redis.expire(key, 2592000)
        await redis.expire(history_key, 2592000)
        
        logger.info(f"Tracking updated for order {order_id}: {status.value} - {location}")
    
    async def get_tracking_status(self, order_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current tracking status for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Tracking information dictionary
        """
        redis = await self._get_redis()
        key = f"tracking:{order_id}"
        
        data = await redis.hgetall(key)
        if not data:
            return None
        
        return {
            "order_id": order_id,
            "tracking_number": data.get(b"tracking_number", b"").decode(),
            "carrier": data.get(b"carrier", b"").decode(),
            "status": data.get(b"status", b"").decode(),
            "last_update": data.get(b"last_update", b"").decode(),
        }
    
    async def get_tracking_history(self, order_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get tracking history for an order.
        
        Args:
            order_id: Order ID
            limit: Maximum number of history entries
            
        Returns:
            List of tracking updates
        """
        redis = await self._get_redis()
        history_key = f"tracking:{order_id}:history"
        
        history = await redis.lrange(history_key, 0, limit - 1)
        return [self._deserialize_update(h) for h in history]
    
    async def track_with_carrier(
        self,
        tracking_number: str,
        carrier: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch tracking information from carrier API.
        
        Args:
            tracking_number: Tracking number
            carrier: Carrier name
            
        Returns:
            Tracking information from carrier
        """
        # Carrier API integration placeholder
        # In production, implement specific carrier APIs:
        # - Ethiopian Postal Service
        # - DHL Ethiopia
        # - FedEx
        # - Aramex
        carriers = {
            "ethiopian_post": self._track_ethiopian_post,
            "dhl": self._track_dhl,
            "fedex": self._track_fedex,
            "aramex": self._track_aramex,
        }
        
        tracking_func = carriers.get(carrier.lower())
        if tracking_func:
            try:
                return await tracking_func(tracking_number)
            except Exception as e:
                logger.error(f"Carrier tracking failed for {carrier}: {e}")
        
        return None
    
    async def _track_ethiopian_post(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Track with Ethiopian Postal Service."""
        # Placeholder - implement Ethiopian Post API
        # API endpoint: https://api.ethiopost.et/track
        logger.debug(f"Tracking with Ethiopian Post: {tracking_number}")
        return None
    
    async def _track_dhl(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Track with DHL."""
        # Placeholder - implement DHL API
        logger.debug(f"Tracking with DHL: {tracking_number}")
        return None
    
    async def _track_fedex(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Track with FedEx."""
        # Placeholder - implement FedEx API
        logger.debug(f"Tracking with FedEx: {tracking_number}")
        return None
    
    async def _track_aramex(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Track with Aramex."""
        # Placeholder - implement Aramex API
        logger.debug(f"Tracking with Aramex: {tracking_number}")
        return None
    
    def _serialize_update(self, update: TrackingUpdate) -> str:
        """Serialize tracking update to string."""
        import json
        return json.dumps({
            "status": update.status.value,
            "location": update.location,
            "timestamp": update.timestamp.isoformat(),
            "description": update.description,
            "carrier_data": update.carrier_data,
        })
    
    def _deserialize_update(self, data: bytes) -> Dict[str, Any]:
        """Deserialize tracking update from string."""
        import json
        return json.loads(data.decode())


# Global order tracker instance
order_tracker = OrderTracker()


async def track_order(order_id: int) -> Optional[Dict[str, Any]]:
    """Convenience function to track an order."""
    return await order_tracker.get_tracking_status(order_id)


async def update_tracking_status(
    order_id: int,
    tracking_number: str,
    carrier: str,
    status: TrackingStatus,
    location: Optional[str] = None,
) -> None:
    """Convenience function to update tracking status."""
    await order_tracker.update_tracking(
        order_id=order_id,
        tracking_number=tracking_number,
        carrier=carrier,
        status=status,
        location=location,
    )


async def get_tracking_info(order_id: int) -> Optional[Dict[str, Any]]:
    """Convenience function to get tracking information."""
    status = await order_tracker.get_tracking_status(order_id)
    if status:
        history = await order_tracker.get_tracking_history(order_id)
        status["history"] = history
    return status


__all__ = [
    "OrderTracker",
    "TrackingStatus",
    "TrackingUpdate",
    "order_tracker",
    "track_order",
    "update_tracking_status",
    "get_tracking_info",
]