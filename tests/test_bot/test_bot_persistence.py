# ============================
# WOLLOYEWA STORE BOT - BOT PERSISTENCE TESTS
# ============================
"""Unit tests for Telegram bot persistence fallback behavior."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from bot import bot_instance


@pytest.mark.parametrize("persistence_type", ["redis", "json"])
@pytest.mark.asyncio
async def test_persistence_refresh_methods_match_ptb_and_update_data_in_place(
    persistence_type, tmp_path, monkeypatch
):
    if persistence_type == "redis":
        persistence = bot_instance.RedisPersistence("redis://localhost:6379/0")
        load = "_load_data"
    else:
        persistence = bot_instance.JSONFilePersistence(str(tmp_path / "bot.json"))
        load = "_load_section"

    persisted = {
        "bot_data": {"shared": "persisted"},
        "chat_data": {42: {"chat_setting": "persisted"}},
        "user_data": {42: {"user_setting": "persisted"}},
    }
    monkeypatch.setattr(persistence, load, lambda name: persisted[name])

    bot_data = {"local": "kept"}
    chat_data = {"local": "kept"}
    user_data = {"local": "kept"}

    await persistence.refresh_bot_data(bot_data)
    await persistence.refresh_chat_data(42, chat_data)
    await persistence.refresh_user_data(42, user_data)

    assert bot_data == {"local": "kept", "shared": "persisted"}
    assert chat_data == {"local": "kept", "chat_setting": "persisted"}
    assert user_data == {"local": "kept", "user_setting": "persisted"}
    assert persistence.bot_data is bot_data
    assert persistence.chat_data[42] is chat_data
    assert persistence.user_data[42] is user_data


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
        builder.read_timeout.return_value = builder
        builder.write_timeout.return_value = builder
        builder.connect_timeout.return_value = builder
        builder.pool_timeout.return_value = builder
        builder.get_updates_read_timeout.return_value = builder
        builder.build.return_value = mock_app

        bot_instance._application = None
        bot_instance._bot = None

        with patch("bot.bot_instance.ApplicationBuilder", return_value=builder):
            with patch(
                "bot.bot_instance.RedisPersistence", side_effect=RuntimeError("redis unavailable")
            ):
                with patch("bot.bot_instance.JSONFilePersistence") as json_persistence_cls:
                    json_persistence_cls.return_value = "json_persistence"

                    application = await bot_instance.init_bot()

                    assert application is mock_app
                    json_persistence_cls.assert_called_once_with(filepath="bot_data.json")
                    builder.persistence.assert_called_once_with("json_persistence")
                    mock_bot.get_me.assert_awaited_once()
