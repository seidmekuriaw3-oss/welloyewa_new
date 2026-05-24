# ============================
# WOLLOYEWA STORE BOT - AUDIT TRAIL
# ============================
"""Audit logging for security and compliance tracking."""

import json
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from functools import wraps

from core.config import settings
from core.logger import logger, LoggerContext


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    
    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_SUSPENDED = "user_suspended"
    USER_ACTIVATED = "user_activated"
    ROLE_CHANGED = "role_changed"
    
    # Vendor management
    VENDOR_REGISTERED = "vendor_registered"
    VENDOR_APPROVED = "vendor_approved"
    VENDOR_REJECTED = "vendor_rejected"
    VENDOR_SUSPENDED = "vendor_suspended"
    
    # Product management
    PRODUCT_CREATED = "product_created"
    PRODUCT_UPDATED = "product_updated"
    PRODUCT_DELETED = "product_deleted"
    PRODUCT_STATUS_CHANGED = "product_status_changed"
    
    # Order management
    ORDER_CREATED = "order_created"
    ORDER_UPDATED = "order_updated"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REFUNDED = "order_refunded"
    
    # Payment events
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUNDED = "payment_refunded"
    
    # Admin actions
    ADMIN_ACTION = "admin_action"
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    PERMISSION_CHANGED = "permission_changed"
    
    # Security events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    
    # Data events
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    DATA_DELETED = "data_deleted"
    
    # API events
    API_ACCESS = "api_access"
    WEBHOOK_RECEIVED = "webhook_received"
    WEBHOOK_SENT = "webhook_sent"


@dataclass
class AuditEntry:
    """Single audit log entry."""
    
    event_type: AuditEventType
    user_id: Optional[int]
    username: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "username": self.username,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
        }
    
    def to_log(self) -> str:
        """Format as log string."""
        return f"AUDIT: {self.event_type.value} | User: {self.username or self.user_id} | {json.dumps(self.details)}"


class AuditLogger:
    """
    Audit logging for compliance and security monitoring.
    
    Features:
    - Structured audit logging
    - Searchable audit records
    - Retention policy enforcement
    - Export capabilities
    """
    
    def __init__(self):
        self._audit_store: List[AuditEntry] = []
        self._max_entries = 10000
        self._enabled = settings.AUDIT_LOG_ENABLED
    
    def log(
        self,
        event_type: AuditEventType,
        details: Dict[str, Any],
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Log an audit event.
        
        Args:
            event_type: Type of audit event
            details: Event details
            user_id: ID of the user performing action
            username: Username of the user
            ip_address: IP address of the requester
            user_agent: User agent string
            correlation_id: Correlation ID for tracing
        """
        if not self._enabled:
            return
        
        entry = AuditEntry(
            event_type=event_type,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            correlation_id=correlation_id,
        )
        
        self._audit_store.append(entry)
        
        # Enforce retention limit
        if len(self._audit_store) > self._max_entries:
            self._audit_store = self._audit_store[-self._max_entries:]
        
        # Write to log file
        logger.info(entry.to_log())
        
        # If critical event, also log as error
        if event_type in [
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.SQL_INJECTION_ATTEMPT,
            AuditEventType.XSS_ATTEMPT,
        ]:
            logger.warning(entry.to_log())
    
    def get_audit_logs(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with filters.
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of entries to return
            
        Returns:
            List of audit entries as dictionaries
        """
        entries = self._audit_store
        
        # Apply filters
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        
        if start_date:
            entries = [e for e in entries if e.timestamp >= start_date]
        
        if end_date:
            entries = [e for e in entries if e.timestamp <= end_date]
        
        # Sort by timestamp descending
        entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
        
        return [e.to_dict() for e in entries[:limit]]
    
    def export_audit_logs(
        self,
        format: str = "json",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """
        Export audit logs for compliance reporting.
        
        Args:
            format: Export format (json, csv)
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            Exported data as string
        """
        entries = self._audit_store
        
        if start_date:
            entries = [e for e in entries if e.timestamp >= start_date]
        
        if end_date:
            entries = [e for e in entries if e.timestamp <= end_date]
        
        if format == "json":
            return json.dumps([e.to_dict() for e in entries], indent=2)
        elif format == "csv":
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                "timestamp", "event_type", "user_id", "username",
                "ip_address", "details", "correlation_id"
            ])
            writer.writeheader()
            for entry in entries:
                writer.writerow({
                    "timestamp": entry.timestamp.isoformat(),
                    "event_type": entry.event_type.value,
                    "user_id": entry.user_id,
                    "username": entry.username,
                    "ip_address": entry.ip_address,
                    "details": json.dumps(entry.details),
                    "correlation_id": entry.correlation_id,
                })
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def clear_old_logs(self, days: int = 30) -> int:
        """Clear audit logs older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        initial_count = len(self._audit_store)
        self._audit_store = [e for e in self._audit_store if e.timestamp >= cutoff]
        removed = initial_count - len(self._audit_store)
        logger.info(f"Cleared {removed} audit logs older than {days} days")
        return removed
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable audit logging."""
        self._enabled = enabled
        logger.info(f"Audit logging {'enabled' if enabled else 'disabled'}")


# Global audit logger instance
audit_logger = AuditLogger()


def audit_log(
    event_type: AuditEventType,
    details: Dict[str, Any],
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    **kwargs,
) -> None:
    """Convenience function to log audit events."""
    audit_logger.log(
        event_type=event_type,
        details=details,
        user_id=user_id,
        username=username,
        ip_address=kwargs.get("ip_address"),
        user_agent=kwargs.get("user_agent"),
        correlation_id=kwargs.get("correlation_id"),
    )


def get_audit_logs(**filters) -> List[Dict[str, Any]]:
    """Convenience function to retrieve audit logs."""
    return audit_logger.get_audit_logs(**filters)


# Audit decorator for functions
def audit_action(
    event_type: AuditEventType,
    get_details: Optional[callable] = None,
    get_user_id: Optional[callable] = None,
):
    """Decorator to automatically log audit events for functions."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                
                details = {"action": func.__name__, "success": True}
                if get_details:
                    details.update(get_details(*args, **kwargs))
                
                user_id = None
                if get_user_id:
                    user_id = get_user_id(*args, **kwargs)
                
                audit_log(event_type, details, user_id=user_id)
                return result
            except Exception as e:
                details = {"action": func.__name__, "success": False, "error": str(e)}
                if get_details:
                    details.update(get_details(*args, **kwargs))
                
                user_id = None
                if get_user_id:
                    user_id = get_user_id(*args, **kwargs)
                
                audit_log(event_type, details, user_id=user_id)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                details = {"action": func.__name__, "success": True}
                if get_details:
                    details.update(get_details(*args, **kwargs))
                
                user_id = None
                if get_user_id:
                    user_id = get_user_id(*args, **kwargs)
                
                audit_log(event_type, details, user_id=user_id)
                return result
            except Exception as e:
                details = {"action": func.__name__, "success": False, "error": str(e)}
                if get_details:
                    details.update(get_details(*args, **kwargs))
                
                user_id = None
                if get_user_id:
                    user_id = get_user_id(*args, **kwargs)
                
                audit_log(event_type, details, user_id=user_id)
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


__all__ = [
    "AuditLogger",
    "AuditEventType",
    "AuditEntry",
    "audit_logger",
    "audit_log",
    "get_audit_logs",
    "audit_action",
]