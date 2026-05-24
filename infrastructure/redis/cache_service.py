# ============================
# WOLLOYEWA STORE BOT - CACHE SERVICE
# ============================
"""Cache service for managing application caching."""

import json
import hashlib
from typing import Any, Optional, Callable, TypeVar, Union
from functools import wraps
from datetime import datetime, timedelta

from infrastructure.redis.client import get_redis_client
from core.logger import logger

T = TypeVar('T')


class CacheService:
    """
    Cache service for application data.
    
    Features:
    - Set/get/delete cache entries
    - Automatic serialization/deserialization
    - Cache invalidation patterns
    - TTL management
    """
    
    def __init__(self):
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if key doesn't exist
            
        Returns:
            Cached value or default
        """
        try:
            redis = await self._get_redis()
            value = await redis.get(key)
            
            if value is None:
                return default
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Cache get failed for key '{key}': {e}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
            
        Returns:
            True if successful
        """
        try:
            redis = await self._get_redis()
            
            # Serialize if needed
            if not isinstance(value, str):
                value = json.dumps(value, default=str)
            
            return await redis.set(key, value, ttl=ttl, nx=nx, xx=xx)
            
        except Exception as e:
            logger.error(f"Cache set failed for key '{key}': {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more cache keys."""
        try:
            redis = await self._get_redis()
            return await redis.delete(*keys)
        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            redis = await self._get_redis()
            return await redis.exists(key)
        except Exception as e:
            logger.error(f"Cache exists check failed: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment cache value."""
        try:
            redis = await self._get_redis()
            return await redis.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache increment failed: {e}")
            return 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on cache key."""
        try:
            redis = await self._get_redis()
            return await redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Cache expire failed: {e}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Get value from cache or compute if not exists.
        
        Args:
            key: Cache key
            factory: Function to compute value if not cached
            ttl: Time to live in seconds
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache
        value = await self.get(key)
        if value is not None:
            return value
        
        # Compute value
        if callable(factory):
            value = factory()
            if hasattr(value, '__await__'):
                value = await value
        
        # Store in cache
        if value is not None:
            await self.set(key, value, ttl=ttl)
        
        return value
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            Number of keys invalidated
        """
        try:
            redis = await self._get_redis()
            keys = await redis.keys(pattern)
            if keys:
                return await redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache pattern invalidation failed: {e}")
            return 0
    
    async def clear(self) -> bool:
        """Clear all cache."""
        try:
            redis = await self._get_redis()
            await redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False
    
    def generate_key(self, prefix: str, *parts: Any) -> str:
        """
        Generate a cache key from parts.
        
        Args:
            prefix: Key prefix
            *parts: Key parts to join
            
        Returns:
            Generated cache key
        """
        key_parts = [prefix]
        for part in parts:
            if part is not None:
                key_parts.append(str(part))
        return ":".join(key_parts)


# Global cache service instance
cache_service = CacheService()


def cached(
    key_prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None,
):
    """
    Decorator for caching function results.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
        key_builder: Custom function to build cache key
        
    Usage:
        @cached("user_data", ttl=300)
        async def get_user_data(user_id: int):
            return await fetch_user(user_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder using function name and arguments
                parts = [key_prefix]
                for arg in args:
                    parts.append(str(arg))
                for k, v in sorted(kwargs.items()):
                    parts.append(f"{k}:{v}")
                cache_key = ":".join(parts)
                
                # Hash long keys
                if len(cache_key) > 200:
                    cache_key = f"{key_prefix}:{hashlib.md5(cache_key.encode()).hexdigest()}"
            
            # Try to get from cache
            cached_value = await cache_service.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                await cache_service.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


async def invalidate_cache(pattern: str) -> int:
    """Invalidate cache keys matching pattern."""
    return await cache_service.invalidate_pattern(pattern)


async def get_cached_or_set(
    key: str,
    factory: Callable,
    ttl: Optional[int] = None,
) -> Any:
    """Get from cache or compute and store."""
    return await cache_service.get_or_set(key, factory, ttl)


__all__ = [
    "CacheService",
    "cache_service",
    "cached",
    "invalidate_cache",
    "get_cached_or_set",
]