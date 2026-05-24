# ============================
# WOLLOYEWA STORE BOT - ERROR HANDLER
# ============================
"""Telegram bot global error handling."""

import traceback
import html
import json
import re
from telegram import Update
from telegram.ext import ContextTypes
from core.logger import logger
from core.config import settings

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        f"</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ ይቅርታ፣ ያልተጠበቀ ስህተት ተከስቷል። የአስተዳደር ቡድኑ መረጃው ደርሶታል።"
        )

    # Send to admin log channel if configured
    for admin_id in settings.admin_ids_list:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message[:4096], parse_mode="HTML")
        except Exception:
            pass


def is_critical_error(error: Exception) -> bool:
    """
    Check if error is critical enough to notify admins.
    
    Args:
        error: The exception that occurred
        
    Returns:
        True if critical
    """
    critical_types = (
        ConnectionError,
        TimeoutError,
        MemoryError,
        SystemError,
    )
    
    if isinstance(error, critical_types):
        return True
    
    # Check for authentication/authorization errors
    error_str = str(error).lower()
    critical_keywords = [
        "auth", "permission", "token", "unauthorized",
        "database", "connection", "timeout",
    ]
    
    for keyword in critical_keywords:
        if keyword in error_str:
            return True
    
    return False


def get_error_file(traceback_str: str) -> str:
    """
    Extract file name from traceback.
    
    Args:
        traceback_str: Full traceback string
        
    Returns:
        File name or "Unknown"
    """
    lines = traceback_str.split("\n")
    for line in lines:
        if 'File "' in line:
            match = re.search(r'File "([^"]+)"', line)
            if match:
                return match.group(1).split("/")[-1]
    return "Unknown"


def get_error_line(traceback_str: str) -> str:
    """
    Extract line number from traceback.
    
    Args:
        traceback_str: Full traceback string
        
    Returns:
        Line number or "Unknown"
    """
    lines = traceback_str.split("\n")
    for line in lines:
        if 'line ' in line:
            import re
            match = re.search(r'line (\d+)', line)
            if match:
                return match.group(1)
    return "Unknown"


def get_first_traceback_lines(traceback_str: str, num_lines: int = 3) -> str:
    """
    Get first N lines of traceback.
    
    Args:
        traceback_str: Full traceback string
        num_lines: Number of lines to return
        
    Returns:
        First N lines of traceback
    """
    lines = traceback_str.split("\n")
    return "\n".join(lines[:num_lines])


__all__ = ["error_handler"]