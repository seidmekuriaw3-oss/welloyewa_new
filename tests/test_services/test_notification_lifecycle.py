import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from core.events import ORDER_CREATED, VENDOR_REJECTED, Event
from infrastructure.notifications.lifecycle import (
    _enqueue_notification,
    _order_message,
    _vendor_message,
)


@pytest.mark.unit
def test_order_confirmation_is_localized_and_escapes_dynamic_content():
    order = SimpleNamespace(order_number="<ORD-1>", total=120.5)

    amharic, _ = _order_message(
        ORDER_CREATED,
        order,
        SimpleNamespace(language="am"),
        {},
    )
    english, _ = _order_message(
        ORDER_CREATED,
        order,
        SimpleNamespace(language="en"),
        {},
    )

    assert "ትዕዛዝዎ ተቀብሏል" in amharic
    assert "Order received" in english
    assert "&lt;ORD-1&gt;" in amharic
    assert "<ORD-1>" not in amharic
    assert "ETB 120.50" in english


@pytest.mark.unit
def test_vendor_rejection_includes_escaped_reason_in_both_languages():
    vendor = SimpleNamespace(business_name="<Shop>", rejection_reason=None)

    amharic, _ = _vendor_message(
        VENDOR_REJECTED,
        vendor,
        {"reason": "<missing document>"},
        "am",
    )
    english, _ = _vendor_message(
        VENDOR_REJECTED,
        vendor,
        {"reason": "<missing document>"},
        "en",
    )

    assert "&lt;Shop&gt;" in amharic
    assert "&lt;missing document&gt;" in amharic
    assert "was declined" in english
    assert "&lt;missing document&gt;" in english


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lifecycle_handler_queues_event_for_background_delivery():
    from infrastructure.workers.tasks import send_lifecycle_notification_task

    event = Event(name=ORDER_CREATED, data={"order_id": 25})
    with patch.object(send_lifecycle_notification_task, "delay") as queue:
        await _enqueue_notification(event)

    queue.assert_called_once_with(ORDER_CREATED, {"order_id": 25})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lifecycle_queue_failure_falls_back_without_raising():
    from infrastructure.workers.tasks import send_lifecycle_notification_task

    event = Event(name=ORDER_CREATED, data={"order_id": 26})
    with (
        patch.object(send_lifecycle_notification_task, "delay", side_effect=RuntimeError),
        patch(
            "infrastructure.notifications.lifecycle.dispatch_lifecycle_notification",
            new_callable=AsyncMock,
        ) as dispatch,
    ):
        await _enqueue_notification(event)
        await asyncio.sleep(0.3)

    dispatch.assert_awaited_once_with(ORDER_CREATED, {"order_id": 26})
