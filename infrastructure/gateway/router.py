# ============================
# WOLLOYEWA STORE BOT - GATEWAY ROUTER
# ============================
"""API Gateway router for request routing and service discovery."""

import re
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from core.logger import logger


class RouteMethod(str, Enum):
    """HTTP methods for routes."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class RouteConfig:
    """Configuration for a route."""
    
    path: str
    method: RouteMethod
    handler: Callable
    service_name: str
    service_url: str
    timeout: int = 30
    rate_limit: Optional[int] = None
    rate_limit_window: int = 60
    require_auth: bool = True
    allowed_roles: List[str] = field(default_factory=list)
    circuit_breaker_enabled: bool = True
    retry_enabled: bool = True
    max_retries: int = 3
    cache_ttl: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Route:
    """Route definition with pattern matching."""
    
    def __init__(self, config: RouteConfig):
        self.config = config
        self._path_pattern = self._compile_path_pattern(config.path)
    
    def _compile_path_pattern(self, path: str) -> re.Pattern:
        """Compile path pattern for variable extraction."""
        # Convert {variable} to regex group
        pattern = re.sub(r'\{([^}]+)\}', r'(?P<\1>[^/]+)', path)
        return re.compile(f"^{pattern}$")
    
    def matches(self, path: str, method: str) -> bool:
        """Check if route matches the request."""
        return (
            method.upper() == self.config.method.value and
            self._path_pattern.match(path) is not None
        )
    
    def extract_params(self, path: str) -> Dict[str, str]:
        """Extract path parameters from URL."""
        match = self._path_pattern.match(path)
        return match.groupdict() if match else {}
    
    async def handle(self, request: Any, **kwargs) -> Any:
        """Handle the request."""
        return await self.config.handler(request, **kwargs)


class GatewayRouter:
    """
    API Gateway router for request routing.
    
    Features:
    - Path-based routing with variable extraction
    - Service discovery integration
    - Route configuration management
    - Dynamic route addition/removal
    """
    
    def __init__(self):
        self._routes: List[Route] = []
        self._route_map: Dict[str, Route] = {}
    
    def add_route(self, config: RouteConfig) -> None:
        """
        Add a new route.
        
        Args:
            config: Route configuration
        """
        route = Route(config)
        self._routes.append(route)
        route_key = f"{config.method.value}:{config.path}"
        self._route_map[route_key] = route
        logger.info(f"Added route: {config.method.value} {config.path} -> {config.service_name}")
    
    def remove_route(self, method: str, path: str) -> bool:
        """
        Remove a route.
        
        Args:
            method: HTTP method
            path: Route path
            
        Returns:
            True if route was removed
        """
        route_key = f"{method.upper()}:{path}"
        
        if route_key in self._route_map:
            del self._route_map[route_key]
            self._routes = [r for r in self._routes if r.config.method.value != method.upper() or r.config.path != path]
            logger.info(f"Removed route: {method} {path}")
            return True
        
        return False
    
    def get_route(self, path: str, method: str) -> Optional[Route]:
        """
        Get a route that matches the request.
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            Matching route or None
        """
        method = method.upper()
        
        for route in self._routes:
            if route.matches(path, method):
                return route
        
        return None
    
    async def route_request(self, request: Any) -> Optional[Any]:
        """
        Route a request to the appropriate handler.
        
        Args:
            request: Request object with path and method
            
        Returns:
            Handler response or None
        """
        path = getattr(request, 'path', request.get('path', '/'))
        method = getattr(request, 'method', request.get('method', 'GET'))
        
        route = self.get_route(path, method)
        
        if not route:
            logger.warning(f"No route found for {method} {path}")
            return None
        
        # Extract path parameters
        path_params = route.extract_params(path)
        
        # Handle request
        try:
            response = await route.handle(request, **path_params)
            return response
        except Exception as e:
            logger.error(f"Route handler error for {method} {path}: {e}")
            raise
    
    def get_all_routes(self) -> List[Dict[str, Any]]:
        """Get all registered routes."""
        return [
            {
                "method": r.config.method.value,
                "path": r.config.path,
                "service": r.config.service_name,
                "require_auth": r.config.require_auth,
                "rate_limit": r.config.rate_limit,
            }
            for r in self._routes
        ]
    
    def clear_routes(self) -> None:
        """Clear all routes."""
        self._routes.clear()
        self._route_map.clear()
        logger.info("Cleared all routes")


# Global router instance
gateway_router = GatewayRouter()


def add_route(config: RouteConfig) -> None:
    """Add a route to the gateway."""
    gateway_router.add_route(config)


def remove_route(method: str, path: str) -> bool:
    """Remove a route from the gateway."""
    return gateway_router.remove_route(method, path)


def get_route(path: str, method: str) -> Optional[Route]:
    """Get a route from the gateway."""
    return gateway_router.get_route(path, method)


__all__ = [
    "GatewayRouter",
    "Route",
    "RouteConfig",
    "RouteMethod",
    "gateway_router",
    "add_route",
    "remove_route",
    "get_route",
]