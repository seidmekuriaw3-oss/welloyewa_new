# ============================
# WOLLOYEWA STORE BOT - CIRCUIT BREAKER V2
# ============================
"""Enhanced circuit breaker for service protection."""

import time
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, Callable, TypeVar
from dataclasses import dataclass, field
from functools import wraps

from core.logger import logger

T = TypeVar('T')


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"    # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: float = 60.0      # Seconds before attempting reset
    half_open_max_calls: int = 3        # Max calls in half-open state
    success_threshold: int = 2          # Successes needed to close
    timeout: float = 30.0               # Request timeout in seconds
    exclude_exceptions: tuple = ()      # Exceptions that don't count as failures


class CircuitBreaker:
    """
    Enhanced circuit breaker for service protection.
    
    Features:
    - Prevents cascading failures
    - Automatic recovery detection
    - Request timeout handling
    - Metrics collection
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change_time: float = time.time()
        self._half_open_calls = 0
        
        # Metrics
        self._total_requests = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_timeouts = 0
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self._state == CircuitState.HALF_OPEN
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        self._total_requests += 1
        
        # Check if we can proceed
        if not await self._can_proceed():
            raise CircuitOpenError(f"Circuit '{self.name}' is open")
        
        # Execute with timeout
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs),
                    timeout=self.config.timeout
                )
            
            await self._record_success()
            return result
            
        except asyncio.TimeoutError:
            self._total_timeouts += 1
            await self._record_failure("timeout")
            raise CircuitTimeoutError(f"Request to '{self.name}' timed out after {self.config.timeout}s")
            
        except Exception as e:
            # Check if exception should be excluded
            if isinstance(e, self.config.exclude_exceptions):
                raise
            
            await self._record_failure(str(e))
            raise
    
    async def _can_proceed(self) -> bool:
        """Check if request can proceed."""
        if self._state == CircuitState.CLOSED:
            return True
        
        elif self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.config.recovery_timeout:
                await self._transition_to_half_open()
                return True
            return False
        
        elif self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
        
        return False
    
    async def _record_success(self) -> None:
        """Record a successful request."""
        self._total_successes += 1
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                await self._transition_to_closed()
        
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
    
    async def _record_failure(self, reason: str) -> None:
        """Record a failed request."""
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                await self._transition_to_open(reason)
        
        elif self._state == CircuitState.HALF_OPEN:
            await self._transition_to_open(reason)
    
    async def _transition_to_closed(self) -> None:
        """Transition circuit to closed state."""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_state_change_time = time.time()
        
        logger.info(f"Circuit '{self.name}' closed (was {old_state.value})")
    
    async def _transition_to_open(self, reason: str = None) -> None:
        """Transition circuit to open state."""
        old_state = self._state
        self._state = CircuitState.OPEN
        self._last_state_change_time = time.time()
        
        logger.warning(f"Circuit '{self.name}' opened (was {old_state.value}) - {reason}")
    
    async def _transition_to_half_open(self) -> None:
        """Transition circuit to half-open state."""
        old_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._half_open_calls = 0
        self._last_state_change_time = time.time()
        
        logger.info(f"Circuit '{self.name}' half-open (was {old_state.value})")
    
    async def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        await self._transition_to_closed()
        logger.info(f"Circuit '{self.name}' manually reset")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_requests": self._total_requests,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "total_timeouts": self._total_timeouts,
            "last_failure_time": self._last_failure_time,
            "last_state_change": self._last_state_change_time,
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout,
        }


class CircuitOpenError(Exception):
    """Raised when circuit is open."""
    pass


class CircuitTimeoutError(Exception):
    """Raised when request times out."""
    pass


# Registry of circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """
    Get or create a circuit breaker.
    
    Args:
        name: Circuit breaker name
        config: Configuration (only used when creating new)
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator for circuit breaker protection.
    
    Args:
        name: Circuit breaker name
        config: Configuration
        
    Usage:
        @circuit_breaker("payment_service")
        async def process_payment():
            ...
    """
    def decorator(func: Callable):
        cb = get_circuit_breaker(name, config)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await cb.call(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "CircuitOpenError",
    "CircuitTimeoutError",
    "get_circuit_breaker",
    "circuit_breaker",
]