# ============================
# WOLLOYEWA STORE BOT - TENANT RESOLVER
# ============================
"""Multi-tenant support for isolating data between different businesses."""

import re
from contextvars import ContextVar
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from core.logger import logger


class TenantResolutionStrategy(str, Enum):
    """Strategies for resolving tenant from request."""
    SUBDOMAIN = "subdomain"      # tenant.example.com
    HEADER = "header"            # X-Tenant-ID header
    QUERY_PARAM = "query_param"  # ?tenant_id=xxx
    API_KEY = "api_key"          # API key associated with tenant


@dataclass
class TenantInfo:
    """Information about a tenant."""
    
    id: str
    name: str
    domain: Optional[str] = None
    subscription_tier: str = "free"
    is_active: bool = True
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


class TenantNotFoundError(Exception):
    """Raised when tenant cannot be resolved."""
    pass


class TenantContext:
    """
    Context manager for tenant-aware operations.
    
    Usage:
        async with TenantContext(tenant_id="tenant_123"):
            # All operations within this block use tenant_123
            await db.query(...)
    """
    
    _current_tenant: ContextVar[Optional[TenantInfo]] = ContextVar("current_tenant", default=None)
    
    def __init__(self, tenant_id: str, tenant_info: Optional[TenantInfo] = None):
        self.tenant_id = tenant_id
        self.tenant_info = tenant_info or TenantInfo(id=tenant_id, name=tenant_id)
        self._previous_tenant = None
    
    async def __aenter__(self):
        self._previous_tenant = self._current_tenant.get()
        self._current_tenant.set(self.tenant_info)
        logger.debug(f"Entered tenant context: {self.tenant_id}")
        return self.tenant_info
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._previous_tenant is not None:
            self._current_tenant.set(self._previous_tenant)
        else:
            self._current_tenant.set(None)
        logger.debug(f"Exited tenant context: {self.tenant_id}")
    
    @classmethod
    def get_current_tenant(cls) -> Optional[TenantInfo]:
        """Get the current tenant from context."""
        return cls._current_tenant.get()
    
    @classmethod
    def set_current_tenant(cls, tenant: Optional[TenantInfo]):
        """Set the current tenant in context."""
        cls._current_tenant.set(tenant)


class TenantResolver:
    """
    Resolves tenant information from incoming requests.
    
    Features:
    - Multiple resolution strategies
    - Tenant caching
    - Domain-based routing
    - API key association
    """
    
    def __init__(self):
        self.strategy = TenantResolutionStrategy.HEADER
        self._tenant_cache: Dict[str, TenantInfo] = {}
        self._domain_to_tenant: Dict[str, str] = {}
        self._api_key_to_tenant: Dict[str, str] = {}
    
    def configure(
        self,
        strategy: TenantResolutionStrategy = TenantResolutionStrategy.HEADER,
    ) -> None:
        """Configure tenant resolution strategy."""
        self.strategy = strategy
        logger.info(f"Tenant resolution strategy set to: {strategy.value}")
    
    def register_tenant(
        self,
        tenant_id: str,
        name: str,
        domain: Optional[str] = None,
        api_key: Optional[str] = None,
        subscription_tier: str = "free",
    ) -> None:
        """
        Register a tenant.
        
        Args:
            tenant_id: Unique tenant identifier
            name: Tenant name
            domain: Domain for subdomain resolution
            api_key: API key for key-based resolution
            subscription_tier: Subscription plan
        """
        tenant = TenantInfo(
            id=tenant_id,
            name=name,
            domain=domain,
            subscription_tier=subscription_tier,
        )
        self._tenant_cache[tenant_id] = tenant
        
        if domain:
            self._domain_to_tenant[domain] = tenant_id
        
        if api_key:
            self._api_key_to_tenant[api_key] = tenant_id
        
        logger.info(f"Registered tenant: {tenant_id} ({name})")
    
    def resolve_from_request(self, request: Any) -> Optional[TenantInfo]:
        """
        Resolve tenant from request.
        
        Args:
            request: HTTP request object
            
        Returns:
            TenantInfo if resolved, None otherwise
        """
        tenant_id = None
        
        if self.strategy == TenantResolutionStrategy.SUBDOMAIN:
            tenant_id = self._resolve_from_subdomain(request)
        
        elif self.strategy == TenantResolutionStrategy.HEADER:
            tenant_id = self._resolve_from_header(request)
        
        elif self.strategy == TenantResolutionStrategy.QUERY_PARAM:
            tenant_id = self._resolve_from_query_param(request)
        
        elif self.strategy == TenantResolutionStrategy.API_KEY:
            tenant_id = self._resolve_from_api_key(request)
        
        if tenant_id and tenant_id in self._tenant_cache:
            return self._tenant_cache[tenant_id]
        
        return None
    
    def _resolve_from_subdomain(self, request: Any) -> Optional[str]:
        """Extract tenant from subdomain."""
        host = getattr(request, 'headers', {}).get('Host', '')
        host = host.split(':')[0]  # Remove port
        
        # Extract subdomain
        parts = host.split('.')
        if len(parts) >= 2:
            subdomain = parts[0]
            # Check if subdomain matches a registered domain
            if subdomain in self._domain_to_tenant:
                return self._domain_to_tenant[subdomain]
        
        return None
    
    def _resolve_from_header(self, request: Any) -> Optional[str]:
        """Extract tenant from X-Tenant-ID header."""
        headers = getattr(request, 'headers', {})
        tenant_id = headers.get('X-Tenant-ID', headers.get('X-Tenant-Id'))
        return tenant_id
    
    def _resolve_from_query_param(self, request: Any) -> Optional[str]:
        """Extract tenant from query parameter."""
        params = getattr(request, 'query_params', {})
        return params.get('tenant_id', params.get('tenant'))
    
    def _resolve_from_api_key(self, request: Any) -> Optional[str]:
        """Extract tenant from API key."""
        headers = getattr(request, 'headers', {})
        api_key = headers.get('X-API-Key', headers.get('Authorization', ''))
        
        if api_key.startswith('Bearer '):
            api_key = api_key[7:]
        
        return self._api_key_to_tenant.get(api_key)
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantInfo]:
        """Get tenant by ID."""
        return self._tenant_cache.get(tenant_id)
    
    def clear_cache(self) -> None:
        """Clear tenant cache."""
        self._tenant_cache.clear()
        self._domain_to_tenant.clear()
        self._api_key_to_tenant.clear()


# Global tenant resolver instance
tenant_resolver = TenantResolver()


def get_current_tenant() -> Optional[TenantInfo]:
    """Get the current tenant from context."""
    return TenantContext.get_current_tenant()


def set_current_tenant(tenant: Optional[TenantInfo]) -> None:
    """Set the current tenant in context."""
    TenantContext.set_current_tenant(tenant)


def clear_current_tenant() -> None:
    """Clear the current tenant from context."""
    TenantContext.set_current_tenant(None)


def tenant_aware(func):
    """
    Decorator to make a function tenant-aware.
    
    Automatically sets up tenant context based on request.
    """
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        tenant = tenant_resolver.resolve_from_request(request)
        
        if not tenant:
            raise TenantNotFoundError("Could not resolve tenant from request")
        
        async with TenantContext(tenant.id, tenant):
            return await func(request, *args, **kwargs)
    
    return wrapper


__all__ = [
    "TenantResolver",
    "TenantContext",
    "TenantInfo",
    "TenantResolutionStrategy",
    "TenantNotFoundError",
    "tenant_resolver",
    "get_current_tenant",
    "set_current_tenant",
    "clear_current_tenant",
    "tenant_aware",
]