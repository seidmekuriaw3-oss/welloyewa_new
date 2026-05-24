# ============================
# WOLLOYEWA STORE BOT - LOGGING MIDDLEWARE
# ============================
"""Logging middleware for bot requests and responses."""

import time
import json
from typing import Callable, Awaitable
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from core.logger import logger


class LoggingMiddleware:
    """
    Logging middleware for bot updates.
    
    Logs:
    - User actions
    - Command execution
    - Response times
    - Errors
    """
    
    async def __call__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        next_handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
    ) -> None:
        """
        Process the update with logging.
        
        Args:
            update: Telegram update
            context: Callback context
            next_handler: Next handler in chain
        """
        start_time = time.time()
        user = update.effective_user
        chat = update.effective_chat
        
        # Extract update info
        update_type = self._get_update_type(update)
        command = None
        text = None
        
        if update.message:
            if update.message.text:
                text = update.message.text
                if text.startswith('/'):
                    command = text.split()[0]
        
        # Log incoming update
        log_data = {
            "update_id": update.update_id,
            "user_id": user.id if user else None,
            "username": user.username if user else None,
            "chat_id": chat.id if chat else None,
            "update_type": update_type,
            "command": command,
            "text": text[:100] if text else None,
        }
        
        logger.info(f"Incoming update: {json.dumps(log_data, default=str)}")
        
        try:
            # Process the update
            await next_handler(update, context)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Log success
            logger.info(
                f"Update processed: user={user.id if user else None}, "
                f"command={command}, duration={response_time:.2f}ms"
            )
            
        except Exception as e:
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Log error
            logger.error(
                f"Update failed: user={user.id if user else None}, "
                f"command={command}, duration={response_time:.2f}ms, "
                f"error={str(e)}"
            )
            raise
    
    def _get_update_type(self, update: Update) -> str:
        """Determine update type."""
        if update.message:
            if update.message.text:
                return "message_text"
            elif update.message.photo:
                return "message_photo"
            elif update.message.document:
                return "message_document"
            elif update.message.location:
                return "message_location"
            elif update.message.contact:
                return "message_contact"
            else:
                return "message_other"
        elif update.callback_query:
            return "callback_query"
        elif update.inline_query:
            return "inline_query"
        elif update.chosen_inline_result:
            return "chosen_inline_result"
        else:
            return "unknown"


# Global logging middleware instance
logging_middleware = LoggingMiddleware()


__all__ = ["LoggingMiddleware", "logging_middleware"]