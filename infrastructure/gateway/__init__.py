# ============================
# WOLLOYEWA STORE BOT - API GATEWAY MODULE
# ============================
"""API Gateway for routing, circuit breaking, and request handling."""

from infrastructure.gateway.router import (
    GatewayRouter,
    Route,
    RouteConfig,
    add_route,
    remove_route,
    get_route,
)
from infrastructure.gateway.circuit_breaker_v2 import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig,
    circuit_breaker,
    get_circuit_breaker,
)
from infrastructure.gateway.retry_policies import (
    RetryPolicy,
    RetryConfig,
    ExponentialBackoff,
    FixedBackoff,
    retry_request,
    RetryableError,
)
from infrastructure.gateway.request_validator import (
    RequestValidator,
    ValidationRule,
    validate_request,
    sanitize_request,
)
from infrastructure.gateway.response_cache import (
    ResponseCache,
    cache_response,
    get_cached_response,
    invalidate_cache,
    CacheStrategy,
)
from infrastructure.gateway.api_versioning import (
    APIVersioning,
    VersionedRouter,
    version_route,
    get_versioned_handler,
    VersionNegotiator,
)

__all__ = [
    # Router
    "GatewayRouter",
    "Route",
    "RouteConfig",
    "add_route",
    "remove_route",
    "get_route",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerConfig",
    "circuit_breaker",
    "get_circuit_breaker",
    # Retry Policies
    "RetryPolicy",
    "RetryConfig",
    "ExponentialBackoff",
    "FixedBackoff",
    "retry_request",
    "RetryableError",
    # Request Validator
    "RequestValidator",
    "ValidationRule",
    "validate_request",
    "sanitize_request",
    # Response Cache
    "ResponseCache",
    "cache_response",
    "get_cached_response",
    "invalidate_cache",
    "CacheStrategy",
    # API Versioning
    "APIVersioning",
    "VersionedRouter",
    "version_route",
    "get_versioned_handler",
    "VersionNegotiator",
]