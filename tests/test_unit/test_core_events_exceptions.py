"""Focused tests for core event and exception behavior."""

import pytest

from core.events import Event, EventBus, EventPriority, emit_event
from core.exceptions import (
    AuthenticationError,
    DuplicateRecordError,
    InsufficientStockError,
    NotFoundError,
    PhoneNumberError,
    RecordNotFoundError,
    ValidationError,
    WolloyewaException,
)


def test_exception_serializes_standard_error_payload():
    error = WolloyewaException("Broken", code="BROKEN", status_code=418, details={"field": "x"})

    assert error.to_dict() == {
        "error": "BROKEN",
        "message": "Broken",
        "status_code": 418,
        "details": {"field": "x"},
    }


@pytest.mark.parametrize(
    ("error", "code", "status_code"),
    [
        (RecordNotFoundError("Product", 7), "RECORD_NOT_FOUND", 404),
        (DuplicateRecordError("User", "email", "a@example.com"), "DUPLICATE_RECORD", 409),
        (ValidationError(errors={"name": ["required"]}), "VALIDATION_ERROR", 422),
        (PhoneNumberError("123"), "VALIDATION_ERROR", 422),
        (AuthenticationError(), "AUTHENTICATION_ERROR", 401),
        (NotFoundError("Order", 12), "NOT_FOUND", 404),
        (InsufficientStockError("Widget", 5, 2), "INSUFFICIENT_STOCK", 400),
    ],
)
def test_specialized_exceptions_expose_api_metadata(error, code, status_code):
    payload = error.to_dict()

    assert payload["error"] == code
    assert payload["status_code"] == status_code
    assert payload["message"]


@pytest.mark.asyncio
async def test_event_bus_runs_high_priority_handlers_first_and_wildcards():
    bus = EventBus()
    calls = []

    async def normal_handler(event):
        calls.append("normal")

    async def high_handler(event):
        calls.append("high")

    async def wildcard_handler(event):
        calls.append("wildcard")

    bus.subscribe("demo", normal_handler, EventPriority.NORMAL)
    bus.subscribe("demo", high_handler, EventPriority.HIGH)
    bus.subscribe("*", wildcard_handler, EventPriority.LOW)

    await bus.publish(Event("demo"))

    assert calls == ["wildcard", "high", "normal"]


@pytest.mark.asyncio
async def test_event_bus_unsubscribe_removes_handler():
    bus = EventBus()
    handler = lambda event: None
    bus.subscribe("demo", handler)

    bus.unsubscribe("demo", handler)

    assert bus._handlers["demo"] == []


@pytest.mark.asyncio
async def test_emit_event_queues_and_processes_event():
    bus = EventBus()
    received = []

    async def handler(event):
        received.append((event.name, event.data, event.source))

    bus.subscribe("demo", handler)
    original_bus = __import__("core.events", fromlist=["event_bus"]).event_bus
    import core.events as events_module

    events_module.event_bus = bus
    try:
        await bus.start()
        await emit_event("demo", {"value": 1}, source="test")
        await bus.wait_for_empty()
        assert received == [("demo", {"value": 1}, "test")]
    finally:
        await bus.stop()
        events_module.event_bus = original_bus
