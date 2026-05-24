# ============================
# WOLLOYEWA STORE BOT - REDIS RATE LIMITER
# ============================
"""Rate limiting implementation using Redis."""

import time
from typing import Optional, Tuple, Callable, Any
from functools import wraps
from enum import Enum

from infrastructure.redis.client import get_redis_client
from core.logger import logger


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, window: int, retry_after: int):
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded: {limit} requests per {window} seconds. Retry after {retry_after} seconds.")


class RateLimiter:
    """
    Rate limiter using Redis for distributed rate limiting.
    
    Features:
    - Multiple strategies (fixed window, sliding window, token bucket)
    - Per-user, per-IP, and custom key rate limiting
    - Automatic cleanup of expired keys
    """
    
    def __init__(self):
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def check_fixed_window(
        self,
        key: str,
        limit: int,
        window: int,
        cost: int = 1,
    ) -> Tuple[bool, int, int]:
        """
        Fixed window rate limiter.
        
        Args:
            key: Rate limit key
            limit: Maximum requests per window
            window: Window size in seconds
            cost: Cost of this request
            
        Returns:
            Tuple of (allowed, remaining, retry_after)
        """
        redis = await self._get_redis()
        current_window = int(time.time() / window)
        window_key = f"rate_limit:fixed:{key}:{current_window}"
        
        current = await redis.incr(window_key, cost)
        if current == cost:
            await redis.expire(window_key, window)
        
        if current > limit:
            retry_after = window - (int(time.time()) % window)
            return False, 0, retry_after
        
        return True, limit - current, 0
    
    async def check_sliding_window(
        self,
        key: str,
        limit: int,
        window: int,
        cost: int = 1,
    ) -> Tuple[bool, int, int]:
        """
        Sliding window rate limiter using sorted set.
        
        Args:
            key: Rate limit key
            limit: Maximum requests per window
            window: Window size in seconds
            cost: Cost of this request
            
        Returns:
            Tuple of (allowed, remaining, retry_after)
        """
        redis = await self._get_redis()
        now = time.time()
        window_start = now - window
        
        redis_key = f"rate_limit:sliding:{key}"
        
        # Remove old entries
        await redis.zremrangebyscore(redis_key, 0, window_start)
        
        # Count current requests
        current = await redis.zcard(redis_key)
        
        if current + cost > limit:
            # Get oldest request time for retry after
            oldest = await redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                retry_after = int((oldest[0][1] + window) - now)
            else:
                retry_after = window
            return False, 0, max(1, retry_after)
        
        # Add current request
        for _ in range(cost):
            await redis.zadd(redis_key, {str(now): now})
        await redis.expire(redis_key, window)
        
        return True, limit - (current + cost), 0
    
    async def check_token_bucket(
        self,
        key: str,
        limit: int,
        window: int,
        cost: int = 1,
    ) -> Tuple[bool, int, int]:
        """
        Token bucket rate limiter.
        
        Args:
            key: Rate limit key
            limit: Maximum tokens (burst capacity)
            window: Refill window in seconds
            cost: Cost of this request
            
        Returns:
            Tuple of (allowed, remaining, retry_after)
        """
        redis = await self._get_redis()
        now = time.time()
        
        redis_key = f"rate_limit:token:{key}"
        rate = limit / window  # Tokens per second
        
        # Get current tokens
        tokens = await redis.hget(redis_key, "tokens")
        last_refill = await redis.hget(redis_key, "last_refill")
        
        if tokens is None:
            tokens = limit
            last_refill = now
        else:
            tokens = float(tokens)
            last_refill = float(last_refill)
            
            # Refill tokens
            elapsed = now - last_refill
            new_tokens = elapsed * rate
            if new_tokens > 0:
                tokens = min(limit, tokens + new_tokens)
                last_refill = now
        
        if tokens >= cost:
            tokens -= cost
            await redis.hset(redis_key, "tokens", tokens)
            await redis.hset(redis_key, "last_refill", last_refill)
            await redis.expire(redis_key, window * 2)
            return True, int(tokens), 0
        else:
            # Calculate time to wait for next token
            tokens_needed = cost - tokens
            wait_time = tokens_needed / rate
            return False, 0, int(wait_time) + 1
    
    async def check(
        self,
        key: str,
        limit: int,
        window: int,
        strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW,
        cost: int = 1,
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit.
        
        Args:
            key: Rate limit key
            limit: Maximum requests per window
            window: Window size in seconds
            strategy: Rate limiting strategy
            cost: Cost of this request
            
        Returns:
            Tuple of (allowed, remaining, retry_after)
        """
        if strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self.check_fixed_window(key, limit, window, cost)
        elif strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self.check_token_bucket(key, limit, window, cost)
        else:  # SLIDING_WINDOW (default)
            return await self.check_sliding_window(key, limit, window, cost)
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        redis = await self._get_redis()
        
        # Delete all rate limit keys for this key
        patterns = [
            f"rate_limit:fixed:{key}:*",
            f"rate_limit:sliding:{key}",
            f"rate_limit:token:{key}",
        ]
        
        for pattern in patterns:
            keys = await redis.keys(pattern)
            if keys:
                await redis.delete(*keys)


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(
    limit: int,
    window: int,
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW,
    key_func: Optional[Callable] = None,
    cost: int = 1,
):
    """
    Decorator for rate limiting functions/endpoints.
    
    Args:
        limit: Maximum requests per window
        window: Window size in seconds
        strategy: Rate limiting strategy
        key_func: Function to extract rate limit key from arguments
        cost: Cost of the operation
        
    Usage:
        @rate_limit(limit=10, window=60)
        async def my_endpoint(request):
            return {"message": "Hello"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine rate limit key
            if key_func:
                rate_key = key_func(*args, **kwargs)
            else:
                # Default: use function name and first argument
                arg_str = str(args[0]) if args else "default"
                rate_key = f"{func.__module__}.{func.__name__}:{arg_str}"
            
            # Check rate limit
            allowed, remaining, retry_after = await rate_limiter.check(
                key=rate_key,
                limit=limit,
                window=window,
                strategy=strategy,
                cost=cost,
            )
            
            if not allowed:
                raise RateLimitExceeded(limit, window, retry_after)
            
            # Execute function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


__all__ = [
    "RateLimiter",
    "RateLimitStrategy",
    "RateLimitExceeded",
    "rate_limiter",
    "rate_limit",
]