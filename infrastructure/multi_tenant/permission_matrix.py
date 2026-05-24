# ============================
# WOLLOYEWA STORE BOT - PERMISSION MATRIX
# ============================
"""Role-based permission matrix for fine-grained access control."""

from enum import Enum
from typing import Dict, Set, List, Optional, Any
from dataclasses import dataclass
from functools import wraps

from core.logger import logger


class ResourceType(str, Enum):
    """Types of resources that can be accessed."""
    PRODUCT = "product"
    ORDER = "order"
    USER = "user"
    VENDOR = "vendor"
    CATEGORY = "category"
    INVENTORY = "inventory"
    REPORT = "report"
    SETTINGS = "settings"
    TEAM = "team"
    PAYMENT = "payment"


class Permission(str, Enum):
    """Permission actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    APPROVE = "approve"
    REJECT = "reject"
    EXPORT = "export"
    MANAGE = "manage"  # All actions


# Default role permissions
ROLE_PERMISSIONS: Dict[str, Dict[ResourceType, Set[Permission]]] = {
    "owner": {
        ResourceType.PRODUCT: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE, Permission.LIST},
        ResourceType.ORDER: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE, Permission.LIST},
        ResourceType.USER: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE, Permission.LIST},
        ResourceType.VENDOR: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE, Permission.LIST, Permission.APPROVE, Permission.REJECT},
        ResourceType.CATEGORY: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE, Permission.LIST},
        ResourceType.INVENTORY: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE, Permission.LIST},
        ResourceType.REPORT: {Permission.READ, Permission.LIST, Permission.EXPORT},
        ResourceType.SETTINGS: {Permission.READ, Permission.UPDATE, Permission.MANAGE},
        ResourceType.TEAM: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE, Permission.LIST, Permission.MANAGE},
        ResourceType.PAYMENT: {Permission.READ, Permission.LIST, Permission.APPROVE, Permission.REJECT},
    },
    "admin": {
        ResourceType.PRODUCT: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE, Permission.LIST},
        ResourceType.ORDER: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.LIST},
        ResourceType.USER: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.LIST},
        ResourceType.VENDOR: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.LIST, Permission.APPROVE},
        ResourceType.CATEGORY: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.LIST},
        ResourceType.INVENTORY: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.LIST},
        ResourceType.REPORT: {Permission.READ, Permission.LIST, Permission.EXPORT},
        ResourceType.SETTINGS: {Permission.READ, Permission.UPDATE},
        ResourceType.TEAM: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.LIST},
        ResourceType.PAYMENT: {Permission.READ, Permission.LIST},
    },
    "manager": {
        ResourceType.PRODUCT: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.LIST},
        ResourceType.ORDER: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.LIST},
        ResourceType.USER: {Permission.READ, Permission.LIST},
        ResourceType.VENDOR: {Permission.READ, Permission.LIST},
        ResourceType.CATEGORY: {Permission.READ, Permission.LIST},
        ResourceType.INVENTORY: {Permission.READ, Permission.UPDATE, Permission.LIST},
        ResourceType.REPORT: {Permission.READ, Permission.LIST},
        ResourceType.SETTINGS: {Permission.READ},
        ResourceType.PAYMENT: {Permission.READ},
    },
    "member": {
        ResourceType.PRODUCT: {Permission.READ, Permission.LIST},
        ResourceType.ORDER: {Permission.CREATE, Permission.READ, Permission.LIST},
        ResourceType.USER: {Permission.READ},
        ResourceType.REPORT: {Permission.READ},
    },
    "viewer": {
        ResourceType.PRODUCT: {Permission.READ, Permission.LIST},
        ResourceType.ORDER: {Permission.READ, Permission.LIST},
        ResourceType.USER: {Permission.READ},
        ResourceType.REPORT: {Permission.READ},
    },
}


class PermissionDeniedError(Exception):
    """Raised when a user lacks required permission."""
    
    def __init__(self, permission: Permission, resource: ResourceType):
        self.permission = permission
        self.resource = resource
        super().__init__(f"Permission denied: {permission.value} on {resource.value}")


class PermissionManager:
    """
    Permission manager for role-based access control.
    
    Features:
    - Fine-grained permissions per resource
    - Role-based permission assignment
    - Permission checking
    - Custom permission overrides
    """
    
    def __init__(self):
        self._role_permissions = ROLE_PERMISSIONS.copy()
        self._user_overrides: Dict[int, Dict[ResourceType, Set[Permission]]] = {}
        self._tenant_overrides: Dict[str, Dict[str, Dict[ResourceType, Set[Permission]]]] = {}
    
    def get_permissions_for_role(self, role: str) -> Dict[ResourceType, Set[Permission]]:
        """Get permissions for a role."""
        return self._role_permissions.get(role, {})
    
    def add_role_permission(
        self,
        role: str,
        resource: ResourceType,
        permission: Permission,
    ) -> None:
        """Add a permission to a role."""
        if role not in self._role_permissions:
            self._role_permissions[role] = {}
        
        if resource not in self._role_permissions[role]:
            self._role_permissions[role][resource] = set()
        
        self._role_permissions[role][resource].add(permission)
        logger.debug(f"Added permission {permission.value} on {resource.value} to role {role}")
    
    def remove_role_permission(
        self,
        role: str,
        resource: ResourceType,
        permission: Permission,
    ) -> None:
        """Remove a permission from a role."""
        if role in self._role_permissions:
            if resource in self._role_permissions[role]:
                self._role_permissions[role][resource].discard(permission)
                logger.debug(f"Removed permission {permission.value} on {resource.value} from role {role}")
    
    def assign_user_permission(
        self,
        user_id: int,
        resource: ResourceType,
        permission: Permission,
    ) -> None:
        """Assign a custom permission to a user."""
        if user_id not in self._user_overrides:
            self._user_overrides[user_id] = {}
        
        if resource not in self._user_overrides[user_id]:
            self._user_overrides[user_id][resource] = set()
        
        self._user_overrides[user_id][resource].add(permission)
        logger.debug(f"Assigned permission {permission.value} on {resource.value} to user {user_id}")
    
    def revoke_user_permission(
        self,
        user_id: int,
        resource: ResourceType,
        permission: Permission,
    ) -> None:
        """Revoke a custom permission from a user."""
        if user_id in self._user_overrides:
            if resource in self._user_overrides[user_id]:
                self._user_overrides[user_id][resource].discard(permission)
    
    def has_permission(
        self,
        role: str,
        resource: ResourceType,
        permission: Permission,
        user_id: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """
        Check if a role/user has a specific permission.
        
        Args:
            role: User's role
            resource: Resource type
            permission: Permission to check
            user_id: Optional user ID for custom overrides
            tenant_id: Optional tenant ID for tenant-specific overrides
            
        Returns:
            True if permission is granted
        """
        # Check tenant-specific overrides first
        if tenant_id and tenant_id in self._tenant_overrides:
            tenant_overrides = self._tenant_overrides[tenant_id]
            if role in tenant_overrides:
                role_overrides = tenant_overrides[role]
                if resource in role_overrides:
                    if permission in role_overrides[resource]:
                        return True
        
        # Check user-specific overrides
        if user_id and user_id in self._user_overrides:
            user_perms = self._user_overrides[user_id]
            if resource in user_perms:
                if permission in user_perms[resource]:
                    return True
        
        # Check role permissions
        if role in self._role_permissions:
            role_perms = self._role_permissions[role]
            if resource in role_perms:
                if permission in role_perms[resource]:
                    return True
            
            # Check for MANAGE permission (covers all actions)
            if Permission.MANAGE in role_perms.get(resource, set()):
                return True
        
        return False
    
    def require_permission(
        self,
        role: str,
        resource: ResourceType,
        permission: Permission,
        user_id: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        """
        Require a permission, raise exception if not granted.
        
        Raises:
            PermissionDeniedError: If permission is not granted
        """
        if not self.has_permission(role, resource, permission, user_id, tenant_id):
            raise PermissionDeniedError(permission, resource)
    
    def get_effective_permissions(
        self,
        role: str,
        user_id: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[ResourceType, Set[Permission]]:
        """Get effective permissions for a user/role."""
        # Start with role permissions
        effective = {}
        
        if role in self._role_permissions:
            for resource, perms in self._role_permissions[role].items():
                effective[resource] = perms.copy()
        
        # Apply tenant overrides
        if tenant_id and tenant_id in self._tenant_overrides:
            tenant_overrides = self._tenant_overrides[tenant_id]
            if role in tenant_overrides:
                for resource, perms in tenant_overrides[role].items():
                    if resource not in effective:
                        effective[resource] = set()
                    effective[resource].update(perms)
        
        # Apply user overrides
        if user_id and user_id in self._user_overrides:
            for resource, perms in self._user_overrides[user_id].items():
                if resource not in effective:
                    effective[resource] = set()
                effective[resource].update(perms)
        
        return effective


# Global permission manager
permission_manager = PermissionManager()


def check_permission(
    role: str,
    resource: ResourceType,
    permission: Permission,
    user_id: Optional[int] = None,
) -> bool:
    """Check if a role has permission."""
    return permission_manager.has_permission(role, resource, permission, user_id)


def require_permission(
    resource: ResourceType,
    permission: Permission,
):
    """
    Decorator for requiring permission.
    
    Usage:
        @require_permission(ResourceType.PRODUCT, Permission.CREATE)
        async def create_product(request, user):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from arguments (implementation depends on framework)
            user = kwargs.get('user') or (args[1] if len(args) > 1 else None)
            
            if not user:
                raise PermissionDeniedError(permission, resource)
            
            permission_manager.require_permission(
                role=user.get('role', 'member'),
                resource=resource,
                permission=permission,
                user_id=user.get('id'),
            )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def assign_permission(
    user_id: int,
    resource: ResourceType,
    permission: Permission,
) -> None:
    """Assign a permission to a user."""
    permission_manager.assign_user_permission(user_id, resource, permission)


async def revoke_permission(
    user_id: int,
    resource: ResourceType,
    permission: Permission,
) -> None:
    """Revoke a permission from a user."""
    permission_manager.revoke_user_permission(user_id, resource, permission)


__all__ = [
    "PermissionManager",
    "ResourceType",
    "Permission",
    "PermissionDeniedError",
    "permission_manager",
    "check_permission",
    "require_permission",
    "assign_permission",
    "revoke_permission",
]