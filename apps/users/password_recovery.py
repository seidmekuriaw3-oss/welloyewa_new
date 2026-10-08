"""OTP-based password recovery delivered through linked Telegram or email."""

import hashlib
import hmac

from apps.users.repository import UserRepository
from core.config import settings
from core.exceptions import AuthenticationError
from core.logger import logger
from core.security import generate_otp, hash_password
from core.utils.validators import Validator
from infrastructure.redis.client import get_redis_client

RESET_TTL_SECONDS = 300
RESET_REQUEST_WINDOW_SECONDS = 3600
RESET_MAX_REQUESTS = 3
RESET_MAX_ATTEMPTS = 5

_CONSUME_CODE_SCRIPT = """
local stored = redis.call('GET', KEYS[1])
if not stored then
    return 0
end
if stored == ARGV[1] then
    redis.call('DEL', KEYS[1], KEYS[2])
    return 1
end
local attempts = redis.call('INCR', KEYS[2])
if attempts == 1 then
    redis.call('EXPIRE', KEYS[2], tonumber(ARGV[2]))
end
if attempts >= tonumber(ARGV[3]) then
    redis.call('DEL', KEYS[1])
end
return -1
"""


class PasswordRecoveryService:
    """Issue and consume short-lived, single-use password reset codes."""

    def __init__(self, db):
        self.user_repo = UserRepository(db)

    @staticmethod
    def _phone_fingerprint(phone: str) -> str:
        key = settings.SECRET_KEY.encode("utf-8")
        return hmac.new(key, f"password-reset-phone:{phone}".encode(), hashlib.sha256).hexdigest()

    @classmethod
    def _code_digest(cls, phone: str, code: str) -> str:
        key = settings.SECRET_KEY.encode("utf-8")
        message = f"password-reset-code:{cls._phone_fingerprint(phone)}:{code}".encode()
        return hmac.new(key, message, hashlib.sha256).hexdigest()

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        return Validator.phone(phone, normalize=True)

    async def _redis(self):
        manager = await get_redis_client()
        return await manager.get_client()

    @staticmethod
    async def _deliver_code(user, code: str) -> str | None:
        """Send the code to a contact already linked to the account."""
        user_id = getattr(user, "id", None)
        message = (
            "🔐 Wolloyewa Store\n"
            f"የይለፍ ቃል መቀየሪያ ኮድዎ: {code}\n"
            "ኮዱ ለ5 ደቂቃ ይሰራል። እርስዎ ካልጠየቁት ይህን መልዕክት ችላ ይበሉ።"
        )

        telegram_id = getattr(user, "telegram_id", None)
        if telegram_id:
            try:
                from infrastructure.notifications.telegram_notifier import (
                    send_telegram_message,
                )

                if await send_telegram_message(int(telegram_id), message):
                    logger.info("Password recovery code delivered via Telegram for user_id=%s", user_id)
                    return "telegram"
            except Exception as exc:
                logger.warning(
                    "Password recovery Telegram delivery failed for user_id=%s (%s)",
                    user_id,
                    type(exc).__name__,
                )

        email = getattr(user, "email", None)
        if email:
            try:
                from infrastructure.notifications.email_service import send_password_reset_email

                name = " ".join(
                    part
                    for part in (
                        getattr(user, "first_name", None),
                        getattr(user, "last_name", None),
                    )
                    if part
                ) or "Customer"
                if await send_password_reset_email(email, name, code):
                    logger.info("Password recovery code delivered via email for user_id=%s", user_id)
                    return "email"
            except Exception as exc:
                logger.warning(
                    "Password recovery email delivery failed for user_id=%s (%s)",
                    user_id,
                    type(exc).__name__,
                )

        return None

    async def request_code(self, phone_number: str) -> None:
        """Send a recovery code to a linked Telegram or email contact."""
        phone = self._normalize_phone(phone_number)
        fingerprint = self._phone_fingerprint(phone)
        redis = await self._redis()

        request_key = f"auth:password_reset:requests:{fingerprint}"
        request_count = await redis.incr(request_key)
        if request_count == 1:
            await redis.expire(request_key, RESET_REQUEST_WINDOW_SECONDS)
        if request_count > RESET_MAX_REQUESTS:
            return

        user = await self.user_repo.get_by_phone(phone)
        if not user or getattr(user, "is_deleted", False) or user.status != "active":
            return

        code = generate_otp()
        code_key = f"auth:password_reset:code:{fingerprint}"
        attempts_key = f"auth:password_reset:attempts:{fingerprint}"
        await redis.set(code_key, self._code_digest(phone, code), ex=RESET_TTL_SECONDS)
        await redis.delete(attempts_key)

        try:
            channel = await self._deliver_code(user, code)
        except Exception as exc:
            await redis.delete(code_key, attempts_key)
            logger.warning("Password recovery delivery failed (%s)", type(exc).__name__)
            return

        if not channel:
            await redis.delete(code_key, attempts_key)
            logger.warning("Password recovery has no usable Telegram or email delivery channel")

    async def reset_password(self, phone_number: str, code: str, new_password: str) -> None:
        """Verify and consume a recovery code before replacing the password hash."""
        phone = self._normalize_phone(phone_number)
        user = await self.user_repo.get_by_phone(phone)
        if not user or getattr(user, "is_deleted", False) or user.status != "active":
            raise AuthenticationError("Invalid or expired recovery code")

        fingerprint = self._phone_fingerprint(phone)
        code_key = f"auth:password_reset:code:{fingerprint}"
        attempts_key = f"auth:password_reset:attempts:{fingerprint}"
        redis = await self._redis()
        consumed = await redis.eval(
            _CONSUME_CODE_SCRIPT,
            2,
            code_key,
            attempts_key,
            self._code_digest(phone, code),
            RESET_TTL_SECONDS,
            RESET_MAX_ATTEMPTS,
        )
        if int(consumed) != 1:
            raise AuthenticationError("Invalid or expired recovery code")

        await self.user_repo.update(user.id, {"password_hash": hash_password(new_password)})
        logger.info("Password recovery completed for user_id=%s", user.id)


__all__ = ["PasswordRecoveryService"]
