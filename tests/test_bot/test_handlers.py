# ============================
# WOLLOYEWA STORE BOT - BOT HANDLER TESTS
# ============================
"""Tests for Telegram bot handlers."""

from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from types import SimpleNamespace

import pytest
from telegram import User


def _message(text=None):
    message = Mock()
    message.text = text
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()
    return message


def _update(user=None, text=None):
    message = _message(text)
    return SimpleNamespace(
        effective_user=user,
        effective_chat=SimpleNamespace(id=getattr(user, "id", 123456789)),
        effective_message=message,
        message=message,
        callback_query=None,
    )


def _context():
    bot = Mock()
    bot.get_me = AsyncMock(return_value=Mock(id=999))
    bot.get_user_profile_photos = AsyncMock(
        return_value=SimpleNamespace(
            total_count=0,
            photos=[],
        )
    )
    bot.send_photo = AsyncMock()
    return SimpleNamespace(user_data={}, bot_data={}, args=[], bot=bot)


@pytest.mark.unit
class TestStartHandler:
    """Tests for start command handler."""

    @pytest.mark.asyncio
    async def test_start_command_new_user(self):
        """Test start command for new user."""
        from bot.handlers.start import start_command

        # Create mock update
        mock_user = User(id=123456789, first_name="Test", username="testuser", is_bot=False)
        mock_update = _update(mock_user, "/start")

        # Create mock context
        mock_context = _context()
        mock_context.bot.get_user_profile_photos.return_value = SimpleNamespace(
            total_count=1,
            photos=[[SimpleNamespace(file_id="bot-profile-photo")]],
        )

        # Mock database
        with patch("bot.handlers.start.transaction_session") as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()
            with patch("bot.handlers.start.UserService") as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_service.get_user_by_telegram.return_value = None
                mock_service.get_or_create_user.return_value = Mock(id=1)

                await start_command(mock_update, mock_context)

                mock_context.bot.send_photo.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_help_command(self):
        """Test help command."""
        from bot.handlers.start import help_command

        mock_update = _update(text="/help")
        mock_context = _context()

        await help_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()


@pytest.mark.unit
class TestCatalogHandler:
    """Tests for catalog handlers."""

    @pytest.mark.asyncio
    async def test_menu_command(self):
        """Test menu command."""
        from bot.handlers.catalog import menu_command

        mock_update = _update(text="/menu")
        mock_context = _context()

        with patch("bot.handlers.catalog.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aiter__.return_value = [mock_session]

            with patch("bot.handlers.catalog.CategoryService") as mock_cat_service:
                mock_service = AsyncMock()
                mock_cat_service.return_value = mock_service
                mock_service.get_all_categories.return_value = []

                await menu_command(mock_update, mock_context)

                mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_category_callback(self):
        """Test category selection callback."""
        from bot.handlers.catalog import category_callback

        mock_update = _update()
        mock_query = SimpleNamespace(
            answer=AsyncMock(),
            message=_message(),
            data="cat_1",
        )
        mock_update.callback_query = mock_query
        mock_context = _context()

        with patch(
            "bot.handlers.catalog.show_category_products", new_callable=AsyncMock
        ) as mock_show:
            await category_callback(mock_update, mock_context)

            mock_query.answer.assert_called_once()
            mock_show.assert_called_once()


@pytest.mark.unit
class TestCartHandler:
    """Tests for cart handlers."""

    @pytest.mark.asyncio
    async def test_cart_command_empty(self):
        """Test cart command when cart is empty."""
        from bot.handlers.cart import cart_command

        mock_update = _update(SimpleNamespace(id=123456789), "/cart")
        mock_context = _context()

        with patch("bot.handlers.cart.get_user_cart", return_value=[]):
            await cart_command(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_to_cart(self):
        """Test adding product to cart."""
        from bot.handlers.cart import add_to_cart

        context = _context()
        await add_to_cart(123456789, 1, context)

        assert context.user_data["cart"] == [{"product_id": 1, "quantity": 1}]


@pytest.mark.unit
class TestProfileHandler:
    """Tests for profile handlers."""

    @pytest.mark.asyncio
    async def test_profile_command(self):
        """Test profile command."""
        from bot.handlers.profile import profile_command

        mock_update = _update(SimpleNamespace(id=123456789), "/profile")
        mock_context = _context()
        mock_context.user_data["language"] = "en"

        with patch("bot.handlers.profile.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aiter__.return_value = [mock_session]

            with patch("bot.handlers.profile.UserService") as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_user = SimpleNamespace(
                    id=1,
                    full_name="Test User",
                    first_name="Test",
                    username="testuser",
                    phone_number=None,
                    email=None,
                    role="customer",
                    created_at=datetime.utcnow(),
                )
                mock_service.get_user_by_telegram.return_value = mock_user
                mock_service.get_user_stats.return_value = {"total_orders": 0, "total_spent": 0}

                await profile_command(mock_update, mock_context)

                mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_profile_language_picker_edits_caption_for_photo_message(self):
        from bot.handlers.profile import profile_callback

        message = SimpleNamespace(
            photo=[object()],
            document=None,
            reply_text=AsyncMock(),
        )
        query = SimpleNamespace(
            data="profile_change_language",
            message=message,
            answer=AsyncMock(),
            edit_message_caption=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
        context = SimpleNamespace(user_data={"language": "en"})

        await profile_callback(update, context)

        query.answer.assert_awaited_once()
        query.edit_message_caption.assert_awaited_once()
        query.edit_message_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_profile_command_renders_missing_fields_and_saved_address(self):
        from bot.handlers.profile import profile_command

        mock_update = _update(SimpleNamespace(id=123456789), "/profile")
        mock_context = _context()
        mock_context.user_data["language"] = "en"
        address = SimpleNamespace(
            is_default=True,
            address_line1="Bole",
            address_line2=None,
            subcity="Bole",
            city="Addis Ababa",
            woreda=None,
            house_number="12",
        )
        mock_user = SimpleNamespace(
            id=1,
            full_name=None,
            first_name=None,
            username=None,
            phone_number=None,
            email=None,
            role=None,
            created_at=None,
            addresses=[address],
        )

        with patch("bot.handlers.profile.get_db_session") as mock_db:
            mock_db.return_value.__aiter__.return_value = [AsyncMock()]
            with patch("bot.handlers.profile.UserService") as user_service:
                service = AsyncMock()
                user_service.return_value = service
                service.get_user_by_telegram.return_value = mock_user
                service.get_user_stats.return_value = {
                    "total_orders": None,
                    "total_spent": None,
                    "average_order_value": None,
                }

                await profile_command(mock_update, mock_context)

        text = mock_update.message.reply_text.await_args.args[0]
        assert "Not set" in text
        assert "Bole, Bole, Addis Ababa, 12" in text
        assert "None" not in text

    @pytest.mark.asyncio
    async def test_profile_command_reports_database_error(self):
        from sqlalchemy.exc import OperationalError

        from bot.handlers.profile import profile_command

        mock_update = _update(SimpleNamespace(id=123456789), "/profile")
        mock_context = _context()
        mock_context.user_data["language"] = "en"

        async def broken_session():
            raise OperationalError("select profile", {}, RuntimeError("database unavailable"))
            yield

        with patch("bot.handlers.profile.get_db_session", broken_session):
            await profile_command(mock_update, mock_context)

        assert "could not load your profile" in (
            mock_update.message.reply_text.await_args.args[0].lower()
        )

    @pytest.mark.asyncio
    async def test_profile_command_uses_user_telegram_photo_and_banner_fallback(self):
        from bot.handlers.profile import profile_command

        user = SimpleNamespace(
            id=1,
            full_name="Test User",
            first_name="Test",
            username="tester",
            phone_number=None,
            email=None,
            role="customer",
            created_at=datetime.utcnow(),
            addresses=[],
            profile_picture=None,
        )
        update = _update(SimpleNamespace(id=123456789), "/profile")
        context = _context()
        context.bot.get_user_profile_photos = AsyncMock(
            side_effect=[
                SimpleNamespace(
                    total_count=1,
                    photos=[[SimpleNamespace(file_id="telegram-user-photo")]],
                ),
                SimpleNamespace(
                    total_count=1,
                    photos=[[SimpleNamespace(file_id="store-banner-photo")]],
                ),
            ]
        )
        context.bot.get_me = AsyncMock(return_value=SimpleNamespace(id=999))

        with patch("bot.handlers.profile.get_db_session") as get_session:
            get_session.return_value.__aiter__.return_value = [AsyncMock()]
            with patch("bot.handlers.profile.UserService") as service_factory:
                service = AsyncMock()
                service_factory.return_value = service
                service.get_user_by_telegram.return_value = user
                service.get_user_stats.return_value = {}

                await profile_command(update, context)

        context.bot.send_photo.assert_awaited_once()
        assert context.bot.send_photo.await_args.kwargs["photo"] == "telegram-user-photo"
        assert context.bot.send_photo.await_args.kwargs["caption"]
        assert context.bot.send_photo.await_args.kwargs["reply_markup"]

    @pytest.mark.asyncio
    async def test_profile_photo_send_retries_banner_after_telegram_network_error(self):
        from telegram.error import NetworkError

        from bot.handlers.profile import _show_profile_card

        update = _update(SimpleNamespace(id=123456789))
        context = _context()
        context.bot.send_photo.side_effect = [
            NetworkError("temporary Telegram network error"),
            Mock(),
        ]
        keyboard = Mock()

        await _show_profile_card(
            update,
            context,
            "Profile details",
            keyboard,
            ["telegram-user-photo", "store-banner-photo"],
        )

        assert context.bot.send_photo.await_count == 2
        assert context.bot.send_photo.await_args_list[0].kwargs["photo"] == "telegram-user-photo"
        assert context.bot.send_photo.await_args_list[1].kwargs["photo"] == "store-banner-photo"

    @pytest.mark.asyncio
    async def test_profile_photo_edit_ignores_message_not_modified(self):
        from telegram.error import BadRequest

        from bot.handlers.profile import _show_profile_card

        query = SimpleNamespace(
            message=SimpleNamespace(photo=[object()], document=None),
            edit_message_media=AsyncMock(
                side_effect=BadRequest("Message is not modified")
            ),
            edit_message_caption=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query)

        await _show_profile_card(update, _context(), "Profile", Mock(), ["same-photo"])

        query.edit_message_media.assert_awaited_once()
        query.edit_message_caption.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_profile_photo_upload_stores_telegram_file_id(self):
        from bot.handlers.profile import profile_photo_handler

        message = SimpleNamespace(
            photo=[
                SimpleNamespace(file_id="small-photo", file_size=100),
                SimpleNamespace(file_id="large-photo", file_size=1000),
            ],
            reply_text=AsyncMock(),
        )
        update = SimpleNamespace(
            effective_message=message,
            effective_user=SimpleNamespace(id=123),
            callback_query=None,
        )
        context = _context()
        context.user_data["updating_field"] = "profile_picture"

        with patch("bot.handlers.profile._save_profile_update", new=AsyncMock(return_value=True)) as save:
            with patch("bot.handlers.profile.profile_command", new=AsyncMock()) as show_profile:
                await profile_photo_handler(update, context)

        assert save.await_args.args[1].profile_picture == "large-photo"
        assert "updating_field" not in context.user_data
        show_profile.assert_awaited_once_with(update, context)


@pytest.mark.unit
class TestSearchHandler:
    """Tests for search handlers."""

    @pytest.mark.asyncio
    async def test_search_command(self):
        """Test search command."""
        from bot.handlers.search import search_command

        mock_update = _update(text="/search")
        mock_context = _context()

        await search_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()


@pytest.mark.unit
class TestWishlistHandler:
    """Tests for wishlist handlers."""

    @pytest.mark.asyncio
    async def test_wishlist_command_empty(self):
        """Test wishlist command when empty."""
        from bot.handlers.wishlist import wishlist_command

        mock_update = _update(SimpleNamespace(id=123456789), "/wishlist")
        mock_context = _context()

        await wishlist_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()


@pytest.mark.unit
class TestFeedbackHandler:
    """Tests for feedback handlers."""

    @pytest.mark.asyncio
    async def test_feedback_command(self):
        """Test feedback command."""
        from bot.handlers.feedback import feedback_command

        mock_update = _update(text="/feedback")
        mock_context = _context()

        await feedback_command(mock_update, mock_context)

        assert mock_update.message.reply_text.await_count == 2


@pytest.mark.unit
class TestLocationHandler:
    """Tests for location handlers."""

    @pytest.mark.asyncio
    async def test_location_command(self):
        """Test location command."""
        from bot.handlers.location import location_command

        mock_update = _update(text="/location")
        mock_context = _context()

        await location_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()


__all__ = [
    "TestCartHandler",
    "TestCatalogHandler",
    "TestFeedbackHandler",
    "TestLocationHandler",
    "TestProfileHandler",
    "TestSearchHandler",
    "TestStartHandler",
    "TestWishlistHandler",
]
