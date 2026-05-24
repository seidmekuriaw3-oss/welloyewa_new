# ============================
# WOLLOYEWA STORE BOT - REVIEWS MANAGEMENT
# ============================
"""Product review management with moderation and analytics."""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from core.logger import logger
from core.exceptions import NotFoundError, PermissionError, ValidationError
from apps.products.models import Review, Product
from core.constants import ProductStatus


class ReviewManager:
    """
    Manager for product reviews and ratings.
    
    Features:
    - Review creation and moderation
    - Rating calculation and updates
    - Review analytics and summaries
    - Vendor responses to reviews
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_review(
        self,
        user_id: int,
        product_id: int,
        rating: int,
        title: Optional[str] = None,
        comment: Optional[str] = None,
        comment_am: Optional[str] = None,
        images: Optional[List[str]] = None,
        order_id: Optional[int] = None,
    ) -> Review:
        """
        Create a new product review.
        
        Args:
            user_id: User ID
            product_id: Product ID
            rating: Rating (1-5)
            title: Review title
            comment: Review comment
            comment_am: Amharic comment
            images: List of image URLs
            order_id: Order ID for verified purchase
            
        Returns:
            Created Review
        """
        # Check if user already reviewed this product
        existing = await self.get_user_review(user_id, product_id)
        if existing:
            raise ValidationError("You have already reviewed this product")
        
        # Create review
        review = Review(
            user_id=user_id,
            product_id=product_id,
            rating=rating,
            title=title,
            comment=comment,
            comment_am=comment_am,
            images=images,
            order_id=order_id,
            is_verified_purchase=order_id is not None,
            is_approved=False,  # Requires moderation
        )
        
        self.db.add(review)
        await self.db.flush()
        
        # Update product rating
        await self.update_product_rating(product_id)
        
        logger.info(f"Review created: user {user_id} for product {product_id}, rating {rating}")
        return review
    
    async def get_review(self, review_id: int) -> Optional[Review]:
        """Get review by ID."""
        return await self.db.get(Review, review_id)
    
    async def get_user_review(self, user_id: int, product_id: int) -> Optional[Review]:
        """Get user's review for a product."""
        query = select(Review).where(
            Review.user_id == user_id,
            Review.product_id == product_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_product_reviews(
        self,
        product_id: int,
        approved_only: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Review], int]:
        """
        Get reviews for a product.
        
        Args:
            product_id: Product ID
            approved_only: Show only approved reviews
            limit: Maximum number of reviews
            offset: Number to skip
            
        Returns:
            Tuple of (reviews, total_count)
        """
        conditions = [Review.product_id == product_id]
        if approved_only:
            conditions.append(Review.is_approved == True)
        
        # Count query
        count_query = select(func.count()).select_from(Review).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Main query
        query = select(Review).where(and_(*conditions))
        query = query.order_by(Review.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        
        return result.scalars().all(), total
    
    async def get_pending_reviews(self, limit: int = 50) -> List[Review]:
        """Get reviews pending approval."""
        query = select(Review).where(Review.is_approved == False)
        query = query.order_by(Review.created_at.asc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def approve_review(self, review_id: int, admin_id: int) -> Review:
        """Approve a review."""
        review = await self.get_review(review_id)
        if not review:
            raise NotFoundError("Review", review_id)
        
        review.is_approved = True
        review.approved_at = datetime.utcnow()
        review.approved_by = admin_id
        
        await self.db.flush()
        
        # Update product rating
        await self.update_product_rating(review.product_id)
        
        logger.info(f"Review {review_id} approved by admin {admin_id}")
        return review
    
    async def reject_review(self, review_id: int, reason: Optional[str] = None) -> bool:
        """Reject and delete a review."""
        review = await self.get_review(review_id)
        if not review:
            return False
        
        product_id = review.product_id
        await self.db.delete(review)
        await self.db.flush()
        
        # Update product rating
        await self.update_product_rating(product_id)
        
        logger.info(f"Review {review_id} rejected: {reason}")
        return True
    
    async def add_vendor_response(self, review_id: int, vendor_id: int, response: str) -> Review:
        """Add vendor response to a review."""
        review = await self.get_review(review_id)
        if not review:
            raise NotFoundError("Review", review_id)
        
        # Check if vendor owns the product
        product = await self.db.get(Product, review.product_id)
        if not product or product.vendor_id != vendor_id:
            raise PermissionError("You don't have permission to respond to this review")
        
        review.vendor_response = response
        review.vendor_response_at = datetime.utcnow()
        
        await self.db.flush()
        
        logger.info(f"Vendor {vendor_id} responded to review {review_id}")
        return review
    
    async def update_product_rating(self, product_id: int) -> None:
        """Update product's average rating and review count."""
        product = await self.db.get(Product, product_id)
        if not product:
            return
        
        # Calculate average rating from approved reviews
        query = select(
            func.avg(Review.rating).label("avg_rating"),
            func.count().label("review_count")
        ).where(
            Review.product_id == product_id,
            Review.is_approved == True
        )
        
        result = await self.db.execute(query)
        row = result.one()
        
        product.rating = float(row.avg_rating) if row.avg_rating else 0.0
        product.reviews_count = row.review_count or 0
        
        await self.db.flush()
        logger.debug(f"Updated rating for product {product_id}: {product.rating} ({product.reviews_count} reviews)")
    
    async def get_review_summary(self, product_id: int) -> Dict[str, Any]:
        """
        Get review summary statistics for a product.
        
        Returns:
            Dictionary with rating distribution and averages
        """
        query = select(
            func.count().label("total"),
            func.avg(Review.rating).label("average"),
            func.sum(func.case((Review.rating == 5, 1), else_=0)).label("rating_5"),
            func.sum(func.case((Review.rating == 4, 1), else_=0)).label("rating_4"),
            func.sum(func.case((Review.rating == 3, 1), else_=0)).label("rating_3"),
            func.sum(func.case((Review.rating == 2, 1), else_=0)).label("rating_2"),
            func.sum(func.case((Review.rating == 1, 1), else_=0)).label("rating_1"),
        ).where(
            Review.product_id == product_id,
            Review.is_approved == True
        )
        
        result = await self.db.execute(query)
        row = result.one()
        
        total = row.total or 0
        average = float(row.average) if row.average else 0.0
        
        return {
            "total_reviews": total,
            "average_rating": round(average, 1),
            "rating_distribution": {
                5: row.rating_5 or 0,
                4: row.rating_4 or 0,
                3: row.rating_3 or 0,
                2: row.rating_2 or 0,
                1: row.rating_1 or 0,
            },
        }
    
    async def mark_review_helpful(self, review_id: int, user_id: int) -> bool:
        """Mark a review as helpful."""
        review = await self.get_review(review_id)
        if not review:
            return False
        
        review.helpful_count += 1
        await self.db.flush()
        return True
    
    async def mark_review_not_helpful(self, review_id: int, user_id: int) -> bool:
        """Mark a review as not helpful."""
        review = await self.get_review(review_id)
        if not review:
            return False
        
        review.not_helpful_count += 1
        await self.db.flush()
        return True
    
    async def delete_review(self, review_id: int, user_id: int, is_admin: bool = False) -> bool:
        """Delete a review."""
        review = await self.get_review(review_id)
        if not review:
            return False
        
        # Check permission
        if not is_admin and review.user_id != user_id:
            raise PermissionError("You don't have permission to delete this review")
        
        product_id = review.product_id
        await self.db.delete(review)
        await self.db.flush()
        
        # Update product rating
        await self.update_product_rating(product_id)
        
        logger.info(f"Review {review_id} deleted by {'admin' if is_admin else 'user'} {user_id}")
        return True


async def calculate_product_rating(db: AsyncSession, product_id: int) -> Dict[str, Any]:
    """Convenience function to calculate product rating."""
    manager = ReviewManager(db)
    return await manager.get_review_summary(product_id)


async def get_product_reviews_summary(
    db: AsyncSession,
    product_id: int,
) -> Dict[str, Any]:
    """Convenience function to get product reviews summary."""
    manager = ReviewManager(db)
    return await manager.get_review_summary(product_id)


__all__ = [
    "ReviewManager",
    "calculate_product_rating",
    "get_product_reviews_summary",
]