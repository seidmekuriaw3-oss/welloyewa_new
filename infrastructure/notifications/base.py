# ============================
# WOLLOYEWA STORE BOT - NOTIFICATIONS BASE
# ============================
"""Base classes and interfaces for notification providers."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


class NotificationType(str, Enum):
    """Types of notifications."""
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    PUSH = "push"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationError(Exception):
    """Base exception for notification errors."""
    
    def __init__(self, message: str, provider: str = None):
        self.message = message
        self.provider = provider
        super().__init__(message)


@dataclass
class NotificationRequest:
    """
    Notification request data.
    
    Attributes:
        type: Notification type (email, sms, telegram)
        to: Recipient address (email, phone number, or chat ID)
        subject: Subject line (for emails)
        content: Main notification content
        template: Template name to use
        template_data: Data for template rendering
        priority: Notification priority
        attachments: List of file attachments (for emails)
        metadata: Additional metadata
    """
    
    type: NotificationType
    to: str
    subject: Optional[str] = None
    content: Optional[str] = None
    template: Optional[str] = None
    template_data: Dict[str, Any] = field(default_factory=dict)
    priority: NotificationPriority = NotificationPriority.NORMAL
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationResponse:
    """
    Notification response data.
    
    Attributes:
        success: Whether notification was sent successfully
        message_id: Provider message ID
        status: Delivery status
        error: Error message if failed
        sent_at: Timestamp when sent
        provider_response: Raw provider response
    """
    
    success: bool
    message_id: Optional[str] = None
    status: str = "pending"
    error: Optional[str] = None
    sent_at: datetime = field(default_factory=datetime.utcnow)
    provider_response: Dict[str, Any] = field(default_factory=dict)


class NotificationProvider(ABC):
    """
    Abstract base class for notification providers.
    
    All notification channels must implement this interface.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @property
    @abstractmethod
    def notification_type(self) -> NotificationType:
        """Notification type this provider handles."""
        pass
    
    @abstractmethod
    async def send(self, request: NotificationRequest) -> NotificationResponse:
        """
        Send a notification.
        
        Args:
            request: Notification request
            
        Returns:
            Notification response
        """
        pass
    
    @abstractmethod
    async def get_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get delivery status of a notification.
        
        Args:
            message_id: Provider message ID
            
        Returns:
            Status information
        """
        pass
    
    async def send_batch(
        self,
        requests: List[NotificationRequest],
    ) -> List[NotificationResponse]:
        """
        Send multiple notifications in batch.
        
        Args:
            requests: List of notification requests
            
        Returns:
            List of notification responses
        """
        responses = []
        for request in requests:
            response = await self.send(request)
            responses.append(response)
        return responses


__all__ = [
    "NotificationProvider",
    "NotificationRequest",
    "NotificationResponse",
    "NotificationType",
    "NotificationPriority",
    "NotificationError",
]