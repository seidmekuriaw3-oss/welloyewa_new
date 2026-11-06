"""Shared checkout availability rules for web and Telegram customers."""

from dataclasses import dataclass

from apps.store_settings.models import StoreSettings
from core.config import settings
from core.exceptions import ValidationError

DEFAULT_PAYMENT_METHODS = ("chapa", "telebirr", "cbe", "cod")
PAYMENT_METHOD_KEYS = {
    "chapa": "chapa",
    "telebirr": "telebirr",
    "cbe": "cbe",
    "cbe_birr": "cbe",
    "cod": "cod",
    "cash_on_delivery": "cod",
}


@dataclass(frozen=True)
class CheckoutAvailability:
    store_open: bool
    maintenance_message: str | None
    enabled_payment_methods: frozenset[str]
    configured_payment_gateways: dict[str, bool]


def payment_gateway_status() -> dict[str, bool]:
    """Report whether all required deployment credentials are present."""
    return {
        "chapa": bool(settings.CHAPA_SECRET_KEY),
        "telebirr": bool(
            settings.TELEBIRR_APP_ID
            and settings.TELEBIRR_APP_KEY
            and settings.TELEBIRR_SHORT_CODE
        ),
        "cbe": bool(
            settings.CBE_BIRR_MERCHANT_ID
            and settings.CBE_BIRR_TERMINAL_ID
            and settings.CBE_BIRR_SECRET_KEY
        ),
    }


async def get_checkout_availability(db) -> CheckoutAvailability:
    """Resolve the current store settings and remove unconfigured gateways."""
    store_settings = await db.get(StoreSettings, 1)
    configured = payment_gateway_status()
    configured["cod"] = True
    allowed = (
        store_settings.enabled_payment_methods
        if store_settings is not None
        else DEFAULT_PAYMENT_METHODS
    )
    enabled = frozenset(
        key
        for value in allowed
        if (key := PAYMENT_METHOD_KEYS.get(value)) and configured.get(key, False)
    )
    return CheckoutAvailability(
        store_open=store_settings.store_open if store_settings is not None else True,
        maintenance_message=(
            store_settings.maintenance_message if store_settings is not None else None
        ),
        enabled_payment_methods=enabled,
        configured_payment_gateways=configured,
    )


async def validate_checkout_availability(db, payment_method: str) -> CheckoutAvailability:
    """Raise a domain validation error when a checkout option is unavailable."""
    availability = await get_checkout_availability(db)
    if not availability.store_open:
        raise ValidationError(
            availability.maintenance_message or "The store is currently closed."
        )
    payment_key = PAYMENT_METHOD_KEYS.get(payment_method)
    if payment_key not in availability.enabled_payment_methods:
        raise ValidationError("This payment method is currently unavailable.")
    return availability
