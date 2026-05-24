# ============================
# WOLLOYEWA STORE BOT - PRICING ENGINE
# ============================
"""Dynamic pricing, discounts, and pricing rules engine."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from core.logger import logger


class DiscountType(str, Enum):
    """Types of discounts."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    BUY_X_GET_Y = "buy_x_get_y"
    BULK_DISCOUNT = "bulk_discount"


@dataclass
class PriceRule:
    """Rule for dynamic pricing."""
    
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    action: Callable[[Decimal], Decimal]
    priority: int = 0
    is_active: bool = True
    applies_to: List[str] = field(default_factory=list)  # product_ids, category_ids, etc.


@dataclass
class PriceResult:
    """Result of price calculation."""
    
    original_price: Decimal
    final_price: Decimal
    discount_amount: Decimal
    discount_percentage: float
    applied_rules: List[str]
    is_on_sale: bool = False


class PricingEngine:
    """
    Dynamic pricing engine for products.
    
    Features:
    - Percentage and fixed amount discounts
    - Bulk pricing (quantity-based)
    - Time-based promotions
    - User-specific pricing (loyalty, etc.)
    - Stackable rules with priority
    """
    
    def __init__(self):
        self._rules: List[PriceRule] = []
        self._init_default_rules()
    
    def _init_default_rules(self) -> None:
        """Initialize default pricing rules."""
        # Rule 1: On-sale products
        self.add_rule(PriceRule(
            name="product_on_sale",
            condition=lambda ctx: ctx.get("is_on_sale", False),
            action=lambda price: self._apply_sale_discount(price, ctx),
            priority=10,
        ))
        
        # Rule 2: Bulk discount
        self.add_rule(PriceRule(
            name="bulk_discount",
            condition=lambda ctx: ctx.get("quantity", 1) >= 3,
            action=lambda price: price * Decimal('0.95'),  # 5% off for 3+ items
            priority=20,
        ))
    
    def add_rule(self, rule: PriceRule) -> None:
        """Add a pricing rule."""
        self._rules.append(rule)
        # Sort by priority (lower number = higher priority)
        self._rules.sort(key=lambda r: r.priority)
        logger.debug(f"Added pricing rule: {rule.name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a pricing rule by name."""
        original_count = len(self._rules)
        self._rules = [r for r in self._rules if r.name != rule_name]
        return len(self._rules) < original_count
    
    def calculate_price(
        self,
        product: Dict[str, Any],
        quantity: int = 1,
        user_id: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> PriceResult:
        """
        Calculate final price for a product.
        
        Args:
            product: Product data dict with price, is_on_sale, etc.
            quantity: Number of items
            user_id: User ID for user-specific pricing
            additional_context: Additional context for rules
            
        Returns:
            PriceResult with calculated price
        """
        original_price = Decimal(str(product.get("price", 0)))
        current_price = original_price
        applied_rules = []
        
        # Build context
        context = {
            "product": product,
            "quantity": quantity,
            "user_id": user_id,
            "is_on_sale": product.get("is_on_sale", False),
            "sale_start_date": product.get("sale_start_date"),
            "sale_end_date": product.get("sale_end_date"),
            "compare_price": product.get("compare_price"),
            **(additional_context or {}),
        }
        
        # Apply rules in priority order
        for rule in self._rules:
            if not rule.is_active:
                continue
            
            # Check if rule applies to this product
            if rule.applies_to:
                product_id = product.get("id")
                category_id = product.get("category_id")
                if product_id not in rule.applies_to and category_id not in rule.applies_to:
                    continue
            
            try:
                if rule.condition(context):
                    current_price = rule.action(current_price)
                    applied_rules.append(rule.name)
                    context["last_applied_price"] = current_price
            except Exception as e:
                logger.error(f"Error applying pricing rule {rule.name}: {e}")
        
        # Ensure price doesn't go below zero
        final_price = max(current_price, Decimal('0'))
        
        # Calculate discount
        discount_amount = original_price - final_price
        discount_percentage = float((discount_amount / original_price) * 100) if original_price > 0 else 0
        
        return PriceResult(
            original_price=original_price,
            final_price=final_price,
            discount_amount=discount_amount,
            discount_percentage=round(discount_percentage, 1),
            applied_rules=applied_rules,
            is_on_sale=discount_amount > 0,
        )
    
    def _apply_sale_discount(self, price: Decimal, context: Dict[str, Any]) -> Decimal:
        """Apply sale discount from product."""
        compare_price = context.get("compare_price")
        if compare_price and compare_price > price:
            return price  # Already discounted
        return price
    
    def calculate_bulk_price(
        self,
        base_price: Decimal,
        quantity: int,
        tier_prices: Optional[List[Dict[str, Any]]] = None,
    ) -> Decimal:
        """
        Calculate bulk pricing based on quantity tiers.
        
        Args:
            base_price: Base price per unit
            quantity: Number of units
            tier_prices: List of tiers with min_quantity and price
            
        Returns:
            Price per unit after bulk discount
        """
        if not tier_prices:
            return base_price
        
        # Sort tiers by min_quantity descending
        sorted_tiers = sorted(tier_prices, key=lambda t: t.get("min_quantity", 0), reverse=True)
        
        for tier in sorted_tiers:
            if quantity >= tier.get("min_quantity", 0):
                return Decimal(str(tier.get("price", base_price)))
        
        return base_price


# Global pricing engine instance
pricing_engine = PricingEngine()


def calculate_discounted_price(
    price: Decimal,
    discount_value: float,
    discount_type: DiscountType = DiscountType.PERCENTAGE,
) -> Decimal:
    """
    Calculate discounted price.
    
    Args:
        price: Original price
        discount_value: Discount amount or percentage
        discount_type: Type of discount
        
    Returns:
        Discounted price
    """
    if discount_type == DiscountType.PERCENTAGE:
        discount = price * Decimal(str(discount_value / 100))
        return max(price - discount, Decimal('0'))
    elif discount_type == DiscountType.FIXED_AMOUNT:
        return max(price - Decimal(str(discount_value)), Decimal('0'))
    else:
        return price


def apply_bulk_discount(
    base_price: Decimal,
    quantity: int,
    thresholds: List[Dict[str, Any]],
) -> Decimal:
    """
    Apply bulk discount based on quantity thresholds.
    
    Args:
        base_price: Base price per unit
        quantity: Number of units
        thresholds: List of {min_qty: int, discount: float}
        
    Returns:
        Price per unit after bulk discount
    """
    discount = Decimal('0')
    
    for threshold in thresholds:
        if quantity >= threshold.get("min_qty", 0):
            discount = Decimal(str(threshold.get("discount", 0)))
    
    if discount > 0:
        return base_price * (Decimal('1') - discount / 100)
    
    return base_price


def calculate_price_with_tax(
    price: Decimal,
    tax_rate: float = 0.15,
    tax_inclusive: bool = True,
) -> Decimal:
    """
    Calculate price including or excluding tax.
    
    Args:
        price: Base price
        tax_rate: Tax rate (default 15% for Ethiopia)
        tax_inclusive: Whether tax is already included
        
    Returns:
        Price with tax
    """
    if tax_inclusive:
        # Tax is already included, extract it if needed
        return price
    else:
        # Add tax
        return price * (Decimal('1') + Decimal(str(tax_rate)))


__all__ = [
    "PricingEngine",
    "PriceRule",
    "PriceResult",
    "DiscountType",
    "pricing_engine",
    "calculate_discounted_price",
    "apply_bulk_discount",
    "calculate_price_with_tax",
]