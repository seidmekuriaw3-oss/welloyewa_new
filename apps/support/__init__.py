# ============================
# WOLLOYEWA STORE BOT - SUPPORT MODULE
# ============================
"""Customer support module for tickets, FAQs, and helpdesk."""

from apps.support.models import (
    Ticket,
    TicketMessage,
    TicketCategory,
    FAQ,
    FAQCategory,
    SupportArticle,
)
from apps.support.services import (
    TicketService,
    FAQService,
    SupportService,
)
from apps.support.repository import (
    TicketRepository,
    TicketMessageRepository,
    FAQRepository,
)
from apps.support.schemas import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketMessageCreate,
    TicketMessageResponse,
    TicketCategoryCreate,
    TicketCategoryResponse,
    FAQCreate,
    FAQUpdate,
    FAQResponse,
    FAQCategoryCreate,
    FAQCategoryResponse,
)
from apps.support.ticketing import (
    TicketManager,
    create_ticket,
    update_ticket_status,
    add_ticket_message,
    assign_ticket,
)
from apps.support.faq_engine import (
    FAQEngine,
    search_faqs,
    get_faq_by_slug,
    get_faqs_by_category,
    get_suggested_answers,
)

__all__ = [
    # Models
    "Ticket",
    "TicketMessage",
    "TicketCategory",
    "FAQ",
    "FAQCategory",
    "SupportArticle",
    # Services
    "TicketService",
    "FAQService",
    "SupportService",
    # Repositories
    "TicketRepository",
    "TicketMessageRepository",
    "FAQRepository",
    # Schemas
    "TicketCreate",
    "TicketUpdate",
    "TicketResponse",
    "TicketMessageCreate",
    "TicketMessageResponse",
    "TicketCategoryCreate",
    "TicketCategoryResponse",
    "FAQCreate",
    "FAQUpdate",
    "FAQResponse",
    "FAQCategoryCreate",
    "FAQCategoryResponse",
    # Ticketing
    "TicketManager",
    "create_ticket",
    "update_ticket_status",
    "add_ticket_message",
    "assign_ticket",
    # FAQ Engine
    "FAQEngine",
    "search_faqs",
    "get_faq_by_slug",
    "get_faqs_by_category",
    "get_suggested_answers",
]