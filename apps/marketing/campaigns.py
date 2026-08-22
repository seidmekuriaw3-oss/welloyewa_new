# ============================
# WOLLOYEWA STORE BOT - CAMPAIGNS MANAGER
# ============================
"""Campaign management for marketing initiatives and promotions."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.marketing.models import Campaign, Promotion
from apps.marketing.repository import CampaignRepository, PromotionRepository
from core.events import emit_event
from core.exceptions import NotFoundError, ValidationError
from core.logger import logger


class CampaignManager:
    """
    Campaign manager for marketing initiatives.

    Features:
    - Create and manage marketing campaigns
    - Track campaign performance metrics
    - Campaign scheduling and activation
    - Integration with promotions
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.campaign_repo = CampaignRepository(db)
        self.promotion_repo = PromotionRepository(db)

    async def create_campaign(
        self,
        name: str,
        campaign_type: str,
        start_date: datetime,
        end_date: datetime,
        description: str | None = None,
        budget: Decimal | None = None,
        target_segments: list[str] | None = None,
        target_cities: list[str] | None = None,
    ) -> Campaign:
        """Create a new marketing campaign."""
        campaign = await self.campaign_repo.create(
            {
                "name": name,
                "description": description,
                "campaign_type": campaign_type,
                "start_date": start_date,
                "end_date": end_date,
                "budget": budget,
                "target_segments": target_segments,
                "target_cities": target_cities,
                "status": "draft",
            }
        )

        logger.info(f"Campaign created: {campaign.name} (ID: {campaign.id})")
        return campaign

    async def activate_campaign(self, campaign_id: int) -> Campaign:
        """Activate a campaign."""
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError("Campaign", campaign_id)

        now = datetime.utcnow()
        if now < campaign.start_date:
            raise ValidationError(f"Cannot activate before start date: {campaign.start_date}")

        if now > campaign.end_date:
            raise ValidationError(f"Cannot activate after end date: {campaign.end_date}")

        campaign = await self.campaign_repo.update(campaign_id, {"status": "active"})

        # Emit event
        await emit_event(
            "campaign.activated",
            {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "campaign_type": campaign.campaign_type,
            },
            sync=False,
        )

        logger.info(f"Campaign activated: {campaign.name}")
        return campaign

    async def pause_campaign(self, campaign_id: int) -> Campaign:
        """Pause an active campaign."""
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError("Campaign", campaign_id)

        if campaign.status != "active":
            raise ValidationError(f"Cannot pause campaign with status: {campaign.status}")

        campaign = await self.campaign_repo.update(campaign_id, {"status": "paused"})

        logger.info(f"Campaign paused: {campaign.name}")
        return campaign

    async def complete_campaign(self, campaign_id: int) -> Campaign:
        """Mark a campaign as completed."""
        campaign = await self.campaign_repo.update(campaign_id, {"status": "completed"})

        # Emit event for reporting
        await emit_event(
            "campaign.completed",
            {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "impressions": campaign.impressions,
                "clicks": campaign.clicks,
                "conversions": campaign.conversions,
                "revenue": float(campaign.revenue),
            },
            sync=False,
        )

        logger.info(f"Campaign completed: {campaign.name}")
        return campaign

    async def get_active_campaigns(self) -> list[Campaign]:
        """Get all active campaigns."""
        return await self.campaign_repo.get_active_campaigns()

    async def get_campaign_metrics(self, campaign_id: int) -> dict[str, Any]:
        """Get detailed metrics for a campaign."""
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError("Campaign", campaign_id)

        ctr = (campaign.clicks / campaign.impressions * 100) if campaign.impressions > 0 else 0
        conversion_rate = (
            (campaign.conversions / campaign.clicks * 100) if campaign.clicks > 0 else 0
        )
        roi = (
            ((campaign.revenue - campaign.spent) / campaign.spent * 100)
            if campaign.spent > 0
            else 0
        )

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "status": campaign.status,
            "impressions": campaign.impressions,
            "clicks": campaign.clicks,
            "ctr": round(ctr, 2),
            "conversions": campaign.conversions,
            "conversion_rate": round(conversion_rate, 2),
            "revenue": float(campaign.revenue),
            "spent": float(campaign.spent),
            "roi": round(roi, 2),
            "budget_remaining": (
                float(campaign.budget - campaign.spent) if campaign.budget else None
            ),
        }

    async def add_promotion_to_campaign(
        self,
        campaign_id: int,
        promotion_data: dict[str, Any],
    ) -> Promotion:
        """Add a promotion to a campaign."""
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError("Campaign", campaign_id)

        promotion_data["campaign_id"] = campaign_id
        promotion = await self.promotion_repo.create(promotion_data)

        logger.info(f"Promotion added to campaign {campaign.name}: {promotion.id}")
        return promotion

    async def get_campaign_promotions(self, campaign_id: int) -> list[Promotion]:
        """Get all promotions for a campaign."""
        return await self.promotion_repo.get_promotions_by_campaign(campaign_id)

    async def track_campaign_click(
        self,
        campaign_id: int,
        user_id: int | None = None,
    ) -> None:
        """Track a click on a campaign."""
        await self.campaign_repo.increment_clicks(campaign_id)

        if user_id:
            await emit_event(
                "campaign.clicked",
                {"campaign_id": campaign_id, "user_id": user_id},
                sync=False,
            )

    async def track_campaign_conversion(
        self,
        campaign_id: int,
        user_id: int,
        order_id: int,
        revenue: Decimal,
    ) -> None:
        """Track a conversion from a campaign."""
        await self.campaign_repo.increment_conversions(campaign_id, revenue)

        await emit_event(
            "campaign.converted",
            {
                "campaign_id": campaign_id,
                "user_id": user_id,
                "order_id": order_id,
                "revenue": float(revenue),
            },
            sync=False,
        )

    async def calculate_campaign_budget_usage(self, campaign_id: int) -> dict[str, Any]:
        """Calculate budget usage for a campaign."""
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError("Campaign", campaign_id)

        if not campaign.budget:
            return {"has_budget": False, "used_percentage": 0, "remaining": 0}

        used_percentage = (campaign.spent / campaign.budget * 100) if campaign.budget > 0 else 0
        remaining = campaign.budget - campaign.spent

        return {
            "has_budget": True,
            "total_budget": float(campaign.budget),
            "spent": float(campaign.spent),
            "remaining": float(remaining),
            "used_percentage": round(used_percentage, 2),
        }


async def run_campaign(db: AsyncSession, campaign_id: int) -> Campaign:
    """Activate and run a campaign."""
    manager = CampaignManager(db)
    return await manager.activate_campaign(campaign_id)


async def get_active_campaigns(db: AsyncSession) -> list[Campaign]:
    """Get all active campaigns."""
    manager = CampaignManager(db)
    return await manager.get_active_campaigns()


async def track_campaign_metrics(
    db: AsyncSession,
    campaign_id: int,
    event_type: str,
    user_id: int | None = None,
    order_id: int | None = None,
    revenue: Decimal | None = None,
) -> None:
    """Track campaign metrics based on event type."""
    manager = CampaignManager(db)

    if event_type == "click":
        await manager.track_campaign_click(campaign_id, user_id)
    elif event_type == "conversion" and order_id and revenue:
        await manager.track_campaign_conversion(campaign_id, user_id, order_id, revenue)


__all__ = [
    "CampaignManager",
    "get_active_campaigns",
    "run_campaign",
    "track_campaign_metrics",
]
