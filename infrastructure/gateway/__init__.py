# ============================
# WOLLOYEWA STORE BOT - API GATEWAY MODULE
# ============================
"""API Gateway for routing, circuit breaking, and request handling."""

from infrastructure.gateway.api_versioning import (
    APIVersioning,
    VersionedRouter,
    VersionNegotiator,
    get_versioned_handler,
    version_route,
)
from infrastructure.gateway.circuit_breaker_v2 import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    circuit_breaker,
    get_circuit_breaker,
)
from infrastructure.gateway.request_validator import (
    RequestValidator,
    ValidationRule,
    sanitize_request,
    validate_request,
)
from infrastructure.gateway.response_cache import (
    CacheStrategy,
    ResponseCache,
    cache_response,
    get_cached_response,
    invalidate_cache,
)
from infrastructure.gateway.retry_policies import (
    ExponentialBackoff,
    FixedBackoff,
    RetryableError,
    RetryConfig,
    RetryPolicy,
    retry_request,
)
from infrastructure.gateway.router import (
    GatewayRouter,
    Route,
    RouteConfig,
    add_route,
    get_route,
    remove_route,
)

__all__ = [
    # API Versioning
    "APIVersioning",
    "CacheStrategy",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "ExponentialBackoff",
    "FixedBackoff",
    # Router
    "GatewayRouter",
    # Request Validator
    "RequestValidator",
    # Response Cache
    "ResponseCache",
    "RetryConfig",
    # Retry Policies
    "RetryPolicy",
    "RetryableError",
    "Route",
    "RouteConfig",
    "ValidationRule",
    "VersionNegotiator",
    "VersionedRouter",
    "add_route",
    "cache_response",
    "circuit_breaker",
    "get_cached_response",
    "get_circuit_breaker",
    "get_route",
    "get_versioned_handler",
    "invalidate_cache",
    "remove_route",
    "retry_request",
    "sanitize_request",
    "validate_request",
    "version_route",
]
