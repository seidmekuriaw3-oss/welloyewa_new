# ============================
# WOLLOYEWA STORE BOT - MULTI-TENANT MODULE
# ============================
"""Multi-tenant support for managing multiple businesses on a single instance."""

from infrastructure.multi_tenant.tenant_resolver import (
    TenantResolver,
    TenantContext,
    TenantInfo,
    get_current_tenant,
    set_current_tenant,
    clear_current_tenant,
    tenant_aware,
    TenantNotFoundError,
)
from infrastructure.multi_tenant.team_management import (
    TeamManager,
    Team,
    TeamMember,
    TeamRole,
    Invitation,
    create_team,
    add_team_member,
    remove_team_member,
    update_member_role,
)
from infrastructure.multi_tenant.permission_matrix import (
    PermissionManager,
    Permission,
    ResourceType,
    check_permission,
    require_permission,
    assign_permission,
    revoke_permission,
    PermissionDeniedError,
)
from infrastructure.multi_tenant.subscription_plans import (
    SubscriptionManager,
    SubscriptionPlan,
    SubscriptionTier,
    Feature,
    get_plan_features,
    check_feature_access,
    upgrade_plan,
    downgrade_plan,
)

__all__ = [
    # Tenant Resolver
    "TenantResolver",
    "TenantContext",
    "TenantInfo",
    "get_current_tenant",
    "set_current_tenant",
    "clear_current_tenant",
    "tenant_aware",
    "TenantNotFoundError",
    # Team Management
    "TeamManager",
    "Team",
    "TeamMember",
    "TeamRole",
    "Invitation",
    "create_team",
    "add_team_member",
    "remove_team_member",
    "update_member_role",
    # Permission Matrix
    "PermissionManager",
    "Permission",
    "ResourceType",
    "check_permission",
    "require_permission",
    "assign_permission",
    "revoke_permission",
    "PermissionDeniedError",
    # Subscription Plans
    "SubscriptionManager",
    "SubscriptionPlan",
    "SubscriptionTier",
    "Feature",
    "get_plan_features",
    "check_feature_access",
    "upgrade_plan",
    "downgrade_plan",
]