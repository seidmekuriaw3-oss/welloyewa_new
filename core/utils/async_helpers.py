"""Helpers for integrating async production APIs with lightweight test doubles."""

import inspect
from typing import Any


async def maybe_await(value: Any) -> Any:
    """Await awaitables and return synchronous values unchanged."""
    if inspect.isawaitable(value):
        return await value
    return value
