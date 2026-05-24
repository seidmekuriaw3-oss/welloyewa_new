# ============================
# WOLLOYEWA STORE BOT - RETRY POLICIES
# ============================
"""Retry policies for resilient service communication."""

import asyncio
import random
from enum import Enum
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from functools import wraps

from core.logger import logger


class RetryableError(Exception):
    """Exception that should trigger a retry."""
    pass


class RetryStrategy(str, Enum):
    """Retry backoff strategies."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"
    FULL_JITTER = "full_jitter"


@dataclass
class RetryConfig:
    """Configuration for retry policy."""
    
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    multiplier: float = 2.0
    retry_on: List[Union[int, Exception]] = field(default_factory=list)
    retry_on_timeout: bool = True
    jitter: bool = True


class RetryPolicy:
    """
    Retry policy for resilient operations.
    
    Features:
    - Multiple backoff strategies
    - Configurable retry conditions
    - Jitter to prevent thundering herd
    - Max retry limits
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt.
        
        Args:
            attempt: Attempt number (1-indexed)
            
        Returns:
            Delay in seconds
        """
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.initial_delay
        
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.initial_delay * attempt
        
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.initial_delay * (self.config.multiplier ** (attempt - 1))
        
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            delay = self.config.initial_delay * (self.config.multiplier ** (attempt - 1))
            if self.config.jitter:
                delay = delay * (0.5 + random.random())
        
        elif self.config.strategy == RetryStrategy.FULL_JITTER:
            max_delay = self.config.initial_delay * (self.config.multiplier ** (attempt - 1))
            delay = random.uniform(0, max_delay)
        
        else:
            delay = self.config.initial_delay
        
        return min(delay, self.config.max_delay)
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """
        Determine if a retry should be attempted.
        
        Args:
            attempt: Current attempt number
            exception: The exception that occurred
            
        Returns:
            True if should retry
        """
        if attempt >= self.config.max_attempts:
            return False
        
        # Check if exception type should trigger retry
        if self.config.retry_on:
            for retry_type in self.config.retry_on:
                if isinstance(retry_type, type) and isinstance(exception, retry_type):
                    return True
                if isinstance(retry_type, int) and hasattr(exception, 'status_code'):
                    if exception.status_code == retry_type:
                        return True
        
        # Check for timeout
        if self.config.retry_on_timeout and isinstance(exception, asyncio.TimeoutError):
            return True
        
        # Check for RetryableError
        if isinstance(exception, RetryableError):
            return True
        
        return False
    
    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                
                if self.should_retry(attempt, e):
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Retry {attempt}/{self.config.max_attempts} for {func.__name__} "
                        f"after {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise last_exception


class ExponentialBackoff:
    """
    Exponential backoff with jitter.
    
    Usage:
        backoff = ExponentialBackoff()
        async for delay in backoff.retry():
            await operation()
    """
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        max_attempts: int = 5,
        jitter: bool = True,
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.jitter = jitter
    
    def _get_delay(self, attempt: int) -> float:
        """Get delay for the given attempt."""
        delay = self.base_delay * (2 ** attempt)
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return min(delay, self.max_delay)
    
    async def retry(self):
        """Async iterator for retry attempts."""
        for attempt in range(self.max_attempts):
            yield attempt
            if attempt < self.max_attempts - 1:
                delay = self._get_delay(attempt)
                await asyncio.sleep(delay)


class FixedBackoff:
    """Fixed delay backoff."""
    
    def __init__(self, delay: float = 1.0, max_attempts: int = 3):
        self.delay = delay
        self.max_attempts = max_attempts
    
    async def retry(self):
        """Async iterator for retry attempts."""
        for attempt in range(self.max_attempts):
            yield attempt
            if attempt < self.max_attempts - 1:
                await asyncio.sleep(self.delay)


async def retry_request(
    func: Callable,
    *args,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    **kwargs,
) -> Any:
    """
    Retry a function with configurable backoff.
    
    Args:
        func: Function to execute
        *args: Positional arguments
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries
        strategy: Retry strategy
        **kwargs: Keyword arguments for func
        
    Returns:
        Function result
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        strategy=strategy,
    )
    policy = RetryPolicy(config)
    return await policy.execute(func, *args, **kwargs)


__all__ = [
    "RetryPolicy",
    "RetryConfig",
    "RetryStrategy",
    "RetryableError",
    "ExponentialBackoff",
    "FixedBackoff",
    "retry_request",
]