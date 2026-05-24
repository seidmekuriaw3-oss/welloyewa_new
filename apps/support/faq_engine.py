# ============================
# WOLLOYEWA STORE BOT - FAQ ENGINE
# ============================
"""FAQ search and suggestion engine for customer self-service."""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from core.logger import logger
from apps.support.models import FAQ, FAQCategory
from apps.support.repository import FAQRepository


class FAQEngine:
    """
    FAQ search and suggestion engine.
    
    Features:
    - Full-text search across FAQs
    - Category-based filtering
    - Suggested answers based on user queries
    - Helpful/unhelpful tracking
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.faq_repo = FAQRepository(db)
    
    async def search_faqs(
        self,
        query: str,
        category_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[FAQ]:
        """
        Search FAQs by keyword.
        
        Args:
            query: Search query
            category_id: Filter by category
            limit: Maximum results
            
        Returns:
            List of matching FAQs
        """
        search_pattern = f"%{query}%"
        
        conditions = [FAQ.is_active == True]
        
        if category_id:
            conditions.append(FAQ.category_id == category_id)
        
        stmt = select(FAQ).where(
            or_(
                FAQ.question.ilike(search_pattern),
                FAQ.question_am.ilike(search_pattern),
                FAQ.answer.ilike(search_pattern),
                FAQ.answer_am.ilike(search_pattern),
                FAQ.keywords.cast(str).ilike(search_pattern)
            ),
            *conditions
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        faqs = result.scalars().all()
        
        # Sort by relevance (simple: keyword matches in question are more relevant)
        query_lower = query.lower()
        def relevance_score(faq: FAQ) -> int:
            score = 0
            if query_lower in faq.question.lower():
                score += 10
            if query_lower in (faq.question_am or "").lower():
                score += 10
            if faq.keywords and any(query_lower in kw.lower() for kw in faq.keywords):
                score += 5
            if query_lower in faq.answer.lower():
                score += 2
            return score
        
        faqs.sort(key=relevance_score, reverse=True)
        
        return faqs
    
    async def get_faq_by_slug(self, slug: str) -> Optional[FAQ]:
        """Get FAQ by slug."""
        return await self.faq_repo.get_by_slug(slug)
    
    async def get_faqs_by_category(
        self,
        category_id: int,
        limit: int = 50,
    ) -> List[FAQ]:
        """Get FAQs by category."""
        return await self.faq_repo.get_by_category(category_id, limit)
    
    async def get_all_categories_with_counts(self) -> List[Dict[str, Any]]:
        """Get all FAQ categories with FAQ counts."""
        result = await self.db.execute(
            select(FAQCategory).where(FAQCategory.is_active == True)
            .order_by(FAQCategory.display_order)
        )
        categories = result.scalars().all()
        
        categories_with_counts = []
        for category in categories:
            count_result = await self.db.execute(
                select(func.count()).select_from(FAQ)
                .where(FAQ.category_id == category.id, FAQ.is_active == True)
            )
            faq_count = count_result.scalar() or 0
            
            categories_with_counts.append({
                "id": category.id,
                "name": category.name,
                "name_am": category.name_am,
                "slug": category.slug,
                "icon": category.icon,
                "faq_count": faq_count,
                "display_order": category.display_order,
            })
        
        return categories_with_counts
    
    async def get_suggested_answers(
        self,
        query: str,
        limit: int = 5,
    ) -> List[FAQ]:
        """
        Get suggested answers based on user query.
        
        Args:
            query: User's question or query
            limit: Maximum suggestions
            
        Returns:
            List of suggested FAQs
        """
        # Search for matching FAQs
        faqs = await self.search_faqs(query, limit=limit * 2)
        
        # Filter and rank suggestions
        suggestions = []
        query_words = set(query.lower().split())
        
        for faq in faqs:
            # Calculate match score
            score = 0
            
            # Check question match
            question_words = set(faq.question.lower().split())
            match_count = len(query_words & question_words)
            score += match_count * 10
            
            # Check keywords match
            if faq.keywords:
                keyword_matches = sum(1 for kw in faq.keywords if kw.lower() in query.lower())
                score += keyword_matches * 5
            
            # Boost popular FAQs
            helpful_ratio = faq.helpful_percentage
            if helpful_ratio > 80:
                score += 5
            
            suggestions.append((faq, score))
        
        # Sort by score and take top results
        suggestions.sort(key=lambda x: x[1], reverse=True)
        
        return [faq for faq, _ in suggestions[:limit]]
    
    async def mark_faq_helpful(self, faq_id: int) -> None:
        """Mark an FAQ as helpful."""
        await self.faq_repo.mark_helpful(faq_id)
        logger.info(f"FAQ {faq_id} marked as helpful")
    
    async def mark_faq_not_helpful(self, faq_id: int) -> None:
        """Mark an FAQ as not helpful."""
        await self.faq_repo.mark_not_helpful(faq_id)
        logger.info(f"FAQ {faq_id} marked as not helpful")
    
    async def get_popular_faqs(self, limit: int = 10) -> List[FAQ]:
        """Get most helpful FAQs."""
        return await self.faq_repo.get_popular_faqs(limit)
    
    async def get_faq_stats(self) -> Dict[str, Any]:
        """Get FAQ statistics."""
        total = await self.faq_repo.count()
        
        result = await self.db.execute(
            select(
                func.sum(FAQ.helpful_count).label("total_helpful"),
                func.sum(FAQ.not_helpful_count).label("total_not_helpful"),
            )
        )
        row = result.one()
        
        total_helpful = row.total_helpful or 0
        total_not_helpful = row.total_not_helpful or 0
        total_votes = total_helpful + total_not_helpful
        
        return {
            "total_faqs": total,
            "total_helpful_votes": total_helpful,
            "total_not_helpful_votes": total_not_helpful,
            "average_helpful_percentage": (total_helpful / total_votes * 100) if total_votes > 0 else 0,
        }


async def search_faqs(
    db: AsyncSession,
    query: str,
    category_id: Optional[int] = None,
    limit: int = 20,
) -> List[FAQ]:
    """Search FAQs by keyword."""
    engine = FAQEngine(db)
    return await engine.search_faqs(query, category_id, limit)


async def get_faq_by_slug(db: AsyncSession, slug: str) -> Optional[FAQ]:
    """Get FAQ by slug."""
    engine = FAQEngine(db)
    return await engine.get_faq_by_slug(slug)


async def get_faqs_by_category(
    db: AsyncSession,
    category_id: int,
    limit: int = 50,
) -> List[FAQ]:
    """Get FAQs by category."""
    engine = FAQEngine(db)
    return await engine.get_faqs_by_category(category_id, limit)


async def get_suggested_answers(
    db: AsyncSession,
    query: str,
    limit: int = 5,
) -> List[FAQ]:
    """Get suggested answers based on user query."""
    engine = FAQEngine(db)
    return await engine.get_suggested_answers(query, limit)


__all__ = [
    "FAQEngine",
    "search_faqs",
    "get_faq_by_slug",
    "get_faqs_by_category",
    "get_suggested_answers",
]