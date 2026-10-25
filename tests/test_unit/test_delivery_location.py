"""Tests for shared delivery-location handling in Telegram and the web checkout."""

from pathlib import Path

import pytest
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from bot.web_app.router import CheckoutRequest
from core.security.middleware import SecurityHeadersMiddleware
from core.utils.location import format_delivery_address, google_maps_url


def test_delivery_address_uses_google_maps_link_for_coordinates():
    maps_url = google_maps_url(9.03, 38.74)

    assert maps_url == "https://maps.google.com/?q=9.03000,38.74000"
    assert format_delivery_address("Shared location", 9.03, 38.74) == (
        "Shared location | Google Maps: https://maps.google.com/?q=9.03000,38.74000"
    )


def test_checkout_accepts_optional_coordinate_pair():
    checkout = CheckoutRequest(
        items=[],
        full_name="Test User",
        phone="0912345678",
        city="Addis Ababa",
        address="Shared location",
        payment_method="cod",
        latitude=9.03,
        longitude=38.74,
    )

    assert checkout.latitude == 9.03
    assert checkout.longitude == 38.74


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(9.03, None), (None, 38.74), (91, 38.74), (9.03, 181)],
)
def test_checkout_rejects_incomplete_or_out_of_range_coordinates(latitude, longitude):
    with pytest.raises(ValidationError):
        CheckoutRequest(
            items=[],
            full_name="Test User",
            phone="0912345678",
            city="Addis Ababa",
            address="Shared location",
            payment_method="cod",
            latitude=latitude,
            longitude=longitude,
        )


def test_checkout_page_offers_location_capture_and_map_link():
    template = (
        Path(__file__).parents[2]
        / "bot"
        / "web_app"
        / "templates"
        / "checkout.html"
    ).read_text(encoding="utf-8")

    assert "navigator.geolocation.getCurrentPosition" in template
    assert "Google Maps" in template
    assert "deliveryCoordinates" in template


@pytest.mark.asyncio
async def test_security_policy_allows_geolocation_for_same_origin(monkeypatch):
    import core.security.middleware as middleware

    monkeypatch.setattr(middleware, "_IS_DEVELOPMENT", False)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/app/checkout",
            "headers": [],
            "query_string": b"",
        }
    )

    async def call_next(_request):
        return Response()

    response = await SecurityHeadersMiddleware(app=lambda: None).dispatch(
        request, call_next
    )

    assert response.headers["Permissions-Policy"] == (
        "geolocation=(self), microphone=(), camera=()"
    )
