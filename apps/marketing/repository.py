# ============================
# WOLLOYEWA STORE BOT - MARKETING REPOSITORIES
# ============================
"""Database repositories for marketing models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.repository import BaseRepository
from apps.marketing.models import Coupon, CouponUsage, LoyaltyTransaction, Campaign, Promotion
from core.logger import logger


class CouponRepository(BaseRepository[Coupon]):
    """Repository for Coupon model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Coupon, db)
    
    async def get_by_code(self, code: str) -> Optional[Coupon]:
        """Get coupon by code."""
        query = select(Coupon).where(Coupon.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_coupons(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Coupon], int]:
        """Get active coupons."""
        now = datetime.utcnow()
        conditions = [
            Coupon.is_active == True,
            Coupon.valid_from <= now,
            Coupon.valid_to >= now,
        ]
        
        count_query = select(func.count()).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        query = select(Coupon).where(and_(*conditions))
        query = query.order_by(Coupon.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        
        return result.scalars().all(), total
    
    async def get_valid_coupons_for_user(
        self,
        user_id: int,
        order_amount: Decimal,
    ) -> List[Coupon]:
        """Get valid coupons for a user."""
        now = datetime.utcnow()
        conditions = [
            Coupon.is_active == True,
            Coupon.valid_from <= now,
            Coupon.valid_to >= now,
            or_(
                Coupon.min_purchase_amount.is_(None),
                Coupon.min_purchase_amount <= order_amount
            ),
            or_(
                Coupon.usage_limit.is_(None),
                Coupon.used_count < Coupon.usage_limit
            ),
        ]
        
        query = select(Coupon).where(and_(*conditions))
        query = query.order_by(Coupon.discount_value.desc())
        result = await self.db.execute(query)
        
        coupons = result.scalars().all()
        
        # Filter by user-specific limits
        valid_coupons = []
        for coupon in coupons:
            user_usage = await self.db.execute(
                select(func.count()).where(
                    CouponUsage.coupon_id == coupon.id,
                    CouponUsage.user_id == user_id
                )
            )
            user_usage_count = user_usage.scalar() or 0
            
            if coupon.per_user_limit is None or user_usage_count < coupon.per_user_limit:
                valid_coupons.append(coupon)
        
        return valid_coupons
    
    async def get_expired_coupons(self) -> List[Coupon]:
        """Get expired coupons."""
        now = datetime.utcnow()
        query = select(Coupon).where(
            Coupon.valid_to < now,
            Coupon.is_active == True
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def deactivate_expired_coupons(self) -> int:
        """Deactivate expired coupons."""
        expired = await self.get_expired_coupons()
        for coupon in expired:
            await self.update(coupon.id, {"is_active": False})
        return len(expired)


class CouponUsageRepository(BaseRepository[CouponUsage]):
    """Repository for CouponUsage model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(CouponUsage, db)
    
    async def get_by_coupon(
        self,
        coupon_id: int,
        limit: int = 100,
    ) -> List[CouponUsage]:
        """Get usages for a coupon."""
        query = select(CouponUsage).where(CouponUsage.coupon_id == coupon_id)
        query = query.order_by(CouponUsage.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_user(
        self,
        user_id: int,
        limit: int = 100,
    ) -> List[CouponUsage]:
        """Get usages by user."""
        query = select(CouponUsage).where(CouponUsage.user_id == user_id)
        query = query.order_by(CouponUsage.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_usage_count(self, coupon_id: int, user_id: Optional[int] = None) -> int:
        """Get usage count for a coupon."""
        conditions = [CouponUsage.coupon_id == coupon_id]
        if user_id:
            conditions.append(CouponUsage.user_id == user_id)
        
        query = select(func.count()).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalar() or 0


class LoyaltyTransactionRepository(BaseRepository[LoyaltyTransaction]):
    """Repository for LoyaltyTransaction model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(LoyaltyTransaction, db)
    
    async def get_by_user(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[LoyaltyTransaction], int]:
        """Get transactions for a user."""
        conditions = [LoyaltyTransaction.user_id == user_id]
        
        count_query = select(func.count()).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        query = select(LoyaltyTransaction).where(and_(*conditions))
        query = query.order_by(LoyaltyTransaction.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        
        return result.scalars().all(), total
    
    async def get_balance(self, user_id: int) -> int:
        """Get current points balance for a user."""
        query = select(LoyaltyTransaction).where(
            LoyaltyTransaction.user_id == user_id
        ).order_by(LoyaltyTransaction.created_at.desc()).limit(1)
        
        result = await self.db.execute(query)
        last_transaction = result.scalar_one_or_none()
        
        if last_transaction:
            return last_transaction.points_balance
        return 0


class CampaignRepository(BaseRepository[Campaign]):
    """Repository for Campaign model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Campaign, db)
    
    async def get_active_campaigns(self) -> List[Campaign]:
        """Get active campaigns."""
        now = datetime.utcnow()
        query = select(Campaign).where(
            Campaign.status == "active",
            Campaign.start_date <= now,
            Campaign.end_date >= now,
        )
        query = query.order_by(Campaign.start_date)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_campaigns_by_status(
        self,
        status: str,
        limit: int = 50,
    ) -> List[Campaign]:
        """Get campaigns by status."""
        query = select(Campaign).where(Campaign.status == status)
        query = query.order_by(Campaign.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def increment_impressions(self, campaign_id: int) -> None:
        """Increment campaign impressions."""
        await self.db.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(impressions=Campaign.impressions + 1)
        )
        await self.db.flush()
    
    async def increment_clicks(self, campaign_id: int) -> None:
        """Increment campaign clicks."""
        await self.db.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(clicks=Campaign.clicks + 1)
        )
        await self.db.flush()
    
    async def increment_conversions(self, campaign_id: int, revenue: Decimal) -> None:
        """Increment campaign conversions and revenue."""
        await self.db.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(
                conversions=Campaign.conversions + 1,
                revenue=Campaign.revenue + revenue
            )
        )
        await self.db.flush()


class PromotionRepository(BaseRepository[Promotion]):
    """Repository for Promotion model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Promotion, db)
    
    async def get_active_promotions(
        self,
        product_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> List[Promotion]:
        """Get active promotions for product or category."""
        now = datetime.utcnow()
        conditions = [
            Promotion.is_active == True,
            Promotion.start_date <= now,
            Promotion.end_date >= now,
            or_(
                Promotion.usage_limit.is_(None),
                Promotion.used_count < Promotion.usage_limit
            ),
        ]
        
        query = select(Promotion).where(and_(*conditions))
        
        if product_id:
            query = query.where(
                or_(
                    Promotion.product_ids.contains([product_id]),
                    Promotion.product_ids.is_(None)
                )
            )
        
        if category_id:
            query = query.where(
                or_(
                    Promotion.category_ids.contains([category_id]),
                    Promotion.category_ids.is_(None)
                )
            )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_promotions_by_campaign(
        self,
        campaign_id: int,
    ) -> List[Promotion]:
        """Get promotions for a campaign."""
        query = select(Promotion).where(Promotion.campaign_id == campaign_id)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def increment_usage(self, promotion_id: int) -> None:
        """Increment promotion usage count."""
        await self.db.execute(
            update(Promotion)
            .where(Promotion.id == promotion_id)
            .values(used_count=Promotion.used_count + 1)
        )
        await self.db.flush()


__all__ = [
    "CouponRepository",
    "CouponUsageRepository",
    "LoyaltyTransactionRepository",
    "CampaignRepository",
    "PromotionRepository",
]