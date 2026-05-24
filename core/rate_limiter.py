# ============================
# WOLLOYEWA STORE BOT - RATE LIMITER
# ============================
"""Advanced rate limiting implementation with multiple strategies."""

import asyncio
import time
from enum import Enum
from typing import Dict, Optional, Tuple, Any, List
from dataclasses import dataclass, field
from collections import deque

from core.config import settings
from core.logger import logger


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    key: str
    limit: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_limit: Optional[int] = None
    
    def __post_init__(self):
        if self.burst_limit is None:
            self.burst_limit = self.limit


class FixedWindowLimiter:
    """Fixed window rate limiter."""
    
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._windows: Dict[str, Tuple[int, float]] = {}  # key -> (count, window_start)
    
    async def check(self, key: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier for the requester
            
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        current_time = time.time()
        current_window = int(current_time / self.window_seconds)
        
        if key not in self._windows or self._windows[key][1] != current_window:
            self._windows[key] = (1, current_window)
            return True, self.limit - 1
        
        count, window = self._windows[key]
        
        if count >= self.limit:
            return False, 0
        
        self._windows[key] = (count + 1, window)
        return True, self.limit - (count + 1)
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if key in self._windows:
            del self._windows[key]


class SlidingWindowLimiter:
    """Sliding window rate limiter using timestamps."""
    
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: Dict[str, deque] = field(default_factory=dict)
    
    async def check(self, key: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier for the requester
            
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        if key not in self._requests:
            self._requests[key] = deque()
        
        # Remove expired timestamps
        requests = self._requests[key]
        while requests and requests[0] < cutoff_time:
            requests.popleft()
        
        if len(requests) >= self.limit:
            return False, 0
        
        requests.append(current_time)
        return True, self.limit - len(requests)
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if key in self._requests:
            self._requests.pop(key, None)


class TokenBucketLimiter:
    """Token bucket rate limiter with burst support."""
    
    def __init__(self, limit: int, window_seconds: int, burst_limit: int = None):
        self.limit = limit  # Tokens per window
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit or limit
        self._tokens: Dict[str, float] = {}
        self._last_refill: Dict[str, float] = {}
        self._rate = limit / window_seconds  # Tokens per second
    
    async def check(self, key: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier for the requester
            
        Returns:
            Tuple of (allowed, remaining_tokens)
        """
        current_time = time.time()
        
        if key not in self._tokens:
            self._tokens[key] = self.burst_limit
            self._last_refill[key] = current_time
        
        # Refill tokens based on time passed
        time_passed = current_time - self._last_refill[key]
        new_tokens = time_passed * self._rate
        
        if new_tokens > 0:
            self._tokens[key] = min(self.burst_limit, self._tokens[key] + new_tokens)
            self._last_refill[key] = current_time
        
        if self._tokens[key] >= 1:
            self._tokens[key] -= 1
            remaining = int(self._tokens[key])
            return True, remaining
        
        return False, 0
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        self._tokens.pop(key, None)
        self._last_refill.pop(key, None)


class LeakyBucketLimiter:
    """Leaky bucket rate limiter for smooth request processing."""
    
    def __init__(self, limit: int, window_seconds: int, leak_rate: float = None):
        self.capacity = limit
        self.window_seconds = window_seconds
        self.leak_rate = leak_rate or (limit / window_seconds)  # Leak rate per second
        self._water: Dict[str, float] = {}
        self._last_leak: Dict[str, float] = {}
    
    async def check(self, key: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier for the requester
            
        Returns:
            Tuple of (allowed, remaining_capacity)
        """
        current_time = time.time()
        
        if key not in self._water:
            self._water[key] = 0
            self._last_leak[key] = current_time
        
        # Leak water based on time passed
        time_passed = current_time - self._last_leak[key]
        leaked = time_passed * self.leak_rate
        
        if leaked > 0:
            self._water[key] = max(0, self._water[key] - leaked)
            self._last_leak[key] = current_time
        
        if self._water[key] < self.capacity:
            self._water[key] += 1
            remaining = int(self.capacity - self._water[key])
            return True, remaining
        
        return False, 0
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        self._water.pop(key, None)
        self._last_leak.pop(key, None)


class RateLimiter:
    """
    Advanced rate limiter supporting multiple strategies.
    
    Usage:
        limiter = RateLimiter()
        allowed, remaining = await limiter.check("user:123", limit=60, window=60)
    """
    
    def __init__(self):
        self._limiters: Dict[str, Any] = {}
        self._redis_client = None
        self._use_redis = False
    
    async def _get_limiter(
        self,
        key: str,
        limit: int,
        window: int,
        strategy: RateLimitStrategy,
        burst_limit: Optional[int] = None,
    ) -> Any:
        """Get or create a rate limiter instance."""
        limiter_key = f"{key}:{limit}:{window}:{strategy.value}"
        
        if limiter_key not in self._limiters:
            if strategy == RateLimitStrategy.FIXED_WINDOW:
                self._limiters[limiter_key] = FixedWindowLimiter(limit, window)
            elif strategy == RateLimitStrategy.SLIDING_WINDOW:
                self._limiters[limiter_key] = SlidingWindowLimiter(limit, window)
            elif strategy == RateLimitStrategy.TOKEN_BUCKET:
                self._limiters[limiter_key] = TokenBucketLimiter(limit, window, burst_limit)
            elif strategy == RateLimitStrategy.LEAKY_BUCKET:
                self._limiters[limiter_key] = LeakyBucketLimiter(limit, window)
            else:
                self._limiters[limiter_key] = SlidingWindowLimiter(limit, window)
        
        return self._limiters[limiter_key]
    
    async def check(
        self,
        key: str,
        limit: int = None,
        window: int = None,
        strategy: RateLimitStrategy = None,
        burst_limit: Optional[int] = None,
    ) -> Tuple[bool, int, Optional[int]]:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier for the requester
            limit: Maximum requests allowed
            window: Time window in seconds
            strategy: Rate limiting strategy
            burst_limit: Burst limit for token bucket
            
        Returns:
            Tuple of (allowed, remaining, retry_after_seconds)
        """
        # Use default values if not provided
        limit = limit or settings.RATE_LIMIT_PER_MINUTE
        window = window or 60
        strategy = strategy or RateLimitStrategy(settings.RATE_LIMIT_STRATEGY)
        
        # Use Redis for distributed rate limiting if available
        if self._use_redis and self._redis_client:
            return await self._check_redis(key, limit, window, strategy)
        
        # Use in-memory rate limiter
        limiter = await self._get_limiter(key, limit, window, strategy, burst_limit)
        allowed, remaining = await limiter.check(key)
        
        retry_after = None
        if not allowed:
            retry_after = window
        
        return allowed, remaining, retry_after
    
    async def _check_redis(
        self,
        key: str,
        limit: int,
        window: int,
        strategy: RateLimitStrategy,
    ) -> Tuple[bool, int, Optional[int]]:
        """Check rate limit using Redis for distributed environments."""
        try:
            redis_key = f"rate_limit:{key}"
            current_time = time.time()
            window_start = current_time - window
            
            # Use Redis sorted set for sliding window
            if strategy == RateLimitStrategy.SLIDING_WINDOW:
                # Remove old entries
                await self._redis_client.zremrangebyscore(redis_key, 0, window_start)
                
                # Count current requests
                count = await self._redis_client.zcard(redis_key)
                
                if count < limit:
                    # Add current request
                    await self._redis_client.zadd(redis_key, {str(current_time): current_time})
                    await self._redis_client.expire(redis_key, window)
                    return True, limit - count - 1, None
                
                # Get oldest request time for retry after
                oldest = await self._redis_client.zrange(redis_key, 0, 0, withscores=True)
                retry_after = int((oldest[0][1] + window) - current_time) if oldest else window
                return False, 0, max(1, retry_after)
            
            # Simple counter for other strategies
            count = await self._redis_client.incr(redis_key)
            if count == 1:
                await self._redis_client.expire(redis_key, window)
            
            if count > limit:
                ttl = await self._redis_client.ttl(redis_key)
                return False, 0, max(1, ttl)
            
            return True, limit - count, None
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}, falling back to in-memory")
            self._use_redis = False
            return await self.check(key, limit, window, strategy, burst_limit)
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        for limiter in self._limiters.values():
            await limiter.reset(key)
        
        if self._redis_client:
            await self._redis_client.delete(f"rate_limit:{key}")
    
    def set_redis_client(self, redis_client) -> None:
        """Set Redis client for distributed rate limiting."""
        self._redis_client = redis_client
        self._use_redis = True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics."""
        return {
            "use_redis": self._use_redis,
            "active_limiters": len(self._limiters),
            "strategy": settings.RATE_LIMIT_STRATEGY,
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============================
# Rate Limit Decorator
# ============================

def rate_limit(
    limit: int = None,
    window: int = None,
    strategy: RateLimitStrategy = None,
    key_func: Optional[Callable] = None,
):
    """
    Decorator for rate limiting functions/endpoints.
    
    Args:
        limit: Maximum requests allowed
        window: Time window in seconds
        strategy: Rate limiting strategy
        key_func: Function to extract rate limit key from arguments
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get rate limit key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default: use function name and first argument
                key = f"{func.__name__}:{args[0] if args else 'default'}"
            
            # Check rate limit
            allowed, remaining, retry_after = await rate_limiter.check(
                key=key,
                limit=limit,
                window=window,
                strategy=strategy,
            )
            
            if not allowed:
                raise RateLimitError(retry_after=retry_after)
            
            # Add remaining limit to response headers if possible
            if hasattr(args[0], 'headers') if args else False:
                # FastAPI response object
                args[0].headers["X-RateLimit-Remaining"] = str(remaining)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================
# Per-User Rate Limiter
# ============================

class UserRateLimiter:
    """Specialized rate limiter for user-specific limits."""
    
    def __init__(self):
        self._limits: Dict[str, RateLimitConfig] = {}
    
    def set_user_limit(
        self,
        user_id: int,
        limit: int,
        window: int,
        strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW,
    ) -> None:
        """Set custom rate limit for a specific user."""
        key = f"user:{user_id}"
        self._limits[key] = RateLimitConfig(
            key=key,
            limit=limit,
            window_seconds=window,
            strategy=strategy,
        )
    
    async def check_user(self, user_id: int) -> Tuple[bool, int, Optional[int]]:
        """Check rate limit for a specific user."""
        key = f"user:{user_id}"
        
        if key in self._limits:
            config = self._limits[key]
            return await rate_limiter.check(
                key=key,
                limit=config.limit,
                window=config.window_seconds,
                strategy=config.strategy,
            )
        
        # Default limit
        return await rate_limiter.check(
            key=key,
            limit=settings.RATE_LIMIT_PER_MINUTE,
            window=60,
        )


# Global user rate limiter
user_rate_limiter = UserRateLimiter()


__all__ = [
    "RateLimiter",
    "RateLimitStrategy",
    "RateLimitConfig",
    "rate_limiter",
    "user_rate_limiter",
    "rate_limit",
    "UserRateLimiter",
]