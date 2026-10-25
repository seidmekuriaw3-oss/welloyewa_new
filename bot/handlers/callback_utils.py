"""Safe helpers for Telegram callback query acknowledgements and edits."""

from telegram.error import BadRequest

from core.logger import logger


def _is_stale_callback_error(error: BadRequest) -> bool:
    message = str(error).casefold()
    return any(
        marker in message
        for marker in (
            "query is too old",
            "query id is invalid",
            "query is already answered",
        )
    )


async def answer_callback_query(query, text: str | None = None, show_alert: bool = False) -> bool:
    """Acknowledge a callback promptly; return False when Telegram has expired it."""
    try:
        await query.answer(text=text, show_alert=show_alert)
    except BadRequest as exc:
        if not _is_stale_callback_error(exc):
            raise
        logger.debug("Ignoring expired callback query %s: %s", query.id, exc)
        return False
    return True


async def edit_callback_message(query, text: str, **kwargs) -> bool:
    """Edit a callback message and treat an already-identical message as success."""
    try:
        await query.edit_message_text(text, **kwargs)
    except BadRequest as exc:
        if "message is not modified" not in str(exc).casefold():
            raise
        logger.debug("Callback message %s was already up to date", query.id)
        return False
    return True


__all__ = ["answer_callback_query", "edit_callback_message"]
