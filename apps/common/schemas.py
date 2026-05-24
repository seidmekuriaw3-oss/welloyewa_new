# ============================
# WOLLOYEWA STORE BOT - BASE SCHEMAS
# ============================
"""Base Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
    )


class IdSchema(BaseSchema):
    """Schema with ID field."""
    
    id: int = Field(..., description="Unique identifier")


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class MessageResponse(BaseSchema):
    """Simple message response."""
    
    message: str = Field(..., description="Response message")
    success: bool = Field(True, description="Whether operation was successful")


class ErrorResponse(BaseSchema):
    """Error response schema."""
    
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class PaginationParams(BaseSchema):
    """Pagination query parameters."""
    
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response."""
    
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        """Create paginated response from items and pagination parameters."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class FilterParams(BaseSchema):
    """Common filter parameters."""
    
    search: Optional[str] = Field(None, description="Search query")
    status: Optional[str] = Field(None, description="Filter by status")
    from_date: Optional[datetime] = Field(None, description="Filter from date")
    to_date: Optional[datetime] = Field(None, description="Filter to date")
    sort_by: Optional[str] = Field(None, description="Sort by field")
    sort_desc: bool = Field(False, description="Sort descending")


class DateRangeSchema(BaseSchema):
    """Date range filter."""
    
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")


class BulkOperationResponse(BaseSchema):
    """Response for bulk operations."""
    
    success_count: int = Field(..., description="Number of successful operations")
    failed_count: int = Field(..., description="Number of failed operations")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Error details")


class IdsListSchema(BaseSchema):
    """Schema for list of IDs."""
    
    ids: List[int] = Field(..., description="List of IDs", min_length=1)


__all__ = [
    "BaseSchema",
    "IdSchema",
    "TimestampSchema",
    "MessageResponse",
    "ErrorResponse",
    "PaginationParams",
    "PaginatedResponse",
    "FilterParams",
    "DateRangeSchema",
    "BulkOperationResponse",
    "IdsListSchema",
]