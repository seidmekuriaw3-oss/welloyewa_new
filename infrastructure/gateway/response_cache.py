# ============================
# WOLLOYEWA STORE BOT - RESPONSE CACHE
# ============================
"""Response caching for API gateway to improve performance."""

import hashlib
import json
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime, timedelta
from functools import wraps

from infrastructure.redis.client import get_redis_client
from core.logger import logger


class CacheStrategy(str, Enum):
    """Cache strategies."""
    DISABLED = "disabled"
    READ_THROUGH = "read_through"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    REFRESH_AHEAD = "refresh_ahead"


class ResponseCache:
    """
    Response cache for API gateway.
    
    Features:
    - Automatic cache key generation
    - TTL management
    - Cache invalidation
    - Multiple strategies
    """
    
    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._redis = None
        self._cache_config: Dict[str, Dict[str, Any]] = {}
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    def configure(
        self,
        endpoint: str,
        ttl: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.READ_THROUGH,
        vary_by: Optional[List[str]] = None,
    ) -> None:
        """
        Configure caching for an endpoint.
        
        Args:
            endpoint: Endpoint path
            ttl: Cache TTL in seconds
            strategy: Cache strategy
            vary_by: Headers/params to vary cache by
        """
        self._cache_config[endpoint] = {
            "ttl": ttl or self.default_ttl,
            "strategy": strategy,
            "vary_by": vary_by or [],
        }
        logger.debug(f"Configured cache for endpoint: {endpoint}")
    
    def _generate_cache_key(
        self,
        endpoint: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
    ) -> str:
        """
        Generate cache key for request.
        
        Args:
            endpoint: Endpoint path
            params: Query parameters
            headers: Request headers
            
        Returns:
            Cache key
        """
        config = self._cache_config.get(endpoint, {})
        vary_by = config.get("vary_by", [])
        
        # Build key components
        key_parts = [endpoint]
        
        # Add vary parameters
        for vary in vary_by:
            if vary in params:
                key_parts.append(f"{vary}={params[vary]}")
            elif vary in headers:
                key_parts.append(f"{vary}={headers[vary]}")
        
        key_string = ":".join(key_parts)
        
        # Hash long keys
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"cache:{key_hash}"
        
        return f"cache:{key_string}"
    
    async def get(
        self,
        endpoint: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response.
        
        Args:
            endpoint: Endpoint path
            params: Query parameters
            headers: Request headers
            
        Returns:
            Cached response or None
        """
        config = self._cache_config.get(endpoint, {})
        
        if config.get("strategy") == CacheStrategy.DISABLED:
            return None
        
        cache_key = self._generate_cache_key(endpoint, params, headers)
        
        try:
            redis = await self._get_redis()
            cached = await redis.get(cache_key)
            
            if cached:
                logger.debug(f"Cache hit for {endpoint}")
                return json.loads(cached)
            else:
                logger.debug(f"Cache miss for {endpoint}")
                return None
                
        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            return None
    
    async def set(
        self,
        endpoint: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        response: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache a response.
        
        Args:
            endpoint: Endpoint path
            params: Query parameters
            headers: Request headers
            response: Response to cache
            ttl: Custom TTL
            
        Returns:
            True if cached successfully
        """
        config = self._cache_config.get(endpoint, {})
        
        if config.get("strategy") == CacheStrategy.DISABLED:
            return False
        
        cache_ttl = ttl or config.get("ttl", self.default_ttl)
        cache_key = self._generate_cache_key(endpoint, params, headers)
        
        try:
            redis = await self._get_redis()
            await redis.setex(
                cache_key,
                cache_ttl,
                json.dumps(response, default=str),
            )
            logger.debug(f"Cached response for {endpoint} (TTL: {cache_ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False
    
    async def invalidate(self, endpoint: str, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache for an endpoint.
        
        Args:
            endpoint: Endpoint path
            pattern: Optional key pattern (e.g., "user:123")
            
        Returns:
            Number of keys invalidated
        """
        try:
            redis = await self._get_redis()
            
            if pattern:
                cache_key = f"cache:{endpoint}:{pattern}"
                await redis.delete(cache_key)
                return 1
            else:
                # Delete all cache keys for this endpoint
                keys = await redis.keys(f"cache:{endpoint}:*")
                if keys:
                    await redis.delete(*keys)
                    return len(keys)
                return 0
                
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return 0
    
    async def clear(self) -> int:
        """Clear all cached responses."""
        try:
            redis = await self._get_redis()
            keys = await redis.keys("cache:*")
            if keys:
                await redis.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return 0


# Global response cache instance
response_cache = ResponseCache()


def cache_response(
    ttl: Optional[int] = None,
    strategy: CacheStrategy = CacheStrategy.READ_THROUGH,
    vary_by: Optional[List[str]] = None,
):
    """
    Decorator for caching endpoint responses.
    
    Args:
        ttl: Cache TTL in seconds
        strategy: Cache strategy
        vary_by: Headers/params to vary cache by
        
    Usage:
        @app.get("/api/products")
        @cache_response(ttl=60, vary_by=["category"])
        async def get_products(request):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request info
            request = kwargs.get('request') or (args[0] if args else None)
            
            if not request:
                return await func(*args, **kwargs)
            
            endpoint = request.url.path
            params = dict(request.query_params)
            headers = dict(request.headers)
            
            # Configure cache for this endpoint
            response_cache.configure(endpoint, ttl=ttl, strategy=strategy, vary_by=vary_by)
            
            # Try to get from cache
            if strategy != CacheStrategy.WRITE_THROUGH:
                cached = await response_cache.get(endpoint, params, headers)
                if cached:
                    return cached
            
            # Execute function
            response = await func(*args, **kwargs)
            
            # Cache response
            if response and strategy != CacheStrategy.DISABLED:
                await response_cache.set(endpoint, params, headers, response, ttl=ttl)
            
            return response
        
        return wrapper
    return decorator


async def get_cached_response(
    endpoint: str,
    params: Dict[str, Any],
    headers: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """Get cached response."""
    return await response_cache.get(endpoint, params, headers)


async def invalidate_cache(endpoint: str, pattern: Optional[str] = None) -> int:
    """Invalidate cache for an endpoint."""
    return await response_cache.invalidate(endpoint, pattern)


__all__ = [
    "ResponseCache",
    "CacheStrategy",
    "response_cache",
    "cache_response",
    "get_cached_response",
    "invalidate_cache",
]