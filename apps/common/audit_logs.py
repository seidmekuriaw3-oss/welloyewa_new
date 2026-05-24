# ============================
# WOLLOYEWA STORE BOT - AUDIT LOGS
# ============================
"""Audit logging for tracking changes across all applications."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, Integer, String, DateTime, JSON, BigInteger, Index, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.models import BaseModel, TimestampMixin
from core.logger import logger


class AuditLog(BaseModel, TimestampMixin):
    """
    Audit log entry model.
    
    Tracks all changes to database records for compliance and debugging.
    """
    
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, READ, LOGIN, LOGOUT
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)  # Table/model name
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    old_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    new_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    changes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Diff between old and new
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    __table_args__ = (
        Index('idx_audit_logs_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_logs_action_time', 'action', 'created_at'),
        Index('idx_audit_logs_user_time', 'user_id', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "changes": self.changes,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat(),
            "request_id": self.request_id,
        }


class AuditLogEntry:
    """Helper class for creating audit log entries."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.
        
        Args:
            action: Action performed (CREATE, UPDATE, DELETE, READ, LOGIN, LOGOUT)
            entity_type: Type of entity (table/model name)
            entity_id: ID of the entity
            user_id: ID of the user who performed the action
            username: Username of the user
            old_data: Data before change
            new_data: Data after change
            changes: Calculated changes between old and new
            ip_address: IP address of the requester
            user_agent: User agent string
            request_id: Request ID for tracing
            correlation_id: Correlation ID for tracing
            
        Returns:
            Created AuditLog entry
        """
        # Calculate changes if not provided but both old and new data exist
        if changes is None and old_data is not None and new_data is not None:
            changes = self._calculate_changes(old_data, new_data)
        
        log_entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            user_id=user_id,
            username=username,
            old_data=old_data,
            new_data=new_data,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        
        self.db.add(log_entry)
        await self.db.flush()
        
        logger.debug(f"Audit log created: {action} on {entity_type} by user {user_id}")
        return log_entry
    
    def _calculate_changes(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate differences between old and new data.
        
        Args:
            old_data: Original data dictionary
            new_data: Updated data dictionary
            
        Returns:
            Dictionary of changed fields with old and new values
        """
        changes = {}
        
        # Skip common fields that shouldn't be audited
        skip_fields = {'updated_at', 'created_at', 'id'}
        
        all_keys = set(old_data.keys()) | set(new_data.keys())
        
        for key in all_keys:
            if key in skip_fields:
                continue
            
            old_value = old_data.get(key)
            new_value = new_data.get(key)
            
            if old_value != new_value:
                changes[key] = {
                    "old": self._serialize_value(old_value),
                    "new": self._serialize_value(new_value),
                }
        
        return changes if changes else None
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize value for JSON storage."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (dict, list)):
            return value
        if hasattr(value, 'value'):  # Enum
            return value.value
        return str(value)


async def audit_log(
    db: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    old_data: Optional[Dict[str, Any]] = None,
    new_data: Optional[Dict[str, Any]] = None,
    changes: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> AuditLog:
    """
    Convenience function to create an audit log entry.
    
    Args:
        db: Database session
        action: Action performed
        entity_type: Type of entity
        entity_id: ID of the entity
        user_id: ID of the user
        username: Username of the user
        old_data: Data before change
        new_data: Data after change
        changes: Calculated changes
        ip_address: IP address
        user_agent: User agent
        request_id: Request ID
        correlation_id: Correlation ID
        
    Returns:
        Created AuditLog entry
    """
    entry = AuditLogEntry(db)
    return await entry.log(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        username=username,
        old_data=old_data,
        new_data=new_data,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        correlation_id=correlation_id,
    )


async def get_audit_logs(
    db: AsyncSession,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[AuditLog]:
    """
    Retrieve audit logs with filters.
    
    Args:
        db: Database session
        entity_type: Filter by entity type
        entity_id: Filter by entity ID
        user_id: Filter by user ID
        action: Filter by action
        limit: Maximum number of records
        offset: Number of records to skip
        
    Returns:
        List of audit log entries
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


__all__ = [
    "AuditLog",
    "AuditLogEntry",
    "audit_log",
    "get_audit_logs",
]