# ============================
# WOLLOYEWA STORE BOT - TICKETING SYSTEM
# ============================
"""Ticket management system for customer support."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from core.exceptions import NotFoundError, ValidationError
from core.utils.string_utils import generate_random_string
from apps.support.models import Ticket, TicketMessage
from apps.support.repository import TicketRepository, TicketMessageRepository


class TicketManager:
    """
    Ticket manager for customer support.
    
    Features:
    - Create and manage support tickets
    - Track ticket status and assignments
    - Handle ticket messages and replies
    - SLA tracking and overdue detection
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ticket_repo = TicketRepository(db)
        self.message_repo = TicketMessageRepository(db)
    
    async def generate_ticket_number(self) -> str:
        """Generate a unique ticket number."""
        prefix = "TKT"
        while True:
            random_part = generate_random_string(8, include_digits=True, include_special=False)
            ticket_number = f"{prefix}-{random_part}"
            existing = await self.ticket_repo.get_by_number(ticket_number)
            if not existing:
                return ticket_number
    
    async def create_ticket(
        self,
        user_id: int,
        subject: str,
        message: str,
        category_id: Optional[int] = None,
        priority: str = "medium",
        attachments: Optional[List[str]] = None,
    ) -> Ticket:
        """Create a new support ticket."""
        ticket_number = await self.generate_ticket_number()
        
        ticket = await self.ticket_repo.create({
            "ticket_number": ticket_number,
            "user_id": user_id,
            "category_id": category_id,
            "subject": subject,
            "message": message,
            "priority": priority,
            "attachments": attachments,
            "status": "open",
        })
        
        logger.info(f"Ticket created: {ticket_number} by user {user_id}")
        return ticket
    
    async def get_ticket(self, ticket_id: int) -> Ticket:
        """Get ticket by ID."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)
        return ticket
    
    async def get_ticket_by_number(self, ticket_number: str) -> Optional[Ticket]:
        """Get ticket by ticket number."""
        return await self.ticket_repo.get_by_number(ticket_number)
    
    async def add_message(
        self,
        ticket_id: int,
        user_id: int,
        message: str,
        is_staff: bool = False,
        attachments: Optional[List[str]] = None,
    ) -> TicketMessage:
        """Add a message to a ticket."""
        ticket = await self.get_ticket(ticket_id)
        
        # Update ticket status if closed
        if ticket.status == "closed":
            await self.ticket_repo.update(ticket_id, {"status": "open"})
        
        msg = await self.message_repo.create({
            "ticket_id": ticket_id,
            "user_id": user_id,
            "message": message,
            "is_staff_reply": is_staff,
            "attachments": attachments,
        })
        
        logger.info(f"Message added to ticket {ticket.ticket_number}")
        return msg
    
    async def assign_ticket(self, ticket_id: int, assigned_to: int) -> Ticket:
        """Assign ticket to a support agent."""
        ticket = await self.get_ticket(ticket_id)
        
        updated = await self.ticket_repo.update(ticket_id, {
            "assigned_to": assigned_to,
            "status": "in_progress",
        })
        
        logger.info(f"Ticket {ticket.ticket_number} assigned to agent {assigned_to}")
        return updated
    
    async def update_status(
        self,
        ticket_id: int,
        status: str,
        resolution_note: Optional[str] = None,
    ) -> Ticket:
        """Update ticket status."""
        valid_statuses = ["open", "in_progress", "resolved", "closed"]
        if status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        
        update_data = {"status": status}
        
        if status == "resolved":
            update_data["resolved_at"] = datetime.utcnow()
            if resolution_note:
                update_data["resolution_note"] = resolution_note
        elif status == "closed":
            update_data["closed_at"] = datetime.utcnow()
        
        updated = await self.ticket_repo.update(ticket_id, update_data)
        
        logger.info(f"Ticket {updated.ticket_number} status updated to {status}")
        return updated
    
    async def resolve_ticket(self, ticket_id: int, resolution_note: str) -> Ticket:
        """Resolve a ticket."""
        return await self.update_status(ticket_id, "resolved", resolution_note)
    
    async def close_ticket(self, ticket_id: int) -> Ticket:
        """Close a resolved ticket."""
        ticket = await self.get_ticket(ticket_id)
        if ticket.status != "resolved":
            raise ValidationError("Only resolved tickets can be closed")
        
        return await self.update_status(ticket_id, "closed")
    
    async def reopen_ticket(self, ticket_id: int) -> Ticket:
        """Reopen a closed or resolved ticket."""
        ticket = await self.get_ticket(ticket_id)
        if ticket.status not in ["resolved", "closed"]:
            raise ValidationError(f"Cannot reopen ticket with status: {ticket.status}")
        
        return await self.update_status(ticket_id, "open")
    
    async def rate_ticket(
        self,
        ticket_id: int,
        user_id: int,
        rating: int,
        feedback: Optional[str] = None,
    ) -> Ticket:
        """Rate a resolved ticket."""
        ticket = await self.get_ticket(ticket_id)
        
        if ticket.user_id != user_id:
            raise ValidationError("You can only rate your own tickets")
        
        if ticket.status != "resolved":
            raise ValidationError("Only resolved tickets can be rated")
        
        if rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5")
        
        updated = await self.ticket_repo.update(ticket_id, {
            "rating": rating,
            "feedback": feedback,
        })
        
        logger.info(f"Ticket {ticket.ticket_number} rated {rating}/5")
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
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Ticket], int]:
        """Get all tickets (admin)."""
        return await self.ticket_repo.get_all_tickets(status, limit=limit, offset=offset)
    
    async def get_ticket_messages(self, ticket_id: int) -> List[TicketMessage]:
        """Get all messages for a ticket."""
        return await self.message_repo.get_by_ticket(ticket_id)
    
    async def get_overdue_tickets(self, sla_hours: int = 24) -> List[Ticket]:
        """Get tickets that are overdue for response."""
        return await self.ticket_repo.get_overdue_tickets(sla_hours)
    
    async def get_ticket_stats(self) -> Dict[str, Any]:
        """Get ticket statistics."""
        return await self.ticket_repo.get_ticket_stats()


async def create_ticket(
    db: AsyncSession,
    user_id: int,
    subject: str,
    message: str,
    category_id: Optional[int] = None,
    priority: str = "medium",
) -> Ticket:
    """Create a new support ticket."""
    manager = TicketManager(db)
    return await manager.create_ticket(user_id, subject, message, category_id, priority)


async def update_ticket_status(
    db: AsyncSession,
    ticket_id: int,
    status: str,
    resolution_note: Optional[str] = None,
) -> Ticket:
    """Update ticket status."""
    manager = TicketManager(db)
    return await manager.update_status(ticket_id, status, resolution_note)


async def add_ticket_message(
    db: AsyncSession,
    ticket_id: int,
    user_id: int,
    message: str,
    is_staff: bool = False,
) -> TicketMessage:
    """Add a message to a ticket."""
    manager = TicketManager(db)
    return await manager.add_message(ticket_id, user_id, message, is_staff)


async def assign_ticket(
    db: AsyncSession,
    ticket_id: int,
    assigned_to: int,
) -> Ticket:
    """Assign ticket to a support agent."""
    manager = TicketManager(db)
    return await manager.assign_ticket(ticket_id, assigned_to)


__all__ = [
    "TicketManager",
    "create_ticket",
    "update_ticket_status",
    "add_ticket_message",
    "assign_ticket",
]