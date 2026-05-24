# ============================
# WOLLOYEWA STORE BOT - MIDDLEWARE TESTS
# ============================
"""Tests for bot middleware components."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from telegram import Update, User


@pytest.mark.unit
class TestAuthMiddleware:
    """Tests for authentication middleware."""
    
    @pytest.mark.asyncio
    async def test_auth_middleware_existing_user(self):
        """Test auth middleware with existing user."""
        from bot.middlewares.auth import auth_middleware
        
        mock_update = Mock(spec=Update)
        mock_user = User(id=123456789, first_name="Test", username="testuser", is_bot=False)
        mock_update.effective_user = mock_user
        mock_context = Mock()
        mock_context.user_data = {}
        
        next_handler = AsyncMock()
        
        with patch('bot.middlewares.auth.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aiter__.return_value = [mock_session]
            
            with patch('bot.middlewares.auth.UserService') as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_service.get_or_create_user.return_value = Mock(id=1, role="customer")
                
                await auth_middleware(mock_update, mock_context, next_handler)
                
                assert "user_id" in mock_context.user_data
                assert "user_role" in mock_context.user_data
                next_handler.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_auth_middleware_no_user(self):
        """Test auth middleware with no user."""
        from bot.middlewares.auth import auth_middleware
        
        mock_update = Mock(spec=Update)
        mock_update.effective_user = None
        mock_context = Mock()
        next_handler = AsyncMock()
        
        await auth_middleware(mock_update, mock_context, next_handler)
        
        # Should still call next handler
        next_handler.assert_called_once()


@pytest.mark.unit
class TestThrottlingMiddleware:
    """Tests for throttling middleware."""
    
    @pytest.mark.asyncio
    async def test_throttling_normal_request(self):
        """Test throttling with normal request frequency."""
        from bot.middlewares.throttling import throttling_middleware
        
        mock_update = Mock(spec=Update)
        mock_user = User(id=123456789, first_name="Test", is_bot=False)
        mock_update.effective_user = mock_user
        mock_update.message = Mock()
        mock_update.message.text = "/start"
        mock_context = Mock()
        next_handler = AsyncMock()
        
        await throttling_middleware(mock_update, mock_context, next_handler)
        
        next_handler.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_throttling_exceeded_limit(self):
        """Test throttling when rate limit exceeded."""
        from bot.middlewares.throttling import throttling_middleware
        
        mock_update = Mock(spec=Update)
        mock_user = User(id=123456789, first_name="Test", is_bot=False)
        mock_update.effective_user = mock_user
        mock_update.message = Mock()
        mock_update.message.text = "/search"
        mock_context = Mock()
        next_handler = AsyncMock()
        
        # Mock the check_rate_limit to return False
        with patch.object(throttling_middleware, 'check_rate_limit', return_value=(False, 30)):
            await throttling_middleware(mock_update, mock_context, next_handler)
            
            # Should reply with rate limit message
            mock_update.message.reply_text.assert_called_once()
            next_handler.assert_not_called()
    
    def test_check_rate_limit(self):
        """Test rate limit checking logic."""
        from bot.middlewares.throttling import throttling_middleware
        
        user_id = 123456789
        # Clear user requests
        throttling_middleware._user_requests.clear()
        
        is_allowed, _ = throttling_middleware.check_rate_limit(user_id)
        
        assert is_allowed is True


@pytest.mark.unit
class TestLoggingMiddleware:
    """Tests for logging middleware."""
    
    @pytest.mark.asyncio
    async def test_logging_middleware(self):
        """Test logging middleware."""
        from bot.middlewares.logging import logging_middleware
        
        mock_update = Mock(spec=Update)
        mock_update.update_id = 1
        mock_user = User(id=123456789, first_name="Test", is_bot=False)
        mock_update.effective_user = mock_user
        mock_update.message = Mock()
        mock_update.message.text = "/start"
        mock_context = Mock()
        next_handler = AsyncMock()
        
        await logging_middleware(mock_update, mock_context, next_handler)
        
        next_handler.assert_called_once()


@pytest.mark.unit
class TestI18nMiddleware:
    """Tests for internationalization middleware."""
    
    @pytest.mark.asyncio
    async def test_i18n_middleware(self):
        """Test i18n middleware."""
        from bot.middlewares.i18n import i18n_middleware
        
        mock_update = Mock(spec=Update)
        mock_user = User(id=123456789, first_name="Test", is_bot=False)
        mock_update.effective_user = mock_user
        mock_context = Mock()
        mock_context.user_data = {}
        next_handler = AsyncMock()
        
        with patch('bot.middlewares.i18n.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aiter__.return_value = [mock_session]
            
            with patch('bot.middlewares.i18n.UserService') as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_user = Mock(language="am")
                mock_service.get_user_by_telegram.return_value = mock_user
                
                await i18n_middleware(mock_update, mock_context, next_handler)
                
                assert "language" in mock_context.user_data
                assert "t" in mock_context.user_data
                next_handler.assert_called_once()
    
    def test_get_translator(self):
        """Test translator function."""
        from bot.middlewares.i18n import I18nMiddleware
        
        middleware = I18nMiddleware()
        translator = middleware.get_translator("am")
        
        assert translator is not None
        assert callable(translator)
        
        # Test translation
        result = translator("welcome")
        assert result is not None


@pytest.mark.unit
class TestRoleCheckMiddleware:
    """Tests for role check middleware."""
    
    @pytest.mark.asyncio
    async def test_admin_only_decorator_admin(self):
        """Test admin_only decorator with admin user."""
        from bot.middlewares.role_check import admin_only
        
        mock_update = Mock(spec=Update)
        mock_user = User(id=5848843259, first_name="Admin", is_bot=False)
        mock_update.effective_user = mock_user
        mock_context = Mock()
        
        @admin_only
        async def test_handler(update, context):
            return "allowed"
        
        with patch('bot.middlewares.role_check.settings') as mock_settings:
            mock_settings.admin_ids_list = [5848843259]
            
            result = await test_handler(mock_update, mock_context)
            assert result == "allowed"
    
    @pytest.mark.asyncio
    async def test_admin_only_decorator_non_admin(self):
        """Test admin_only decorator with non-admin user."""
        from bot.middlewares.role_check import admin_only
        
        mock_update = Mock(spec=Update)
        mock_user = User(id=123456789, first_name="User", is_bot=False)
        mock_update.effective_user = mock_user
        mock_update.message = Mock()
        mock_context = Mock()
        
        @admin_only
        async def test_handler(update, context):
            return "allowed"
        
        with patch('bot.middlewares.role_check.settings') as mock_settings:
            mock_settings.admin_ids_list = [5848843259]
            
            await test_handler(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_vendor_only_decorator_vendor(self):
        """Test vendor_only decorator with vendor user."""
        from bot.middlewares.role_check import vendor_only
        
        mock_update = Mock(spec=Update)
        mock_user = User(id=123456789, first_name="Vendor", is_bot=False)
        mock_update.effective_user = mock_user
        mock_context = Mock()
        mock_context.user_data = {"user_role": "vendor"}
        
        @vendor_only
        async def test_handler(update, context):
            return "allowed"
        
        result = await test_handler(mock_update, mock_context)
        assert result == "allowed"


__all__ = [
    "TestAuthMiddleware",
    "TestThrottlingMiddleware",
    "TestLoggingMiddleware",
    "TestI18nMiddleware",
    "TestRoleCheckMiddleware",
]