from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


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
