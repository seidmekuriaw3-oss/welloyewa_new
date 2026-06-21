<<<<<<< HEAD
__all__ = []
=======
# ============================
# WOLLOYEWA STORE BOT - MARKETING MODULE
# ============================
"""Marketing module for promotions, campaigns, and loyalty programs."""

from apps.marketing.models import (
    Coupon,
    CouponUsage,
    LoyaltyProgram,
    LoyaltyTransaction,
    Campaign,
    CampaignRule,
    Promotion,
)
from apps.marketing.services import (
    CouponService,
    LoyaltyService,
    CampaignService,
    PromotionService,
)
from apps.marketing.repository import (
    CouponRepository,
    LoyaltyRepository,
    CampaignRepository,
    PromotionRepository,
)
from apps.marketing.schemas import (
    CouponCreate,
    CouponUpdate,
    CouponResponse,
    CouponValidateRequest,
    CouponValidateResponse,
    LoyaltyProgramCreate,
    LoyaltyProgramUpdate,
    LoyaltyProgramResponse,
    LoyaltyTransactionCreate,
    LoyaltyTransactionResponse,
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
)
from apps.marketing.loyalty import (
    LoyaltyManager,
    calculate_points,
    redeem_points,
    get_user_points,
    get_points_history,
)
from apps.marketing.coupons import (
    CouponManager,
    generate_coupon_code,
    validate_coupon,
    apply_coupon,
)
from apps.marketing.campaigns import (
    CampaignManager,
    run_campaign,
    get_active_campaigns,
    track_campaign_metrics,
)

class MarketingService:
    """Composite marketing service exposing all marketing sub-services."""

    def __init__(self, db):
        self.coupons = CouponService(db)
        self.loyalty = LoyaltyService(db)
        self.campaigns = CampaignService(db)
        self.promotions = PromotionService(db)


__all__ = [
    "MarketingService",
    # Models
    "Coupon",
    "CouponUsage",
    "LoyaltyProgram",
    "LoyaltyTransaction",
    "Campaign",
    "CampaignRule",
    "Promotion",
    # Services
    "CouponService",
    "LoyaltyService",
    "CampaignService",
    "PromotionService",
    # Repositories
    "CouponRepository",
    "LoyaltyRepository",
    "CampaignRepository",
    "PromotionRepository",
    # Schemas
    "CouponCreate",
    "CouponUpdate",
    "CouponResponse",
    "CouponValidateRequest",
    "CouponValidateResponse",
    "LoyaltyProgramCreate",
    "LoyaltyProgramUpdate",
    "LoyaltyProgramResponse",
    "LoyaltyTransactionCreate",
    "LoyaltyTransactionResponse",
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignResponse",
    "PromotionCreate",
    "PromotionUpdate",
    "PromotionResponse",
    # Loyalty
    "LoyaltyManager",
    "calculate_points",
    "redeem_points",
    "get_user_points",
    "get_points_history",
    # Coupons
    "CouponManager",
    "generate_coupon_code",
    "validate_coupon",
    "apply_coupon",
    # Campaigns
    "CampaignManager",
    "run_campaign",
    "get_active_campaigns",
    "track_campaign_metrics",
]
>>>>>>> 58a16d4ee3078d96a16a22860de294107e7c3aef
