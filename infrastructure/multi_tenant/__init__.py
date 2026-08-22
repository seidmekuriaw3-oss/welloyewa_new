# ============================
# WOLLOYEWA STORE BOT - MULTI-TENANT MODULE
# ============================
"""Multi-tenant support for managing multiple businesses on a single instance."""

from infrastructure.multi_tenant.permission_matrix import (
    Permission,
    PermissionDeniedError,
    PermissionManager,
    ResourceType,
    assign_permission,
    check_permission,
    require_permission,
    revoke_permission,
)
from infrastructure.multi_tenant.subscription_plans import (
    Feature,
    SubscriptionManager,
    SubscriptionPlan,
    SubscriptionTier,
    check_feature_access,
    downgrade_plan,
    get_plan_features,
    upgrade_plan,
)
from infrastructure.multi_tenant.team_management import (
    Invitation,
    Team,
    TeamManager,
    TeamMember,
    TeamRole,
    add_team_member,
    create_team,
    remove_team_member,
    update_member_role,
)
from infrastructure.multi_tenant.tenant_resolver import (
    TenantContext,
    TenantInfo,
    TenantNotFoundError,
    TenantResolver,
    clear_current_tenant,
    get_current_tenant,
    set_current_tenant,
    tenant_aware,
)

__all__ = [
    "Feature",
    "Invitation",
    "Permission",
    "PermissionDeniedError",
    # Permission Matrix
    "PermissionManager",
    "ResourceType",
    # Subscription Plans
    "SubscriptionManager",
    "SubscriptionPlan",
    "SubscriptionTier",
    "Team",
    # Team Management
    "TeamManager",
    "TeamMember",
    "TeamRole",
    "TenantContext",
    "TenantInfo",
    "TenantNotFoundError",
    # Tenant Resolver
    "TenantResolver",
    "add_team_member",
    "assign_permission",
    "check_feature_access",
    "check_permission",
    "clear_current_tenant",
    "create_team",
    "downgrade_plan",
    "get_current_tenant",
    "get_plan_features",
    "remove_team_member",
    "require_permission",
    "revoke_permission",
    "set_current_tenant",
    "tenant_aware",
    "update_member_role",
    "upgrade_plan",
]
