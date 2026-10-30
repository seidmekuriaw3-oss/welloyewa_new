from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from apps.users.schemas import UserUpdate
from apps.users.services import UserService


@pytest.mark.asyncio
async def test_user_update_can_persist_explicitly_cleared_optional_fields():
    service = UserService(AsyncMock())
    service.user_repo = AsyncMock()
    updated_user = SimpleNamespace(id=42)
    service.user_repo.update.return_value = updated_user

    with patch("apps.users.services.emit_event", new_callable=AsyncMock):
        result = await service.update_user(
            42,
            UserUpdate(last_name=None, email=None),
            partial=False,
        )

    assert result is updated_user
    service.user_repo.update.assert_awaited_once_with(
        42,
        {"last_name": None, "email": None},
        partial=False,
    )


@pytest.mark.asyncio
async def test_user_update_accepts_mapping_callers():
    service = UserService(AsyncMock())
    service.user_repo = AsyncMock()
    service.user_repo.update.return_value = SimpleNamespace(id=42)

    with patch("apps.users.services.emit_event", new_callable=AsyncMock):
        await service.update_user(42, {"status": "active"})

    service.user_repo.update.assert_awaited_once_with(
        42,
        {"status": "active"},
        partial=True,
    )
