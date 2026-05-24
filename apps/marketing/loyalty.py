# ============================
# WOLLOYEWA STORE BOT - LOYALTY PROGRAM
# ============================
"""Loyalty program management for customer rewards and points."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from core.exceptions import NotFoundError, ValidationError
from apps.marketing.repository import LoyaltyTransactionRepository
from apps.marketing.models import LoyaltyTransaction
from apps.orders.repository import OrderRepository


class LoyaltyManager:
    """
    Loyalty program manager.
    
    Features:
    - Points earning and redemption
    - Tier management
    - Points expiration
    - Transaction history
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.transaction_repo = LoyaltyTransactionRepository(db)
        self.order_repo = OrderRepository(db)
        
        # Default points configuration
        self.points_per_birr = 1.0  # 1 point per ETB
        self.birr_per_point = 0.01  # 0.01 ETB per point (100 points = 1 ETB)
        self.min_redeem_points = 100
        self.max_redeem_per_order = 1000
        self.points_expiry_days = 365
    
    async def get_user_points(self, user_id: int) -> int:
        """Get current points balance for a user."""
        return await self.transaction_repo.get_balance(user_id)
    
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
        """
        Add points to a user's account.
        
        Args:
            user_id: User ID
            points: Points to add (positive integer)
            transaction_type: Type of transaction (earn, adjust)
            reference_id: Reference ID (order_id, review_id, etc.)
            reference_type: Reference type (order, review, share, birthday)
            description: Transaction description
            
        Returns:
            LoyaltyTransaction record
        """
        if points <= 0:
            raise ValidationError("Points must be positive")
        
        current_balance = await self.get_user_points(user_id)
        new_balance = current_balance + points
        
        transaction = await self.transaction_repo.create({
            "user_id": user_id,
            "transaction_type": transaction_type,
            "points": points,
            "points_balance": new_balance,
            "reference_id": reference_id,
            "reference_type": reference_type,
            "description": description,
        })
        
        logger.info(f"Added {points} points to user {user_id}. New balance: {new_balance}")
        return transaction
    
    async def redeem_points(
        self,
        user_id: int,
        points: int,
        order_id: int,
    ) -> Decimal:
        """
        Redeem points for order discount.
        
        Args:
            user_id: User ID
            points: Points to redeem
            order_id: Order ID
            
        Returns:
            Discount amount in Birr
        """
        current_balance = await self.get_user_points(user_id)
        
        if points < self.min_redeem_points:
            raise ValidationError(f"Minimum redemption is {self.min_redeem_points} points")
        
        if points > self.max_redeem_per_order:
            raise ValidationError(f"Maximum redemption per order is {self.max_redeem_per_order} points")
        
        if points > current_balance:
            raise ValidationError(f"Insufficient points. You have {current_balance} points")
        
        # Calculate discount value
        discount_amount = Decimal(str(points * self.birr_per_point))
        
        # Get order to check total
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order", order_id)
        
        # Ensure discount doesn't exceed order total
        discount_amount = min(discount_amount, order.total)
        
        # Deduct points
        new_balance = current_balance - points
        
        transaction = await self.transaction_repo.create({
            "user_id": user_id,
            "transaction_type": "redeem",
            "points": -points,
            "points_balance": new_balance,
            "reference_id": order_id,
            "reference_type": "order",
            "description": f"Redeemed {points} points for order {order.order_number}",
        })
        
        logger.info(f"User {user_id} redeemed {points} points for {discount_amount} ETB discount")
        return discount_amount
    
    async def get_points_value(self, points: int) -> Decimal:
        """Get monetary value of points."""
        return Decimal(str(points * self.birr_per_point))
    
    async def get_user_tier(self, user_id: int) -> str:
        """Get user's loyalty tier based on points."""
        points = await self.get_user_points(user_id)
        
        if points >= 5000:
            return "platinum"
        elif points >= 2000:
            return "gold"
        elif points >= 500:
            return "silver"
        return "bronze"
    
    async def get_tier_benefits(self, tier: str) -> Dict[str, Any]:
        """Get benefits for a specific tier."""
        benefits = {
            "bronze": {
                "discount_rate": 0,
                "free_shipping": False,
                "priority_support": False,
                "birthday_points": 50,
            },
            "silver": {
                "discount_rate": 5,
                "free_shipping": True,
                "priority_support": False,
                "birthday_points": 100,
            },
            "gold": {
                "discount_rate": 10,
                "free_shipping": True,
                "priority_support": True,
                "birthday_points": 200,
            },
            "platinum": {
                "discount_rate": 15,
                "free_shipping": True,
                "priority_support": True,
                "birthday_points": 500,
            },
        }
        return benefits.get(tier, benefits["bronze"])
    
    async def award_order_points(self, user_id: int, order_id: int, total_amount: Decimal) -> None:
        """Award points for an order."""
        points = int(float(total_amount) * self.points_per_birr)
        
        if points > 0:
            await self.add_points(
                user_id=user_id,
                points=points,
                transaction_type="earn",
                reference_id=order_id,
                reference_type="order",
                description=f"Earned {points} points from order",
            )
    
    async def award_review_points(self, user_id: int, review_id: int) -> None:
        """Award points for writing a product review."""
        points = 10
        await self.add_points(
            user_id=user_id,
            points=points,
            transaction_type="earn",
            reference_id=review_id,
            reference_type="review",
            description=f"Earned {points} points for product review",
        )
    
    async def award_birthday_points(self, user_id: int) -> None:
        """Award birthday bonus points."""
        tier = await self.get_user_tier(user_id)
        benefits = await self.get_tier_benefits(tier)
        points = benefits["birthday_points"]
        
        await self.add_points(
            user_id=user_id,
            points=points,
            transaction_type="earn",
            reference_type="birthday",
            description=f"Birthday bonus: {points} points",
        )
    
    async def expire_old_points(self, days: Optional[int] = None) -> int:
        """Expire points older than specified days."""
        expiry_days = days or self.points_expiry_days
        # Implementation for points expiration
        logger.info(f"Expiring points older than {expiry_days} days")
        return 0


async def calculate_points(
    db: AsyncSession,
    user_id: int,
    order_amount: Decimal,
) -> int:
    """Calculate points earned from an order."""
    manager = LoyaltyManager(db)
    return int(float(order_amount) * manager.points_per_birr)


async def redeem_points(
    db: AsyncSession,
    user_id: int,
    points: int,
    order_id: int,
) -> Decimal:
    """Redeem points for discount."""
    manager = LoyaltyManager(db)
    return await manager.redeem_points(user_id, points, order_id)


async def get_user_points(db: AsyncSession, user_id: int) -> int:
    """Get user's current points balance."""
    manager = LoyaltyManager(db)
    return await manager.get_user_points(user_id)


async def get_points_history(
    db: AsyncSession,
    user_id: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get user's points transaction history."""
    manager = LoyaltyManager(db)
    transactions, total = await manager.get_points_history(user_id, limit)
    return [t.to_dict() for t in transactions]


__all__ = [
    "LoyaltyManager",
    "calculate_points",
    "redeem_points",
    "get_user_points",
    "get_points_history",
]