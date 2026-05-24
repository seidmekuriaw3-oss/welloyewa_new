# ============================
# WOLLOYEWA STORE BOT - SUPPORT REPOSITORIES
# ============================
"""Database repositories for support models."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.repository import BaseRepository
from apps.support.models import Ticket, TicketMessage, FAQ
from core.logger import logger


class TicketRepository(BaseRepository[Ticket]):
    """Repository for Ticket model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Ticket, db)
    
    async def get_by_number(self, ticket_number: str) -> Optional[Ticket]:
        """Get ticket by ticket number."""
        query = select(Ticket).where(Ticket.ticket_number == ticket_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_user(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Ticket], int]:
        """Get tickets for a specific user."""
        conditions = [Ticket.user_id == user_id]
        if status:
            conditions.append(Ticket.status == status)
        
        # Count query
        count_query = select(func.count()).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Main query
        query = select(Ticket).where(and_(*conditions))
        query = query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        
        return result.scalars().all(), total
    
    async def get_all_tickets(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Ticket], int]:
        """Get all tickets with filters (admin)."""
        conditions = []
        if status:
            conditions.append(Ticket.status == status)
        if priority:
            conditions.append(Ticket.priority == priority)
        if assigned_to:
            conditions.append(Ticket.assigned_to == assigned_to)
        
        count_query = select(func.count()).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        query = select(Ticket).where(and_(*conditions))
        query = query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        
        return result.scalars().all(), total
    
    async def get_open_tickets(self, limit: int = 100) -> List[Ticket]:
        """Get open tickets."""
        query = select(Ticket).where(Ticket.status.in_(["open", "in_progress"]))
        query = query.order_by(Ticket.priority.desc(), Ticket.created_at.asc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_overdue_tickets(self, sla_hours: int = 24) -> List[Ticket]:
        """Get tickets that are overdue for response."""
        cutoff = datetime.utcnow()
        query = select(Ticket).where(
            Ticket.status.in_(["open", "in_progress"]),
            Ticket.created_at < cutoff
        )
        result = await self.db.execute(query)
        
        overdue = []
        for ticket in result.scalars().all():
            if ticket.response_time_hours and ticket.response_time_hours > sla_hours:
                overdue.append(ticket)
        
        return overdue
    
    async def get_ticket_stats(self) -> Dict[str, Any]:
        """Get ticket statistics."""
        query = select(
            func.sum(func.case((Ticket.status == "open", 1), else_=0)).label("open"),
            func.sum(func.case((Ticket.status == "in_progress", 1), else_=0)).label("in_progress"),
            func.sum(func.case((Ticket.status == "resolved", 1), else_=0)).label("resolved"),
            func.sum(func.case((Ticket.status == "closed", 1), else_=0)).label("closed"),
            func.avg(func.case((Ticket.rating.isnot(None), Ticket.rating), else_=0)).label("avg_rating"),
        )
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "open": row.open or 0,
            "in_progress": row.in_progress or 0,
            "resolved": row.resolved or 0,
            "closed": row.closed or 0,
            "average_rating": float(row.avg_rating) if row.avg_rating else 0,
        }


class TicketMessageRepository(BaseRepository[TicketMessage]):
    """Repository for TicketMessage model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(TicketMessage, db)
    
    async def get_by_ticket(self, ticket_id: int, limit: int = 100) -> List[TicketMessage]:
        """Get all messages for a ticket."""
        query = select(TicketMessage).where(TicketMessage.ticket_id == ticket_id)
        query = query.order_by(TicketMessage.created_at.asc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_last_message(self, ticket_id: int) -> Optional[TicketMessage]:
        """Get the last message in a ticket."""
        query = select(TicketMessage).where(TicketMessage.ticket_id == ticket_id)
        query = query.order_by(TicketMessage.created_at.desc()).limit(1)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


class FAQRepository(BaseRepository[FAQ]):
    """Repository for FAQ model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(FAQ, db)
    
    async def get_by_slug(self, slug: str) -> Optional[FAQ]:
        """Get FAQ by slug."""
        query = select(FAQ).where(FAQ.slug == slug, FAQ.is_active == True)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_category(
        self,
        category_id: int,
        limit: int = 50,
    ) -> List[FAQ]:
        """Get FAQs by category."""
        query = select(FAQ).where(
            FAQ.category_id == category_id,
            FAQ.is_active == True
        )
        query = query.order_by(FAQ.display_order).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> List[FAQ]:
        """Search FAQs by question or keywords."""
        search_pattern = f"%{query}%"
        
        stmt = select(FAQ).where(
            FAQ.is_active == True,
            or_(
                FAQ.question.ilike(search_pattern),
                FAQ.question_am.ilike(search_pattern),
                FAQ.answer.ilike(search_pattern),
                FAQ.answer_am.ilike(search_pattern),
                FAQ.keywords.cast(String).ilike(search_pattern)
            )
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_popular_faqs(self, limit: int = 10) -> List[FAQ]:
        """Get most helpful FAQs."""
        query = select(FAQ).where(FAQ.is_active == True)
        query = query.order_by((FAQ.helpful_count - FAQ.not_helpful_count).desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def mark_helpful(self, faq_id: int) -> None:
        """Mark FAQ as helpful."""
        await self.db.execute(
            update(FAQ)
            .where(FAQ.id == faq_id)
            .values(helpful_count=FAQ.helpful_count + 1)
        )
        await self.db.flush()
    
    async def mark_not_helpful(self, faq_id: int) -> None:
        """Mark FAQ as not helpful."""
        await self.db.execute(
            update(FAQ)
            .where(FAQ.id == faq_id)
            .values(not_helpful_count=FAQ.not_helpful_count + 1)
        )
        await self.db.flush()


__all__ = ["TicketRepository", "TicketMessageRepository", "FAQRepository"]