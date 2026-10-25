from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from apps.analytics.services import ProductAnalyticsService
from apps.orders.schemas import OrderCreate
from apps.orders.services import OrderTrackingService
from core.exceptions import NotFoundError


def test_order_create_ignores_client_supplied_discount():
    order = OrderCreate.model_validate(
        {
            "items": [{"product_id": 1, "quantity": 1}],
            "payment_method": "chapa",
            "shipping_address": "Test address",
            "shipping_city": "Addis Ababa",
            "shipping_phone": "0912345678",
            "discount": 100000,
            "shipping_fee": 0,
        }
    )

    assert "discount" not in order.model_dump()
    assert "shipping_fee" not in order.model_dump()


@pytest.mark.asyncio
async def test_order_tracking_requires_matching_contact():
    service = OrderTrackingService(None)
    order = SimpleNamespace(user_id=4, shipping_phone="+251 91-234-5678")
    service.order_repo.get_by_order_number = AsyncMock(return_value=order)
    service.user_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(email="buyer@example.com")
    )

    assert await service.track_order("ORD-1", "attacker@example.com") is None
    assert await service.track_order("ORD-1", "+251 91-234-5678") is order


@pytest.mark.asyncio
async def test_vendor_cannot_read_other_product_performance():
    service = ProductAnalyticsService(None)
    service.product_repo.get_by_id = AsyncMock(return_value=SimpleNamespace(vendor_id=8))
    service.sales_repo.get_product_sales = AsyncMock()

    with pytest.raises(NotFoundError):
        await service.get_product_performance(product_id=3, vendor_id=9)

    service.sales_repo.get_product_sales.assert_not_awaited()
