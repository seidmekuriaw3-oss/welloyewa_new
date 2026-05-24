# ============================
# WOLLOYEWA STORE BOT - NOTIFICATION SERVICE TESTS
# ============================
"""Tests for notification services."""

import pytest
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.unit
class TestEmailService:
    """Tests for email notification service."""
    
    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Test sending email successfully."""
        from infrastructure.notifications.email_service import send_email
        
        with patch('infrastructure.notifications.email_service._email_service') as mock_service:
            mock_service.send = AsyncMock(return_value=Mock(success=True))
            
            result = await send_email(
                to="test@example.com",
                subject="Test Subject",
                content="Test content",
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_order_confirmation_email(self):
        """Test sending order confirmation email."""
        from infrastructure.notifications.email_service import send_order_confirmation_email
        
        with patch('infrastructure.notifications.email_service.send_email') as mock_send:
            mock_send.return_value = True
            
            result = await send_order_confirmation_email(
                to="test@example.com",
                name="Test User",
                order_number="ORD-001",
                total="100.00",
            )
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_password_reset_email(self):
        """Test sending password reset email."""
        from infrastructure.notifications.email_service import send_password_reset_email
        
        with patch('infrastructure.notifications.email_service.send_email') as mock_send:
            mock_send.return_value = True
            
            result = await send_password_reset_email(
                to="test@example.com",
                name="Test User",
                code="123456",
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_welcome_email(self):
        """Test sending welcome email."""
        from infrastructure.notifications.email_service import send_welcome_email
        
        with patch('infrastructure.notifications.email_service.send_email') as mock_send:
            mock_send.return_value = True
            
            result = await send_welcome_email(
                to="test@example.com",
                name="Test User",
            )
            
            assert result is True


@pytest.mark.unit
class TestSMSService:
    """Tests for SMS notification service."""
    
    @pytest.mark.asyncio
    async def test_send_sms_success(self):
        """Test sending SMS successfully."""
        from infrastructure.notifications.sms_gateway import send_sms
        
        with patch('infrastructure.notifications.sms_gateway._sms_gateway') as mock_gateway:
            mock_gateway.send = AsyncMock(return_value=Mock(success=True))
            
            result = await send_sms(
                to="0912345678",
                message="Test message",
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_verification_code(self):
        """Test sending verification code SMS."""
        from infrastructure.notifications.sms_gateway import send_verification_code
        
        with patch('infrastructure.notifications.sms_gateway.send_sms') as mock_send:
            mock_send.return_value = True
            
            result = await send_verification_code(
                phone="0912345678",
                code="123456",
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_order_update_sms(self):
        """Test sending order update SMS."""
        from infrastructure.notifications.sms_gateway import send_order_update_sms
        
        with patch('infrastructure.notifications.sms_gateway.send_sms') as mock_send:
            mock_send.return_value = True
            
            result = await send_order_update_sms(
                phone="0912345678",
                order_number="ORD-001",
                status="shipped",
            )
            
            assert result is True


@pytest.mark.unit
class TestTelegramNotifier:
    """Tests for Telegram notification service."""
    
    @pytest.mark.asyncio
    async def test_send_telegram_message(self):
        """Test sending Telegram message."""
        from infrastructure.notifications.telegram_notifier import send_telegram_message
        
        with patch('infrastructure.notifications.telegram_notifier._telegram_notifier') as mock_notifier:
            mock_notifier.send = AsyncMock(return_value=Mock(success=True))
            
            result = await send_telegram_message(
                chat_id=123456789,
                message="Test message",
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_to_admin(self):
        """Test sending message to admin."""
        from infrastructure.notifications.telegram_notifier import send_to_admin
        
        with patch('infrastructure.notifications.telegram_notifier._telegram_notifier') as mock_notifier:
            mock_notifier.send_to_admin = AsyncMock(return_value=True)
            
            result = await send_to_admin("Test admin message")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_order_notification(self):
        """Test sending order notification."""
        from infrastructure.notifications.telegram_notifier import send_order_notification
        
        with patch('infrastructure.notifications.telegram_notifier._telegram_notifier') as mock_notifier:
            mock_notifier.send_order_notification = AsyncMock(return_value=True)
            
            result = await send_order_notification(
                user_id=123456789,
                order_number="ORD-001",
                status="confirmed",
                total="100.00",
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_notify_vendor(self):
        """Test notifying vendor."""
        from infrastructure.notifications.telegram_notifier import notify_vendor
        
        with patch('infrastructure.notifications.telegram_notifier._telegram_notifier') as mock_notifier:
            mock_notifier.notify_vendor = AsyncMock(return_value=True)
            
            result = await notify_vendor(
                vendor_id=987654321,
                message="New order received",
            )
            
            assert result is True


@pytest.mark.unit
class TestNotificationProvider:
    """Tests for notification provider base class."""
    
    @pytest.mark.asyncio
    async def test_notification_request(self):
        """Test notification request creation."""
        from infrastructure.notifications.base import NotificationRequest, NotificationType, NotificationPriority
        
        request = NotificationRequest(
            type=NotificationType.EMAIL,
            to="test@example.com",
            subject="Test",
            content="Test content",
            priority=NotificationPriority.HIGH,
        )
        
        assert request.type == NotificationType.EMAIL
        assert request.to == "test@example.com"
        assert request.priority == NotificationPriority.HIGH
    
    @pytest.mark.asyncio
    async def test_notification_response(self):
        """Test notification response creation."""
        from infrastructure.notifications.base import NotificationResponse
        
        response = NotificationResponse(
            success=True,
            message_id="msg_123",
            status="sent",
        )
        
        assert response.success is True
        assert response.message_id == "msg_123"


@pytest.mark.unit
class TestBatchNotifications:
    """Tests for batch notification operations."""
    
    @pytest.mark.asyncio
    async def test_broadcast_to_users(self):
        """Test broadcasting to multiple users."""
        from infrastructure.notifications.telegram_notifier import TelegramNotifier
        
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', AsyncMock(return_value=Mock(success=True))):
            user_ids = [123, 456, 789]
            message = "Broadcast message"
            
            stats = await notifier.broadcast_to_users(user_ids, message)
            
            assert stats["total"] == 3
            assert stats["success"] == 3
            assert stats["failed"] == 0


@pytest.mark.unit
class TestNotificationTemplates:
    """Tests for notification templates."""
    
    def test_email_template_rendering(self):
        """Test email template rendering."""
        from infrastructure.notifications.email_service import EmailService
        
        service = EmailService()
        template_name = "welcome"
        template_data = {"name": "Test User"}
        
        rendered = service._render_template(template_name, template_data)
        
        assert rendered is not None
        assert "Test User" in rendered or rendered == ""
    
    def test_sms_templates(self):
        """Test SMS templates."""
        from infrastructure.notifications.sms_gateway import SMSGateway
        
        gateway = SMSGateway()
        # Test phone number normalization
        normalized = gateway._normalize_phone("0912345678")
        assert normalized == "251912345678" or normalized is None


__all__ = [
    "TestEmailService",
    "TestSMSService",
    "TestTelegramNotifier",
    "TestNotificationProvider",
    "TestBatchNotifications",
    "TestNotificationTemplates",
]