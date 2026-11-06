# ============================
# WOLLOYEWA STORE BOT - COUPONS MANAGER
# ============================
"""Coupon management for discounts and promotions."""

import random
import string
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.marketing.models import Coupon
from apps.marketing.repository import CouponRepository, CouponUsageRepository
from apps.orders.models import Order
from core.exceptions import NotFoundError, ValidationError
from core.logger import logger


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
            random_part = "".join(random.choices(characters, k=length))
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
        eligible_items: list[dict[str, Any]] | None = None,
        user_usage_count: int | None = None,
    ) -> dict[str, Any]:
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
                "discount_amount": Decimal("0"),
            }

        # Check if coupon is active
        if not coupon.is_active:
            return {
                "is_valid": False,
                "message": "Coupon is no longer active",
                "discount_amount": Decimal("0"),
            }

        # Check validity period
        now = datetime.utcnow()
        if now < coupon.valid_from:
            return {
                "is_valid": False,
                "message": f"Coupon is not valid until {coupon.valid_from.strftime('%Y-%m-%d')}",
                "discount_amount": Decimal("0"),
            }

        if now > coupon.valid_to:
            return {
                "is_valid": False,
                "message": "Coupon has expired",
                "discount_amount": Decimal("0"),
            }

        # Check usage limit
        if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
            return {
                "is_valid": False,
                "message": "Coupon has reached its usage limit",
                "discount_amount": Decimal("0"),
            }

        # Check per-user limit
        if coupon.per_user_limit is not None:
            user_usage = (
                user_usage_count
                if user_usage_count is not None
                else await self.usage_repo.get_usage_count(coupon.id, user_id)
            )
            if user_usage >= coupon.per_user_limit:
                return {
                    "is_valid": False,
                    "message": "You have already used this coupon the maximum number of times",
                    "discount_amount": Decimal("0"),
                }

        # Check minimum purchase
        if coupon.min_purchase_amount and order_amount < coupon.min_purchase_amount:
            return {
                "is_valid": False,
                "message": f"Minimum purchase amount of {coupon.min_purchase_amount} ETB required",
                "discount_amount": Decimal("0"),
            }

        # Check new customer restriction
        if coupon.new_customers_only and user_order_count > 0:
            return {
                "is_valid": False,
                "message": "This coupon is for new customers only",
                "discount_amount": Decimal("0"),
            }

        # Check first order restriction
        if coupon.first_order_only and user_order_count > 0:
            return {
                "is_valid": False,
                "message": "This coupon is for first order only",
                "discount_amount": Decimal("0"),
            }

        eligible_amount = self._eligible_amount(coupon, order_amount, eligible_items)
        if eligible_amount <= 0:
            return {
                "is_valid": False,
                "message": "This coupon does not apply to the items in your cart",
                "discount_amount": Decimal("0"),
            }
        discount_amount = coupon.calculate_discount(eligible_amount)
        if discount_amount <= 0:
            return {
                "is_valid": False,
                "message": "This coupon does not apply to the items in your cart",
                "discount_amount": Decimal("0"),
            }

        return {
            "is_valid": True,
            "message": "Coupon is valid",
            "discount_amount": discount_amount,
            "coupon": coupon,
        }

    @staticmethod
    def _eligible_amount(
        coupon,
        order_amount: Decimal,
        items: list[dict[str, Any]] | None,
    ) -> Decimal:
        products = {int(value) for value in (coupon.applicable_products or [])}
        categories = {str(value) for value in (coupon.applicable_categories or [])}
        excluded_products = {int(value) for value in (coupon.excluded_products or [])}
        excluded_categories = {str(value) for value in (coupon.excluded_categories or [])}
        if not any((products, categories, excluded_products, excluded_categories)):
            return order_amount
        if items is None:
            return Decimal("0")

        eligible = Decimal("0")
        for item in items:
            product_id = int(item["product_id"])
            category_id = item.get("category_id")
            category_key = str(category_id) if category_id is not None else ""
            if product_id in excluded_products or category_key in excluded_categories:
                continue
            included = not products and not categories
            if product_id in products or category_key in categories:
                included = True
            if included:
                eligible += Decimal(str(item["amount"]))
        return eligible

    async def apply_coupon(
        self,
        code: str,
        user_id: int,
        order_id: int,
        order_amount: Decimal,
        eligible_items: list[dict[str, Any]] | None = None,
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
        coupon = await self.db.scalar(
            select(Coupon).where(Coupon.code == code.upper()).with_for_update()
        )
        user_order_count = await self.db.scalar(
            select(func.count(Order.id)).where(
                Order.user_id == user_id,
                Order.id != order_id,
            )
        )
        validation = await self.validate_coupon(
            code,
            user_id,
            order_amount,
            user_order_count=user_order_count or 0,
            eligible_items=eligible_items,
        )

        if not validation["is_valid"]:
            raise ValidationError(validation["message"])

        coupon = validation["coupon"]
        discount_amount = validation["discount_amount"]

        # Record usage
        await self.usage_repo.create(
            {
                "coupon_id": coupon.id,
                "user_id": user_id,
                "order_id": order_id,
                "discount_amount": discount_amount,
                "order_amount": order_amount,
            }
        )

        # Update coupon usage count
        coupon.use()
        await self.db.flush()

        logger.info(
            f"Coupon {code} applied to order {order_id} for user {user_id}. Discount: {discount_amount}"
        )
        return discount_amount

    async def get_coupon_stats(self, coupon_id: int) -> dict[str, Any]:
        """Get usage statistics for a coupon."""
        coupon = await self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundError("Coupon", coupon_id)

        usages = await self.usage_repo.get_by_coupon(coupon_id)

        total_discount = sum(u.discount_amount for u in usages)
        unique_users = len({u.user_id for u in usages})

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
) -> dict[str, Any]:
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
    "apply_coupon",
    "generate_coupon_code",
    "validate_coupon",
]
