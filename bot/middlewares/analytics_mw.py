# ============================
# WOLLOYEWA STORE BOT - ANALYTICS MIDDLEWARE
# ============================
"""Analytics tracking middleware for bot user actions."""

import time
from typing import Callable, Awaitable
from telegram import Update
from telegram.ext import ContextTypes

from core.logger import logger
from core.data_pipeline.real_time_analytics import real_time_analytics
from core.monitoring.metrics import metrics_collector


class AnalyticsMiddleware:
    """
    Analytics middleware for tracking user actions.
    
    Records:
    - Command usage
    - User sessions
    - Response times
    - Error rates
    """
    
    async def __call__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        next_handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
    ) -> None:
        """
        Process the update and track analytics.
        
        Args:
            update: Telegram update
            context: Callback context
            next_handler: Next handler in chain
        """
        start_time = time.time()
        command = None
        user_id = None
        success = True
        
        try:
            # Extract command from update
            if update.message and update.message.text:
                text = update.message.text
                if text.startswith('/'):
                    command = text.split()[0]
            
            if update.effective_user:
                user_id = update.effective_user.id
            
            # Track user activity
            if user_id:
                await real_time_analytics.track_user_action(
                    user_id=user_id,
                    action_type="command",
                    data={"command": command or "unknown"},
                )
            
            # Process the update
            await next_handler(update, context)
            
        except Exception as e:
            success = False
            logger.error(f"Analytics middleware error: {e}")
            raise
        
        finally:
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Track metrics
            if command:
                metrics_collector.record_bot_command(
                    command=command,
                    duration=response_time,
                    success=success,
                )
            
            logger.debug(
                f"Analytics: user={user_id}, command={command}, "
                f"success={success}, duration={response_time:.2f}ms"
            )


# Global analytics middleware instance
analytics_middleware = AnalyticsMiddleware()


__all__ = ["AnalyticsMiddleware", "analytics_middleware"]