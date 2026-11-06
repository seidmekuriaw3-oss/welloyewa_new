from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError


def build_coupon(**overrides):
    from apps.marketing.models import Coupon

    values = {
        "code": "SAVE10",
        "name": "Save ten percent",
        "discount_type": "percentage",
        "discount_value": Decimal("10"),
        "valid_from": datetime.utcnow() - timedelta(days=1),
        "valid_to": datetime.utcnow() + timedelta(days=1),
        "is_active": True,
        "used_count": 0,
    }
    values.update(overrides)
    return Coupon(**values)


def test_coupon_percentage_discount_caps_and_rounds():
    coupon = build_coupon(max_discount_amount=Decimal("25.00"))

    assert coupon.calculate_discount(Decimal("500.00")) == Decimal("25.00")
    assert coupon.calculate_discount(Decimal("10.05")) == Decimal("1.01")


def test_coupon_fixed_discount_never_exceeds_eligible_purchase_amount():
    coupon = build_coupon(
        discount_type="fixed_amount",
        discount_value=Decimal("75.00"),
    )

    assert coupon.calculate_discount(Decimal("20.00")) == Decimal("20.00")


@pytest.mark.asyncio
async def test_coupon_validation_calculates_only_scoped_category_items():
    from apps.marketing.coupons import CouponManager

    coupon = build_coupon(
        applicable_categories=["4"],
        min_purchase_amount=Decimal("100.00"),
    )
    manager = CouponManager(AsyncMock())
    manager.coupon_repo = SimpleNamespace(get_by_code=AsyncMock(return_value=coupon))
    manager.usage_repo = SimpleNamespace(get_usage_count=AsyncMock(return_value=0))

    result = await manager.validate_coupon(
        "save10",
        user_id=7,
        order_amount=Decimal("150.00"),
        eligible_items=[
            {"product_id": 1, "category_id": 4, "amount": Decimal("50.00")},
            {"product_id": 2, "category_id": 9, "amount": Decimal("100.00")},
        ],
    )

    assert result["is_valid"] is True
    assert result["discount_amount"] == Decimal("5.00")


@pytest.mark.asyncio
async def test_coupon_validation_rejects_nonmatching_scope_minimum_and_usage_limit():
    from apps.marketing.coupons import CouponManager

    coupon = build_coupon(
        applicable_products=[55],
        min_purchase_amount=Decimal("100.00"),
        usage_limit=1,
        used_count=1,
    )
    manager = CouponManager(AsyncMock())
    manager.coupon_repo = SimpleNamespace(get_by_code=AsyncMock(return_value=coupon))
    manager.usage_repo = SimpleNamespace(get_usage_count=AsyncMock(return_value=0))

    exhausted = await manager.validate_coupon(
        "SAVE10",
        user_id=7,
        order_amount=Decimal("150.00"),
        eligible_items=[{"product_id": 55, "category_id": 4, "amount": Decimal("150.00")}],
    )
    assert exhausted["is_valid"] is False
    assert "usage limit" in exhausted["message"]

    coupon.used_count = 0
    unmatched = await manager.validate_coupon(
        "SAVE10",
        user_id=7,
        order_amount=Decimal("150.00"),
        eligible_items=[{"product_id": 8, "category_id": 4, "amount": Decimal("150.00")}],
    )
    assert unmatched["is_valid"] is False
    assert "does not apply" in unmatched["message"]

    below_minimum = await manager.validate_coupon(
        "SAVE10",
        user_id=7,
        order_amount=Decimal("99.00"),
        eligible_items=[{"product_id": 55, "category_id": 4, "amount": Decimal("99.00")}],
    )
    assert below_minimum["is_valid"] is False
    assert "Minimum purchase" in below_minimum["message"]


def test_discount_payload_validates_scope_limits_and_timezone():
    from bot.web_app.router import WebDiscountCreate

    start = datetime.now().replace(microsecond=0)
    discount = WebDiscountCreate(
        code="  april10 ",
        name=" April discount ",
        discount_type="percentage",
        discount_value="10",
        valid_from=start,
        valid_to=start + timedelta(days=1),
        scope="category",
        scope_id=4,
    )
    assert discount.code == "APRIL10"
    assert discount.name == "April discount"
    assert discount.valid_from.tzinfo is None

    with pytest.raises(ValidationError):
        WebDiscountCreate(
            code="TOOMUCH",
            name="Invalid percent",
            discount_type="percentage",
            discount_value="101",
            valid_from=start,
            valid_to=start + timedelta(days=1),
        )
    with pytest.raises(ValidationError):
        WebDiscountCreate(
            code="MISSING",
            name="Missing scope ID",
            discount_type="fixed_amount",
            discount_value="5",
            valid_from=start,
            valid_to=start + timedelta(days=1),
            scope="product",
        )


def test_admin_settings_api_response_never_contains_environment_secrets(monkeypatch):
    import bot.web_app.router as router
    from core.config import settings

    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "secret-telegram-token")
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_URL", "https://example.test/secret-path")
    monkeypatch.setattr(settings, "CHAPA_SECRET_KEY", "secret-payment-key")
    monkeypatch.setattr(settings, "TELEBIRR_APP_ID", "telebirr-id")
    monkeypatch.setattr(settings, "TELEBIRR_APP_KEY", "telebirr-key")
    monkeypatch.setattr(settings, "TELEBIRR_SHORT_CODE", "telebirr-short")
    monkeypatch.setattr(settings, "CBE_BIRR_MERCHANT_ID", "cbe-merchant")
    monkeypatch.setattr(settings, "CBE_BIRR_TERMINAL_ID", "cbe-terminal")
    monkeypatch.setattr(settings, "CBE_BIRR_SECRET_KEY", "cbe-secret")
    configured = SimpleNamespace(
        store_open=True,
        currency_code="ETB",
        enabled_payment_methods=["cod"],
        notification_settings={"customer_orders": True},
        maintenance_message=None,
    )

    response = router._store_settings_payload(configured)
    serialized = str(response)

    assert response["environment_status"]["telegram_bot"] is True
    assert response["environment_status"]["telegram_webhook"] is True
    assert response["environment_status"]["payment_gateways"]["chapa"] is True
    assert response["environment_status"]["payment_gateways"]["telebirr"] is True
    assert response["environment_status"]["payment_gateways"]["cbe"] is True
    assert "secret-telegram-token" not in serialized
    assert "secret-path" not in serialized
    assert "secret-payment-key" not in serialized


@pytest.mark.asyncio
async def test_admin_settings_update_merges_notification_preferences():
    import bot.web_app.router as router

    store_settings = SimpleNamespace(
        store_open=True,
        currency_code="ETB",
        enabled_payment_methods=["cod"],
        notification_settings={
            "customer_orders": True,
            "vendor_updates": True,
            "admin_alerts": True,
            "support_updates": True,
        },
        maintenance_message=None,
    )
    db = Mock()
    db.get = AsyncMock(return_value=store_settings)
    db.flush = AsyncMock()

    result = await router.web_admin_update_settings(
        router.WebStoreSettingsUpdate(
            store_open=False,
            notification_settings={"customer_orders": False},
        ),
        current_user={"id": 1, "role": "admin"},
        db=db,
    )

    assert store_settings.store_open is False
    assert store_settings.notification_settings == {
        "customer_orders": False,
        "vendor_updates": True,
        "admin_alerts": True,
        "support_updates": True,
    }
    assert isinstance(result["environment_status"]["telegram_bot"], bool)
    db.flush.assert_awaited_once()


def test_store_settings_update_rejects_secret_fields():
    from bot.web_app.router import WebStoreSettingsUpdate

    with pytest.raises(ValidationError):
        WebStoreSettingsUpdate(telegram_bot_token="must-not-be-editable")

    with pytest.raises(ValidationError):
        WebStoreSettingsUpdate(notification_settings={"unknown": False})


@pytest.mark.asyncio
async def test_checkout_availability_requires_complete_gateway_configuration(monkeypatch):
    from apps.store_settings.checkout import get_checkout_availability
    from core.config import settings

    monkeypatch.setattr(settings, "CHAPA_SECRET_KEY", "chapa-secret")
    monkeypatch.setattr(settings, "TELEBIRR_APP_ID", "telebirr-id")
    monkeypatch.setattr(settings, "TELEBIRR_APP_KEY", "telebirr-key")
    monkeypatch.setattr(settings, "TELEBIRR_SHORT_CODE", None)
    monkeypatch.setattr(settings, "CBE_BIRR_MERCHANT_ID", None)
    monkeypatch.setattr(settings, "CBE_BIRR_TERMINAL_ID", None)
    monkeypatch.setattr(settings, "CBE_BIRR_SECRET_KEY", "cbe-secret")
    db = Mock()
    db.get = AsyncMock(return_value=None)

    options = await get_checkout_availability(db)

    assert options.store_open is True
    assert options.enabled_payment_methods == frozenset({"chapa", "cod"})


@pytest.mark.asyncio
async def test_checkout_availability_rejects_closed_store_and_disabled_gateway():
    from apps.store_settings.checkout import validate_checkout_availability
    from core.exceptions import ValidationError as DomainValidationError

    db = Mock()
    db.get = AsyncMock(
        side_effect=[
            SimpleNamespace(
                store_open=False,
                maintenance_message="Back shortly",
                enabled_payment_methods=["cod"],
            ),
            SimpleNamespace(
                store_open=True,
                maintenance_message=None,
                enabled_payment_methods=["cod"],
            ),
        ]
    )

    with pytest.raises(DomainValidationError, match="Back shortly"):
        await validate_checkout_availability(db, "cash_on_delivery")
    with pytest.raises(DomainValidationError, match="payment method"):
        await validate_checkout_availability(db, "chapa")
