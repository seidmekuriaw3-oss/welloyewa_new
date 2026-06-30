# ============================
# WOLLOYEWA STORE BOT - LIVE CURRENCY CONVERTER
# ============================
"""Live currency conversion using external exchange rate APIs."""

import json
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import httpx

from core.config import settings
from core.logger import logger
from infrastructure.redis.client import get_redis_client


class LiveCurrencyConverter:
    """
    Live currency converter using external API.
    
    Features:
    - Real-time exchange rates
    - Rate caching to reduce API calls
    - Support for multiple currencies
    - Automatic fallback to cached rates
    """
    
    def __init__(self):
        self._cache_ttl = 3600  # 1 hour cache
        self._redis = None
        self._base_currency = "ETB"
        
        # Supported currencies
        self.supported_currencies = {
            "ETB": "Ethiopian Birr",
            "USD": "US Dollar",
            "EUR": "Euro",
            "GBP": "British Pound",
            "CNY": "Chinese Yuan",
            "AED": "UAE Dirham",
            "SAR": "Saudi Riyal",
            "KES": "Kenyan Shilling",
            "JPY": "Japanese Yen",
            "CAD": "Canadian Dollar",
            "AUD": "Australian Dollar",
            "CHF": "Swiss Franc",
        }
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Optional[Decimal]:
        """
        Get exchange rate between two currencies.
        
        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            
        Returns:
            Exchange rate as Decimal
        """
        if from_currency.upper() == to_currency.upper():
            return Decimal(1)
        
        # Try cache first
        cache_key = f"exchange_rate:{from_currency}:{to_currency}"
        redis = await self._get_redis()
        cached = await redis.get(cache_key)
        
        if cached:
            return Decimal(cached)
        
        # Fetch from API
        rate = await self._fetch_exchange_rate(from_currency, to_currency)
        
        if rate:
            # Cache the rate
            await redis.set(cache_key, str(rate), ex=self._cache_ttl)
            return rate
        
        # Fallback to base rates via ETB
        return await self._get_rate_via_etb(from_currency, to_currency)
    
    async def _fetch_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Optional[Decimal]:
        """
        Fetch exchange rate from external API.
        
        Priority APIs:
        1. ExchangeRate-API (primary)
        2. Frankfurter (fallback)
        """
        # Try ExchangeRate-API
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://api.exchangerate-api.com/v4/latest/{from_currency}",
                )
                
                if response.status_code == 200:
                    data = response.json()
                    rate = data.get("rates", {}).get(to_currency)
                    if rate:
                        return Decimal(str(rate))
        except Exception as e:
            logger.warning(f"ExchangeRate-API failed: {e}")
        
        # Try Frankfurter as fallback
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}",
                )
                
                if response.status_code == 200:
                    data = response.json()
                    rate = data.get("rates", {}).get(to_currency)
                    if rate:
                        return Decimal(str(rate))
        except Exception as e:
            logger.warning(f"Frankfurter API failed: {e}")
        
        return None
    
    async def _get_rate_via_etb(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Optional[Decimal]:
        """
        Get exchange rate by converting through ETB.
        """
        from_to_etb = await self._fetch_exchange_rate(from_currency, "ETB")
        etb_to_to = await self._fetch_exchange_rate("ETB", to_currency)
        
        if from_to_etb and etb_to_to:
            return from_to_etb * etb_to_to
        
        return None
    
    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Converted amount
        """
        if from_currency.upper() == to_currency.upper():
            return amount
        
        rate = await self.get_exchange_rate(from_currency, to_currency)
        
        if not rate:
            logger.warning(f"No exchange rate found for {from_currency} to {to_currency}")
            return amount
        
        converted = amount * rate
        return converted.quantize(Decimal("0.01"))
    
    async def to_etb(self, amount: Decimal, from_currency: str) -> Decimal:
        """Convert amount to Ethiopian Birr."""
        return await self.convert(amount, from_currency, "ETB")
    
    async def from_etb(self, amount: Decimal, to_currency: str) -> Decimal:
        """Convert amount from Ethiopian Birr to another currency."""
        return await self.convert(amount, "ETB", to_currency)
    
    async def get_all_rates(self, base_currency: str = "ETB") -> Dict[str, Decimal]:
        """
        Get all exchange rates for a base currency.
        
        Args:
            base_currency: Base currency code
            
        Returns:
            Dictionary of currency -> rate
        """
        rates = {}
        
        for currency in self.supported_currencies:
            if currency != base_currency:
                rate = await self.get_exchange_rate(base_currency, currency)
                if rate:
                    rates[currency] = rate
        
        return rates


# Global converter instance
_currency_converter = LiveCurrencyConverter()


async def convert_currency(
    amount: Decimal,
    from_currency: str,
    to_currency: str,
) -> Decimal:
    """Convert amount between currencies."""
    return await _currency_converter.convert(amount, from_currency, to_currency)


async def get_exchange_rate(
    from_currency: str,
    to_currency: str,
) -> Optional[Decimal]:
    """Get exchange rate between two currencies."""
    return await _currency_converter.get_exchange_rate(from_currency, to_currency)


CurrencyConverter = LiveCurrencyConverter

__all__ = [
    "LiveCurrencyConverter",
    "CurrencyConverter",
    "convert_currency",
    "get_exchange_rate",
]