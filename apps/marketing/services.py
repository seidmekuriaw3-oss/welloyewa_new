# ============================
# WOLLOYEWA STORE BOT - MARKETING SERVICES
# ============================
"""Business logic for coupons, loyalty programs, campaigns, and promotions."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from core.exceptions import NotFoundError, ValidationError
from core.events import emit_event
from apps.marketing.repository import (
    CouponRepository,
    CouponUsageRepository,
    LoyaltyTransactionRepository,
    CampaignRepository,
    PromotionRepository,
)
from apps.marketing.models import Coupon, CouponUsage, LoyaltyTransaction, Campaign, Promotion
from apps.marketing.schemas import (
    CouponCreate,
    CouponUpdate,
    CouponValidateRequest,
    LoyaltyProgramCreate,
    LoyaltyTransactionCreate,
    CampaignCreate,
    CampaignUpdate,
    PromotionCreate,
    PromotionUpdate,
)
from apps.marketing.loyalty import LoyaltyManager
from apps.marketing.coupons import CouponManager
from apps.marketing.campaigns import CampaignManager


class CouponService:
    """Service for coupon management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.coupon_repo = CouponRepository(db)
        self.usage_repo = CouponUsageRepository(db)
        self.coupon_manager = CouponManager(db)
    
    async def create_coupon(self, data: CouponCreate) -> Coupon:
        """Create a new coupon."""
        # Check if code already exists
        existing = await self.coupon_repo.get_by_code(data.code)
        if existing:
            raise ValidationError(f"Coupon code '{data.code}' already exists")
        
        coupon = await self.coupon_repo.create(data.dict())
        logger.info(f"Coupon created: {coupon.code}")
        return coupon
    
    async def get_coupon(self, coupon_id: int) -> Coupon:
        """Get coupon by ID."""
        coupon = await self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundError("Coupon", coupon_id)
        return coupon
    
    async def get_coupon_by_code(self, code: str) -> Optional[Coupon]:
        """Get coupon by code."""
        return await self.coupon_repo.get_by_code(code)
    
    async def update_coupon(self, coupon_id: int, data: CouponUpdate) -> Coupon:
        """Update a coupon."""
        coupon = await self.get_coupon(coupon_id)
        updated = await self.coupon_repo.update(coupon_id, data.dict(exclude_unset=True))
        logger.info(f"Coupon updated: {coupon.code}")
        return updated
    
    async def delete_coupon(self, coupon_id: int) -> bool:
        """Delete a coupon."""
        coupon = await self.get_coupon(coupon_id)
        result = await self.coupon_repo.delete(coupon_id)
        logger.info(f"Coupon deleted: {coupon.code}")
        return result
    
    async def validate_coupon(
        self,
        code: str,
        user_id: int,
        order_amount: Decimal,
        user_order_count: int = 0,
    ) -> Dict[str, Any]:
        """Validate a coupon for use."""
        return await self.coupon_manager.validate_coupon(
            code, user_id, order_amount, user_order_count
        )
    
    async def apply_coupon(
        self,
        code: str,
        user_id: int,
        order_id: int,
        order_amount: Decimal,
    ) -> Decimal:
        """Apply a coupon to an order."""
        return await self.coupon_manager.apply_coupon(
            code, user_id, order_id, order_amount
        )
    
    async def get_active_coupons(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Coupon], int]:
        """Get active coupons."""
        return await self.coupon_repo.get_active_coupons(limit, offset)
    
    async def get_coupons_for_user(
        self,
        user_id: int,
        order_amount: Decimal,
    ) -> List[Coupon]:
        """Get valid coupons for a user."""
        return await self.coupon_repo.get_valid_coupons_for_user(user_id, order_amount)


class LoyaltyService:
    """Service for loyalty program operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.transaction_repo = LoyaltyTransactionRepository(db)
        self.loyalty_manager = LoyaltyManager(db)
    
    async def get_user_points(self, user_id: int) -> int:
        """Get current points balance for a user."""
        return await self.loyalty_manager.get_user_points(user_id)
    
    async def get_points_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[LoyaltyTransaction], int]:
        """Get points transaction history."""
        return await self.transaction_repo.get_by_user(user_id, limit, offset)
    
    async def add_points(
        self,
        user_id: int,
        points: int,
        transaction_type: str,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> LoyaltyTransaction:
        """Add points to a user's account."""
        return await self.loyalty_manager.add_points(
            user_id, points, transaction_type, reference_id, reference_type, description
        )
    
    async def redeem_points(
        self,
        user_id: int,
        points: int,
        order_id: int,
    ) -> Decimal:
        """Redeem points for discount."""
        return await self.loyalty_manager.redeem_points(user_id, points, order_id)
    
    async def get_points_value(self, points: int) -> Decimal:
        """Get monetary value of points."""
        return await self.loyalty_manager.get_points_value(points)
    
    async def get_user_tier(self, user_id: int) -> Optional[str]:
        """Get user's loyalty tier."""
        points = await self.get_user_points(user_id)
        # Define tiers based on points
        if points >= 5000:
            return "platinum"
        elif points >= 2000:
            return "gold"
        elif points >= 500:
            return "silver"
        return "bronze"


class CampaignService:
    """Service for campaign management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.campaign_repo = CampaignRepository(db)
        self.campaign_manager = CampaignManager(db)
    
    async def create_campaign(self, data: CampaignCreate) -> Campaign:
        """Create a new campaign."""
        campaign = await self.campaign_repo.create(data.dict())
        logger.info(f"Campaign created: {campaign.name}")
        return campaign
    
    async def get_campaign(self, campaign_id: int) -> Campaign:
        """Get campaign by ID."""
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError("Campaign", campaign_id)
        return campaign
    
    async def update_campaign(self, campaign_id: int, data: CampaignUpdate) -> Campaign:
        """Update a campaign."""
        campaign = await self.get_campaign(campaign_id)
        updated = await self.campaign_repo.update(campaign_id, data.dict(exclude_unset=True))
        logger.info(f"Campaign updated: {campaign.name}")
        return updated
    
    async def activate_campaign(self, campaign_id: int) -> Campaign:
        """Activate a campaign."""
        return await self.campaign_manager.activate_campaign(campaign_id)
    
    async def pause_campaign(self, campaign_id: int) -> Campaign:
        """Pause a campaign."""
        return await self.campaign_manager.pause_campaign(campaign_id)
    
    async def get_active_campaigns(self) -> List[Campaign]:
        """Get active campaigns."""
        return await self.campaign_repo.get_active_campaigns()
    
    async def track_impression(self, campaign_id: int) -> None:
        """Track campaign impression."""
        await self.campaign_repo.increment_impressions(campaign_id)
    
    async def track_click(self, campaign_id: int, user_id: Optional[int] = None) -> None:
        """Track campaign click."""
        await self.campaign_repo.increment_clicks(campaign_id)
        
        if user_id:
            await emit_event(
                "campaign.clicked",
                {"campaign_id": campaign_id, "user_id": user_id},
                sync=False,
            )
    
    async def track_conversion(
        self,
        campaign_id: int,
        user_id: int,
        order_id: int,
        revenue: Decimal,
    ) -> None:
        """Track campaign conversion."""
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


class PromotionService:
    """Service for promotion management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.promotion_repo = PromotionRepository(db)
    
    async def create_promotion(self, data: PromotionCreate) -> Promotion:
        """Create a new promotion."""
        promotion = await self.promotion_repo.create(data.dict())
        logger.info(f"Promotion created: {promotion.id}")
        return promotion
    
    async def get_promotion(self, promotion_id: int) -> Promotion:
        """Get promotion by ID."""
        promotion = await self.promotion_repo.get_by_id(promotion_id)
        if not promotion:
            raise NotFoundError("Promotion", promotion_id)
        return promotion
    
    async def update_promotion(self, promotion_id: int, data: PromotionUpdate) -> Promotion:
        """Update a promotion."""
        promotion = await self.get_promotion(promotion_id)
        updated = await self.promotion_repo.update(promotion_id, data.dict(exclude_unset=True))
        logger.info(f"Promotion updated: {promotion.id}")
        return updated
    
    async def get_active_promotions(
        self,
        product_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> List[Promotion]:
        """Get active promotions for a product or category."""
        return await self.promotion_repo.get_active_promotions(product_id, category_id)
    
    async def calculate_promotion_discount(
        self,
        product_id: int,
        product_price: Decimal,
        quantity: int = 1,
    ) -> Decimal:
        """Calculate discount from applicable promotions."""
        promotions = await self.get_active_promotions(product_id=product_id)
        
        if not promotions:
            return Decimal('0')
        
        # Use the best discount
        best_discount = Decimal('0')
        for promotion in promotions:
            if promotion.promotion_type == "discount":
                if promotion.discount_type == "percentage":
                    discount = product_price * (promotion.discount_value / 100)
                else:
                    discount = promotion.discount_value
                
                if promotion.max_discount:
                    discount = min(discount, promotion.max_discount)
                
                best_discount = max(best_discount, discount)
            elif promotion.promotion_type == "buy_x_get_y":
                # Buy X Get Y logic
                if quantity >= (promotion.buy_quantity or 0):
                    free_items = (quantity // (promotion.buy_quantity or 1)) * (promotion.get_quantity or 0)
                    discount = product_price * free_items
                    best_discount = max(best_discount, discount)
        
        return min(best_discount, product_price * quantity)


__all__ = ["CouponService", "LoyaltyService", "CampaignService", "PromotionService"]