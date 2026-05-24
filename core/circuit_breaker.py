# ============================
# WOLLOYEWA STORE BOT - CIRCUIT BREAKER
# ============================
"""Circuit breaker pattern for handling external service failures."""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Awaitable, Union
from functools import wraps

from core.logger import logger

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests go through
    OPEN = "open"          # Failure threshold reached, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Circuit breaker for '{service_name}' is open. Service unavailable.")


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting against cascading failures.
    
    Monitors failures and opens the circuit when threshold is reached,
    allowing the service to recover before allowing requests again.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
        success_threshold: int = 2,
        exclude_exceptions: Optional[tuple] = None,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name/identifier
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before moving to half-open
            half_open_max_calls: Max calls allowed in half-open state
            success_threshold: Number of successes needed to close circuit
            exclude_exceptions: Exceptions that don't count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        self.exclude_exceptions = exclude_exceptions or ()
        
        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change_time: float = time.time()
        self._half_open_calls_made = 0
        
        # Locks for thread safety
        self._lock = asyncio.Lock()
        
        # Metrics
        self._total_failures = 0
        self._total_successes = 0
        self._total_opens = 0
        self._total_half_opens = 0
    
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
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.recovery_timeout
    
    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception from the called function
        """
        async with self._lock:
            await self._check_state_before_call()
        
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            # Check if exception should be excluded from failure counting
            if not isinstance(e, self.exclude_exceptions):
                await self._record_failure()
            raise
    
    async def _check_state_before_call(self) -> None:
        """Check circuit state before allowing a call."""
        if self._state == CircuitState.CLOSED:
            return
        
        elif self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                await self._transition_to_half_open()
            else:
                raise CircuitBreakerError(self.name)
        
        elif self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls_made >= self.half_open_max_calls:
                raise CircuitBreakerError(self.name)
            self._half_open_calls_made += 1
    
    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._total_successes += 1
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                
                if self._success_count >= self.success_threshold:
                    await self._transition_to_closed()
            
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0
    
    async def _record_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    await self._transition_to_open()
            
            elif self._state == CircuitState.HALF_OPEN:
                await self._transition_to_open()
    
    async def _transition_to_open(self) -> None:
        """Transition circuit to open state."""
        if self._state != CircuitState.OPEN:
            self._state = CircuitState.OPEN
            self._last_state_change_time = time.time()
            self._total_opens += 1
            logger.warning(
                f"Circuit breaker '{self.name}' opened after {self._failure_count} failures"
            )
    
    async def _transition_to_half_open(self) -> None:
        """Transition circuit to half-open state."""
        if self._state != CircuitState.HALF_OPEN:
            self._state = CircuitState.HALF_OPEN
            self._last_state_change_time = time.time()
            self._success_count = 0
            self._half_open_calls_made = 0
            self._total_half_opens += 1
            logger.info(f"Circuit breaker '{self.name}' transitioned to half-open")
    
    async def _transition_to_closed(self) -> None:
        """Transition circuit to closed state."""
        if self._state != CircuitState.CLOSED:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls_made = 0
            self._last_state_change_time = time.time()
            logger.info(f"Circuit breaker '{self.name}' closed (recovered)")
    
    async def reset(self) -> None:
        """Force reset circuit breaker to closed state."""
        async with self._lock:
            await self._transition_to_closed()
            logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "total_opens": self._total_opens,
            "total_half_opens": self._total_half_opens,
            "last_failure_time": self._last_failure_time,
            "last_state_change_time": self._last_state_change_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


# ============================
# Circuit Breaker Registry
# ============================

class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    _instance: Optional['CircuitBreakerRegistry'] = None
    _breakers: Dict[str, CircuitBreaker]
    
    def __new__(cls) -> 'CircuitBreakerRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._breakers = {}
        return cls._instance
    
    def get_or_create(
        self,
        name: str,
        **kwargs,
    ) -> CircuitBreaker:
        """
        Get existing circuit breaker or create a new one.
        
        Args:
            name: Circuit breaker name
            **kwargs: Circuit breaker configuration parameters
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, **kwargs)
        return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        return {
            name: breaker.get_metrics()
            for name, breaker in self._breakers.items()
        }
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()


# ============================
# Decorator for Circuit Breaker
# ============================

def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    **kwargs,
):
    """
    Decorator to wrap a function with circuit breaker protection.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before moving to half-open
        **kwargs: Additional circuit breaker parameters
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        breaker = circuit_breaker_registry.get_or_create(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            **kwargs,
        )
        
        @wraps(func)
        async def wrapper(*args, **func_kwargs):
            return await breaker.call(func, *args, **func_kwargs)
        
        return wrapper
    
    return decorator


# ============================
# Pre-configured Circuit Breakers
# ============================

# Payment gateway circuit breakers
payment_circuit_breaker = circuit_breaker_registry.get_or_create(
    name="payment_gateway",
    failure_threshold=3,
    recovery_timeout=30.0,
)

# Telegram API circuit breaker
telegram_circuit_breaker = circuit_breaker_registry.get_or_create(
    name="telegram_api",
    failure_threshold=5,
    recovery_timeout=60.0,
)

# Database circuit breaker
database_circuit_breaker = circuit_breaker_registry.get_or_create(
    name="database",
    failure_threshold=3,
    recovery_timeout=15.0,
)

# Redis circuit breaker
redis_circuit_breaker = circuit_breaker_registry.get_or_create(
    name="redis",
    failure_threshold=3,
    recovery_timeout=15.0,
)


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitState",
    "circuit_breaker_registry",
    "circuit_breaker",
    "payment_circuit_breaker",
    "telegram_circuit_breaker",
    "database_circuit_breaker",
    "redis_circuit_breaker",
]