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
    
    async def __call__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        next_handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
    ) -> None:
        """
        Process the update through the middleware.
        
        Args:
            update: Telegram update
            context: Callback context
            next_handler: Next handler in chain
        """
        user = update.effective_user
        
        if not user:
            await next_handler(update, context)
            return
        
        # Check if user is authenticated
        user_data = await self.get_or_create_user(user.id, user.first_name, user.username)
        
        if user_data:
            # Store user in context
            context.user_data["user_id"] = user_data["id"]
            context.user_data["user_role"] = user_data["role"]
            context.user_data["user"] = user_data
            
            await next_handler(update, context)
        else:
            # User not authenticated - send error
            await update.message.reply_text(
                "❌ እባክዎ እንደገና /start በመጫን ይሞክሩ።"
            )
    
    async def get_or_create_user(
        self,
        telegram_id: int,
        first_name: str,
        username: str = None,
    ) -> Dict[str, Any]:
        """
        Get or create user in database.
        
        Args:
            telegram_id: Telegram user ID
            first_name: User's first name
            username: Telegram username
            
        Returns:
            User data dictionary
        """
        # Check cache
        if telegram_id in self._user_cache:
            return self._user_cache[telegram_id]
        
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
                    "role": user.role,
                    "status": user.status,
                    "phone_number": user.phone_number,
                    "email": user.email,
                    "language": user.language,
                }
                self._user_cache[telegram_id] = user_data
                return user_data
            break
        
        return None
    
    def clear_cache(self, telegram_id: int = None) -> None:
        """Clear user cache."""
        if telegram_id:
            self._user_cache.pop(telegram_id, None)
        else:
            self._user_cache.clear()


# Global auth middleware instance
auth_middleware = AuthMiddleware()


async def auth_middleware_wrapper(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    next_handler: Callable,
) -> None:
    """Wrapper for auth middleware."""
    await auth_middleware(update, context, next_handler)


__all__ = ["AuthMiddleware", "auth_middleware", "auth_middleware_wrapper"]