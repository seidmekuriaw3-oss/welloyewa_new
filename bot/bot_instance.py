#!/usr/bin/env python3
"""Telegram bot initialization and configuration."""

import json
from typing import Any

from telegram import Bot
from telegram.ext import (
    Application,
    ApplicationBuilder,
    BasePersistence,
    PersistenceInput,
)
from telegram.ext._utils.types import CDCData

from core.config import settings
from core.logger import logger


class RedisPersistence(BasePersistence):
    """Telegram persistence backed by Redis."""

    def __init__(self, url: str, key_prefix: str = "telegram_persistence", ttl: int = 86400):
        super().__init__(PersistenceInput())
        self._redis = None
        try:
            import redis

            self._redis = redis.from_url(url, encoding="utf-8", decode_responses=True)
        except Exception:
            self._redis = None
        self._key_prefix = key_prefix
        self._ttl = ttl
        self.bot_data: dict[str, Any] = self._load_data("bot_data")
        self.chat_data: dict[int, dict[str, Any]] = self._load_data("chat_data")
        self.user_data: dict[int, dict[str, Any]] = self._load_data("user_data")
        self.callback_data: dict[int, CDCData] = self._load_data("callback_data")
        self.conversations: dict[str, dict[str, Any]] = self._load_data("conversations")

    def _storage_key(self, name: str) -> str:
        return f"{self._key_prefix}:{name}"

    def _load_data(self, name: str) -> dict[Any, Any]:
        if self._redis is None:
            return {}
        try:
            raw = self._redis.get(self._storage_key(name))
            if not raw:
                return {}
            data = json.loads(raw)
            if isinstance(data, dict):
                return {
                    int(k) if isinstance(k, str) and k.isdigit() else k: v for k, v in data.items()
                }
            return {}
        except Exception:
            return {}

    def _save_data(self, name: str, data: Any) -> None:
        if self._redis is None:
            return
        try:
            self._redis.set(self._storage_key(name), json.dumps(data, default=str), ex=self._ttl)
        except Exception:
            pass

    async def get_user_data(self) -> dict[int, dict[str, Any]]:
        return self.user_data

    async def get_chat_data(self) -> dict[int, dict[str, Any]]:
        return self.chat_data

    async def get_bot_data(self) -> dict[str, Any]:
        return self.bot_data

    async def get_callback_data(self) -> CDCData:
        if not self.callback_data:
            return ([], {})
        return next(iter(self.callback_data.values()), ([], {}))

    async def get_conversations(self, name: str) -> dict[str, Any]:
        return self.conversations.setdefault(name, {})

    async def update_user_data(self, user_id: int, data: dict[str, Any]) -> None:
        self.user_data[int(user_id)] = data
        self._save_data("user_data", self.user_data)

    async def update_chat_data(self, chat_id: int, data: dict[str, Any]) -> None:
        self.chat_data[int(chat_id)] = data
        self._save_data("chat_data", self.chat_data)

    async def update_bot_data(self, data: dict[str, Any]) -> None:
        self.bot_data = data
        self._save_data("bot_data", self.bot_data)

    async def update_callback_data(self, data: CDCData) -> None:
        if not data:
            return
        self.callback_data[0] = data
        self._save_data("callback_data", self.callback_data)

    async def update_conversation(self, name: str, key: tuple[int | str, ...], new_state: object | None) -> None:
        convo_dict = self.conversations.setdefault(name, {})
        if new_state is None:
            convo_dict.pop(str(key), None)
        else:
            convo_dict[str(key)] = new_state
        self._save_data("conversations", self.conversations)

    async def drop_chat_data(self, chat_id: int) -> None:
        self.chat_data.pop(int(chat_id), None)
        self._save_data("chat_data", self.chat_data)

    async def drop_user_data(self, user_id: int) -> None:
        self.user_data.pop(int(user_id), None)
        self._save_data("user_data", self.user_data)

    async def refresh_bot_data(self, bot_data: dict[str, Any]) -> None:
        bot_data.update(self._load_data("bot_data"))
        self.bot_data = bot_data

    async def refresh_chat_data(self, chat_id: int, chat_data: dict[str, Any]) -> None:
        persisted_data = self._load_data("chat_data").get(chat_id, {})
        chat_data.update(persisted_data)
        self.chat_data[chat_id] = chat_data

    async def refresh_user_data(self, user_id: int, user_data: dict[str, Any]) -> None:
        persisted_data = self._load_data("user_data").get(user_id, {})
        user_data.update(persisted_data)
        self.user_data[user_id] = user_data

    async def flush(self) -> None:
        self._save_data("bot_data", self.bot_data)
        self._save_data("chat_data", self.chat_data)
        self._save_data("user_data", self.user_data)
        self._save_data("callback_data", self.callback_data)
        self._save_data("conversations", self.conversations)

    async def stop(self) -> None:
        await self.flush()


class JSONFilePersistence(BasePersistence):
    """Telegram persistence backed by a JSON file (fallback when Redis is unavailable)."""

    def __init__(self, filepath: str = "bot_data.json"):
        super().__init__(PersistenceInput())
        self.filepath = filepath
        self.bot_data: dict[str, Any] = self._load_section("bot_data")
        self.chat_data: dict[int, dict[str, Any]] = self._load_section("chat_data")
        self.user_data: dict[int, dict[str, Any]] = self._load_section("user_data")
        self.callback_data: dict[int, CDCData] = self._load_section("callback_data")
        self.conversations: dict[str, dict[str, Any]] = self._load_section("conversations")

    def _load_all(self) -> dict[str, Any]:
        try:
            with open(self.filepath, encoding="utf-8") as f:
                return json.load(f) or {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _load_section(self, name: str) -> dict[Any, Any]:
        try:
            data = self._load_all().get(name, {})
            if isinstance(data, dict):
                return {
                    int(k) if isinstance(k, str) and k.isdigit() else k: v for k, v in data.items()
                }
            return {}
        except Exception:
            return {}

    def _save_section(self, name: str, data: Any) -> None:
        try:
            existing = self._load_all()
            existing[name] = data
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(existing, f, default=str, ensure_ascii=False)
        except Exception:
            pass

    async def get_user_data(self) -> dict[int, dict[str, Any]]:
        return self.user_data

    async def get_chat_data(self) -> dict[int, dict[str, Any]]:
        return self.chat_data

    async def get_bot_data(self) -> dict[str, Any]:
        return self.bot_data

    async def get_callback_data(self) -> CDCData:
        if not self.callback_data:
            return ([], {})
        return next(iter(self.callback_data.values()), ([], {}))

    async def get_conversations(self, name: str) -> dict[str, Any]:
        return self.conversations.setdefault(name, {})

    async def update_user_data(self, user_id: int, data: dict[str, Any]) -> None:
        self.user_data[int(user_id)] = data
        self._save_section("user_data", self.user_data)

    async def update_chat_data(self, chat_id: int, data: dict[str, Any]) -> None:
        self.chat_data[int(chat_id)] = data
        self._save_section("chat_data", self.chat_data)

    async def update_bot_data(self, data: dict[str, Any]) -> None:
        self.bot_data = data
        self._save_section("bot_data", self.bot_data)

    async def update_callback_data(self, data: CDCData) -> None:
        if not data:
            return
        self.callback_data[0] = data
        self._save_section("callback_data", self.callback_data)

    async def update_conversation(self, name: str, key: tuple[int | str, ...], new_state: object | None) -> None:
        convo_dict = self.conversations.setdefault(name, {})
        if new_state is None:
            convo_dict.pop(str(key), None)
        else:
            convo_dict[str(key)] = new_state
        self._save_section("conversations", self.conversations)

    async def drop_chat_data(self, chat_id: int) -> None:
        self.chat_data.pop(int(chat_id), None)
        self._save_section("chat_data", self.chat_data)

    async def drop_user_data(self, user_id: int) -> None:
        self.user_data.pop(int(user_id), None)
        self._save_section("user_data", self.user_data)

    async def refresh_bot_data(self, bot_data: dict[str, Any]) -> None:
        bot_data.update(self._load_section("bot_data"))
        self.bot_data = bot_data

    async def refresh_chat_data(self, chat_id: int, chat_data: dict[str, Any]) -> None:
        persisted_data = self._load_section("chat_data").get(chat_id, {})
        chat_data.update(persisted_data)
        self.chat_data[chat_id] = chat_data

    async def refresh_user_data(self, user_id: int, user_data: dict[str, Any]) -> None:
        persisted_data = self._load_section("user_data").get(user_id, {})
        user_data.update(persisted_data)
        self.user_data[user_id] = user_data

    async def flush(self) -> None:
        self._save_section("bot_data", self.bot_data)
        self._save_section("chat_data", self.chat_data)
        self._save_section("user_data", self.user_data)
        self._save_section("callback_data", self.callback_data)
        self._save_section("conversations", self.conversations)

    async def stop(self) -> None:
        await self.flush()


# Global bot instances
_bot: Bot | None = None
_application: Application | None = None


async def init_bot() -> Application:
    """Initialize the Telegram bot application."""
    global _application, _bot

    if _application is not None:
        return _application

    logger.info("Initializing Telegram bot...")

    # Use Redis persistence if available, else fall back to JSON file
    try:
        import redis as _redis_sync

        _test_client = _redis_sync.from_url(str(settings.REDIS_URL), socket_connect_timeout=2)
        _test_client.ping()
        _test_client.close()
        persistence = RedisPersistence(
            url=str(settings.REDIS_URL),
            key_prefix="telegram_persistence",
            ttl=settings.REDIS_SESSION_TTL,
        )
        logger.info("Using Redis-based persistence for Telegram bot state")
    except Exception as exc:
        logger.warning(
            "Redis persistence unavailable, using JSON file (%s)", type(exc).__name__
        )
        persistence = JSONFilePersistence(filepath="bot_data.json")

    _application = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .persistence(persistence)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .get_updates_read_timeout(60)
        .build()
    )

    _bot = _application.bot

    # Register all handlers
    try:
        from bot.handlers import register_handlers

        await register_handlers(_application)
        logger.info("Telegram bot handlers registered successfully")
    except Exception as e:
        logger.warning(f"Could not register handlers in init_bot: {e}")

    logger.info(f"Bot initialized: {await _bot.get_me()}")
    return _application


async def shutdown_bot() -> None:
    """Shutdown the Telegram bot gracefully."""
    global _application
    if _application:
        logger.info("Shutting down bot...")
        await _application.shutdown()
        _application = None
        logger.info("Bot shutdown complete")


def get_bot() -> Bot:
    """Get the bot instance."""
    if _bot is None:
        raise RuntimeError("Bot not initialized. Call init_bot() first.")
    return _bot


def get_dispatcher():
    """Get the application (dispatcher) instance."""
    if _application is None:
        raise RuntimeError("Bot not initialized. Call init_bot() first.")
    return _application


bot = None
dispatcher = None

__all__ = ["bot", "dispatcher", "get_bot", "get_dispatcher", "init_bot", "shutdown_bot"]
