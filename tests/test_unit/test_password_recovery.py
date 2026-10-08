from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from apps.users.password_recovery import PasswordRecoveryService
from core.exceptions import AuthenticationError
from infrastructure.notifications import sms_gateway
from apps.users import schemas
from infrastructure.api.v1.endpoints import users as users_endpoint


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.counters = {}

    async def incr(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, _key, _seconds):
        return True

    async def set(self, key, value, ex=None):
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, *keys):
        removed = 0
        for key in keys:
            if key in self.values:
                del self.values[key]
                removed += 1
            self.counters.pop(key, None)
        return removed

    async def eval(self, _script, numkeys, *args):
        assert numkeys == 2
        code_key, attempts_key, expected_digest, ttl, max_attempts = args
        if code_key not in self.values:
            return 0
        if self.values[code_key] == expected_digest:
            await self.delete(code_key, attempts_key)
            return 1
        attempt_count = await self.incr(attempts_key)
        if attempt_count >= int(max_attempts):
            await self.delete(code_key)
        return -1


def _service(monkeypatch, user):
    redis = FakeRedis()
    redis_manager = SimpleNamespace(get_client=AsyncMock(return_value=redis))
    monkeypatch.setattr(
        "apps.users.password_recovery.get_redis_client",
        AsyncMock(return_value=redis_manager),
    )

    service = PasswordRecoveryService(object())
    service.user_repo.get_by_phone = AsyncMock(return_value=user)
    service.user_repo.update = AsyncMock()
    monkeypatch.setattr("apps.users.password_recovery.hash_password", lambda value: f"hashed:{value}")
    return service, redis


@pytest.mark.asyncio
async def test_password_reset_code_is_hashed_and_single_use(monkeypatch):
    user = SimpleNamespace(id=7, status="active", is_deleted=False)
    service, redis = _service(monkeypatch, user)
    delivered = {}

    async def send_code(phone, code):
        delivered.update(phone=phone, code=code)
        return True

    monkeypatch.setattr(sms_gateway, "send_verification_code", send_code)
    await service.request_code("0912345678")

    assert delivered["phone"] == "0912345678"
    assert len(delivered["code"]) == 6
    fingerprint = service._phone_fingerprint("0912345678")
    code_key = f"auth:password_reset:code:{fingerprint}"
    assert redis.values[code_key] == service._code_digest("0912345678", delivered["code"])
    assert redis.values[code_key] != delivered["code"]

    await service.reset_password("0912345678", delivered["code"], "new-password")
    service.user_repo.update.assert_awaited_once_with(7, {"password_hash": "hashed:new-password"})
    with pytest.raises(AuthenticationError):
        await service.reset_password("0912345678", delivered["code"], "another-password")


@pytest.mark.asyncio
async def test_unknown_phone_does_not_trigger_sms(monkeypatch):
    service, _ = _service(monkeypatch, None)
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(sms_gateway, "send_verification_code", sender)

    await service.request_code("0912345678")

    sender.assert_not_awaited()


@pytest.mark.asyncio
async def test_recovery_requests_are_rate_limited(monkeypatch):
    user = SimpleNamespace(id=7, status="active", is_deleted=False)
    service, _ = _service(monkeypatch, user)
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(sms_gateway, "send_verification_code", sender)

    for _ in range(4):
        await service.request_code("0912345678")

    assert sender.await_count == 3


@pytest.mark.asyncio
async def test_five_invalid_codes_invalidate_recovery_code(monkeypatch):
    user = SimpleNamespace(id=7, status="active", is_deleted=False)
    service, redis = _service(monkeypatch, user)
    fingerprint = service._phone_fingerprint("0912345678")
    code_key = f"auth:password_reset:code:{fingerprint}"
    await redis.set(code_key, service._code_digest("0912345678", "123456"), ex=300)

    for _ in range(5):
        with pytest.raises(AuthenticationError):
            await service.reset_password("0912345678", "000000", "new-password")

    assert code_key not in redis.values


@pytest.mark.asyncio
async def test_request_endpoint_returns_same_generic_message(monkeypatch):
    calls = []

    class StubRecoveryService:
        def __init__(self, _db):
            pass

        async def request_code(self, phone):
            calls.append(phone)

    monkeypatch.setattr(users_endpoint, "PasswordRecoveryService", StubRecoveryService)
    payload = schemas.PasswordResetStartRequest(phone_number="0912345678")
    response = await users_endpoint.request_password_reset(payload, object())

    assert response.message.startswith("If the phone number is registered")
    assert calls == ["0912345678"]
