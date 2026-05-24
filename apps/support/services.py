# ============================
# WOLLOYEWA STORE BOT - SUPPORT SERVICES
# ============================
"""Business logic for customer support operations."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from core.exceptions import NotFoundError, ValidationError, PermissionError
from core.utils.string_utils import generate_random_string
from apps.support.repository import TicketRepository, TicketMessageRepository, FAQRepository
from apps.support.models import Ticket, TicketMessage, FAQ
from apps.support.schemas import TicketCreate, TicketUpdate, TicketMessageCreate, FAQCreate, FAQUpdate
from apps.users.services import UserService


class TicketService:
    """Service for support ticket management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ticket_repo = TicketRepository(db)
        self.message_repo = TicketMessageRepository(db)
        self.user_service = UserService(db)
    
    async def generate_ticket_number(self) -> str:
        """Generate a unique ticket number."""
        prefix = "TKT"
        while True:
            random_part = generate_random_string(8, include_digits=True, include_special=False)
            ticket_number = f"{prefix}-{random_part}"
            existing = await self.ticket_repo.get_by_number(ticket_number)
            if not existing:
                return ticket_number
    
    async def create_ticket(self, user_id: int, data: TicketCreate) -> Ticket:
        """Create a new support ticket."""
        user = await self.user_service.get_user(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        ticket_number = await self.generate_ticket_number()
        
        ticket = await self.ticket_repo.create({
            "ticket_number": ticket_number,
            "user_id": user_id,
            "category_id": data.category_id,
            "subject": data.subject,
            "message": data.message,
            "priority": data.priority,
            "status": "open",
        })
        
        logger.info(f"Ticket created: {ticket_number} by user {user_id}")
        return ticket
    
    async def get_ticket(self, ticket_id: int, user_id: Optional[int] = None, is_admin: bool = False) -> Ticket:
        """Get ticket by ID with permission check."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)
        
        # Check permission
        if not is_admin and ticket.user_id != user_id:
            raise PermissionError("You don't have permission to view this ticket")
        
        return ticket
    
    async def get_ticket_by_number(self, ticket_number: str) -> Optional[Ticket]:
        """Get ticket by number."""
        return await self.ticket_repo.get_by_number(ticket_number)
    
    async def update_ticket(self, ticket_id: int, data: TicketUpdate, is_admin: bool = False) -> Ticket:
        """Update a ticket."""
        ticket = await self.get_ticket(ticket_id)
        
        update_data = data.dict(exclude_unset=True)
        
        # Only admins can change status, priority, assignment
        if not is_admin:
            allowed_fields = []
            update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not update_data:
            return ticket
        
        updated = await self.ticket_repo.update(ticket_id, update_data)
        logger.info(f"Ticket {ticket.ticket_number} updated")
        return updated
    
    async def add_message(self, ticket_id: int, user_id: int, data: TicketMessageCreate, is_staff: bool = False) -> TicketMessage:
        """Add a message to a ticket."""
        ticket = await self.get_ticket(ticket_id, user_id, is_staff)
        
        # Update ticket status if closed
        if ticket.status == "closed":
            await self.ticket_repo.update(ticket_id, {"status": "open"})
        
        message = await self.message_repo.create({
            "ticket_id": ticket_id,
            "user_id": user_id,
            "message": data.message,
            "is_staff_reply": is_staff,
            "attachments": data.attachments,
        })
        
        logger.info(f"Message added to ticket {ticket.ticket_number} by user {user_id}")
        return message
    
    async def assign_ticket(self, ticket_id: int, assigned_to: int, admin_id: int) -> Ticket:
        """Assign ticket to a support agent."""
        ticket = await self.get_ticket(ticket_id)
        
        updated = await self.ticket_repo.update(ticket_id, {
            "assigned_to": assigned_to,
            "status": "in_progress",
        })
        
        logger.info(f"Ticket {ticket.ticket_number} assigned to agent {assigned_to} by admin {admin_id}")
        return updated
    
    async def resolve_ticket(self, ticket_id: int, resolution_note: str, resolved_by: int) -> Ticket:
        """Resolve a ticket."""
        ticket = await self.get_ticket(ticket_id)
        
        updated = await self.ticket_repo.update(ticket_id, {
            "status": "resolved",
            "resolved_at": datetime.utcnow(),
            "resolution_note": resolution_note,
        })
        
        logger.info(f"Ticket {ticket.ticket_number} resolved by {resolved_by}")
        return updated
    
    async def close_ticket(self, ticket_id: int, closed_by: int) -> Ticket:
        """Close a resolved ticket."""
        ticket = await self.get_ticket(ticket_id)
        
        if ticket.status != "resolved":
            raise ValidationError("Only resolved tickets can be closed")
        
        updated = await self.ticket_repo.update(ticket_id, {
            "status": "closed",
            "closed_at": datetime.utcnow(),
            "closed_by": closed_by,
        })
        
        logger.info(f"Ticket {ticket.ticket_number} closed by {closed_by}")
        return updated
    
    async def reopen_ticket(self, ticket_id: int, user_id: int) -> Ticket:
        """Reopen a closed ticket."""
        ticket = await self.get_ticket(ticket_id, user_id)
        
        if ticket.status not in ["resolved", "closed"]:
            raise ValidationError(f"Cannot reopen ticket with status: {ticket.status}")
        
        updated = await self.ticket_repo.update(ticket_id, {
            "status": "open",
            "resolved_at": None,
            "closed_at": None,
        })
        
        logger.info(f"Ticket {ticket.ticket_number} reopened by user {user_id}")
        return updated
    
    async def rate_ticket(self, ticket_id: int, user_id: int, rating: int, feedback: Optional[str] = None) -> Ticket:
        """Rate a resolved ticket."""
        ticket = await self.get_ticket(ticket_id, user_id)
        
        if ticket.status != "resolved":
            raise ValidationError("Only resolved tickets can be rated")
        
        updated = await self.ticket_repo.update(ticket_id, {
            "rating": rating,
            "feedback": feedback,
        })
        
        logger.info(f"Ticket {ticket.ticket_number} rated {rating}/5 by user {user_id}")
        return updated
    
    async def get_user_tickets(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Ticket], int]:
        """Get tickets for a user."""
        return await self.ticket_repo.get_by_user(user_id, status, limit, offset)
    
    async def get_all_tickets(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Ticket], int]:
        """Get all tickets (admin only)."""
        return await self.ticket_repo.get_all_tickets(status, priority, assigned_to, limit, offset)
    
    async def get_ticket_messages(self, ticket_id: int) -> List[TicketMessage]:
        """Get all messages for a ticket."""
        return await self.message_repo.get_by_ticket(ticket_id)


class FAQService:
    """Service for FAQ management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.faq_repo = FAQRepository(db)
    
    async def create_faq(self, data: FAQCreate) -> FAQ:
        """Create a new FAQ."""
        from core.utils.string_utils import slugify
        
        slug = slugify(data.question)
        
        # Ensure unique slug
        counter = 1
        while await self.faq_repo.get_by_slug(slug):
            slug = f"{slugify(data.question)}-{counter}"
            counter += 1
        
        faq = await self.faq_repo.create({
            "category_id": data.category_id,
            "question": data.question,
            "question_am": data.question_am,
            "answer": data.answer,
            "answer_am": data.answer_am,
            "slug": slug,
            "keywords": data.keywords,
            "display_order": data.display_order,
        })
        
        logger.info(f"FAQ created: {faq.question[:50]}")
        return faq
    
    async def get_faq(self, faq_id: int) -> FAQ:
        """Get FAQ by ID."""
        faq = await self.faq_repo.get_by_id(faq_id)
        if not faq:
            raise NotFoundError("FAQ", faq_id)
        return faq
    
    async def get_faq_by_slug(self, slug: str) -> Optional[FAQ]:
        """Get FAQ by slug."""
        return await self.faq_repo.get_by_slug(slug)
    
    async def update_faq(self, faq_id: int, data: FAQUpdate) -> FAQ:
        """Update an FAQ."""
        faq = await self.get_faq(faq_id)
        
        update_data = data.dict(exclude_unset=True)
        
        # Update slug if question changed
        if data.question and data.question != faq.question:
            from core.utils.string_utils import slugify
            update_data["slug"] = slugify(data.question)
        
        updated = await self.faq_repo.update(faq_id, update_data)
        logger.info(f"FAQ updated: {updated.question[:50]}")
        return updated
    
    async def delete_faq(self, faq_id: int) -> bool:
        """Delete an FAQ."""
        faq = await self.get_faq(faq_id)
        result = await self.faq_repo.delete(faq_id)
        logger.info(f"FAQ deleted: {faq.question[:50]}")
        return result
    
    async def search_faqs(self, query: str, limit: int = 20) -> List[FAQ]:
        """Search FAQs by question or keywords."""
        return await self.faq_repo.search(query, limit)
    
    async def get_faqs_by_category(self, category_id: int, limit: int = 50) -> List[FAQ]:
        """Get FAQs by category."""
        return await self.faq_repo.get_by_category(category_id, limit)
    
    async def mark_helpful(self, faq_id: int) -> None:
        """Mark FAQ as helpful."""
        await self.faq_repo.mark_helpful(faq_id)
    
    async def mark_not_helpful(self, faq_id: int) -> None:
        """Mark FAQ as not helpful."""
        await self.faq_repo.mark_not_helpful(faq_id)


class SupportService:
    """Main support service combining tickets and FAQs."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ticket_service = TicketService(db)
        self.faq_service = FAQService(db)
    
    async def get_support_dashboard(self) -> Dict[str, Any]:
        """Get support dashboard statistics."""
        open_tickets, _ = await self.ticket_service.get_all_tickets(status="open")
        in_progress, _ = await self.ticket_service.get_all_tickets(status="in_progress")
        resolved, _ = await self.ticket_service.get_all_tickets(status="resolved")
        
        return {
            "open_tickets": len(open_tickets),
            "in_progress_tickets": len(in_progress),
            "resolved_tickets": len(resolved),
            "total_tickets": len(open_tickets) + len(in_progress) + len(resolved),
            "faq_count": await self.faq_repo.count(),
        }


__all__ = ["TicketService", "FAQService", "SupportService"]