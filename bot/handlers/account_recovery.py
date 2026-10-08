"""Account recovery commands for the Telegram bot."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from apps.users.password_recovery import PasswordRecoveryService
from apps.users.repository import UserRepository
from core.config import settings
from core.logger import logger
from infrastructure.database.session import get_db_session


async def reset_password_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send a reset code only to the Telegram account already linked to the user."""
    telegram_user = update.effective_user
    message = update.effective_message
    if telegram_user is None or message is None:
        return

    try:
        async for db in get_db_session():
            user = await UserRepository(db).get_by_telegram(telegram_user.id)
            if user and user.phone_number and user.password_hash:
                await PasswordRecoveryService(db).request_code(user.phone_number)
            break
    except Exception as exc:
        logger.warning("Telegram password recovery request failed (%s)", type(exc).__name__)

    web_app_url = settings.web_app_url
    reply_markup = None
    if web_app_url:
        recovery_url = f"{web_app_url.rstrip('/')}/forgot-password?via=telegram"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔐 የይለፍ ቃሌን ቀይር", url=recovery_url)]]
        )

    await message.reply_text(
        "Хэрэв энэ Telegram хаяг нууц үгтэй бүртгэлтэй холбогдсон бол сэргээх кодыг энэ чатад илгээлээ. "
        "Код 5 минут хүчинтэй. Доорх товчоор нууц үгээ солино уу. "
        "Код ирээгүй бол хуудсан дээрээс код дахин хүсэх, бүртгэлтэй имэйлээ шалгах эсвэл админтай холбогдоно уу.",
        reply_markup=reply_markup,
    )


__all__ = ["reset_password_command"]
