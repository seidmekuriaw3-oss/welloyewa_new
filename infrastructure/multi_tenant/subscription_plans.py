# ============================
# WOLLOYEWA STORE BOT - SUBSCRIPTION PLANS
# ============================
"""Subscription plan management for multi-tenant billing."""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class Feature:
    """Feature in a subscription plan."""
    
    name: str
    description: str
    limit: Optional[int] = None  # None means unlimited
    included: bool = True


@dataclass
class SubscriptionPlan:
    """Subscription plan definition."""
    
    tier: SubscriptionTier
    name: str
    price_monthly: float
    price_yearly: float
    features: Dict[str, Feature] = field(default_factory=dict)
    limits: Dict[str, int] = field(default_factory=dict)
    is_active: bool = True
    description: Optional[str] = None
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if plan includes a feature."""
        if feature_name in self.features:
            return self.features[feature_name].included
        return False
    
    def get_limit(self, limit_name: str) -> Optional[int]:
        """Get a limit value."""
        return self.limits.get(limit_name)


@dataclass
class Subscription:
    """Customer subscription record."""
    
    id: str
    tenant_id: str
    plan_tier: SubscriptionTier
    status: str  # active, past_due, cancelled, expired
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    trial_end: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    payment_method_id: Optional[str] = None


class SubscriptionManager:
    """
    Subscription plan manager for multi-tenant billing.
    
    Features:
    - Multiple subscription tiers
    - Feature-based access control
    - Usage limits
    - Trial periods
    """
    
    def __init__(self):
        self._plans: Dict[SubscriptionTier, SubscriptionPlan] = {}
        self._subscriptions: Dict[str, Subscription] = {}
        self._init_default_plans()
    
    def _init_default_plans(self) -> None:
        """Initialize default subscription plans."""
        # Free plan
        free_plan = SubscriptionPlan(
            tier=SubscriptionTier.FREE,
            name="Free",
            price_monthly=0,
            price_yearly=0,
            description="Basic features for small businesses",
        )
        free_plan.features = {
            "products": Feature("products", "Number of products", limit=50),
            "orders": Feature("orders", "Monthly orders", limit=100),
            "vendors": Feature("vendors", "Number of vendors", limit=1),
            "analytics": Feature("analytics", "Basic analytics", included=True),
            "support": Feature("support", "Email support", included=True),
            "api_access": Feature("api_access", "API access", included=False),
            "custom_domain": Feature("custom_domain", "Custom domain", included=False),
        }
        free_plan.limits = {
            "products": 50,
            "orders_per_month": 100,
            "vendors": 1,
            "team_members": 1,
            "storage_gb": 1,
        }
        
        # Basic plan
        basic_plan = SubscriptionPlan(
            tier=SubscriptionTier.BASIC,
            name="Basic",
            price_monthly=499,
            price_yearly=4990,
            description="Essential features for growing businesses",
        )
        basic_plan.features = {
            "products": Feature("products", "Number of products", limit=500),
            "orders": Feature("orders", "Monthly orders", limit=500),
            "vendors": Feature("vendors", "Number of vendors", limit=3),
            "analytics": Feature("analytics", "Advanced analytics", included=True),
            "support": Feature("support", "Priority email support", included=True),
            "api_access": Feature("api_access", "API access", included=True),
            "custom_domain": Feature("custom_domain", "Custom domain", included=False),
        }
        basic_plan.limits = {
            "products": 500,
            "orders_per_month": 500,
            "vendors": 3,
            "team_members": 5,
            "storage_gb": 10,
        }
        
        # Professional plan
        pro_plan = SubscriptionPlan(
            tier=SubscriptionTier.PROFESSIONAL,
            name="Professional",
            price_monthly=999,
            price_yearly=9990,
            description="Advanced features for established businesses",
        )
        pro_plan.features = {
            "products": Feature("products", "Unlimited products", limit=None),
            "orders": Feature("orders", "Unlimited orders", limit=None),
            "vendors": Feature("vendors", "Unlimited vendors", limit=None),
            "analytics": Feature("analytics", "Advanced analytics + reports", included=True),
            "support": Feature("support", "Priority support", included=True),
            "api_access": Feature("api_access", "Full API access", included=True),
            "custom_domain": Feature("custom_domain", "Custom domain", included=True),
            "multi_currency": Feature("multi_currency", "Multi-currency support", included=True),
        }
        pro_plan.limits = {
            "products": -1,  # Unlimited
            "orders_per_month": -1,
            "vendors": -1,
            "team_members": 20,
            "storage_gb": 50,
        }
        
        # Enterprise plan
        enterprise_plan = SubscriptionPlan(
            tier=SubscriptionTier.ENTERPRISE,
            name="Enterprise",
            price_monthly=2499,
            price_yearly=24990,
            description="Full features for large enterprises",
        )
        enterprise_plan.features = {
            "products": Feature("products", "Unlimited products", limit=None),
            "orders": Feature("orders", "Unlimited orders", limit=None),
            "vendors": Feature("vendors", "Unlimited vendors", limit=None),
            "analytics": Feature("analytics", "Enterprise analytics + custom reports", included=True),
            "support": Feature("support", "24/7 dedicated support", included=True),
            "api_access": Feature("api_access", "Full API access + webhooks", included=True),
            "custom_domain": Feature("custom_domain", "Custom domain + SSL", included=True),
            "multi_currency": Feature("multi_currency", "Multi-currency support", included=True),
            "white_label": Feature("white_label", "White-label solution", included=True),
            "sla": Feature("sla", "SLA guarantee", included=True),
        }
        enterprise_plan.limits = {
            "products": -1,
            "orders_per_month": -1,
            "vendors": -1,
            "team_members": -1,
            "storage_gb": 500,
        }
        
        self._plans = {
            SubscriptionTier.FREE: free_plan,
            SubscriptionTier.BASIC: basic_plan,
            SubscriptionTier.PROFESSIONAL: pro_plan,
            SubscriptionTier.ENTERPRISE: enterprise_plan,
        }
    
    def get_plan(self, tier: SubscriptionTier) -> Optional[SubscriptionPlan]:
        """Get plan by tier."""
        return self._plans.get(tier)
    
    def get_all_plans(self) -> List[SubscriptionPlan]:
        """Get all active plans."""
        return [p for p in self._plans.values() if p.is_active]
    
    def get_plan_features(self, tier: SubscriptionTier) -> Dict[str, Feature]:
        """Get features for a plan."""
        plan = self.get_plan(tier)
        return plan.features if plan else {}
    
    def check_feature_access(
        self,
        tier: SubscriptionTier,
        feature_name: str,
    ) -> bool:
        """Check if a plan includes a feature."""
        plan = self.get_plan(tier)
        if not plan:
            return False
        return plan.has_feature(feature_name)
    
    def get_limit(
        self,
        tier: SubscriptionTier,
        limit_name: str,
    ) -> Optional[int]:
        """Get a limit value for a plan."""
        plan = self.get_plan(tier)
        if not plan:
            return 0
        return plan.get_limit(limit_name)
    
    async def create_subscription(
        self,
        tenant_id: str,
        plan_tier: SubscriptionTier,
        trial_days: int = 0,
    ) -> Subscription:
        """Create a new subscription for a tenant."""
        import uuid
        
        now = datetime.utcnow()
        period_end = now.replace(month=now.month + 1)  # Add 1 month
        
        subscription = Subscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            plan_tier=plan_tier,
            status="active",
            current_period_start=now,
            current_period_end=period_end,
            trial_end=now + timedelta(days=trial_days) if trial_days > 0 else None,
        )
        
        self._subscriptions[subscription.id] = subscription
        logger.info(f"Created subscription {subscription.id} for tenant {tenant_id} with plan {plan_tier.value}")
        
        return subscription
    
    async def get_subscription(self, tenant_id: str) -> Optional[Subscription]:
        """Get subscription for a tenant."""
        for sub in self._subscriptions.values():
            if sub.tenant_id == tenant_id and sub.status == "active":
                return sub
        return None
    
    async def update_subscription_plan(
        self,
        tenant_id: str,
        new_plan_tier: SubscriptionTier,
    ) -> Optional[Subscription]:
        """Update a tenant's subscription plan."""
        subscription = await self.get_subscription(tenant_id)
        if not subscription:
            return None
        
        subscription.plan_tier = new_plan_tier
        subscription.updated_at = datetime.utcnow()
        
        logger.info(f"Updated subscription for tenant {tenant_id} to {new_plan_tier.value}")
        return subscription
    
    async def cancel_subscription(
        self,
        tenant_id: str,
        at_period_end: bool = True,
    ) -> Optional[Subscription]:
        """Cancel a subscription."""
        subscription = await self.get_subscription(tenant_id)
        if not subscription:
            return None
        
        if at_period_end:
            subscription.cancel_at_period_end = True
            logger.info(f"Subscription for tenant {tenant_id} will cancel at period end")
        else:
            subscription.status = "cancelled"
            logger.info(f"Subscription for tenant {tenant_id} cancelled immediately")
        
        subscription.updated_at = datetime.utcnow()
        return subscription


# Global subscription manager
subscription_manager = SubscriptionManager()


def get_plan_features(tier: SubscriptionTier) -> Dict[str, Feature]:
    """Get features for a plan."""
    return subscription_manager.get_plan_features(tier)


def check_feature_access(tier: SubscriptionTier, feature_name: str) -> bool:
    """Check if a plan includes a feature."""
    return subscription_manager.check_feature_access(tier, feature_name)


async def upgrade_plan(tenant_id: str, new_tier: SubscriptionTier) -> Optional[Subscription]:
    """Upgrade a tenant's subscription plan."""
    return await subscription_manager.update_subscription_plan(tenant_id, new_tier)


async def downgrade_plan(tenant_id: str, new_tier: SubscriptionTier) -> Optional[Subscription]:
    """Downgrade a tenant's subscription plan."""
    return await subscription_manager.update_subscription_plan(tenant_id, new_tier)


__all__ = [
    "SubscriptionManager",
    "SubscriptionPlan",
    "SubscriptionTier",
    "Feature",
    "Subscription",
    "subscription_manager",
    "get_plan_features",
    "check_feature_access",
    "upgrade_plan",
    "downgrade_plan",
]