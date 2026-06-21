# ============================
# WOLLOYEWA STORE BOT - BOT PERSISTENCE TESTS
# ============================
"""Unit tests for Telegram bot persistence fallback behavior."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from bot import bot_instance


@pytest.mark.unit
class TestBotPersistence:
    """Tests for Telegram bot persistence initialization."""

    @pytest.mark.asyncio
    async def test_init_bot_falls_back_to_jsonfilepersistence_when_redis_is_unavailable(self):
        """When Redis persistence fails, the bot should fall back to JSON file persistence."""
        mock_app = Mock()
        mock_bot = AsyncMock()
        mock_bot.get_me.return_value = {"id": 123}
        mock_app.bot = mock_bot

        builder = Mock()
        builder.token.return_value = builder
        builder.persistence.return_value = builder
        builder.build.return_value = mock_app

        bot_instance._application = None
        bot_instance._bot = None

        with patch("bot.bot_instance.ApplicationBuilder", return_value=builder):
            with patch("bot.bot_instance.RedisPersistence", side_effect=RuntimeError("redis unavailable")):
                with patch("bot.bot_instance.JSONFilePersistence") as json_persistence_cls:
                    json_persistence_cls.return_value = "json_persistence"

                    application = await bot_instance.init_bot()

                    assert application is mock_app
                    json_persistence_cls.assert_called_once_with(filepath="bot_data.json")
                    builder.persistence.assert_called_once_with("json_persistence")
                    mock_bot.get_me.assert_awaited_once()
