# ============================
# WOLLOYEWA STORE BOT - API VERSIONING
# ============================
"""API versioning support for backward compatibility."""

import re
from typing import Dict, Any, Optional, Callable, List, Union
from enum import Enum
from functools import wraps
from packaging import version

from core.logger import logger


class VersioningStrategy(str, Enum):
    """API versioning strategies."""
    URL_PATH = "url_path"          # /v1/resource
    QUERY_PARAM = "query_param"     # /resource?version=1
    HEADER = "header"               # Accept: application/vnd.api.v1+json
    CONTENT_TYPE = "content_type"   # application/vnd.api.v1+json


class VersionNegotiator:
    """
    API version negotiator.
    
    Features:
    - Multiple versioning strategies
    - Version range support
    - Default version fallback
    - Deprecation handling
    """
    
    def __init__(
        self,
        strategy: VersioningStrategy = VersioningStrategy.URL_PATH,
        default_version: str = "v1",
    ):
        self.strategy = strategy
        self.default_version = default_version
        self._version_handlers: Dict[str, Dict[str, Callable]] = {}
        self._deprecated_versions: Dict[str, str] = {}  # version -> sunset_date
    
    def register_handler(
        self,
        path: str,
        version: str,
        handler: Callable,
        method: str = "GET",
    ) -> None:
        """
        Register a versioned handler.
        
        Args:
            path: API path
            version: API version (e.g., "v1", "v2")
            handler: Handler function
            method: HTTP method
        """
        key = f"{method}:{path}"
        
        if key not in self._version_handlers:
            self._version_handlers[key] = {}
        
        self._version_handlers[key][version] = handler
        logger.debug(f"Registered handler for {method} {path} version {version}")
    
    def get_version(self, request: Any) -> str:
        """
        Extract API version from request.
        
        Args:
            request: Request object
            
        Returns:
            API version string
        """
        if self.strategy == VersioningStrategy.URL_PATH:
            # Extract version from URL path (e.g., /v1/users)
            path = getattr(request, 'url', request.get('path', '/'))
            match = re.match(r'^/(v\d+)/', path)
            if match:
                return match.group(1)
        
        elif self.strategy == VersioningStrategy.QUERY_PARAM:
            # Extract from query parameter
            params = getattr(request, 'query_params', request.get('params', {}))
            version = params.get('api_version', params.get('version'))
            if version:
                return version
        
        elif self.strategy == VersioningStrategy.HEADER:
            # Extract from Accept header
            headers = getattr(request, 'headers', request.get('headers', {}))
            accept = headers.get('Accept', '')
            match = re.search(r'application/vnd\.api\.(v\d+)\+json', accept)
            if match:
                return match.group(1)
        
        elif self.strategy == VersioningStrategy.CONTENT_TYPE:
            # Extract from Content-Type header
            headers = getattr(request, 'headers', request.get('headers', {}))
            content_type = headers.get('Content-Type', '')
            match = re.search(r'application/vnd\.api\.(v\d+)\+json', content_type)
            if match:
                return match.group(1)
        
        return self.default_version
    
    def get_handler(self, path: str, method: str, version: Optional[str] = None) -> Optional[Callable]:
        """
        Get handler for path, method, and version.
        
        Args:
            path: API path
            method: HTTP method
            version: API version (if None, extracted from request)
            
        Returns:
            Handler function or None
        """
        key = f"{method}:{path}"
        
        if key not in self._version_handlers:
            return None
        
        handlers = self._version_handlers[key]
        
        if version and version in handlers:
            # Check if version is deprecated
            if version in self._deprecated_versions:
                sunset_date = self._deprecated_versions[version]
                logger.warning(f"API version {version} is deprecated, will sunset on {sunset_date}")
            return handlers[version]
        
        # Find highest compatible version
        available_versions = sorted(handlers.keys(), key=version.parse, reverse=True)
        
        if available_versions:
            # For now, return the latest version
            # In production, implement proper version compatibility
            return handlers[available_versions[0]]
        
        return None
    
    def deprecate_version(self, version: str, sunset_date: str) -> None:
        """
        Mark a version as deprecated.
        
        Args:
            version: API version
            sunset_date: Sunset date (ISO format)
        """
        self._deprecated_versions[version] = sunset_date
        logger.info(f"Deprecated API version {version}, sunset on {sunset_date}")
    
    def is_version_supported(self, version: str) -> bool:
        """Check if a version is still supported."""
        if version in self._deprecated_versions:
            # Could also check if sunset date has passed
            return True  # Still supported until sunset
        return True
    
    def get_supported_versions(self) -> List[str]:
        """Get list of supported API versions."""
        versions = set()
        for handlers in self._version_handlers.values():
            versions.update(handlers.keys())
        return sorted(list(versions))


class VersionedRouter:
    """
    Versioned API router.
    
    Usage:
        router = VersionedRouter()
        
        @router.route("/users", version="v1")
        async def get_users_v1(request):
            return {"users": []}
        
        @router.route("/users", version="v2")
        async def get_users_v2(request):
            return {"users": [], "meta": {}}
    """
    
    def __init__(self, negotiator: Optional[VersionNegotiator] = None):
        self.negotiator = negotiator or VersionNegotiator()
        self._routes: List[Dict[str, Any]] = []
    
    def route(
        self,
        path: str,
        version: str,
        method: str = "GET",
    ):
        """
        Decorator for versioned routes.
        
        Args:
            path: API path
            version: API version
            method: HTTP method
        """
        def decorator(func: Callable):
            self.negotiator.register_handler(path, version, func, method)
            self._routes.append({
                "path": path,
                "version": version,
                "method": method,
                "handler": func.__name__,
            })
            
            @wraps(func)
            async def wrapper(request):
                return await func(request)
            
            return wrapper
        
        return decorator
    
    async def dispatch(self, request: Any) -> Any:
        """
        Dispatch request to appropriate versioned handler.
        
        Args:
            request: Request object
            
        Returns:
            Handler response
        """
        path = getattr(request, 'url', request.get('path', '/'))
        method = getattr(request, 'method', request.get('method', 'GET'))
        version = self.negotiator.get_version(request)
        
        handler = self.negotiator.get_handler(path, method, version)
        
        if not handler:
            raise NotFoundError(f"No handler found for {method} {path} version {version}")
        
        return await handler(request)
    
    def get_versioned_handler(self, path: str, method: str, version: str) -> Optional[Callable]:
        """Get versioned handler."""
        return self.negotiator.get_handler(path, method, version)


# Global version negotiator
version_negotiator = VersionNegotiator()


def version_route(path: str, version: str, method: str = "GET"):
    """Decorator for versioned routes."""
    def decorator(func: Callable):
        version_negotiator.register_handler(path, version, func, method)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_versioned_handler(path: str, method: str, version: str) -> Optional[Callable]:
    """Get versioned handler."""
    return version_negotiator.get_handler(path, method, version)


APIVersioning = VersionNegotiator

__all__ = [
    "VersionNegotiator",
    "VersionedRouter",
    "VersioningStrategy",
    "APIVersioning",
    "version_negotiator",
    "version_route",
    "get_versioned_handler",
]