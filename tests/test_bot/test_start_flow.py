"""Focused tests for Telegram start, onboarding, and menu routing."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from telegram import Update, User


def make_update(user_id=123, first_name="Test"):
    update = Mock(spec=Update)
    update.effective_user = User(
        id=user_id,
        first_name=first_name,
        username="tester",
        is_bot=False,
    )
    update.message = Mock()
    update.message.reply_text = AsyncMock()
    update.effective_message = update.message
    return update


def make_context(language="en"):
    context = Mock()
    context.user_data = {"user": {"language": language}}
    return context


def test_keyboard_builders_cover_languages_and_admin_state():
    from bot.handlers.start import _build_language_keyboard, _build_main_menu, _build_phone_keyboard

    language_keyboard = _build_language_keyboard()
    assert [row[0].callback_data for row in language_keyboard.inline_keyboard] == [
        "onboard_lang_am",
        "onboard_lang_en",
        "onboard_lang_om",
    ]

    phone_keyboard = _build_phone_keyboard("en")
    assert phone_keyboard.keyboard[0][0].request_contact is True

    regular = _build_main_menu(is_admin=False, lang="unknown")
    admin = _build_main_menu(is_admin=True, lang="om")
    assert len(regular.inline_keyboard) == 5
    assert admin.inline_keyboard[-1][0].callback_data == "menu_admin"


@pytest.mark.asyncio
async def test_start_new_user_shows_language_selection():
    from bot.handlers.start import start_command

    update = make_update()
    context = Mock()
    context.user_data = {}
    user_service = AsyncMock()
    user_service.get_user_by_telegram.return_value = None
    user_service.get_or_create_user.return_value = Mock(id=1)

    with patch("bot.handlers.start.get_db_session") as db_factory:
        db_factory.return_value.__aiter__.return_value = [Mock()]
        with patch("bot.handlers.start.UserService", return_value=user_service):
            await start_command(update, context)

    update.message.reply_text.assert_awaited_once()
    assert context.user_data["onboarding"] is True


@pytest.mark.asyncio
async def test_start_returning_user_shows_localized_menu_and_clears_onboarding():
    from bot.handlers.start import start_command

    update = make_update(user_id=123)
    context = make_context("en")
    context.user_data["onboarding"] = True
    user_service = AsyncMock()
    user_service.get_user_by_telegram.return_value = Mock(id=1)
    user_service.get_or_create_user.return_value = Mock(language="en", phone_number="0912345678")

    with patch("bot.handlers.start.get_db_session") as db_factory:
        db_factory.return_value.__aiter__.return_value = [Mock()]
        with patch("bot.handlers.start.UserService", return_value=user_service):
            await start_command(update, context)

    update.message.reply_text.assert_awaited_once()
    assert "Welcome back" in update.message.reply_text.await_args.args[0]
    assert "onboarding" not in context.user_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action, module_path, function_name",
    [
        ("products", "bot.handlers.catalog", "menu_command"),
        ("search", "bot.handlers.search", "search_command"),
        ("cart", "bot.handlers.cart", "cart_command"),
        ("profile", "bot.handlers.profile", "profile_command"),
        ("orders", "bot.handlers.profile", "orders_command"),
        ("wishlist", "bot.handlers.wishlist", "wishlist_command"),
        ("feedback", "bot.handlers.feedback", "feedback_command"),
    ],
)
async def test_menu_callback_routes_actions(action, module_path, function_name):
    from bot.handlers.start import menu_callback

    update = make_update()
    query = Mock()
    query.data = f"menu_{action}"
    query.answer = AsyncMock()
    update.callback_query = query
    context = make_context()
    handler = AsyncMock()

    with patch(f"{module_path}.{function_name}", handler):
        await menu_callback(update, context)

    query.answer.assert_awaited_once()
    handler.assert_awaited_once_with(update, context)


@pytest.mark.asyncio
async def test_menu_callback_handles_help_back_unknown_and_unauthorized_admin():
    from bot.handlers.start import menu_callback

    update = make_update(user_id=123)
    query = Mock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update.callback_query = query
    context = make_context("en")

    for action in ("help", "back", "unknown"):
        query.data = f"menu_{action}"
        await menu_callback(update, context)
        query.edit_message_text.assert_awaited()

    query.data = "menu_admin"
    with patch("bot.handlers.start.settings", Mock(admin_ids_list=[])):
        await menu_callback(update, context)

    assert "ፈቃድ" in query.edit_message_text.await_args.args[0]


@pytest.mark.asyncio
async def test_noop_callback_acknowledges_query():
    from bot.handlers.start import noop_callback

    update = make_update()
    query = Mock()
    query.answer = AsyncMock()
    update.callback_query = query

    await noop_callback(update, Mock())

    query.answer.assert_awaited_once()
