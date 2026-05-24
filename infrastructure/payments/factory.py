# ============================
# WOLLOYEWA STORE BOT - PAYMENT FACTORY
# ============================
"""Factory pattern for creating payment providers."""

from typing import Optional

from infrastructure.payments.base import PaymentProvider, PaymentMethod, PaymentError
from infrastructure.payments.chapa import ChapaProvider
from infrastructure.payments.telebirr import TelebirrProvider
from infrastructure.payments.cbe_birr import CBEBirrProvider
from core.config import settings
from core.logger import logger


class PaymentFactory:
    """
    Factory for creating payment provider instances.
    
    Usage:
        provider = PaymentFactory.get_provider(PaymentMethod.CHAPA)
        response = await provider.initialize_payment(request)
    """
    
    _providers = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class):
        """Register a payment provider."""
        cls._providers[name] = provider_class
        logger.debug(f"Registered payment provider: {name}")
    
    @classmethod
    def get_provider(cls, method: PaymentMethod) -> PaymentProvider:
        """
        Get payment provider instance.
        
        Args:
            method: Payment method enum
            
        Returns:
            Payment provider instance
            
        Raises:
            PaymentError: If provider not configured or available
        """
        provider_name = method.value
        
        if provider_name not in cls._providers:
            raise PaymentError(f"Payment provider '{provider_name}' not registered")
        
        provider_class = cls._providers[provider_name]
        return provider_class()
    
    @classmethod
    def get_provider_by_name(cls, name: str) -> PaymentProvider:
        """Get provider by string name."""
        try:
            method = PaymentMethod(name)
            return cls.get_provider(method)
        except ValueError:
            raise PaymentError(f"Unknown payment method: {name}")


# Register default providers
PaymentFactory.register_provider(PaymentMethod.CHAPA.value, ChapaProvider)
PaymentFactory.register_provider(PaymentMethod.TELEBIRR.value, TelebirrProvider)
PaymentFactory.register_provider(PaymentMethod.CBE_BIRR.value, CBEBirrProvider)


async def get_payment_provider(method: str) -> PaymentProvider:
    """
    Convenience function to get payment provider.
    
    Args:
        method: Payment method name
        
    Returns:
        Payment provider instance
    """
    return PaymentFactory.get_provider_by_name(method)


async def process_payment(
    method: str,
    amount: Decimal,
    order_id: int,
    order_number: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    **kwargs,
) -> PaymentResponse:
    """
    Process a payment using the specified method.
    
    Args:
        method: Payment method (chapa, telebirr, cbe_birr)
        amount: Payment amount
        order_id: Order ID
        order_number: Order number
        customer_name: Customer full name
        customer_email: Customer email
        customer_phone: Customer phone
        **kwargs: Additional parameters
        
    Returns:
        Payment response
    """
    from infrastructure.payments.base import PaymentRequest
    
    provider = await get_payment_provider(method)
    
    request = PaymentRequest(
        amount=amount,
        currency="ETB",
        order_id=order_id,
        order_number=order_number,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        description=f"Order {order_number}",
        callback_url=kwargs.get("callback_url"),
        webhook_url=kwargs.get("webhook_url"),
        metadata=kwargs.get("metadata", {}),
    )
    
    return await provider.initialize_payment(request)


__all__ = [
    "PaymentFactory",
    "get_payment_provider",
    "process_payment",
]