# ============================
# WOLLOYEWA STORE BOT - USER PREFERENCES
# ============================
"""User preferences management for notification settings and personalization."""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.logger import logger
from apps.users.models import UserPreferences


class UserPreferencesManager:
    """Manager for user preferences operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_preferences(self, user_id: int) -> Optional[UserPreferences]:
        """Get user preferences by user ID."""
        query = select(UserPreferences).where(UserPreferences.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_or_create_preferences(self, user_id: int) -> UserPreferences:
        """Get preferences or create default if not exists."""
        preferences = await self.get_preferences(user_id)
        if not preferences:
            preferences = UserPreferences(user_id=user_id)
            self.db.add(preferences)
            await self.db.flush()
            logger.debug(f"Created default preferences for user {user_id}")
        return preferences
    
    async def update_preferences(
        self,
        user_id: int,
        data: Dict[str, Any],
    ) -> UserPreferences:
        """Update user preferences."""
        preferences = await self.get_or_create_preferences(user_id)
        
        for key, value in data.items():
            if hasattr(preferences, key) and value is not None:
                setattr(preferences, key, value)
        
        await self.db.flush()
        logger.debug(f"Updated preferences for user {user_id}")
        return preferences
    
    async def update_notification_settings(
        self,
        user_id: int,
        email_notifications: Optional[bool] = None,
        sms_notifications: Optional[bool] = None,
        push_notifications: Optional[bool] = None,
        marketing_emails: Optional[bool] = None,
        promotional_sms: Optional[bool] = None,
    ) -> UserPreferences:
        """Update notification-specific preferences."""
        data = {}
        if email_notifications is not None:
            data["email_notifications"] = email_notifications
        if sms_notifications is not None:
            data["sms_notifications"] = sms_notifications
        if push_notifications is not None:
            data["push_notifications"] = push_notifications
        if marketing_emails is not None:
            data["marketing_emails"] = marketing_emails
        if promotional_sms is not None:
            data["promotional_sms"] = promotional_sms
        
        return await self.update_preferences(user_id, data)
    
    async def get_notification_settings(self, user_id: int) -> Dict[str, bool]:
        """Get user's notification settings."""
        preferences = await self.get_or_create_preferences(user_id)
        return {
            "email_notifications": preferences.email_notifications,
            "sms_notifications": preferences.sms_notifications,
            "push_notifications": preferences.push_notifications,
            "marketing_emails": preferences.marketing_emails,
            "promotional_sms": preferences.promotional_sms,
        }
    
    async def should_send_notification(
        self,
        user_id: int,
        notification_type: str,
    ) -> bool:
        """Check if user should receive a specific notification type."""
        settings = await self.get_notification_settings(user_id)
        
        type_map = {
            "order_update": "email_notifications",
            "payment_update": "email_notifications",
            "marketing": "marketing_emails",
            "promotion": "promotional_sms",
            "system_alert": "push_notifications",
        }
        
        setting_key = type_map.get(notification_type, "email_notifications")
        return settings.get(setting_key, True)
    
    async def update_language(self, user_id: int, language: str) -> UserPreferences:
        """Update user's preferred language."""
        return await self.update_preferences(user_id, {"language": language})
    
    async def update_currency(self, user_id: int, currency: str) -> UserPreferences:
        """Update user's preferred currency."""
        return await self.update_preferences(user_id, {"currency": currency})
    
    async def set_default_shipping_address(
        self,
        user_id: int,
        address_id: int,
    ) -> UserPreferences:
        """Set default shipping address."""
        return await self.update_preferences(user_id, {"default_shipping_address_id": address_id})
    
    async def update_preferred_categories(
        self,
        user_id: int,
        categories: list,
    ) -> UserPreferences:
        """Update user's preferred product categories."""
        return await self.update_preferences(user_id, {"preferred_categories": categories})


async def get_user_preferences(db: AsyncSession, user_id: int) -> Optional[UserPreferences]:
    """Convenience function to get user preferences."""
    manager = UserPreferencesManager(db)
    return await manager.get_preferences(user_id)


async def update_user_preferences(
    db: AsyncSession,
    user_id: int,
    data: Dict[str, Any],
) -> UserPreferences:
    """Convenience function to update user preferences."""
    manager = UserPreferencesManager(db)
    return await manager.update_preferences(user_id, data)


async def get_notification_settings(
    db: AsyncSession,
    user_id: int,
) -> Dict[str, bool]:
    """Convenience function to get notification settings."""
    manager = UserPreferencesManager(db)
    return await manager.get_notification_settings(user_id)


async def update_notification_settings(
    db: AsyncSession,
    user_id: int,
    **kwargs,
) -> UserPreferences:
    """Convenience function to update notification settings."""
    manager = UserPreferencesManager(db)
    return await manager.update_notification_settings(user_id, **kwargs)


__all__ = [
    "UserPreferencesManager",
    "get_user_preferences",
    "update_user_preferences",
    "get_notification_settings",
    "update_notification_settings",
]