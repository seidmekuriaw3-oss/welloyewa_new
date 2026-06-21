# # ============================
# WOLLOYEWA STORE BOT - TELEGRAM BOT INSTANCE
# # ============================
"""Telegram bot initialization and configuration."""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from telegram import Bot, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    BasePersistence,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from telegram.ext._utils.types import CDCData

from core.config import settings
from core.logger import logger


class RedisPersistence(BasePersistence):
    """Telegram persistence implementation backed by Redis."""

    def __init__(self, url: str, key_prefix: str = "telegram_persistence", ttl: int = 86400):
        # ለአዲሱ ላይብረሪ የግዴታ የሆኑትን መቼቶች እዚህ ንዑስ ክላሱ ላይ እንገልጻለን (v20+ super().__init__ ላይ አይቀበልም)
        super().__init__()
        self.store_user_data = True
        self.store_chat_data = True
        self.store_bot_data = True
        self.store_callback_data = True
        
        # 'dict' object can't be awaited ዋርኒንግን በስር ነቀል ዘዴ ለመከላከል
        self.is_async = False

        import redis

        self._redis = redis.from_url(url, encoding="utf-8", decode_responses=True)
        self._key_prefix = key_prefix
        self._ttl = ttl
        self.bot_data: Dict[str, Any] = self._load_data("bot_data")
        self.chat_data: Dict[int, Dict[str, Any]] = self._load_data("chat_data")
        self.user_data: Dict[int, Dict[str, Any]] = self._load_data("user_data")
        self.callback_data: Dict[int, Dict[str, Any]] = self._load_data("callback_data")
        self.conversations: Dict[str, Dict[str, Any]] = self._load_data("conversations")

    def _storage_key(self, name: str) -> str:
        return f"{self._key_prefix}:{name}"

    def _load_data(self, name: str) -> Dict[Any, Any]:
        try:
            raw = self._redis.get(self._storage_key(name))
            if not raw:
                return {}

            data = json.loads(raw)
            if isinstance(data, dict):
                return {int(k) if isinstance(k, str) and k.isdigit() else k: v for k, v in data.items()}
            return {}
        except Exception:
            return {}

    def _save_data(self, name: str, data: Any) -> None:
        try:
            self._redis.set(self._storage_key(name), json.dumps(data, default=str), ex=self._ttl)
        except Exception:
            pass

    async def get_user_data(self, *args, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id") or (args[0] if args else None)
        if user_id is None:
            return {}
        return self.user_data.setdefault(int(user_id), {})

    async def get_chat_data(self, *args, **kwargs) -> Dict[str, Any]:
        chat_id = kwargs.get("chat_id") or (args[0] if args else None)
        if chat_id is None:
            return {}
        return self.chat_data.setdefault(int(chat_id), {})

    async def get_callback_data(self, *args, **kwargs) -> CDCData:
        user_id = kwargs.get("user_id") or (args[0] if args else None)
        if user_id is None:
            return {}, {}
        val = self.callback_data.setdefault(int(user_id), {})
        if isinstance(val, tuple) and len(val) == 2:
            return val
        return val, {}

    async def get_conversations(self, *args, **kwargs) -> Dict[str, Any]:
        name = kwargs.get("name") or (args[0] if args else "default")
        return self.conversations.setdefault(str(name), {})

    async def get_bot_data(self) -> Dict[str, Any]:
        return self.bot_data

    async def update_user_data(self, *args, **kwargs) -> None:
        user_id = kwargs.get("user_id") or (args[0] if args else None)
        if user_id is None:
            return
        data = kwargs.get("data") or (args[1] if len(args) > 1 else {})
        self.user_data[int(user_id)] = data
        self._save_data("user_data", self.user_data)

    async def update_chat_data(self, *args, **kwargs) -> None:
        chat_id = kwargs.get("chat_id") or (args[0] if args else None)
        if chat_id is None:
            return
        data = kwargs.get("data") or (args[1] if len(args) > 1 else {})
        self.chat_data[int(chat_id)] = data
        self._save_data("chat_data", self.chat_data)

    async def update_callback_data(self, *args, **kwargs) -> None:
        user_id = kwargs.get("user_id") or (args[0] if args else None)
        if user_id is None:
            return
        data = kwargs.get("data") or (args[1] if len(args) > 1 else {})
        self.callback_data[int(user_id)] = data
        self._save_data("callback_data", self.callback_data)

    async def update_conversation(self, *args, **kwargs) -> None:
        name = kwargs.get("name") or (args[0] if args else "default")
        key = kwargs.get("key") or (args[1] if len(args) > 1 else None)
        new_state = kwargs.get("new_state") or (args[2] if len(args) > 2 else None)
        
        if key is None:
            return

        convo_dict = self.conversations.setdefault(str(name), {})
        
        # ስቴቱ ከጠፋ ስረዛ ይደረጋል፣ ካለ ደግሞ ይመዘገባል
        if new_state is None:
            convo_dict.pop(str(key), None)
        else:
            convo_dict[str(key)] = new_state
            
        self._save_data("conversations", self.conversations)

    async def update_bot_data(self, data: Dict[str, Any]) -> None:
        self.bot_data = data
        self._save_data("bot_data", self.bot_data)

    async def drop_chat_data(self, *args, **kwargs) -> None:
        chat_id = kwargs.get("chat_id") or (args[0] if args else None)
        if chat_id is None:
            return
        self.chat_data.pop(int(chat_id), None)
        self._save_data("chat_data", self.chat_data)

    async def drop_user_data(self, *args, **kwargs) -> None:
        user_id = kwargs.get("user_id") or (args[0] if args else None)
        if user_id is None:
            return
        self.user_data.pop(int(user_id), None)
        self._save_data("user_data", self.user_data)

    async def refresh_bot_data(self, *args, **kwargs) -> None:
        self.bot_data = self._load_data("bot_data")

    async def refresh_chat_data(self, *args, **kwargs) -> None:
        self.chat_data = self._load_data("chat_data")

    async def refresh_user_data(self, *args, **kwargs) -> None:
        self.user_data = self._load_data("user_data")

    async def flush(self) -> None:
        self._save_data("bot_data", self.bot_data)
        self._save_data("chat_data", self.chat_data)
        self._save_data("user_data", self.user_data)
        self._save_data("callback_data", self.callback_data)
        self._save_data("conversations", self.conversations)

    async def stop(self) -> None:
        await self.flush()


class JSONFilePersistence(BasePersistence):
    """Telegram persistence implementation backed by a JSON file."""

    def __init__(self, filepath: str = "bot_data.json"):
        super().__init__()
        self.store_user_data = True
        self.store_chat_data = True
        self.store_bot_data = True
        self.store_callback_data = True
        
        # 'dict' object can't be awaited ዋርኒንግን በስር ነቀል ዘዴ ለመከላከል
        self.is_async = False

        self.filepath = filepath
        self.bot_data: Dict[str, Any] = self._load_data("bot_data")
        self.chat_data: Dict[int, Dict[str, Any]] = self._load_data("chat_data")
        self.user_data: Dict[int, Dict[str, Any]] = self._load_data("user_data")
        self.callback_data: Dict[int, Dict[str, Any]] = self._load_data("callback_data")
        self.conversations: Dict[str, Dict[str, Any]] = self._load_data("conversations")

    def _load_data(self, name: str) -> Dict[Any, Any]:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                payload = json.load(f)
            data = payload.get(name, {}) if isinstance(payload, dict) else {}
            return {int(k) if isinstance(k, str) and k.isdigit() else k: v for k, v in data.items()}
        except FileNotFoundError:
            return {}
        except Exception:
            return {}

    def _save_data(self, name: str, data: Any) -> None:
        try:
            existing = {}
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    existing = json.load(f) or {}
            except Exception:
                existing = {}

            existing[name] = data
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(existing, f, default=str)
        except Exception:
            pass

    async def get_user_data(self, *args, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id") or (args[0] if args else None)
        if user_id is None:
            return {}
        return self.user_data.setdefault(int(user_id), {})

    async def get_chat_data(self, *args, **kwargs) -> Dict[str, Any]:
        chat_id = kwargs.get("chat_id") or (args[0] if args else None)
        if chat_id is None:
            return {}
        return self.chat_data.setdefault(int(chat_id), {})

    async def get_callback_data(self, *args, **kwargs) -> CDCData:
        user_id = kwargs.get("user_id") or (args[0] if args else None)
        if user_id is None:
            return {}, {}
        val = self.callback_data.setdefault(int(user_id), {})
        if isinstance(val, tuple) and len(val) == 2:
            return val
        return val, {}

    async def get_conversations(self, *args, **kwargs) -> Dict[str, Any]:
        name = kwargs.get("name") or (args[0] if args else "default")
        return self.conversations.setdefault(str(name), {})

    async def get_bot_data(self) -> Dict[str, Any]:
        return self.bot_data

    async def update_user_data(self, *args, **kwargs) -> None:
        user_id = kwargs.get("user_id") or (args[0] if args else None)
        if user_id is None:
            return
        data = kwargs.get("data") or (args[1] if len(args) > 1 else {})
        self.user_data[int(user_id)] = data
        self._save_data("user_data", self.user_data)

    async def update_chat_data(self, *args, **kwargs) -> None:
        chat_id = kwargs.get("chat_id") or (args[0] if args else None)
        if chat_id is None:
            return
        data = kwargs.get("data") or (args[1] if len(args) > 1 else {})
        self.chat_data[int(chat_id)] = data
        self._save_data("chat_data", self.chat_data)

    async def update_bot_data(self, data: Dict[str, Any]) -> None:
        self.bot_data = data
        self._save_data("bot_data", self.bot_data)

    async def update_callback_data(self, *args, **kwargs) -> None:
        user_id = kwargs.get("user_id") or (args[0] if args else None)
        if user_id is None:
            return
        data = kwargs.get("data") or (args[1] if len(args) > 1 else {})
        self.callback_data[int(user_id)] = data
        self._save_data("callback_data", self.callback_data)

    async def update_conversation(self, *args, **kwargs) -> None:
        name = kwargs.get("name") or (args[0] if args else "default")
        key = kwargs.get("key") or (args[1] if len(args) > 1 else None)
        new_state = kwargs.get("new_state") or (args[2] if len(args) > 2 else None)
        
        if key is None:
            return

        convo_dict = self.conversations.setdefault(str(name), {})
        
        if new_state is None:
            convo_dict.pop(str(key), None)
        else:
            convo_dict[str(key)] = new_state
            
        self._save_data("conversations", self.conversations)

    async def drop_chat_data(self, *args, **kwargs) -> None:
        chat_id = kwargs.get("chat_id") or (args[0] if args else None)
        if chat_id is None:
            return
        self.chat_data.pop(int(chat_id), None)
        self._save_data("chat_data", self.chat_data)

    async def drop_user_data(self, *args, **kwargs) -> None:
        user_id = kwargs.get("user_id") or (args[0] if args else None)
        if user_id is None:
            return
        self.user_data.pop(int(user_id), None)
        self._save_data("user_data", self.user_data)

    async def refresh_bot_data(self, *args, **kwargs) -> None:
        self.bot_data = self._load_data("bot_data")

    async def refresh_chat_data(self, *args, **kwargs) -> None:
        self.chat_data = self._load_data("chat_data")

    async def refresh_user_data(self, *args, **kwargs) -> None:
        self.user_data = self._load_data("user_data")

    async def flush(self) -> None:
        self._save_data("bot_data", self.bot_data)
        self._save_data("chat_data", self.chat_data)
        self._save_data("user_data", self.user_data)
        self._save_data("callback_data", self.callback_data)
        self._save_data("conversations", self.conversations)

    async def stop(self) -> None:
        await self.flush()


# Global bot instances
_bot: Optional[Bot] = None
_application: Optional[Application] = None


async def init_bot() -> Application:
    """
    Initialize the Telegram bot application with custom timeouts.
    
    Returns:
        Configured Application instance
    """
    global _application, _bot
    
    if _application is not None:
        return _application
    
    logger.info("Initializing Telegram bot...")
    
<<<<<<< HEAD
    # Configure persistence for conversation states using Redis when available.
    try:
        persistence = RedisPersistence(
            url=settings.REDIS_URL,
            key_prefix="telegram_persistence",
            ttl=settings.REDIS_SESSION_TTL,
        )
        logger.info("Using Redis-based persistence for Telegram bot state")
    except Exception as exc:
        logger.warning("Redis persistence unavailable, falling back to JSON file persistence: %s", exc)
        persistence = JSONFilePersistence(filepath="bot_data.json")

    # Build application with added network timeouts to handle slower connection handshakes gracefully
=======
    # Configure persistence for conversation states
    persistence = PicklePersistence(
        filepath="bot_data.pickle",
    )
    
    # Build application
>>>>>>> 58a16d4ee3078d96a16a22860de294107e7c3aef
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
    
    # Automatically register handlers inside the application instance
    try:
        from bot.handlers import register_handlers
        await register_handlers(_application)
        logger.info("Telegram bot handlers registered successfully")
    except Exception as e:
        logger.warning(f"Could not automatically register handlers inside init_bot: {e}")
    
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
    """Get the dispatcher instance."""
    if _application is None:
        raise RuntimeError("Bot not initialized. Call init_bot() first.")
    return _application


bot = None
dispatcher = None

__all__ = ["bot", "dispatcher", "init_bot", "shutdown_bot", "get_bot", "get_dispatcher"]