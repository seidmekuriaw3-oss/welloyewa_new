# ============================
# WOLLOYEWA STORE BOT - COUPONS MANAGER
# ============================
"""Coupon management for discounts and promotions."""

import random
import string
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from core.exceptions import NotFoundError, ValidationError
from apps.marketing.repository import CouponRepository, CouponUsageRepository
from apps.marketing.models import Coupon, CouponUsage


class CouponManager:
    """
    Coupon manager for discount codes.
    
    Features:
    - Generate unique coupon codes
    - Validate coupon usage
    - Track coupon redemptions
    - Apply discounts to orders
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.coupon_repo = CouponRepository(db)
        self.usage_repo = CouponUsageRepository(db)
    
    async def generate_coupon_code(
        self,
        prefix: str = "",
        length: int = 8,
        uppercase: bool = True,
    ) -> str:
        """
        Generate a unique coupon code.
        
        Args:
            prefix: Optional prefix for the code
            length: Length of the random part
            uppercase: Whether to use uppercase letters
            
        Returns:
            Unique coupon code
        """
        characters = string.ascii_uppercase if uppercase else string.ascii_lowercase
        characters += string.digits
        
        while True:
            random_part = ''.join(random.choices(characters, k=length))
            code = f"{prefix}{random_part}" if prefix else random_part
            
            # Check if code already exists
            existing = await self.coupon_repo.get_by_code(code)
            if not existing:
                return code
    
    async def validate_coupon(
        self,
        code: str,
        user_id: int,
        order_amount: Decimal,
        user_order_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Validate a coupon for use.
        
        Args:
            code: Coupon code
            user_id: User ID
            order_amount: Order total amount
            user_order_count: Number of previous orders by user
            
        Returns:
            Validation result with discount amount if valid
        """
        coupon = await self.coupon_repo.get_by_code(code.upper())
        
        if not coupon:
            return {
                "is_valid": False,
                "message": "Invalid coupon code",
                "discount_amount": Decimal('0'),
            }
        
        # Check if coupon is active
        if not coupon.is_active:
            return {
                "is_valid": False,
                "message": "Coupon is no longer active",
                "discount_amount": Decimal('0'),
            }
        
        # Check validity period
        now = datetime.utcnow()
        if now < coupon.valid_from:
            return {
                "is_valid": False,
                "message": f"Coupon is not valid until {coupon.valid_from.strftime('%Y-%m-%d')}",
                "discount_amount": Decimal('0'),
            }
        
        if now > coupon.valid_to:
            return {
                "is_valid": False,
                "message": "Coupon has expired",
                "discount_amount": Decimal('0'),
            }
        
        # Check usage limit
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            return {
                "is_valid": False,
                "message": "Coupon has reached its usage limit",
                "discount_amount": Decimal('0'),
            }
        
        # Check per-user limit
        if coupon.per_user_limit:
            user_usage = await self.usage_repo.get_usage_count(coupon.id, user_id)
            if user_usage >= coupon.per_user_limit:
                return {
                    "is_valid": False,
                    "message": "You have already used this coupon the maximum number of times",
                    "discount_amount": Decimal('0'),
                }
        
        # Check minimum purchase
        if coupon.min_purchase_amount and order_amount < coupon.min_purchase_amount:
            return {
                "is_valid": False,
                "message": f"Minimum purchase amount of {coupon.min_purchase_amount} ETB required",
                "discount_amount": Decimal('0'),
            }
        
        # Check new customer restriction
        if coupon.new_customers_only and user_order_count > 0:
            return {
                "is_valid": False,
                "message": "This coupon is for new customers only",
                "discount_amount": Decimal('0'),
            }
        
        # Check first order restriction
        if coupon.first_order_only and user_order_count > 0:
            return {
                "is_valid": False,
                "message": "This coupon is for first order only",
                "discount_amount": Decimal('0'),
            }
        
        # Calculate discount
        discount_amount = coupon.calculate_discount(order_amount)
        
        return {
            "is_valid": True,
            "message": "Coupon is valid",
            "discount_amount": discount_amount,
            "coupon": coupon,
        }
    
    async def apply_coupon(
        self,
        code: str,
        user_id: int,
        order_id: int,
        order_amount: Decimal,
    ) -> Decimal:
        """
        Apply a coupon to an order.
        
        Args:
            code: Coupon code
            user_id: User ID
            order_id: Order ID
            order_amount: Order total amount
            
        Returns:
            Discount amount applied
        """
        validation = await self.validate_coupon(code, user_id, order_amount)
        
        if not validation["is_valid"]:
            raise ValidationError(validation["message"])
        
        coupon = validation["coupon"]
        discount_amount = validation["discount_amount"]
        
        # Record usage
        await self.usage_repo.create({
            "coupon_id": coupon.id,
            "user_id": user_id,
            "order_id": order_id,
            "discount_amount": discount_amount,
            "order_amount": order_amount,
        })
        
        # Update coupon usage count
        coupon.use()
        await self.coupon_repo.update(coupon.id, {"used_count": coupon.used_count})
        
        logger.info(f"Coupon {code} applied to order {order_id} for user {user_id}. Discount: {discount_amount}")
        return discount_amount
    
    async def get_coupon_stats(self, coupon_id: int) -> Dict[str, Any]:
        """Get usage statistics for a coupon."""
        coupon = await self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundError("Coupon", coupon_id)
        
        usages = await self.usage_repo.get_by_coupon(coupon_id)
        
        total_discount = sum(u.discount_amount for u in usages)
        unique_users = len(set(u.user_id for u in usages))
        
        return {
            "coupon_id": coupon_id,
            "code": coupon.code,
            "used_count": coupon.used_count,
            "total_discount": total_discount,
            "unique_users": unique_users,
            "average_discount": total_discount / len(usages) if usages else 0,
        }
    
    async def deactivate_expired_coupons(self) -> int:
        """Deactivate all expired coupons."""
        expired = await self.coupon_repo.get_expired_coupons()
        for coupon in expired:
            await self.coupon_repo.update(coupon.id, {"is_active": False})
        return len(expired)


async def generate_coupon_code(
    db: AsyncSession,
    prefix: str = "",
    length: int = 8,
) -> str:
    """Generate a unique coupon code."""
    manager = CouponManager(db)
    return await manager.generate_coupon_code(prefix, length)


async def validate_coupon(
    db: AsyncSession,
    code: str,
    user_id: int,
    order_amount: Decimal,
    user_order_count: int = 0,
) -> Dict[str, Any]:
    """Validate a coupon for use."""
    manager = CouponManager(db)
    return await manager.validate_coupon(code, user_id, order_amount, user_order_count)


async def apply_coupon(
    db: AsyncSession,
    code: str,
    user_id: int,
    order_id: int,
    order_amount: Decimal,
) -> Decimal:
    """Apply a coupon to an order."""
    manager = CouponManager(db)
    return await manager.apply_coupon(code, user_id, order_id, order_amount)


__all__ = [
    "CouponManager",
    "generate_coupon_code",
    "validate_coupon",
    "apply_coupon",
]