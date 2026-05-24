# ============================
# WOLLOYEWA STORE BOT - BOT HANDLER TESTS
# ============================
"""Tests for Telegram bot handlers."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes


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
        with patch('bot.handlers.start.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aiter__.return_value = [mock_session]
            
            with patch('bot.handlers.start.UserService') as mock_user_service:
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
        
        with patch('bot.handlers.catalog.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aiter__.return_value = [mock_session]
            
            with patch('bot.handlers.catalog.CategoryService') as mock_cat_service:
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
        
        with patch('bot.handlers.catalog.show_category_products') as mock_show:
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
        
        with patch('bot.handlers.cart.get_user_cart', return_value=[]):
            await cart_command(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_to_cart(self):
        """Test adding product to cart."""
        from bot.handlers.cart import add_to_cart
        
        with patch('bot.handlers.cart.get_redis_client') as mock_redis:
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
        
        with patch('bot.handlers.profile.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aiter__.return_value = [mock_session]
            
            with patch('bot.handlers.profile.UserService') as mock_user_service:
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
        
        with patch('bot.handlers.wishlist.get_user_wishlist', return_value=[]):
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
    "TestStartHandler",
    "TestCatalogHandler",
    "TestCartHandler",
    "TestProfileHandler",
    "TestSearchHandler",
    "TestWishlistHandler",
    "TestFeedbackHandler",
    "TestLocationHandler",
]