"""Helpers for sending locally stored product images through Telegram."""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from telegram import InputFile

_UPLOADS_DIR = Path(__file__).resolve().parent / "web_app" / "static" / "uploads"
_UPLOAD_URL_PREFIX = "/app/static/uploads/"


@contextmanager
def telegram_photo_source(image_ref: str) -> Iterator[str | InputFile]:
    """Yield a Telegram-compatible source for a product image reference."""
    if not image_ref.startswith(_UPLOAD_URL_PREFIX):
        yield image_ref
        return

    filename = image_ref.removeprefix(_UPLOAD_URL_PREFIX)
    if not filename or Path(filename).name != filename:
        raise ValueError(f"Invalid local product image reference: {image_ref}")

    image_path = _UPLOADS_DIR / filename
    with image_path.open("rb") as image_file:
        yield InputFile(image_file, filename=filename)
