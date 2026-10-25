from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.error import BadRequest

from bot.handlers import catalog
from bot.handlers.admin import admin_input, dashboard, orders_admin, users_admin
from bot import product_media


@pytest.mark.asyncio
async def test_menu_command_routes_configured_admin_to_admin_panel(monkeypatch):
    monkeypatch.setattr(catalog, "settings", SimpleNamespace(admin_ids_list=[42]))
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=42),
        effective_message=message,
        callback_query=None,
    )

    await catalog.menu_command(update, SimpleNamespace())

    message.reply_text.assert_awaited_once()
    text = message.reply_text.await_args.args[0]
    kwargs = message.reply_text.await_args.kwargs
    assert "አስተዳደር" in text
    callback_data = {
        button.callback_data
        for row in kwargs["reply_markup"].inline_keyboard
        for button in row
    }
    assert "admin_products" in callback_data
    assert "admin_orders" in callback_data


@pytest.mark.asyncio
async def test_admin_user_search_state_returns_results_and_actions(monkeypatch):
    user = SimpleNamespace(
        id=8,
        full_name="Test User",
        role="customer",
        status="active",
    )
    repo = SimpleNamespace(search_users=AsyncMock(return_value=[user]))
    monkeypatch.setattr(
        "apps.users.services.UserService",
        lambda db: SimpleNamespace(user_repo=repo),
    )

    @asynccontextmanager
    async def transaction_session():
        yield object()

    monkeypatch.setattr(admin_input, "transaction_session", transaction_session)
    monkeypatch.setattr(admin_input, "settings", SimpleNamespace(admin_ids_list=[42]))
    message = SimpleNamespace(text="test", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=42),
        message=message,
    )
    context = SimpleNamespace(
        user_data={"admin_awaiting_user_search": True},
    )

    await admin_input.handle_admin_text_input(update, context)

    assert "admin_awaiting_user_search" not in context.user_data
    message.reply_text.assert_awaited_once()
    buttons = [
        button.callback_data
        for row in message.reply_text.await_args.kwargs["reply_markup"].inline_keyboard
        for button in row
    ]
    assert "admin_suspend_user_8" in buttons


@pytest.mark.asyncio
async def test_admin_user_cannot_suspend_another_admin(monkeypatch):
    user = SimpleNamespace(
        id=8,
        telegram_id=99,
        role="admin",
        status="active",
        is_deleted=False,
    )
    repository = SimpleNamespace(
        get_by_id=AsyncMock(return_value=user),
        update=AsyncMock(),
    )
    monkeypatch.setattr(
        users_admin,
        "UserService",
        lambda db: SimpleNamespace(user_repo=repository),
    )

    @asynccontextmanager
    async def transaction_session():
        yield object()

    monkeypatch.setattr(users_admin, "transaction_session", transaction_session)
    monkeypatch.setattr(
        users_admin, "settings", SimpleNamespace(admin_ids_list=[42, 99])
    )
    message = SimpleNamespace(edit_text=AsyncMock())
    update = SimpleNamespace(callback_query=SimpleNamespace(message=message))

    await users_admin.do_suspend_user(update, SimpleNamespace(), 8)

    repository.update.assert_not_awaited()
    message.edit_text.assert_awaited_once()
    assert "አልተቻለም" in message.edit_text.await_args.args[0]


def test_admin_order_status_choices_match_supported_transitions():
    assert "cancelled" not in orders_admin.STATUS_TRANSITIONS["shipped"]
    assert orders_admin.STATUS_TRANSITIONS["pending"] == ["confirmed", "cancelled"]


@pytest.mark.asyncio
async def test_dashboard_ignores_only_unchanged_message_error(monkeypatch):
    async def get_db_session():
        yield object()

    monkeypatch.setattr(dashboard, "get_db_session", get_db_session)
    monkeypatch.setattr(
        dashboard,
        "SalesAnalyticsService",
        lambda db: SimpleNamespace(
            get_sales_summary=AsyncMock(return_value={"total_revenue": 0})
        ),
    )
    monkeypatch.setattr(
        dashboard,
        "UserService",
        lambda db: SimpleNamespace(
            user_repo=SimpleNamespace(count=AsyncMock(return_value=0))
        ),
    )
    monkeypatch.setattr(
        dashboard,
        "VendorService",
        lambda db: SimpleNamespace(vendor_repo=SimpleNamespace(count=AsyncMock(return_value=0))),
    )
    monkeypatch.setattr(
        dashboard,
        "OrderService",
        lambda db: SimpleNamespace(
            order_repo=SimpleNamespace(count=AsyncMock(return_value=0))
        ),
    )
    edit_text = AsyncMock(
        side_effect=BadRequest(
            "Message is not modified: specified new message content and reply "
            "markup are exactly the same as a current content and reply markup"
        )
    )
    update = SimpleNamespace(
        callback_query=SimpleNamespace(message=SimpleNamespace(edit_text=edit_text))
    )

    await dashboard._send_dashboard_text(update, SimpleNamespace())

    edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_auth_user_creation_uses_transaction_session(monkeypatch):
    from bot.middlewares import auth

    entered_transaction = False

    @asynccontextmanager
    async def transaction_session():
        nonlocal entered_transaction
        entered_transaction = True
        yield object()

    user = SimpleNamespace(
        id=5,
        telegram_id=42,
        username="test",
        first_name="Test",
        last_name=None,
        role="customer",
        status="active",
        phone_number=None,
        email=None,
        language="am",
    )
    service = SimpleNamespace(
        get_or_create_user=AsyncMock(return_value=user)
    )
    monkeypatch.setattr(auth, "transaction_session", transaction_session)
    monkeypatch.setattr(auth, "UserService", lambda db: service)
    middleware = auth.AuthMiddleware()

    result = await middleware.get_or_create_user(42, "Test", "test")

    assert entered_transaction
    assert result["id"] == user.id


def test_local_product_image_is_opened_for_telegram(monkeypatch, tmp_path):
    from telegram import InputFile

    image_bytes = b"test image contents"
    (tmp_path / "product.jpg").write_bytes(image_bytes)
    monkeypatch.setattr(product_media, "_UPLOADS_DIR", tmp_path)

    with product_media.telegram_photo_source(
        "/app/static/uploads/product.jpg"
    ) as photo:
        assert isinstance(photo, InputFile)
        assert photo.input_file_content == image_bytes
        assert photo.filename == "product.jpg"


def test_remote_product_image_remains_a_url():
    image_url = "https://cdn.example.com/product.jpg"

    with product_media.telegram_photo_source(image_url) as photo:
        assert photo == image_url
