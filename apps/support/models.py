# ============================
# WOLLOYEWA STORE BOT - SUPPORT MODELS
# ============================
"""Customer support database models for tickets, FAQs, and help articles."""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float,
    BigInteger, Text, JSON, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from apps.common.models import BaseModel, TimestampMixin

if TYPE_CHECKING:
    from apps.users.models import User


class TicketCategory(BaseModel, TimestampMixin):
    """Support ticket category."""
    
    __tablename__ = "ticket_categories"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_am: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # SLA settings
    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    auto_assign_to: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Relationships
    tickets: Mapped[List["Ticket"]] = relationship("Ticket", back_populates="category")
    
    def __repr__(self) -> str:
        return f"<TicketCategory(id={self.id}, name={self.name})>"


class Ticket(BaseModel, TimestampMixin):
    """Support ticket model."""
    
    __tablename__ = "tickets"
    
    # Ticket identification
    ticket_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    
    # Relationships
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ticket_categories.id"), nullable=True)
    
    # Ticket content
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", index=True)  # open, in_progress, resolved, closed
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")  # low, medium, high, urgent
    
    # Metadata
    attachments: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    ticket_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # Changed from metadata to ticket_metadata
    
    # Resolution
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Ratings
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        primaryjoin="User.id == foreign(Ticket.user_id)",
    )
    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to],
        primaryjoin="Ticket.assigned_to == User.id",
    )
    category: Mapped[Optional["TicketCategory"]] = relationship(
        "TicketCategory",
        back_populates="tickets",
        foreign_keys=[category_id],
        primaryjoin="TicketCategory.id == foreign(Ticket.category_id)",
    )
    messages: Mapped[List["TicketMessage"]] = relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        primaryjoin="Ticket.id == foreign(TicketMessage.ticket_id)",
    )
    
    @hybrid_property
    def is_open(self) -> bool:
        """Check if ticket is open."""
        return self.status in ["open", "in_progress"]
    
    @hybrid_property
    def response_time_hours(self) -> Optional[float]:
        """Calculate response time in hours."""
        if self.messages and len(self.messages) > 0:
            first_response = self.messages[0].created_at
            delta = first_response - self.created_at
            return delta.total_seconds() / 3600
        return None
    
    def resolve(self, note: str, resolved_by: int) -> None:
        """Resolve the ticket."""
        self.status = "resolved"
        self.resolved_at = datetime.utcnow()
        self.resolution_note = note
        self.assigned_to = resolved_by
    
    def close(self, closed_by: int) -> None:
        """Close the ticket."""
        self.status = "closed"
        self.closed_at = datetime.utcnow()
        self.closed_by = closed_by
    
    def reopen(self) -> None:
        """Reopen a closed ticket."""
        self.status = "open"
        self.resolved_at = None
        self.closed_at = None
    
    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, number={self.ticket_number}, status={self.status})>"


class TicketMessage(BaseModel, TimestampMixin):
    """Ticket message/reply model."""
    
    __tablename__ = "ticket_messages"
    
    ticket_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_staff_reply: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attachments: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="messages")
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self) -> str:
        return f"<TicketMessage(id={self.id}, ticket_id={self.ticket_id}, user_id={self.user_id})>"


class FAQCategory(BaseModel, TimestampMixin):
    """FAQ category model."""
    
    __tablename__ = "faq_categories"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_am: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Relationships
    faqs: Mapped[List["FAQ"]] = relationship("FAQ", back_populates="category")
    
    def __repr__(self) -> str:
        return f"<FAQCategory(id={self.id}, name={self.name})>"


class FAQ(BaseModel, TimestampMixin):
    """Frequently Asked Question model."""
    
    __tablename__ = "faqs"
    
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("faq_categories.id"), nullable=True, index=True)
    
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    question_am: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    answer_am: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(550), nullable=False, unique=True, index=True)
    
    # Metadata
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Search keywords
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    not_helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Display
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Relationships
    category: Mapped[Optional["FAQCategory"]] = relationship("FAQCategory", back_populates="faqs")
    
    @hybrid_property
    def helpful_percentage(self) -> float:
        """Calculate helpful percentage."""
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return 0.0
        return (self.helpful_count / total) * 100
    
    def mark_helpful(self) -> None:
        """Mark FAQ as helpful."""
        self.helpful_count += 1
    
    def mark_not_helpful(self) -> None:
        """Mark FAQ as not helpful."""
        self.not_helpful_count += 1
    
    def __repr__(self) -> str:
        return f"<FAQ(id={self.id}, question={self.question[:50]})>"


class SupportArticle(BaseModel, TimestampMixin):
    """Knowledge base article model."""
    
    __tablename__ = "support_articles"
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    title_am: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_am: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(280), nullable=False, unique=True, index=True)
    
    # Metadata
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    author_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # SEO
    meta_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Statistics
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Status
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def increment_views(self) -> None:
        """Increment article view count."""
        self.views += 1
    
    def __repr__(self) -> str:
        return f"<SupportArticle(id={self.id}, title={self.title[:50]})>"