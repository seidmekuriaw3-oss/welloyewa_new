# ============================
# WOLLOYEWA STORE BOT - SUBSCRIPTION BILLING
# ============================
"""Subscription billing system for recurring payments."""

from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from infrastructure.payments.base import PaymentRequest, PaymentResponse
from infrastructure.payments.factory import get_payment_provider
from core.logger import logger


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    TRIAL = "trial"


class BillingCycle(str, Enum):
    """Billing cycle frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class SubscriptionPlan:
    """Subscription plan definition."""
    
    id: str
    name: str
    description: str
    amount: Decimal
    billing_cycle: BillingCycle
    trial_days: int = 0
    features: List[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class Subscription:
    """Customer subscription record."""
    
    id: str
    user_id: int
    plan_id: str
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    trial_end: Optional[datetime] = None
    payment_method_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class SubscriptionBilling:
    """
    Subscription billing system.
    
    Features:
    - Recurring billing automation
    - Trial periods
    - Pause/resume subscriptions
    - Failed payment handling
    - Dunning management
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self._plans: Dict[str, SubscriptionPlan] = {}
        self._init_default_plans()
    
    def _init_default_plans(self) -> None:
        """Initialize default subscription plans."""
        self._plans = {
            "basic": SubscriptionPlan(
                id="basic",
                name="Basic Plan",
                description="Basic features for small businesses",
                amount=Decimal("499.00"),
                billing_cycle=BillingCycle.MONTHLY,
                features=["Up to 50 products", "Basic analytics", "Email support"],
            ),
            "pro": SubscriptionPlan(
                id="pro",
                name="Pro Plan",
                description="Professional features for growing businesses",
                amount=Decimal("999.00"),
                billing_cycle=BillingCycle.MONTHLY,
                trial_days=14,
                features=[
                    "Unlimited products",
                    "Advanced analytics",
                    "Priority support",
                    "Marketing tools",
                ],
            ),
            "enterprise": SubscriptionPlan(
                id="enterprise",
                name="Enterprise Plan",
                description="Full features for large businesses",
                amount=Decimal("2499.00"),
                billing_cycle=BillingCycle.MONTHLY,
                features=[
                    "Everything in Pro",
                    "Dedicated account manager",
                    "API access",
                    "Custom integrations",
                ],
            ),
        }
    
    def get_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """Get subscription plan by ID."""
        return self._plans.get(plan_id)
    
    def get_all_plans(self) -> List[SubscriptionPlan]:
        """Get all active subscription plans."""
        return [p for p in self._plans.values() if p.is_active]
    
    async def create_subscription(
        self,
        user_id: int,
        plan_id: str,
        payment_method_id: str,
    ) -> Subscription:
        """
        Create a new subscription.
        
        Args:
            user_id: User ID
            plan_id: Plan ID
            payment_method_id: Payment method ID
            
        Returns:
            Created subscription
        """
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
        
        now = datetime.utcnow()
        
        # Calculate trial end if applicable
        trial_end = None
        status = SubscriptionStatus.ACTIVE
        
        if plan.trial_days > 0:
            trial_end = now + timedelta(days=plan.trial_days)
            status = SubscriptionStatus.TRIAL
        
        # Calculate billing periods
        period_start = now
        period_end = self._calculate_period_end(now, plan.billing_cycle)
        
        # Create subscription
        subscription = Subscription(
            id=self._generate_subscription_id(),
            user_id=user_id,
            plan_id=plan_id,
            status=status,
            current_period_start=period_start,
            current_period_end=period_end,
            trial_end=trial_end,
            payment_method_id=payment_method_id,
        )
        
        await self._store_subscription(subscription)
        
        # Process first payment if not in trial
        if status != SubscriptionStatus.TRIAL:
            success = await self._process_payment(subscription)
            if not success:
                subscription.status = SubscriptionStatus.PAST_DUE
                await self._update_subscription(subscription)
        
        logger.info(f"Subscription created: {subscription.id} for user {user_id}")
        return subscription
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> Subscription:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription ID
            at_period_end: Cancel at period end (vs immediate)
            
        Returns:
            Updated subscription
        """
        subscription = await self._get_subscription(subscription_id)
        
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        if at_period_end:
            subscription.cancel_at_period_end = True
            await self._update_subscription(subscription)
            logger.info(f"Subscription {subscription_id} will cancel at period end")
        else:
            subscription.status = SubscriptionStatus.CANCELLED
            await self._update_subscription(subscription)
            logger.info(f"Subscription {subscription_id} cancelled immediately")
        
        return subscription
    
    async def pause_subscription(self, subscription_id: str) -> Subscription:
        """Pause an active subscription."""
        subscription = await self._get_subscription(subscription_id)
        
        if subscription.status != SubscriptionStatus.ACTIVE:
            raise ValueError(f"Cannot pause subscription with status: {subscription.status}")
        
        subscription.status = SubscriptionStatus.PAUSED
        await self._update_subscription(subscription)
        
        logger.info(f"Subscription {subscription_id} paused")
        return subscription
    
    async def resume_subscription(self, subscription_id: str) -> Subscription:
        """Resume a paused subscription."""
        subscription = await self._get_subscription(subscription_id)
        
        if subscription.status != SubscriptionStatus.PAUSED:
            raise ValueError(f"Cannot resume subscription with status: {subscription.status}")
        
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.cancel_at_period_end = False
        await self._update_subscription(subscription)
        
        # Process pending payment
        await self._process_payment(subscription)
        
        logger.info(f"Subscription {subscription_id} resumed")
        return subscription
    
    async def process_recurring_billing(self) -> int:
        """
        Process recurring billing for all active subscriptions.
        
        Returns:
            Number of successful payments
        """
        now = datetime.utcnow()
        active_subs = await self._get_active_subscriptions()
        processed = 0
        
        for sub in active_subs:
            # Skip if cancelled at period end and period ended
            if sub.cancel_at_period_end and sub.current_period_end <= now:
                sub.status = SubscriptionStatus.CANCELLED
                await self._update_subscription(sub)
                continue
            
            # Check if billing is due
            if sub.current_period_end <= now:
                success = await self._process_payment(sub)
                
                if success:
                    # Update billing period
                    sub.current_period_start = sub.current_period_end
                    plan = self.get_plan(sub.plan_id)
                    sub.current_period_end = self._calculate_period_end(
                        sub.current_period_start, plan.billing_cycle
                    )
                    sub.status = SubscriptionStatus.ACTIVE
                    processed += 1
                else:
                    sub.status = SubscriptionStatus.PAST_DUE
                
                await self._update_subscription(sub)
        
        logger.info(f"Processed recurring billing: {processed} payments")
        return processed
    
    async def _process_payment(self, subscription: Subscription) -> bool:
        """Process payment for subscription."""
        plan = self.get_plan(subscription.plan_id)
        
        try:
            provider = await get_payment_provider("chapa")  # Configure as needed
            
            request = PaymentRequest(
                amount=plan.amount,
                currency="ETB",
                description=f"Subscription {plan.name} - {subscription.id}",
                metadata={
                    "subscription_id": subscription.id,
                    "plan_id": plan.id,
                    "recurring": True,
                },
            )
            
            response = await provider.initialize_payment(request)
            
            if response.success:
                logger.info(f"Subscription payment successful: {subscription.id}")
                return True
            else:
                logger.error(f"Subscription payment failed: {subscription.id}")
                return False
                
        except Exception as e:
            logger.error(f"Subscription payment error: {e}")
            return False
    
    def _calculate_period_end(
        self,
        start_date: datetime,
        billing_cycle: BillingCycle,
    ) -> datetime:
        """Calculate period end date based on billing cycle."""
        if billing_cycle == BillingCycle.DAILY:
            return start_date + timedelta(days=1)
        elif billing_cycle == BillingCycle.WEEKLY:
            return start_date + timedelta(weeks=1)
        elif billing_cycle == BillingCycle.MONTHLY:
            # Add one month
            if start_date.month == 12:
                return start_date.replace(year=start_date.year + 1, month=1)
            else:
                return start_date.replace(month=start_date.month + 1)
        elif billing_cycle == BillingCycle.QUARTERLY:
            return start_date + timedelta(days=90)
        else:  # YEARLY
            return start_date.replace(year=start_date.year + 1)
    
    def _generate_subscription_id(self) -> str:
        """Generate unique subscription ID."""
        import uuid
        return f"sub_{uuid.uuid4().hex[:12]}"
    
    async def _store_subscription(self, subscription: Subscription) -> None:
        """Store subscription in database."""
        pass
    
    async def _get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription from database."""
        return None
    
    async def _update_subscription(self, subscription: Subscription) -> None:
        """Update subscription in database."""
        pass
    
    async def _get_active_subscriptions(self) -> List[Subscription]:
        """Get active subscriptions from database."""
        return []


async def create_subscription(
    db,
    user_id: int,
    plan_id: str,
    payment_method_id: str,
) -> Subscription:
    """Create a new subscription."""
    billing = SubscriptionBilling(db)
    return await billing.create_subscription(user_id, plan_id, payment_method_id)


async def cancel_subscription(
    db,
    subscription_id: str,
    at_period_end: bool = True,
) -> Subscription:
    """Cancel a subscription."""
    billing = SubscriptionBilling(db)
    return await billing.cancel_subscription(subscription_id, at_period_end)


async def process_recurring_billing(db) -> int:
    """Process recurring billing for all subscriptions."""
    billing = SubscriptionBilling(db)
    return await billing.process_recurring_billing()


__all__ = [
    "SubscriptionBilling",
    "SubscriptionPlan",
    "Subscription",
    "SubscriptionStatus",
    "BillingCycle",
    "create_subscription",
    "cancel_subscription",
    "process_recurring_billing",
]