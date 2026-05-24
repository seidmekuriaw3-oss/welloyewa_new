# ============================
# WOLLOYEWA STORE BOT - CURRENCY UTILITIES
# ============================
"""Currency formatting, conversion, and calculation utilities."""

import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union
from dataclasses import dataclass

from core.config import settings
from core.logger import logger


# Type alias for amount values
Amount = Union[int, float, Decimal, str]


def to_decimal(amount: Amount) -> Decimal:
    """Convert various types to Decimal."""
    if isinstance(amount, Decimal):
        return amount
    if isinstance(amount, str):
        return Decimal(amount)
    if isinstance(amount, (int, float)):
        return Decimal(str(amount))
    raise TypeError(f"Cannot convert {type(amount)} to Decimal")


def format_currency(
    amount: Amount,
    symbol: str = "ብር",
    decimal_places: int = 2,
    include_symbol: bool = True,
    group_digits: bool = True,
) -> str:
    """
    Format currency amount for display.
    
    Args:
        amount: Amount to format
        symbol: Currency symbol
        decimal_places: Number of decimal places
        include_symbol: Whether to include currency symbol
        group_digits: Whether to group thousands
        
    Returns:
        Formatted currency string
    """
    decimal_amount = to_decimal(amount)
    decimal_amount = decimal_amount.quantize(
        Decimal('10') ** -decimal_places,
        rounding=ROUND_HALF_UP,
    )
    
    # Format with or without grouping
    if group_digits:
        formatted = f"{decimal_amount:,.{decimal_places}f}"
    else:
        formatted = f"{decimal_amount:.{decimal_places}f}"
    
    if include_symbol:
        return f"{formatted} {symbol}"
    return formatted


def format_etb(amount: Amount, short: bool = False) -> str:
    """
    Format amount in Ethiopian Birr.
    
    Args:
        amount: Amount to format
        short: Whether to use short format (e.g., "1.5k ብር")
        
    Returns:
        Formatted Birr string
    """
    decimal_amount = to_decimal(amount)
    
    if short and decimal_amount >= 1000:
        thousands = decimal_amount / 1000
        if thousands < 10:
            return f"{thousands:.1f}k ብር"
        return f"{thousands:.0f}k ብር"
    
    return format_currency(amount, symbol="ብር")


def calculate_tax(
    amount: Amount,
    tax_rate: float = 0.15,
    include_inclusive: bool = True,
) -> Decimal:
    """
    Calculate tax for an amount.
    
    Args:
        amount: Original amount
        tax_rate: Tax rate (default 15% VAT)
        include_inclusive: Whether tax is inclusive in amount
        
    Returns:
        Calculated tax amount
    """
    decimal_amount = to_decimal(amount)
    rate = Decimal(str(tax_rate))
    
    if include_inclusive:
        # Tax is already included in price
        # Tax = Price - (Price / (1 + rate))
        tax = decimal_amount - (decimal_amount / (1 + rate))
    else:
        # Tax is added to price
        tax = decimal_amount * rate
    
    return tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def add_tax(amount: Amount, tax_rate: float = 0.15) -> Decimal:
    """
    Add tax to an amount.
    
    Args:
        amount: Original amount (excluding tax)
        tax_rate: Tax rate (default 15%)
        
    Returns:
        Amount including tax
    """
    decimal_amount = to_decimal(amount)
    rate = Decimal(str(tax_rate))
    total = decimal_amount * (1 + rate)
    return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_discount(
    amount: Amount,
    discount_percent: float = None,
    discount_amount: Amount = None,
) -> Decimal:
    """
    Calculate discount on an amount.
    
    Args:
        amount: Original amount
        discount_percent: Discount percentage (0-100)
        discount_amount: Fixed discount amount
        
    Returns:
        Discounted amount
    """
    decimal_amount = to_decimal(amount)
    
    if discount_percent is not None:
        percent = Decimal(str(discount_percent))
        discount = decimal_amount * (percent / 100)
    elif discount_amount is not None:
        discount = to_decimal(discount_amount)
    else:
        return decimal_amount
    
    result = decimal_amount - discount
    return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_discount_percent(original: Amount, discounted: Amount) -> Decimal:
    """
    Calculate discount percentage between original and discounted price.
    
    Args:
        original: Original price
        discounted: Discounted price
        
    Returns:
        Discount percentage
    """
    original_dec = to_decimal(original)
    discounted_dec = to_decimal(discounted)
    
    if original_dec == 0:
        return Decimal(0)
    
    percent = ((original_dec - discounted_dec) / original_dec) * 100
    return percent.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_subtotal(items: list, price_key: str = "price", quantity_key: str = "quantity") -> Decimal:
    """
    Calculate subtotal from list of items.
    
    Args:
        items: List of items with price and quantity
        price_key: Key for price in each item
        quantity_key: Key for quantity in each item
        
    Returns:
        Subtotal amount
    """
    subtotal = Decimal(0)
    for item in items:
        price = to_decimal(item.get(price_key, 0))
        quantity = int(item.get(quantity_key, 0))
        subtotal += price * quantity
    return subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class CurrencyConverter:
    """Currency conversion utility with caching."""
    
    # Fixed exchange rates (in production, fetch from API)
    # Rates are relative to ETB (Ethiopian Birr)
    EXCHANGE_RATES = {
        "ETB": 1.0,      # Ethiopian Birr (base)
        "USD": 0.0175,   # US Dollar
        "EUR": 0.0160,   # Euro
        "GBP": 0.0137,   # British Pound
        "CNY": 0.1260,   # Chinese Yuan
        "AED": 0.0642,   # UAE Dirham
        "SAR": 0.0656,   # Saudi Riyal
        "KES": 2.28,     # Kenyan Shilling
    }
    
    def __init__(self, base_currency: str = "ETB"):
        self.base_currency = base_currency.upper()
        self._cache = {}
    
    def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """
        Get exchange rate between two currencies.
        
        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            
        Returns:
            Exchange rate
        """
        from_curr = from_currency.upper()
        to_curr = to_currency.upper()
        
        cache_key = f"{from_curr}:{to_curr}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Convert via ETB as base
        rate_from = self.EXCHANGE_RATES.get(from_curr, 1.0)
        rate_to = self.EXCHANGE_RATES.get(to_curr, 1.0)
        
        if rate_from == 0:
            rate = Decimal(0)
        else:
            rate = Decimal(str(rate_to / rate_from))
        
        self._cache[cache_key] = rate
        return rate
    
    def convert(
        self,
        amount: Amount,
        from_currency: str,
        to_currency: str,
        round_digits: int = 2,
    ) -> Decimal:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            round_digits: Number of decimal places to round to
            
        Returns:
            Converted amount
        """
        if from_currency.upper() == to_currency.upper():
            return to_decimal(amount)
        
        rate = self.get_rate(from_currency, to_currency)
        decimal_amount = to_decimal(amount)
        converted = decimal_amount * rate
        
        return converted.quantize(
            Decimal('10') ** -round_digits,
            rounding=ROUND_HALF_UP,
        )
    
    def to_etb(self, amount: Amount, from_currency: str) -> Decimal:
        """Convert amount to Ethiopian Birr."""
        return self.convert(amount, from_currency, "ETB")
    
    def from_etb(self, amount: Amount, to_currency: str) -> Decimal:
        """Convert amount from Ethiopian Birr to another currency."""
        return self.convert(amount, "ETB", to_currency)
    
    def update_rate(self, currency: str, rate: float) -> None:
        """Update exchange rate for a currency (relative to ETB)."""
        self.EXCHANGE_RATES[currency.upper()] = rate
        self._cache.clear()
        logger.info(f"Updated exchange rate for {currency.upper()}: {rate}")


# Global currency converter instance
currency_converter = CurrencyConverter()


def round_amount(amount: Amount, decimals: int = 2) -> Decimal:
    """Round amount to specified decimal places."""
    decimal_amount = to_decimal(amount)
    return decimal_amount.quantize(
        Decimal('10') ** -decimals,
        rounding=ROUND_HALF_UP,
    )


def split_amount(amount: Amount, parts: int) -> list:
    """
    Split amount into equal parts.
    
    Args:
        amount: Amount to split
        parts: Number of parts
        
    Returns:
        List of split amounts
    """
    decimal_amount = to_decimal(amount)
    part_amount = (decimal_amount / Decimal(parts)).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP,
    )
    
    # Adjust for rounding differences
    total = part_amount * parts
    diff = decimal_amount - total
    
    result = [part_amount] * parts
    if diff != 0:
        result[0] += diff
    
    return result


def format_for_payment(amount: Amount) -> int:
    """
    Format amount for payment gateway (convert to smallest unit).
    
    Args:
        amount: Amount to format
        
    Returns:
        Amount in smallest currency unit (cents/santim)
    """
    decimal_amount = to_decimal(amount)
    return int(decimal_amount * 100)


def parse_from_payment(amount: int) -> Decimal:
    """
    Parse amount from payment gateway (convert from smallest unit).
    
    Args:
        amount: Amount in smallest currency unit
        
    Returns:
        Amount in main currency unit
    """
    return Decimal(amount) / 100


__all__ = [
    "to_decimal",
    "format_currency",
    "format_etb",
    "calculate_tax",
    "add_tax",
    "calculate_discount",
    "calculate_discount_percent",
    "calculate_subtotal",
    "CurrencyConverter",
    "currency_converter",
    "round_amount",
    "split_amount",
    "format_for_payment",
    "parse_from_payment",
]