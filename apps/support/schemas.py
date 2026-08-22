# ============================
# WOLLOYEWA STORE BOT - SUPPORT SCHEMAS
# ============================
"""Pydantic schemas for support request/response validation."""

from datetime import datetime

from pydantic import Field

from apps.common.schemas import BaseSchema, IdSchema, TimestampSchema

# ============================
# Ticket Category Schemas
# ============================


class TicketCategoryBase(BaseSchema):
    """Base ticket category schema."""

    name: str = Field(..., max_length=100, description="Category name")
    name_am: str | None = Field(None, max_length=100, description="Category name in Amharic")
    description: str | None = Field(None, description="Category description")
    slug: str = Field(..., max_length=120, description="URL-friendly slug")
    icon: str | None = Field(None, max_length=50, description="Icon identifier")
    display_order: int = Field(0, description="Display order")
    is_active: bool = Field(True, description="Whether category is active")
    sla_hours: int = Field(24, ge=1, description="SLA response time in hours")
    auto_assign_to: int | None = Field(None, description="Auto-assign to staff ID")


class TicketCategoryCreate(TicketCategoryBase):
    """Schema for creating a ticket category."""

    pass


class TicketCategoryResponse(TicketCategoryBase, IdSchema, TimestampSchema):
    """Schema for ticket category response."""

    class Config:
        from_attributes = True


# ============================
# Ticket Schemas
# ============================


class TicketBase(BaseSchema):
    """Base ticket schema."""

    category_id: int | None = Field(None, description="Category ID")
    subject: str = Field(..., max_length=255, description="Ticket subject")
    message: str = Field(..., description="Initial message")
    priority: str = Field("medium", description="Priority (low, medium, high, urgent)")


class TicketCreate(TicketBase):
    """Schema for creating a ticket."""

    pass


class TicketUpdate(BaseSchema):
    """Schema for updating a ticket."""

    category_id: int | None = None
    subject: str | None = Field(None, max_length=255)
    status: str | None = None
    priority: str | None = None
    assigned_to: int | None = None
    resolution_note: str | None = None


class TicketResponse(TicketBase, IdSchema, TimestampSchema):
    """Schema for ticket response."""

    ticket_number: str = Field(..., description="Unique ticket number")
    user_id: int = Field(..., description="User ID")
    assigned_to: int | None = Field(None, description="Assigned staff ID")
    status: str = Field(..., description="Ticket status")
    attachments: list[str] | None = Field(None, description="Attachment URLs")
    resolved_at: datetime | None = None
    resolution_note: str | None = None
    closed_at: datetime | None = None
    closed_by: int | None = None
    rating: int | None = Field(None, ge=1, le=5)
    feedback: str | None = None
    response_time_hours: float | None = None
    category_name: str | None = None
    user_name: str | None = None
    assignee_name: str | None = None

    class Config:
        from_attributes = True


class TicketListResponse(BaseSchema):
    """Schema for ticket list response."""

    items: list[TicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================
# Ticket Message Schemas
# ============================


class TicketMessageBase(BaseSchema):
    """Base ticket message schema."""

    message: str = Field(..., description="Message content")
    attachments: list[str] | None = Field(None, description="Attachment URLs")


class TicketMessageCreate(TicketMessageBase):
    """Schema for creating a ticket message."""

    pass


class TicketMessageResponse(TicketMessageBase, IdSchema, TimestampSchema):
    """Schema for ticket message response."""

    ticket_id: int = Field(..., description="Ticket ID")
    user_id: int = Field(..., description="User ID")
    is_staff_reply: bool = Field(False, description="Whether this is a staff reply")
    user_name: str | None = None

    class Config:
        from_attributes = True


# ============================
# FAQ Category Schemas
# ============================


class FAQCategoryBase(BaseSchema):
    """Base FAQ category schema."""

    name: str = Field(..., max_length=100, description="Category name")
    name_am: str | None = Field(None, max_length=100, description="Category name in Amharic")
    description: str | None = Field(None, description="Category description")
    slug: str = Field(..., max_length=120, description="URL-friendly slug")
    icon: str | None = Field(None, max_length=50, description="Icon identifier")
    display_order: int = Field(0, description="Display order")
    is_active: bool = Field(True, description="Whether category is active")


class FAQCategoryCreate(FAQCategoryBase):
    """Schema for creating an FAQ category."""

    pass


class FAQCategoryResponse(FAQCategoryBase, IdSchema, TimestampSchema):
    """Schema for FAQ category response."""

    faq_count: int | None = Field(0, description="Number of FAQs in category")

    class Config:
        from_attributes = True


# ============================
# FAQ Schemas
# ============================


class FAQBase(BaseSchema):
    """Base FAQ schema."""

    category_id: int | None = Field(None, description="Category ID")
    question: str = Field(..., max_length=500, description="Question")
    question_am: str | None = Field(None, max_length=500, description="Question in Amharic")
    answer: str = Field(..., description="Answer")
    answer_am: str | None = Field(None, description="Answer in Amharic")
    keywords: list[str] | None = Field(None, description="Search keywords")
    display_order: int = Field(0, description="Display order")
    is_active: bool = Field(True, description="Whether FAQ is active")


class FAQCreate(FAQBase):
    """Schema for creating an FAQ."""

    pass


class FAQUpdate(BaseSchema):
    """Schema for updating an FAQ."""

    category_id: int | None = None
    question: str | None = Field(None, max_length=500)
    question_am: str | None = Field(None, max_length=500)
    answer: str | None = None
    answer_am: str | None = None
    keywords: list[str] | None = None
    display_order: int | None = None
    is_active: bool | None = None


class FAQResponse(FAQBase, IdSchema, TimestampSchema):
    """Schema for FAQ response."""

    slug: str = Field(..., description="URL-friendly slug")
    helpful_count: int = Field(0, description="Number of helpful votes")
    not_helpful_count: int = Field(0, description="Number of not helpful votes")
    helpful_percentage: float = Field(0.0, description="Helpful percentage")
    category_name: str | None = None

    class Config:
        from_attributes = True


class FAQListResponse(BaseSchema):
    """Schema for FAQ list response."""

    items: list[FAQResponse]
    total: int


# ============================
# Support Dashboard Schemas
# ============================


class TicketStatsResponse(BaseSchema):
    """Schema for ticket statistics."""

    open: int = Field(0, description="Open tickets")
    in_progress: int = Field(0, description="In progress tickets")
    resolved: int = Field(0, description="Resolved tickets")
    closed: int = Field(0, description="Closed tickets")
    average_rating: float = Field(0.0, description="Average rating")


class SupportDashboardResponse(BaseSchema):
    """Schema for support dashboard response."""

    ticket_stats: TicketStatsResponse
    faq_count: int = Field(0, description="Total FAQs")
    recent_tickets: list[TicketResponse] = Field(default_factory=list)


# ============================
# Rating Schemas
# ============================


class TicketRatingRequest(BaseSchema):
    """Schema for ticket rating request."""

    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    feedback: str | None = Field(None, max_length=500, description="Feedback")


class FAQFeedbackRequest(BaseSchema):
    """Schema for FAQ feedback request."""

    helpful: bool = Field(..., description="Whether FAQ was helpful")


__all__ = [
    "FAQBase",
    "FAQCategoryBase",
    "FAQCategoryCreate",
    "FAQCategoryResponse",
    "FAQCreate",
    "FAQFeedbackRequest",
    "FAQListResponse",
    "FAQResponse",
    "FAQUpdate",
    "SupportDashboardResponse",
    "TicketBase",
    "TicketCategoryBase",
    "TicketCategoryCreate",
    "TicketCategoryResponse",
    "TicketCreate",
    "TicketListResponse",
    "TicketMessageBase",
    "TicketMessageCreate",
    "TicketMessageResponse",
    "TicketRatingRequest",
    "TicketResponse",
    "TicketStatsResponse",
    "TicketUpdate",
]
