"""Telegram Mini App authentication data verification."""

import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Any


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict[str, Any] | None:
    """Verify signed Telegram Mini App data and reject missing or stale timestamps."""
    if not init_data or not bot_token or len(init_data) > 8192:
        return None

    try:
        pairs = urllib.parse.parse_qsl(init_data, strict_parsing=True, max_num_fields=100)
        params: dict[str, str] = {}
        for key, value in pairs:
            if key in params:
                return None
            params[key] = value
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
    if (
        not isinstance(user, dict)
        or isinstance(user.get("id"), bool)
        or not isinstance(user.get("id"), int)
        or user["id"] <= 0
    ):
        return None
    return user
