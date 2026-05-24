# ============================
# WOLLOYEWA STORE BOT - ALERTING SYSTEM
# ============================
"""Alert management and notification for critical events."""

import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

from core.config import settings
from core.logger import logger


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert notification channels."""
    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"


@dataclass
class Alert:
    """Represents an alert."""
    
    name: str
    message: str
    level: AlertLevel
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    attributes: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    alert_id: str = field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "message": self.message,
            "level": self.level.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "attributes": self.attributes,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
        }


class AlertRule:
    """Rule for triggering alerts based on conditions."""
    
    def __init__(
        self,
        name: str,
        condition: Callable,
        message: str,
        level: AlertLevel = AlertLevel.WARNING,
        cooldown_seconds: int = 300,
    ):
        self.name = name
        self.condition = condition
        self.message = message
        self.level = level
        self.cooldown_seconds = cooldown_seconds
        self._last_triggered: Optional[datetime] = None
    
    def should_trigger(self, *args, **kwargs) -> bool:
        """Check if rule should trigger."""
        if self._last_triggered:
            elapsed = (datetime.utcnow() - self._last_triggered).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False
        
        try:
            return self.condition(*args, **kwargs)
        except Exception as e:
            logger.error(f"Alert rule condition failed: {e}")
            return False
    
    def mark_triggered(self):
        """Mark rule as triggered."""
        self._last_triggered = datetime.utcnow()


class AlertManager:
    """
    Central alert management system.
    
    Handles:
    - Alert creation and routing
    - Notification delivery
    - Alert deduplication
    - Escalation policies
    """
    
    def __init__(self):
        self._alerts: deque = deque(maxlen=1000)
        self._handlers: Dict[AlertChannel, List[Callable]] = {}
        self._rules: List[AlertRule] = []
        self._alert_history: deque = deque(maxlen=5000)
        self._notifiers = {}
        self._alert_callbacks = []
    
    def register_handler(self, channel: AlertChannel, handler: Callable) -> None:
        """Register a handler for an alert channel."""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)
        logger.debug(f"Registered handler for channel: {channel.value}")
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules.append(rule)
        logger.debug(f"Added alert rule: {rule.name}")
    
    async def send_alert(
        self,
        alert: Alert,
        channels: List[AlertChannel] = None,
    ) -> None:
        """
        Send an alert through specified channels.
        
        Args:
            alert: Alert to send
            channels: Channels to use (defaults to all registered)
        """
        # Add to alert history
        self._alerts.append(alert)
        self._alert_history.append(alert)
        
        # Log alert
        log_func = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical,
        }.get(alert.level, logger.info)
        
        log_func(f"ALERT [{alert.level.value.upper()}] {alert.name}: {alert.message}")
        
        # Send through channels
        channels = channels or list(self._handlers.keys())
        
        for channel in channels:
            if channel in self._handlers:
                for handler in self._handlers[channel]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(alert)
                        else:
                            handler(alert)
                    except Exception as e:
                        logger.error(f"Failed to send alert via {channel.value}: {e}")
        
        # Execute callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    async def check_rules(self, *args, **kwargs) -> List[Alert]:
        """Check all alert rules and trigger if needed."""
        triggered = []
        
        for rule in self._rules:
            if rule.should_trigger(*args, **kwargs):
                alert = Alert(
                    name=rule.name,
                    message=rule.message,
                    level=rule.level,
                    source="alert_rule",
                    attributes={"rule": rule.name},
                )
                await self.send_alert(alert)
                rule.mark_triggered()
                triggered.append(alert)
        
        return triggered
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                logger.info(f"Alert resolved: {alert_id}")
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all unresolved alerts."""
        return [a for a in self._alerts if not a.resolved]
    
    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        """Get alerts by severity level."""
        return [a for a in self._alerts if a.level == level]
    
    def register_alert_callback(self, callback: Callable) -> None:
        """Register a callback for all alerts."""
        self._alert_callbacks.append(callback)
    
    def clear_resolved(self) -> None:
        """Clear resolved alerts from memory."""
        self._alerts = deque([a for a in self._alerts if not a.resolved], maxlen=1000)


# Global alert manager
alert_manager = AlertManager()


# ============================
# Built-in Alert Rules
# ============================

def create_high_error_rate_rule(
    threshold: float = 0.05,  # 5% error rate
    window_seconds: int = 300,
) -> AlertRule:
    """Create rule for high error rate."""
    # This would integrate with metrics collection
    def condition():
        # Placeholder - integrate with actual metrics
        return False
    
    return AlertRule(
        name="high_error_rate",
        condition=condition,
        message=f"Error rate exceeded {threshold * 100}% in the last {window_seconds} seconds",
        level=AlertLevel.ERROR,
    )


def create_low_stock_rule(threshold: int = 5) -> AlertRule:
    """Create rule for low stock alerts."""
    def condition(product_stock: int = 0):
        return product_stock <= threshold
    
    return AlertRule(
        name="low_stock",
        condition=condition,
        message=f"Product stock is below {threshold} units",
        level=AlertLevel.WARNING,
    )


def create_payment_failure_rule(threshold: int = 10) -> AlertRule:
    """Create rule for payment failures."""
    def condition(failure_count: int = 0):
        return failure_count >= threshold
    
    return AlertRule(
        name="payment_failures",
        condition=condition,
        message=f"Payment failures exceeded {threshold} in the last hour",
        level=AlertLevel.CRITICAL,
    )


# ============================
# Default Alert Handlers
# ============================

async def telegram_alert_handler(alert: Alert) -> None:
    """Send alert via Telegram."""
    from infrastructure.notifications.telegram_notifier import notify_admin_async
    
    emoji = {
        AlertLevel.INFO: "ℹ️",
        AlertLevel.WARNING: "⚠️",
        AlertLevel.ERROR: "❌",
        AlertLevel.CRITICAL: "🚨",
    }.get(alert.level, "📢")
    
    message = f"{emoji} *{alert.name.upper()}*\n\n{alert.message}\n\n📁 Source: {alert.source}\n🕐 Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    await notify_admin_async(message)


async def email_alert_handler(alert: Alert) -> None:
    """Send alert via Email."""
    from infrastructure.notifications.email_service import send_email_async
    
    subject = f"[{alert.level.value.upper()}] {alert.name}"
    body = f"""
    Alert: {alert.name}
    Level: {alert.level.value}
    Message: {alert.message}
    Source: {alert.source}
    Time: {alert.timestamp}
    """
    
    await send_email_async(
        to_emails=settings.ADMIN_IDS.split(","),
        subject=subject,
        body=body,
    )


def log_alert_handler(alert: Alert) -> None:
    """Log alert to file."""
    # Already logged in send_alert, this is for additional logging
    pass


# Register default handlers
alert_manager.register_handler(AlertChannel.TELEGRAM, telegram_alert_handler)
alert_manager.register_handler(AlertChannel.EMAIL, email_alert_handler)
alert_manager.register_handler(AlertChannel.WEBHOOK, log_alert_handler)


async def send_alert(
    name: str,
    message: str,
    level: AlertLevel = AlertLevel.WARNING,
    source: str = "system",
    attributes: Dict[str, Any] = None,
    channels: List[AlertChannel] = None,
) -> None:
    """
    Convenience function to send an alert.
    
    Args:
        name: Alert name
        message: Alert message
        level: Alert severity
        source: Alert source
        attributes: Additional attributes
        channels: Notification channels
    """
    alert = Alert(
        name=name,
        message=message,
        level=level,
        source=source,
        attributes=attributes or {},
    )
    
    await alert_manager.send_alert(alert, channels)


__all__ = [
    "AlertManager",
    "Alert",
    "AlertLevel",
    "AlertChannel",
    "AlertRule",
    "alert_manager",
    "send_alert",
    "create_high_error_rate_rule",
    "create_low_stock_rule",
    "create_payment_failure_rule",
]