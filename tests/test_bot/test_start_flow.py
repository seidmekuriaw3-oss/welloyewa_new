"""Focused tests for Telegram start, onboarding, and menu routing."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from telegram import Update, User
from telegram.error import NetworkError


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
    update.effective_chat = Mock(id=user_id)
    update.callback_query = None
    return update


def make_context(language="en"):
    context = Mock()
    context.user_data = {"user": {"language": language}}
    context.bot_data = {}
    context.bot.get_me = AsyncMock(return_value=Mock(id=999))
    context.bot.get_user_profile_photos = AsyncMock(
        return_value=Mock(
            total_count=1,
            photos=[[Mock(file_id="bot-profile-photo")]],
        )
    )
    context.bot.send_photo = AsyncMock()
    return context


def test_keyboard_builders_cover_languages_and_admin_state():
    from bot.handlers.start import _build_language_keyboard, _build_main_menu, _build_phone_keyboard

    language_keyboard = _build_language_keyboard()
    assert [
        language_keyboard.inline_keyboard[index][0].callback_data
        for index in range(3)
    ] == [
        "onboard_lang_am",
        "onboard_lang_en",
        "onboard_lang_om",
    ]
    start_actions = [
        button
        for row in language_keyboard.inline_keyboard[3:]
        for button in row
    ]
    assert [button.callback_data for button in start_actions if button.callback_data] == [
        "menu_products",
        "menu_back",
    ]

    phone_keyboard = _build_phone_keyboard("en")
    assert phone_keyboard.keyboard[0][0].request_contact is True

    regular = _build_main_menu(is_admin=False, lang="unknown")
    admin = _build_main_menu(is_admin=True, lang="om")
    assert len(regular.inline_keyboard) == 5
    assert admin.inline_keyboard[-1][0].callback_data == "menu_admin"


def test_start_keyboard_uses_web_app_button_when_public_url_is_configured():
    from bot.handlers.start import _build_language_keyboard

    with patch("bot.handlers.start.settings") as settings:
        settings.web_app_url = "https://store.example/app/"
        keyboard = _build_language_keyboard()

    store_button = keyboard.inline_keyboard[3][1]
    assert store_button.web_app.url == "https://store.example/app/"
    assert store_button.callback_data is None


@pytest.mark.asyncio
async def test_start_new_user_shows_language_selection():
    from bot.handlers.start import start_command

    update = make_update()
    context = make_context()
    context.user_data = {}
    user_service = AsyncMock()
    user_service.get_user_by_telegram.return_value = None
    user_service.get_or_create_user.return_value = Mock(id=1)

    with patch("bot.handlers.start.transaction_session") as session_factory:
        session_factory.return_value.__aenter__.return_value = Mock()
        with patch("bot.handlers.start.UserService", return_value=user_service):
            await start_command(update, context)

    context.bot.send_photo.assert_awaited_once()
    assert context.bot.send_photo.await_args.kwargs["photo"] == "bot-profile-photo"
    assert "keep track of your orders" in context.bot.send_photo.await_args.kwargs["caption"]
    assert len(context.bot.send_photo.await_args.kwargs["caption"]) <= 1024
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

    with patch("bot.handlers.start.transaction_session") as session_factory:
        session_factory.return_value.__aenter__.return_value = Mock()
        with patch("bot.handlers.start.UserService", return_value=user_service):
            await start_command(update, context)

    context.bot.send_photo.assert_awaited_once()
    assert "Welcome back" in context.bot.send_photo.await_args.kwargs["caption"]
    assert "onboarding" not in context.user_data


@pytest.mark.asyncio
async def test_start_falls_back_to_text_when_profile_photo_cannot_be_sent():
    from bot.handlers.start import _send_start_welcome

    update = make_update()
    context = make_context()
    context.bot.send_photo.side_effect = NetworkError("temporary Telegram failure")

    await _send_start_welcome(update, context, "Welcome", Mock())

    update.message.reply_text.assert_awaited_once()
    assert update.message.reply_text.await_args.kwargs["parse_mode"] == "Markdown"
    assert "start_profile_photo_file_id" not in context.bot_data


@pytest.mark.asyncio
async def test_start_uses_text_when_bot_has_no_profile_photo():
    from bot.handlers.start import _send_start_welcome

    update = make_update()
    context = make_context()
    context.bot.get_user_profile_photos.return_value = Mock(total_count=0, photos=[])

    await _send_start_welcome(update, context, "Welcome", Mock())

    update.message.reply_text.assert_awaited_once()
    context.bot.send_photo.assert_not_awaited()


@pytest.mark.asyncio
async def test_language_selection_updates_photo_caption_and_continues_onboarding():
    from bot.handlers.start import onboard_language_callback

    update = make_update()
    message = Mock(photo=[Mock()])
    message.reply_text = AsyncMock()
    query = Mock(data="onboard_lang_en", message=message)
    query.answer = AsyncMock()
    query.edit_message_caption = AsyncMock()
    query.edit_message_text = AsyncMock()
    update.callback_query = query
    update.effective_message = message
    context = make_context()
    user_service = AsyncMock()
    user_service.get_user_by_telegram.return_value = Mock(id=1)

    with patch("bot.handlers.start.transaction_session") as session_factory:
        session_factory.return_value.__aenter__.return_value = Mock()
        with patch("bot.handlers.start.UserService", return_value=user_service):
            await onboard_language_callback(update, context)

    query.edit_message_caption.assert_awaited_once()
    assert query.edit_message_caption.await_args.kwargs[
        "reply_markup"
    ].to_dict() == {"inline_keyboard": []}
    query.edit_message_text.assert_not_awaited()
    message.reply_text.assert_awaited_once()
    phone_keyboard = message.reply_text.await_args.kwargs["reply_markup"]
    assert phone_keyboard.keyboard[0][0].request_contact is True
    assert context.user_data["language"] == "en"


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
async def test_menu_callback_ignores_expired_query():
    from telegram.error import BadRequest

    from bot.handlers.start import menu_callback

    update = make_update(user_id=123)
    query = Mock()
    query.id = "expired-query"
    query.data = "menu_help"
    query.answer = AsyncMock(
        side_effect=BadRequest(
            "Query is too old and response timeout expired or query id is invalid"
        )
    )
    update.callback_query = query
    context = make_context("en")

    await menu_callback(update, context)

    query.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_noop_callback_acknowledges_query():
    from bot.handlers.start import noop_callback

    update = make_update()
    query = Mock()
    query.answer = AsyncMock()
    update.callback_query = query

    await noop_callback(update, Mock())

    query.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_to_menu_clears_checkout_and_search_state():
    from telegram.ext import ConversationHandler

    from bot.handlers.conversation_navigation import cancel_to_menu

    update = make_update()
    context = make_context("en")
    context.user_data.update(
        {
            "checkout_in_progress": True,
            "checkout_address_id": 10,
            "search_query": "laptop",
            "feedback_rating": 5,
            "cart": [{"product_id": 1, "quantity": 2}],
        }
    )

    result = await cancel_to_menu(update, context)

    assert result == ConversationHandler.END
    assert "checkout_in_progress" not in context.user_data
    assert "search_query" not in context.user_data
    assert "feedback_rating" not in context.user_data
    assert context.user_data["cart"] == [{"product_id": 1, "quantity": 2}]
    assert update.message.reply_text.await_args.kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_expired_callback_answer_is_ignored():
    from telegram.error import BadRequest

    from bot.handlers.callback_utils import answer_callback_query

    query = Mock(id="expired")
    query.answer = AsyncMock(
        side_effect=BadRequest("Query is too old and response timeout expired")
    )

    assert await answer_callback_query(query) is False
    query.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_edit_ignores_unchanged_message():
    from telegram.error import BadRequest

    from bot.handlers.callback_utils import edit_callback_message

    query = Mock(id="unchanged")
    query.edit_message_text = AsyncMock(
        side_effect=BadRequest("Message is not modified")
    )

    assert await edit_callback_message(query, "same") is False


@pytest.mark.asyncio
async def test_feedback_command_enters_rating_state():
    from bot.handlers.feedback import WAITING_RATING, feedback_command

    update = make_update()
    context = make_context("en")

    result = await feedback_command(update, context)

    assert result == WAITING_RATING
    assert update.message.reply_text.await_count == 2
