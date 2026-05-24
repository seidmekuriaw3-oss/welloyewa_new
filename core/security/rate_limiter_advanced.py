# ============================
# WOLLOYEWA STORE BOT - ADVANCED RATE LIMITER
# ============================
"""Advanced rate limiting with multiple strategies and distributed support."""

import asyncio
import time
from enum import Enum
from typing import Dict, Any, Optional, Tuple, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from functools import wraps

from core.config import settings
from core.logger import logger


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    GCRA = "gcra"  # Generic Cell Rate Algorithm


@dataclass
class RateLimitConfig:
    """Configuration for rate limiter."""
    
    key: str
    limit: int
    period: int  # seconds
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst: Optional[int] = None
    cost: int = 1
    
    def __post_init__(self):
        if self.burst is None:
            self.burst = self.limit


class SlidingWindowCounter:
    """Sliding window counter implementation."""
    
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self._counters: Dict[str, Tuple[float, int]] = {}  # key -> (window_start, count)
    
    async def check(self, key: str, cost: int = 1) -> Tuple[bool, int]:
        """Check if request is allowed."""
        now = time.time()
        current_window = int(now / self.window)
        
        if key not in self._counters or self._counters[key][0] != current_window:
            self._counters[key] = (current_window, cost)
            return True, self.limit - cost
        
        count = self._counters[key][1] + cost
        
        if count > self.limit:
            return False, 0
        
        self._counters[key] = (current_window, count)
        return True, self.limit - count


class TokenBucket:
    """Token bucket algorithm implementation."""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self._tokens: Dict[str, float] = {}
        self._last_refill: Dict[str, float] = {}
    
    async def check(self, key: str, cost: int = 1) -> Tuple[bool, int]:
        """Check if request is allowed."""
        now = time.time()
        
        if key not in self._tokens:
            self._tokens[key] = self.capacity
            self._last_refill[key] = now
        
        # Refill tokens
        elapsed = now - self._last_refill[key]
        new_tokens = elapsed * self.rate
        self._tokens[key] = min(self.capacity, self._tokens[key] + new_tokens)
        self._last_refill[key] = now
        
        if self._tokens[key] >= cost:
            self._tokens[key] -= cost
            return True, int(self._tokens[key])
        
        return False, 0


class GCRA:
    """Generic Cell Rate Algorithm for precise rate limiting."""
    
    def __init__(self, rate: float, burst: int):
        self.rate = rate  # requests per second
        self.burst = burst
        self._tats: Dict[str, float] = {}  # Theoretical Arrival Time
    
    async def check(self, key: str, cost: int = 1) -> Tuple[bool, float]:
        """Check if request is allowed."""
        now = time.time()
        tat = self._tats.get(key, now)
        
        # Calculate theoretical arrival time
        tat = max(tat, now) + cost / self.rate
        
        # Check if burst limit exceeded
        if tat - now > self.burst / self.rate:
            return False, tat - now
        
        self._tats[key] = tat
        return True, 0


class AdvancedRateLimiter:
    """
    Advanced rate limiter with multiple strategies and distributed support.
    
    Features:
    - Multiple algorithms (fixed window, sliding window, token bucket, GCRA)
    - Distributed support with Redis
    - Dynamic configuration
    - Metrics collection
    """
    
    def __init__(self):
        self._redis_client = None
        self._use_redis = False
        self._strategies: Dict[str, Any] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"allowed": 0, "denied": 0})
    
    def configure(
        self,
        key: str,
        limit: int,
        period: int,
        strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW,
        burst: Optional[int] = None,
        cost: int = 1,
    ) -> None:
        """Configure rate limiter for a key pattern."""
        config = RateLimitConfig(
            key=key,
            limit=limit,
            period=period,
            strategy=strategy,
            burst=burst,
            cost=cost,
        )
        self._configs[key] = config
        logger.debug(f"Configured rate limiter for {key}: {limit} per {period}s using {strategy.value}")
    
    def _get_config(self, key: str) -> Optional[RateLimitConfig]:
        """Get config for a key (with pattern matching)."""
        # Exact match first
        if key in self._configs:
            return self._configs[key]
        
        # Pattern matching (prefix)
        for pattern, config in self._configs.items():
            if pattern.endswith("*") and key.startswith(pattern[:-1]):
                return config
        
        # Default config
        return RateLimitConfig(
            key=key,
            limit=settings.RATE_LIMIT_PER_MINUTE,
            period=60,
            strategy=RateLimitStrategy(settings.RATE_LIMIT_STRATEGY),
        )
    
    async def _check_local(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> Tuple[bool, int, Optional[int]]:
        """Check rate limit using in-memory strategy."""
        strategy_key = f"{config.strategy.value}:{key}"
        
        if config.strategy == RateLimitStrategy.FIXED_WINDOW:
            if strategy_key not in self._strategies:
                self._strategies[strategy_key] = SlidingWindowCounter(
                    config.limit,
                    config.period
                )
            limiter = self._strategies[strategy_key]
            allowed, remaining = await limiter.check(key, config.cost)
            return allowed, remaining, None
        
        elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            if strategy_key not in self._strategies:
                rate = config.limit / config.period
                self._strategies[strategy_key] = TokenBucket(rate, config.burst)
            limiter = self._strategies[strategy_key]
            allowed, remaining = await limiter.check(key, config.cost)
            return allowed, remaining, None
        
        elif config.strategy == RateLimitStrategy.GCRA:
            if strategy_key not in self._strategies:
                rate = config.limit / config.period
                self._strategies[strategy_key] = GCRA(rate, config.burst)
            limiter = self._strategies[strategy_key]
            allowed, retry_after = await limiter.check(key, config.cost)
            return allowed, 0, int(retry_after) if not allowed else None
        
        else:  # SLIDING_WINDOW
            if strategy_key not in self._strategies:
                self._strategies[strategy_key] = SlidingWindowCounter(
                    config.limit,
                    config.period
                )
            limiter = self._strategies[strategy_key]
            allowed, remaining = await limiter.check(key, config.cost)
            return allowed, remaining, None
    
    async def _check_redis(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> Tuple[bool, int, Optional[int]]:
        """Check rate limit using Redis for distributed environments."""
        if not self._redis_client:
            return await self._check_local(key, config)
        
        try:
            redis_key = f"rate_limit:{config.strategy.value}:{key}"
            
            if config.strategy == RateLimitStrategy.FIXED_WINDOW:
                # Simple counter
                current = await self._redis_client.incr(redis_key)
                if current == 1:
                    await self._redis_client.expire(redis_key, config.period)
                
                if current > config.limit:
                    ttl = await self._redis_client.ttl(redis_key)
                    return False, 0, max(1, ttl)
                
                return True, config.limit - current, None
            
            elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                # Sorted set for sliding window
                now = time.time()
                window_start = now - config.period
                
                # Remove old entries
                await self._redis_client.zremrangebyscore(redis_key, 0, window_start)
                
                # Count current requests
                count = await self._redis_client.zcard(redis_key)
                
                if count < config.limit:
                    # Add current request
                    await self._redis_client.zadd(redis_key, {str(now): now})
                    await self._redis_client.expire(redis_key, config.period)
                    return True, config.limit - count - 1, None
                
                # Get oldest request for retry after
                oldest = await self._redis_client.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int((oldest[0][1] + config.period) - now)
                    return False, 0, max(1, retry_after)
                
                return False, 0, config.period
            
            else:
                # Fallback to local for other strategies
                return await self._check_local(key, config)
                
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return await self._check_local(key, config)
    
    async def check(
        self,
        key: str,
        limit: Optional[int] = None,
        period: Optional[int] = None,
        strategy: Optional[RateLimitStrategy] = None,
        cost: int = 1,
    ) -> Tuple[bool, int, Optional[int]]:
        """
        Check if request is allowed.
        
        Args:
            key: Rate limit key
            limit: Maximum requests (overrides config)
            period: Time period in seconds (overrides config)
            strategy: Rate limit strategy (overrides config)
            cost: Cost of this request (default 1)
            
        Returns:
            Tuple of (allowed, remaining, retry_after)
        """
        config = self._get_config(key)
        
        # Override with explicit parameters
        if limit is not None:
            config.limit = limit
        if period is not None:
            config.period = period
        if strategy is not None:
            config.strategy = strategy
        config.cost = cost
        
        if self._use_redis and self._redis_client:
            return await self._check_redis(key, config)
        else:
            return await self._check_local(key, config)
    
    def set_redis_client(self, redis_client) -> None:
        """Set Redis client for distributed rate limiting."""
        self._redis_client = redis_client
        self._use_redis = True
        logger.info("Advanced rate limiter using Redis for distributed coordination")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics."""
        return {
            "use_redis": self._use_redis,
            "active_limiters": len(self._strategies),
            "configs": len(self._configs),
            "metrics": dict(self._metrics),
        }


# Global rate limiter instance
advanced_rate_limiter = AdvancedRateLimiter()


def rate_limit(
    key: Optional[str] = None,
    limit: Optional[int] = None,
    period: Optional[int] = None,
    strategy: Optional[RateLimitStrategy] = None,
    cost: int = 1,
    key_func: Optional[Callable] = None,
):
    """
    Decorator for rate limiting functions/endpoints.
    
    Args:
        key: Rate limit key (static or function that returns key)
        limit: Maximum requests
        period: Time period in seconds
        strategy: Rate limit strategy
        cost: Cost of the operation
        key_func: Function to extract dynamic key from arguments
        
    Usage:
        @rate_limit(key="api:search", limit=10, period=60)
        async def search_endpoint():
            pass
        
        @rate_limit(key_func=lambda u, *a: f"user:{u.id}")
        async def user_action(user):
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Determine rate limit key
            rate_key = key
            if key_func:
                rate_key = key_func(*args, **kwargs)
            elif rate_key is None:
                rate_key = f"decorator:{func.__module__}:{func.__name__}"
            
            # Check rate limit
            allowed, remaining, retry_after = await advanced_rate_limiter.check(
                key=rate_key,
                limit=limit,
                period=period,
                strategy=strategy,
                cost=cost,
            )
            
            if not allowed:
                from core.exceptions import RateLimitError
                raise RateLimitError(retry_after=retry_after)
            
            # Add rate limit headers if response object exists
            if args and hasattr(args[0], 'headers'):
                args[0].headers["X-RateLimit-Limit"] = str(limit or advanced_rate_limiter._get_config(rate_key).limit)
                args[0].headers["X-RateLimit-Remaining"] = str(remaining)
                if retry_after:
                    args[0].headers["Retry-After"] = str(retry_after)
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Determine rate limit key
            rate_key = key
            if key_func:
                rate_key = key_func(*args, **kwargs)
            elif rate_key is None:
                rate_key = f"decorator:{func.__module__}:{func.__name__}"
            
            # For sync functions, create a new event loop or use asyncio.run
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            allowed, remaining, retry_after = loop.run_until_complete(
                advanced_rate_limiter.check(
                    key=rate_key,
                    limit=limit,
                    period=period,
                    strategy=strategy,
                    cost=cost,
                )
            )
            loop.close()
            
            if not allowed:
                from core.exceptions import RateLimitError
                raise RateLimitError(retry_after=retry_after)
            
            return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


__all__ = [
    "AdvancedRateLimiter",
    "RateLimitConfig",
    "RateLimitStrategy",
    "advanced_rate_limiter",
    "rate_limit",
]