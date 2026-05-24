# ============================
# WOLLOYEWA STORE BOT - THROTTLING MIDDLEWARE
# ============================
"""Rate limiting middleware for bot commands."""

from typing import Callable, Awaitable, Dict, Tuple
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from core.logger import logger
from core.config import settings


class ThrottlingMiddleware:
    """
    Rate limiting middleware for bot commands.
    
    Prevents users from sending too many requests in a short time.
    """
    
    def __init__(self):
        self._user_requests: Dict[int, list] = {}
        self._default_limit = settings.RATE_LIMIT_PER_MINUTE
        self._default_window = 60  # seconds
        
        # Custom limits for specific commands
        self._command_limits = {
            "/search": (10, 60),      # 10 searches per minute
            "/checkout": (5, 60),     # 5 checkouts per minute
            "/broadcast": (2, 300),   # 2 broadcasts per 5 minutes (admin)
        }
    
    async def __call__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        next_handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
    ) -> None:
        """
        Process the update with rate limiting.
        
        Args:
            update: Telegram update
            context: Callback context
            next_handler: Next handler in chain
        """
        user_id = update.effective_user.id if update.effective_user else None
        
        if not user_id:
            await next_handler(update, context)
            return
        
        # Extract command
        command = None
        if update.message and update.message.text and update.message.text.startswith('/'):
            command = update.message.text.split()[0]
        
        # Check rate limit
        is_allowed, retry_after = self.check_rate_limit(user_id, command)
        
        if not is_allowed:
            await update.message.reply_text(
                f"⏳ በጣም ብዙ ጥያቄዎችን በአጭር ጊዜ ውስጥ ልከዋል።\n"
                f"እባክዎ ከ {retry_after} ሰከንድ በኋላ እንደገና ይሞክሩ።"
            )
            return
        
        # Record this request
        self.record_request(user_id, command)
        
        # Process the update
        await next_handler(update, context)
    
    def check_rate_limit(self, user_id: int, command: str = None) -> Tuple[bool, int]:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User ID
            command: Command being executed
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = datetime.utcnow()
        
        # Get limits for this command
        if command and command in self._command_limits:
            limit, window = self._command_limits[command]
        else:
            limit = self._default_limit
            window = self._default_window
        
        # Get user's request history
        if user_id not in self._user_requests:
            self._user_requests[user_id] = []
        
        # Clean old requests
        cutoff = now - timedelta(seconds=window)
        self._user_requests[user_id] = [
            ts for ts in self._user_requests[user_id]
            if ts > cutoff
        ]
        
        # Check limit
        if len(self._user_requests[user_id]) >= limit:
            # Calculate retry after
            if self._user_requests[user_id]:
                oldest = min(self._user_requests[user_id])
                retry_after = int((oldest + timedelta(seconds=window) - now).total_seconds())
                return False, max(1, retry_after)
            return False, window
        
        return True, 0
    
    def record_request(self, user_id: int, command: str = None) -> None:
        """
        Record a user request.
        
        Args:
            user_id: User ID
            command: Command executed
        """
        if user_id not in self._user_requests:
            self._user_requests[user_id] = []
        
        self._user_requests[user_id].append(datetime.utcnow())
        logger.debug(f"Rate limit: user {user_id} executed {command}")
    
    def reset_user(self, user_id: int) -> None:
        """Reset rate limit for a user."""
        self._user_requests.pop(user_id, None)


# Global throttling middleware instance
throttling_middleware = ThrottlingMiddleware()


__all__ = ["ThrottlingMiddleware", "throttling_middleware"]