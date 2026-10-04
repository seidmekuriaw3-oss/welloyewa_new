"""Telegram Mini App authentication data verification."""

import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Any


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict[str, Any] | None:
    """Verify signed Telegram Mini App data and reject missing or stale timestamps."""
    if not init_data or not bot_token:
        return None

    try:
        params = dict(urllib.parse.parse_qsl(init_data, strict_parsing=True))
        received_hash = params.pop("hash", None)
        auth_date = int(params["auth_date"])
    except (KeyError, TypeError, ValueError):
        return None
    except Exception:
        return None

    if not received_hash or abs(time.time() - auth_date) > 3600:
        return None

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        return None

    try:
        user = json.loads(params["user"])
    except (KeyError, TypeError, ValueError):
        return None
    return user if isinstance(user, dict) else None
