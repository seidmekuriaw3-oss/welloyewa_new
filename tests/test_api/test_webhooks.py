from unittest.mock import AsyncMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException
from httpx import AsyncClient
from starlette.requests import Request


@pytest.mark.api
@pytest.mark.parametrize("secret_header", [None, "wrong-token"])
async def test_telegram_webhook_rejects_invalid_secret(
    client: AsyncClient, monkeypatch, secret_header: str | None
):
    from core.config import settings

    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "expected-token")
    headers = (
        {"X-Telegram-Bot-Api-Secret-Token": secret_header} if secret_header else {}
    )

    with patch("bot.webhooks.handle_telegram_update", new_callable=AsyncMock) as handler:
        response = await client.post(
            "/api/v1/webhook/telegram",
            json={"update_id": 1},
            headers=headers,
        )

    assert response.status_code == 403
    handler.assert_not_awaited()


@pytest.mark.api
async def test_telegram_webhook_forwards_update_with_valid_secret(
    client: AsyncClient, monkeypatch
):
    from core.config import settings

    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "expected-token")
    payload = {"update_id": 1}

    with patch("bot.webhooks.handle_telegram_update", new_callable=AsyncMock) as handler:
        response = await client.post(
            "/api/v1/webhook/telegram",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "expected-token"},
        )

    assert response.status_code == 200
    handler.assert_awaited_once_with(payload)


@pytest.mark.api
async def test_telegram_webhook_is_disabled_without_a_configured_secret(
    client: AsyncClient, monkeypatch
):
    from core.config import settings

    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")

    with patch("bot.webhooks.handle_telegram_update", new_callable=AsyncMock) as handler:
        response = await client.post("/api/v1/webhook/telegram", json={"update_id": 1})

    assert response.status_code == 503
    handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_direct_webhook_call_preserves_forbidden_status(monkeypatch):
    from bot.webhooks import telegram_webhook
    from core.config import settings

    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "expected-token")
    body = b'{"update_id": 1}'

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/webhook/telegram",
            "raw_path": b"/api/v1/webhook/telegram",
            "query_string": b"",
            "headers": [
                (b"content-type", b"application/json"),
                (b"x-telegram-bot-api-secret-token", b"wrong-token"),
            ],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        },
        receive,
    )

    with pytest.raises(HTTPException) as exc:
        await telegram_webhook(request, BackgroundTasks())

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_webhook_requires_secret_even_when_development_bypass_is_enabled(monkeypatch):
    from core.config import settings
    from core.dependencies import verify_webhook_signature

    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "DEV_SKIP_MIDDLEWARES", True)

    with pytest.raises(HTTPException) as exc:
        await verify_webhook_signature(Request({"type": "http"}), None)

    assert exc.value.status_code == 503
