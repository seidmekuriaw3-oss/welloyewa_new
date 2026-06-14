# ============================
# WOLLOYEWA STORE BOT - REDIS CLIENT
# ============================
"""Redis connection and client management."""

import json
from typing import Optional, Any, Dict, List, Union
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from core.config import settings
from core.logger import logger


class RedisClient:
    """
    Redis client wrapper with connection pooling.
    
    Features:
    - Connection pooling
    - Automatic reconnect
    - Serialization helpers
    - Key management utilities
    """
    
    def __init__(self):
        self._client: Optional[Redis] = None
        self._initialized = False
    
    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._initialized:
            return
        
        try:
            self._client = await redis.from_url(
                str(settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            
            # Test connection
            await self._client.ping()
            self._initialized = True
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._initialized = False
            logger.info("Redis connection closed")
    
    async def get_client(self) -> Redis:
        """Get Redis client instance."""
        if not self._initialized:
            await self.connect()
        return self._client
    
    # ============================
    # Basic Operations
    # ============================
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        client = await self.get_client()
        return await client.get(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set key-value pair.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds
            nx: Only set if key does not exist
            xx: Only set if key exists
            
        Returns:
            True if successful
        """
        client = await self.get_client()
        
        # Serialize if value is not string
        if not isinstance(value, str):
            value = json.dumps(value)
        
        result = await client.set(key, value, ex=ttl, nx=nx, xx=xx)
        return result is True
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        client = await self.get_client()
        return await client.delete(*keys)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        client = await self.get_client()
        return await client.exists(key) > 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key."""
        client = await self.get_client()
        return await client.expire(key, ttl)
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        client = await self.get_client()
        return await client.ttl(key)
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment key by amount."""
        client = await self.get_client()
        return await client.incrby(key, amount)
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement key by amount."""
        client = await self.get_client()
        return await client.decrby(key, amount)
    
    # ============================
    # Hash Operations
    # ============================
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field."""
        client = await self.get_client()
        return await client.hget(key, field)
    
    async def hset(self, key: str, field: str, value: Any) -> int:
        """Set hash field."""
        client = await self.get_client()
        if not isinstance(value, str):
            value = json.dumps(value)
        return await client.hset(key, field, value)
    
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields."""
        client = await self.get_client()
        return await client.hgetall(key)
    
    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields."""
        client = await self.get_client()
        return await client.hdel(key, *fields)
    
    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """Increment hash field."""
        client = await self.get_client()
        return await client.hincrby(key, field, amount)
    
    # ============================
    # List Operations
    # ============================
    
    async def lpush(self, key: str, *values: Any) -> int:
        """Push to left of list."""
        client = await self.get_client()
        serialized = []
        for v in values:
            serialized.append(json.dumps(v) if not isinstance(v, str) else v)
        return await client.lpush(key, *serialized)
    
    async def rpush(self, key: str, *values: Any) -> int:
        """Push to right of list."""
        client = await self.get_client()
        serialized = []
        for v in values:
            serialized.append(json.dumps(v) if not isinstance(v, str) else v)
        return await client.rpush(key, *serialized)
    
    async def lpop(self, key: str) -> Optional[str]:
        """Pop from left of list."""
        client = await self.get_client()
        return await client.lpop(key)
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop from right of list."""
        client = await self.get_client()
        return await client.rpop(key)
    
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range from list."""
        client = await self.get_client()
        return await client.lrange(key, start, end)
    
    # ============================
    # Set Operations
    # ============================
    
    async def sadd(self, key: str, *members: Any) -> int:
        """Add to set."""
        client = await self.get_client()
        serialized = []
        for m in members:
            serialized.append(str(m))
        return await client.sadd(key, *serialized)
    
    async def srem(self, key: str, *members: Any) -> int:
        """Remove from set."""
        client = await self.get_client()
        serialized = []
        for m in members:
            serialized.append(str(m))
        return await client.srem(key, *serialized)
    
    async def smembers(self, key: str) -> List[str]:
        """Get all set members."""
        client = await self.get_client()
        return await client.smembers(key)
    
    async def sismember(self, key: str, member: Any) -> bool:
        """Check if member in set."""
        client = await self.get_client()
        return await client.sismember(key, str(member))
    
    # ============================
    # Sorted Set Operations
    # ============================
    
    async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """Add to sorted set."""
        client = await self.get_client()
        return await client.zadd(key, mapping)
    
    async def zrange(
        self,
        key: str,
        start: int,
        end: int,
        withscores: bool = False,
    ) -> Union[List[str], List[tuple]]:
        """Get range from sorted set."""
        client = await self.get_client()
        return await client.zrange(key, start, end, withscores=withscores)
    
    async def zrevrange(
        self,
        key: str,
        start: int,
        end: int,
        withscores: bool = False,
    ) -> Union[List[str], List[tuple]]:
        """Get reverse range from sorted set."""
        client = await self.get_client()
        return await client.zrevrange(key, start, end, withscores=withscores)
    
    async def zrem(self, key: str, *members: str) -> int:
        """Remove from sorted set."""
        client = await self.get_client()
        return await client.zrem(key, *members)
    
    # ============================
    # Utility Operations
    # ============================
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        client = await self.get_client()
        return await client.keys(pattern)
    
    async def flushdb(self) -> bool:
        """Flush current database."""
        client = await self.get_client()
        return await client.flushdb()
    
    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            client = await self.get_client()
            return await client.ping()
        except Exception:
            return False


# Global Redis client instance
_redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """Get Redis client instance."""
    return _redis_client


async def init_redis() -> None:
    """Initialize Redis connection."""
    await _redis_client.connect()


async def close_redis() -> None:
    """Close Redis connection."""
    await _redis_client.disconnect()


__all__ = [
    "RedisClient",
    "get_redis_client",
    "init_redis",
    "close_redis",
]