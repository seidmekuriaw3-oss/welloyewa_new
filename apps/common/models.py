# ============================
# WOLLOYEWA STORE BOT - COMMON MODELS
# ============================
"""Base models and mixins for all database models."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, Boolean, JSON, String
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from infrastructure.database.base import Base


class BaseModel(Base):
    """
    Base model class with common attributes.
    
    All database models should inherit from this class.
    """
    
    __abstract__ = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name automatically from class name."""
        import re
        # Convert CamelCase to snake_case
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        # Handle pluralization for common cases
        if name.endswith('y'):
            name = name[:-1] + 'ies'
        elif not name.endswith('s'):
            name = name + 's'
        return name
    
    def to_dict(self, exclude: Optional[list] = None) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Args:
            exclude: List of field names to exclude
            
        Returns:
            Dictionary representation of model
        """
        exclude = exclude or []
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Convert datetime to ISO format
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        return result
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        Update model attributes from dictionary.
        
        Args:
            data: Dictionary of attributes to update
        """
        for key, value in data.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    def soft_delete(self) -> None:
        """Mark record as deleted without removing from database."""
        self.deleted_at = datetime.utcnow()
        self.is_deleted = True
    
    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.is_deleted = False
    
    @property
    def is_active(self) -> bool:
        """Check if record is not deleted."""
        return not self.is_deleted


class MetadataMixin:
    """Mixin for storing additional metadata as JSON."""
    
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    def get_meta(self, key: str, default: Any = None) -> Any:
        """Get a value from metadata."""
        if not self.extra_data:
            return default
        return self.extra_data.get(key, default)
    
    def set_meta(self, key: str, value: Any) -> None:
        """Set a value in metadata."""
        if self.extra_data is None:
            self.extra_data = {}
        self.extra_data[key] = value


class StatusMixin:
    """Mixin for status tracking."""
    
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    
    @property
    def is_active(self) -> bool:
        """Check if status is active."""
        return self.status == "active"
    
    def activate(self) -> None:
        """Set status to active."""
        self.status = "active"
    
    def deactivate(self) -> None:
        """Set status to inactive."""
        self.status = "inactive"
    
    def suspend(self) -> None:
        """Set status to suspended."""
        self.status = "suspended"