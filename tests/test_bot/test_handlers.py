# ============================
# WOLLOYEWA STORE BOT - BOT HANDLER TESTS
# ============================
"""Tests for Telegram bot handlers."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from telegram import Update, User
from telegram.ext import ContextTypes

from core.config import Settings


def test_settings_web_app_url_uses_https_public_value():
    """Public Telegram Mini App URLs must stay HTTPS and keep a trailing slash."""
    cfg = Settings(
        WEB_APP_URL="https://store.example.com/app",
        ADMIN_IDS="100,200",
        POSTGRES_USER="postgres",
        POSTGRES_PASSWORD="pass",
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
        POSTGRES_DB="wolloyewa",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_DB=0,
    )

    assert cfg.web_app_url == "https://store.example.com/app/"
    assert cfg.admin_ids_list == [100, 200]


def test_settings_web_app_url_rejects_local_http_value():
    """Non-public HTTP URLs must not be used for Telegram WebApp buttons."""
    cfg = Settings(WEB_APP_URL="http://localhost:8080/app/")

    assert cfg.web_app_url == ""


def test_settings_web_app_url_supports_replit_domain_fallback():
    """Replit-hosted deployments should still resolve to the public HTTPS app URL."""
    cfg = Settings(REPLIT_DOMAINS="demo-store.replit.app", WEB_APP_URL=None)

    assert cfg.web_app_url.startswith("https://")
    assert cfg.web_app_url.endswith("/app/")


def test_settings_web_app_url_strips_whitespace_and_trailing_slash():
    """Trailing whitespace and repeated trailing slashes should be normalized."""
    cfg = Settings(WEB_APP_URL="  https://store.example.com/app///  ")

    assert cfg.web_app_url == "https://store.example.com/app/"


def test_settings_builds_database_and_redis_urls_from_parts():
    """Environment settings should generate proper DB and Redis connection strings when raw URLs are absent."""
    cfg = Settings(
        ENVIRONMENT="development",
        DATABASE_URL=None,
        REDIS_URL=None,
        POSTGRES_USER="demo",
        POSTGRES_PASSWORD="secret",
        POSTGRES_HOST="db",
        POSTGRES_PORT=5432,
        POSTGRES_DB="shop",
        REDIS_HOST="cache",
        REDIS_PORT=6379,
        REDIS_PASSWORD="redispass",
        REDIS_DB=2,
    )

    assert cfg.DATABASE_URL == "postgresql+asyncpg://demo:secret@db:5432/shop"
    assert cfg.REDIS_URL == "redis://:redispass@cache:6379/2"


@pytest.mark.unit
class TestStartHandler:
    """Tests for start command handler."""

    @pytest.mark.asyncio
    async def test_start_command_new_user(self):
        """Test start command for new user."""
        from bot.handlers.start import start_command

        # Create mock update
        mock_update = Mock(spec=Update)
        mock_user = User(id=123456789, first_name="Test", username="testuser", is_bot=False)
        mock_update.effective_user = mock_user
        mock_update.effective_chat = Mock(id=123456789)
        mock_update.message = Mock()

        # Create mock context
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)

        # Mock database
        with patch("bot.handlers.start.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aiter__.return_value = [mock_session]

            with patch("bot.handlers.start.UserService") as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_service.get_or_create_user.return_value = Mock(id=1)

                await start_command(mock_update, mock_context)

                # Verify message was sent
                mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_command(self):
        """Test help command."""
        from bot.handlers.start import help_command

        mock_update = Mock(spec=Update)
        mock_update.message = Mock()
        mock_context = Mock()

        await help_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()

    def test_store_button_falls_back_to_menu_for_local_http(self):
        """Telegram rejects plain HTTP button URLs, so local HTTP URLs must not be sent to the API."""
        from bot.handlers.start import _build_store_button

        with patch("bot.handlers.start.settings", Mock(web_app_url="http://localhost:8080/app/")):
            button = _build_store_button("Open Store")

        assert button.callback_data == "menu_products"
        assert button.url is None
        assert button.web_app is None

    def test_store_button_uses_telegram_webapp_for_https(self):
        """Production HTTPS deployments should use Telegram's WebApp flow."""
        from bot.handlers.start import _build_store_button

        with patch("bot.handlers.start.settings", Mock(web_app_url="https://example.com/app/")):
            button = _build_store_button("Open Store")

        assert button.web_app.url == "https://example.com/app/"
        assert button.url is None
        assert button.callback_data is None

    def test_build_main_menu_keeps_store_button_and_admin_row(self):
        """The menu should render a WebApp store button and include the admin action when requested."""
        from bot.handlers.start import _build_main_menu

        with patch("bot.handlers.start.settings", Mock(web_app_url="https://example.com/app/")):
            markup = _build_main_menu(is_admin=True, lang="en")

        first_button = markup.inline_keyboard[0][0]
        assert first_button.web_app.url == "https://example.com/app/"
        assert markup.inline_keyboard[-1][0].callback_data == "menu_admin"

    @pytest.mark.asyncio
    async def test_onboard_language_callback_saves_language_and_prompts_phone(self):
        """Language selection should store the user's choice and ask for phone sharing."""
        from bot.handlers.start import onboard_language_callback

        mock_update = Mock(spec=Update)
        mock_query = Mock()
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()
        mock_query.data = "onboard_lang_en"
        mock_update.callback_query = mock_query
        mock_update.effective_user = User(id=123, first_name="Test", username="tester", is_bot=False)
        mock_update.effective_message = Mock()
        mock_update.effective_message.reply_text = AsyncMock()
        mock_context = Mock()
        mock_context.user_data = {}

        with patch("bot.handlers.start.get_db_session") as mock_db:
            mock_db.return_value.__aiter__.return_value = [Mock()]

            with patch("bot.handlers.start.UserService") as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_service.get_user_by_telegram.return_value = Mock(id=7)
                mock_service.update_user = AsyncMock()

                await onboard_language_callback(mock_update, mock_context)

                mock_query.answer.assert_called_once()
                mock_query.edit_message_text.assert_called_once()
                mock_update.effective_message.reply_text.assert_called_once()
                assert mock_context.user_data["onboarding"] is True
                assert mock_context.user_data["onboarding_lang"] == "en"

    @pytest.mark.asyncio
    async def test_shop_command_builds_store_button(self):
        """The shop shortcut should render a valid Telegram WebApp button when the public URL is available."""
        from bot.handlers.start import shop_command

        mock_update = Mock(spec=Update)
        mock_update.message = Mock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = Mock()
        mock_context.user_data = {"user": {"language": "en"}}

        with patch("bot.handlers.start.settings", Mock(web_app_url="https://example.com/app/")):
            await shop_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_command_uses_language_fallback(self):
        """Fallback command handling should respect the user's language preference."""
        from bot.handlers.start import unknown_command

        mock_update = Mock(spec=Update)
        mock_update.message = Mock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = Mock()
        mock_context.user_data = {"user": {"language": "en"}}

        await unknown_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()


@pytest.mark.unit
class TestCatalogHandler:
    """Tests for catalog handlers."""

    @pytest.mark.asyncio
    async def test_menu_command(self):
        """Test menu command."""
        from bot.handlers.catalog import menu_command

        mock_update = Mock(spec=Update)
        mock_update.message = Mock()
        mock_context = Mock()

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

        mock_update = Mock(spec=Update)
        mock_query = Mock()
        mock_query.data = "cat_1"
        mock_update.callback_query = mock_query
        mock_context = Mock()

        with patch("bot.handlers.catalog.show_category_products") as mock_show:
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

        mock_update = Mock(spec=Update)
        mock_update.effective_user = Mock(id=123456789)
        mock_update.message = Mock()
        mock_context = Mock()

        with patch("bot.handlers.cart.get_user_cart", return_value=[]):
            await cart_command(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_to_cart(self):
        """Test adding product to cart."""
        from bot.handlers.cart import add_to_cart

        with patch("bot.handlers.cart.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.get.return_value = None

            await add_to_cart(123456789, 1, Mock())

            mock_redis_instance.setex.assert_called_once()


@pytest.mark.unit
class TestProfileHandler:
    """Tests for profile handlers."""

    @pytest.mark.asyncio
    async def test_profile_command(self):
        """Test profile command."""
        from bot.handlers.profile import profile_command

        mock_update = Mock(spec=Update)
        mock_update.effective_user = Mock(id=123456789)
        mock_update.message = Mock()
        mock_context = Mock()

        with patch("bot.handlers.profile.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aiter__.return_value = [mock_session]

            with patch("bot.handlers.profile.UserService") as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_user = Mock(id=1, full_name="Test User", username="testuser")
                mock_service.get_user_by_telegram.return_value = mock_user
                mock_service.get_user_stats.return_value = {"total_orders": 0, "total_spent": 0}

                await profile_command(mock_update, mock_context)

                mock_update.message.reply_text.assert_called_once()


@pytest.mark.unit
class TestSearchHandler:
    """Tests for search handlers."""

    @pytest.mark.asyncio
    async def test_search_command(self):
        """Test search command."""
        from bot.handlers.search import search_command

        mock_update = Mock(spec=Update)
        mock_update.message = Mock()
        mock_context = Mock()

        await search_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()


@pytest.mark.unit
class TestWishlistHandler:
    """Tests for wishlist handlers."""

    @pytest.mark.asyncio
    async def test_wishlist_command_empty(self):
        """Test wishlist command when empty."""
        from bot.handlers.wishlist import wishlist_command

        mock_update = Mock(spec=Update)
        mock_update.effective_user = Mock(id=123456789)
        mock_update.message = Mock()
        mock_context = Mock()

        with patch("bot.handlers.wishlist.get_user_wishlist", return_value=[]):
            await wishlist_command(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()


@pytest.mark.unit
class TestFeedbackHandler:
    """Tests for feedback handlers."""

    @pytest.mark.asyncio
    async def test_feedback_command(self):
        """Test feedback command."""
        from bot.handlers.feedback import feedback_command

        mock_update = Mock(spec=Update)
        mock_update.message = Mock()
        mock_context = Mock()

        await feedback_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()


@pytest.mark.unit
class TestLocationHandler:
    """Tests for location handlers."""

    @pytest.mark.asyncio
    async def test_location_command(self):
        """Test location command."""
        from bot.handlers.location import location_command

        mock_update = Mock(spec=Update)
        mock_update.message = Mock()
        mock_context = Mock()

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
