# ============================
# WOLLOYEWA STORE BOT - FIREBASE PUSH NOTIFICATIONS
# ============================
"""Firebase Cloud Messaging (FCM) push notifications for mobile apps."""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from core.config import settings
from core.logger import logger


class DevicePlatform(str, Enum):
    """Mobile device platforms."""
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class PushMessage:
    """Push notification message."""
    
    title: str
    body: str
    data: Dict[str, Any] = field(default_factory=dict)
    image_url: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    click_action: Optional[str] = None
    sound: Optional[str] = None
    badge: Optional[int] = None


@dataclass
class PushNotification:
    """Push notification record."""
    
    notification_id: str
    user_id: int
    device_token: str
    platform: DevicePlatform
    message: PushMessage
    sent_at: Optional[datetime] = None
    delivered: bool = False
    error: Optional[str] = None


class FirebasePushNotifier:
    """
    Firebase Cloud Messaging push notifier.
    
    Features:
    - Send push notifications to Android/iOS
    - Device token management
    - Bulk notifications
    - Delivery tracking
    """
    
    def __init__(self):
        self._fcm_client = None
        self._device_tokens: Dict[int, List[Dict[str, Any]]] = {}
        self._initialized = False
    
    async def _initialize(self) -> None:
        """Initialize Firebase client."""
        if self._initialized:
            return
        
        try:
            import firebase_admin
            from firebase_admin import credentials, messaging
            
            # Check if already initialized
            if not firebase_admin._apps:
                # Initialize with credentials
                # In production, load from service account file
                cred = credentials.Certificate("path/to/service-account-key.json")
                firebase_admin.initialize_app(cred)
            
            self._fcm_client = messaging
            self._initialized = True
            logger.info("Firebase Cloud Messaging initialized")
            
        except ImportError:
            logger.warning("Firebase admin not installed. Push notifications disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
    
    async def register_device(
        self,
        user_id: int,
        device_token: str,
        platform: DevicePlatform,
        device_name: Optional[str] = None,
    ) -> bool:
        """
        Register a device for push notifications.
        
        Args:
            user_id: User ID
            device_token: FCM device token
            platform: Device platform
            device_name: Optional device name
            
        Returns:
            True if registered
        """
        if user_id not in self._device_tokens:
            self._device_tokens[user_id] = []
        
        # Check if token already exists
        for token_info in self._device_tokens[user_id]:
            if token_info["token"] == device_token:
                token_info["updated_at"] = datetime.utcnow()
                return True
        
        self._device_tokens[user_id].append({
            "token": device_token,
            "platform": platform,
            "device_name": device_name,
            "registered_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
        })
        
        logger.info(f"Registered device for user {user_id}: {platform.value}")
        return True
    
    async def unregister_device(self, user_id: int, device_token: str) -> bool:
        """
        Unregister a device.
        
        Args:
            user_id: User ID
            device_token: Device token to remove
            
        Returns:
            True if unregistered
        """
        if user_id in self._device_tokens:
            self._device_tokens[user_id] = [
                t for t in self._device_tokens[user_id]
                if t["token"] != device_token
            ]
            logger.info(f"Unregistered device for user {user_id}")
            return True
        
        return False
    
    async def send_notification(
        self,
        user_id: int,
        message: PushMessage,
    ) -> List[PushNotification]:
        """
        Send push notification to a user.
        
        Args:
            user_id: User ID
            message: Push message
            
        Returns:
            List of notification records
        """
        await self._initialize()
        
        notifications = []
        devices = self._device_tokens.get(user_id, [])
        
        if not devices:
            logger.warning(f"No registered devices for user {user_id}")
            return notifications
        
        for device in devices:
            if not device["is_active"]:
                continue
            
            notification = PushNotification(
                notification_id=self._generate_notification_id(),
                user_id=user_id,
                device_token=device["token"],
                platform=device["platform"],
                message=message,
            )
            
            try:
                if self._fcm_client:
                    # Send via FCM
                    await self._send_via_fcm(device["token"], message, device["platform"])
                    notification.sent_at = datetime.utcnow()
                    notification.delivered = True
                else:
                    # Mock mode
                    logger.info(f"Mock push to {device['platform']}: {message.title}")
                    notification.sent_at = datetime.utcnow()
                    notification.delivered = True
                
                notifications.append(notification)
                
            except Exception as e:
                notification.error = str(e)
                notifications.append(notification)
                logger.error(f"Failed to send push to user {user_id}: {e}")
        
        return notifications
    
    async def _send_via_fcm(
        self,
        token: str,
        message: PushMessage,
        platform: DevicePlatform,
    ) -> None:
        """Send notification via FCM."""
        from firebase_admin import messaging
        
        # Build FCM message
        fcm_message = messaging.Message(
            notification=messaging.Notification(
                title=message.title,
                body=message.body,
                image=message.image_url,
            ),
            data=message.data,
            token=token,
            android=messaging.AndroidConfig(
                priority="high" if message.priority == NotificationPriority.HIGH else "normal",
                notification=messaging.AndroidNotification(
                    sound=message.sound or "default",
                    click_action=message.click_action,
                ),
            ) if platform == DevicePlatform.ANDROID else None,
            apns=messaging.APNSConfig(
                headers={
                    "apns-priority": "10" if message.priority == NotificationPriority.HIGH else "5",
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound=message.sound or "default",
                        badge=message.badge,
                    ),
                ),
            ) if platform == DevicePlatform.IOS else None,
        )
        
        # Send
        response = messaging.send(fcm_message)
        logger.debug(f"FCM send response: {response}")
    
    def _generate_notification_id(self) -> str:
        """Generate unique notification ID."""
        import uuid
        return str(uuid.uuid4())
    
    async def send_bulk_notification(
        self,
        user_ids: List[int],
        message: PushMessage,
    ) -> Dict[str, int]:
        """
        Send notification to multiple users.
        
        Args:
            user_ids: List of user IDs
            message: Push message
            
        Returns:
            Statistics about sent notifications
        """
        sent = 0
        failed = 0
        
        for user_id in user_ids:
            notifications = await self.send_notification(user_id, message)
            sent += sum(1 for n in notifications if n.delivered)
            failed += sum(1 for n in notifications if not n.delivered)
        
        return {
            "sent": sent,
            "failed": failed,
            "total_users": len(user_ids),
        }
    
    async def get_user_devices(self, user_id: int) -> List[Dict[str, Any]]:
        """Get registered devices for a user."""
        return self._device_tokens.get(user_id, [])


# Global push notifier
push_notifier = FirebasePushNotifier()


async def send_push_notification(
    user_id: int,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
) -> List[PushNotification]:
    """Send push notification to a user."""
    message = PushMessage(
        title=title,
        body=body,
        data=data or {},
    )
    return await push_notifier.send_notification(user_id, message)


async def send_bulk_push(
    user_ids: List[int],
    title: str,
    body: str,
) -> Dict[str, int]:
    """Send bulk push notification."""
    message = PushMessage(title=title, body=body)
    return await push_notifier.send_bulk_notification(user_ids, message)


async def register_device(
    user_id: int,
    device_token: str,
    platform: str,
    device_name: Optional[str] = None,
) -> bool:
    """Register a device for push notifications."""
    return await push_notifier.register_device(
        user_id, device_token, DevicePlatform(platform), device_name
    )


async def unregister_device(user_id: int, device_token: str) -> bool:
    """Unregister a device."""
    return await push_notifier.unregister_device(user_id, device_token)


__all__ = [
    "FirebasePushNotifier",
    "PushNotification",
    "PushMessage",
    "DevicePlatform",
    "NotificationPriority",
    "push_notifier",
    "send_push_notification",
    "send_bulk_push",
    "register_device",
    "unregister_device",
]