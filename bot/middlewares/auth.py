# ============================
# WOLLOYEWA STORE BOT - AUTH MIDDLEWARE
# ============================
"""Authentication middleware for Telegram bot handlers."""

from typing import Dict, Any, Callable, Awaitable
from telegram import Update
from telegram.ext import ContextTypes

from core.logger import logger
from apps.users.services import UserService
from infrastructure.database.session import get_db_session


class AuthMiddleware:
    """
    Authentication middleware for bot handlers.
    Ensures user is registered before accessing protected handlers.
    """

    def __init__(self):
        self._user_cache: Dict[int, Dict[str, Any]] = {}

    async def get_or_create_user(
        self,
        telegram_id: int,
        first_name: str,
        username: str = None,
    ) -> Dict[str, Any]:
        """Get or create user in database and return a plain dict."""
        if telegram_id in self._user_cache:
            return self._user_cache[telegram_id]

        try:
            async for db in get_db_session():
                user_service = UserService(db)
                user = await user_service.get_or_create_user(
                    telegram_id=telegram_id,
                    first_name=first_name,
                    username=username,
                )
                if user:
                    user_data = {
                        "id": user.id,
                        "telegram_id": user.telegram_id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": str(user.role.value) if hasattr(user.role, "value") else str(user.role),
                        "status": str(user.status.value) if hasattr(user.status, "value") else str(user.status),
                        "phone_number": user.phone_number,
                        "email": user.email,
                        "language": user.language,
                    }
                    self._user_cache[telegram_id] = user_data
                    return user_data
                break
        except Exception as e:
            logger.warning(f"AuthMiddleware: failed to get/create user {telegram_id}: {e}")

        return None

    def invalidate(self, telegram_id: int) -> None:
        """Remove a single user from the cache (call after profile updates)."""
        self._user_cache.pop(telegram_id, None)

    def clear_cache(self, telegram_id: int = None) -> None:
        """Clear user cache (all or single user)."""
        if telegram_id:
            self._user_cache.pop(telegram_id, None)
        else:
            self._user_cache.clear()


# Singleton used across the bot
auth_middleware = AuthMiddleware()


async def ensure_user_registered(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    TypeHandler middleware — runs in group -1 (before all other handlers).

    Ensures every interacting user exists in the database and stores their
    data in context.user_data so downstream handlers can use it without an
    extra DB round-trip.
    """
    tg_user = update.effective_user
    if not tg_user:
        return

    # Skip re-loading if already done in this update cycle
    if context.user_data.get("user_id"):
        return

    user_data = await auth_middleware.get_or_create_user(
        telegram_id=tg_user.id,
        first_name=tg_user.first_name or "User",
        username=tg_user.username,
    )

    if user_data:
        context.user_data["user_id"] = user_data["id"]
        context.user_data["user_role"] = user_data["role"]
        context.user_data["user"] = user_data
    else:
        logger.error(f"Could not register/load user {tg_user.id} — DB may be unavailable.")


__all__ = [
    "AuthMiddleware",
    "auth_middleware",
    "ensure_user_registered",
]
