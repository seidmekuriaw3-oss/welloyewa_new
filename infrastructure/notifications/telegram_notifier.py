# ============================
# WOLLOYEWA STORE BOT - TELEGRAM NOTIFIER
# ============================
"""Telegram notification service for bot and admin communications."""

from typing import Optional, Dict, Any, List
from datetime import datetime

from infrastructure.notifications.base import (
    NotificationProvider,
    NotificationRequest,
    NotificationResponse,
    NotificationType,
    NotificationError,
)
from core.config import settings
from core.logger import logger


class TelegramNotifier(NotificationProvider):
    """
    Telegram notification service.
    
    Features:
    - Send messages to users
    - Admin notifications
    - Order updates
    - Broadcast messages
    """
    
    def __init__(self):
        self._bot = None
        self.admin_ids = settings.admin_ids_list
    
    async def _get_bot(self):
        """Get Telegram bot instance lazily."""
        if self._bot is None:
            from bot.bot_instance import get_bot
            self._bot = await get_bot()
        return self._bot
    
    @property
    def name(self) -> str:
        return "telegram"
    
    @property
    def notification_type(self) -> NotificationType:
        return NotificationType.TELEGRAM
    
    async def send(self, request: NotificationRequest) -> NotificationResponse:
        """
        Send a Telegram message.
        
        Args:
            request: Notification request with chat_id in 'to' field
            
        Returns:
            Notification response
        """
        try:
            bot = await self._get_bot()
            chat_id = int(request.to)
            
            # Parse content (support markdown)
            parse_mode = "HTML" if "<" in request.content else "Markdown"
            
            message = await bot.send_message(
                chat_id=chat_id,
                text=request.content,
                parse_mode=parse_mode,
            )
            
            logger.info(f"Telegram message sent to {chat_id}")
            
            return NotificationResponse(
                success=True,
                message_id=str(message.message_id),
                status="sent",
                sent_at=datetime.utcnow(),
            )
            
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return NotificationResponse(
                success=False,
                error=str(e),
                status="failed",
            )
    
    async def get_status(self, message_id: str) -> Dict[str, Any]:
        """Get message status (stub)."""
        return {"status": "sent", "message_id": message_id}
    
    async def send_to_admin(self, message: str, priority: str = "normal") -> bool:
        """
        Send notification to all admins.
        
        Args:
            message: Message content
            priority: Message priority
            
        Returns:
            True if sent to at least one admin
        """
        if not self.admin_ids:
            logger.warning("No admin IDs configured")
            return False
        
        success_count = 0
        for admin_id in self.admin_ids:
            request = NotificationRequest(
                type=NotificationType.TELEGRAM,
                to=str(admin_id),
                content=message,
            )
            response = await self.send(request)
            if response.success:
                success_count += 1
        
        return success_count > 0
    
    async def send_order_notification(
        self,
        user_id: int,
        order_number: str,
        status: str,
        total: str = None,
    ) -> bool:
        """
        Send order update notification to user.
        
        Args:
            user_id: User's Telegram ID
            order_number: Order number
            status: Order status
            total: Order total
            
        Returns:
            True if sent successfully
        """
        status_messages = {
            "created": f"✅ ትዕዛዝዎ #{order_number} በተሳካ ሁኔታ ተመዝግቧል!\n💰 ጠቅላላ: {total} ብር",
            "confirmed": f"✅ ትዕዛዝ #{order_number} ተረጋግጧል! በቅርቡ እንልካለን።",
            "shipped": f"📦 ትዕዛዝ #{order_number} ተልኳል! በቅርቡ ይደርስዎታል።",
            "delivered": f"🎉 ትዕዛዝ #{order_number} ደርሷል! እባክዎ ምርቶቹን ለመገምገም አይርሱ።",
            "cancelled": f"❌ ትዕዛዝ #{order_number} ተሰርዟል። ተጨማሪ መረጃ ካለብዎ ድጋፍ ያግኙን።",
        }
        
        message = status_messages.get(status, f"ትዕዛዝ #{order_number} ሁኔታ: {status}")
        
        request = NotificationRequest(
            type=NotificationType.TELEGRAM,
            to=str(user_id),
            content=message,
        )
        
        response = await self.send(request)
        return response.success
    
    async def notify_vendor(self, vendor_id: int, message: str) -> bool:
        """
        Send notification to a vendor.
        
        Args:
            vendor_id: Vendor user ID
            message: Notification message
            
        Returns:
            True if sent successfully
        """
        request = NotificationRequest(
            type=NotificationType.TELEGRAM,
            to=str(vendor_id),
            content=message,
        )
        
        response = await self.send(request)
        return response.success
    
    async def broadcast_to_users(self, user_ids: List[int], message: str) -> Dict[str, int]:
        """
        Broadcast message to multiple users.
        
        Args:
            user_ids: List of user Telegram IDs
            message: Message to send
            
        Returns:
            Statistics about sent messages
        """
        success_count = 0
        fail_count = 0
        
        for user_id in user_ids:
            request = NotificationRequest(
                type=NotificationType.TELEGRAM,
                to=str(user_id),
                content=message,
            )
            response = await self.send(request)
            
            if response.success:
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"Broadcast sent to {success_count} users, failed: {fail_count}")
        
        return {
            "total": len(user_ids),
            "success": success_count,
            "failed": fail_count,
        }


# Global Telegram notifier instance
_telegram_notifier = TelegramNotifier()


async def send_telegram_message(chat_id: int, message: str) -> bool:
    """Send a Telegram message to a user."""
    request = NotificationRequest(
        type=NotificationType.TELEGRAM,
        to=str(chat_id),
        content=message,
    )
    response = await _telegram_notifier.send(request)
    return response.success


async def send_to_admin(message: str) -> bool:
    """Send notification to all admins."""
    return await _telegram_notifier.send_to_admin(message)


async def send_order_notification(
    user_id: int,
    order_number: str,
    status: str,
    total: str = None,
) -> bool:
    """Send order update notification to user."""
    return await _telegram_notifier.send_order_notification(user_id, order_number, status, total)


async def notify_vendor(vendor_id: int, message: str) -> bool:
    """Send notification to a vendor."""
    return await _telegram_notifier.notify_vendor(vendor_id, message)


__all__ = [
    "TelegramNotifier",
    "send_telegram_message",
    "send_to_admin",
    "send_order_notification",
    "notify_vendor",
]