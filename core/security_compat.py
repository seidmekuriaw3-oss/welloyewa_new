import hashlib
import hmac
from typing import Any


def verify_telegram_webhook(data: dict[str, Any], token: str) -> bool:
    received_token = data.get("secret_token")
    if not received_token:
        return False
    return hmac.compare_digest(received_token, token)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(password), hashed)


def create_access_token(data: dict) -> str:
    import base64
    import json

    token_data = json.dumps(data)
    return base64.b64encode(token_data.encode()).decode()


def verify_token(token: str) -> dict:
    import base64
    import json

    try:
        data = json.loads(base64.b64decode(token.encode()).decode())
        return data
    except Exception:
        return {}
