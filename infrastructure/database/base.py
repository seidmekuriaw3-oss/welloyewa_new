# ============================
# WOLLOYEWA STORE BOT - DATABASE BASE
# ============================
"""SQLAlchemy base class and metadata."""

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all database models.
    
    All models should inherit from this class.
    """
    
    __abstract__ = True
    
    def __repr__(self) -> str:
        """Generate string representation of model."""
        class_name = self.__class__.__name__
        primary_key = getattr(self, 'id', None)
        return f"<{class_name}(id={primary_key})>"