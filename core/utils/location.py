"""Helpers for storing and sharing delivery locations."""


def google_maps_url(latitude: float, longitude: float) -> str:
    """Return a Google Maps URL for a coordinate pair."""
    return f"https://maps.google.com/?q={latitude:.5f},{longitude:.5f}"


def format_delivery_address(
    address: str | None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> str:
    """Append a consistent Google Maps link when coordinates are available."""
    address_text = (address or "").strip()
    if latitude is None or longitude is None:
        return address_text
    address_text = address_text.split(" | Google Maps:", maxsplit=1)[0]

    label = address_text or "Shared location"
    return f"{label} | Google Maps: {google_maps_url(latitude, longitude)}"
