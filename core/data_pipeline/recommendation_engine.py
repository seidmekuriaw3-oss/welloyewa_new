# ============================
# WOLLOYEWA STORE BOT - RECOMMENDATION ENGINE
# ============================
"""Product recommendation engine using collaborative filtering and popularity."""

import math
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass

from core.logger import logger
from core.redis.client import get_redis_client


@dataclass
class Recommendation:
    """Product recommendation result."""
    
    product_id: int
    score: float
    reason: str  # 'popular', 'purchased_together', 'similar', 'personalized'


class RecommendationEngine:
    """
    Product recommendation engine.
    
    Algorithms:
    - Popularity-based (trending products)
    - Collaborative filtering (users who bought X also bought Y)
    - Content-based (similar products)
    - Personalized (user purchase history)
    """
    
    def __init__(self):
        self._redis = None
        self._product_similarity: Dict[int, List[Tuple[int, float]]] = {}
        self._frequently_bought_together: Dict[int, List[Tuple[int, int]]] = {}
        self._user_purchase_history: Dict[int, Set[int]] = defaultdict(set)
        self._product_purchase_count: Counter = Counter()
        
        # Cache settings
        self._cache_ttl = 3600  # 1 hour
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def update_product_similarity(self, product_id: int, similar_products: List[Tuple[int, float]]) -> None:
        """
        Update similarity scores for a product.
        
        Args:
            product_id: Product ID
            similar_products: List of (product_id, similarity_score)
        """
        self._product_similarity[product_id] = similar_products
        logger.debug(f"Updated similarity for product {product_id}: {len(similar_products)} similar products")
    
    async def update_frequently_bought_together(self, product_id: int, related: List[Tuple[int, int]]) -> None:
        """
        Update frequently bought together data.
        
        Args:
            product_id: Product ID
            related: List of (related_product_id, frequency)
        """
        self._frequently_bought_together[product_id] = related
        logger.debug(f"Updated frequently bought for product {product_id}: {len(related)} related products")
    
    async def record_purchase(self, user_id: int, product_id: int, order_id: int) -> None:
        """
        Record a purchase for collaborative filtering.
        
        Args:
            user_id: User ID
            product_id: Product ID
            order_id: Order ID
        """
        self._user_purchase_history[user_id].add(product_id)
        self._product_purchase_count[product_id] += 1
        
        # Update frequently bought together in real-time
        await self._update_frequently_bought_together(product_id, user_id, order_id)
        
        logger.debug(f"Recorded purchase: user {user_id} bought product {product_id}")
    
    async def _update_frequently_bought_together(self, product_id: int, user_id: int, order_id: int) -> None:
        """Update frequently bought together statistics."""
        # Get all products in the same order
        # In production, fetch from database
        # For now, this is a placeholder
        pass
    
    async def get_popular_recommendations(
        self,
        limit: int = 10,
        exclude_ids: Optional[Set[int]] = None,
    ) -> List[Recommendation]:
        """
        Get popular product recommendations.
        
        Args:
            limit: Number of recommendations
            exclude_ids: Product IDs to exclude
            
        Returns:
            List of recommendations
        """
        exclude = exclude_ids or set()
        
        # Get top purchased products
        popular = self._product_purchase_count.most_common(limit + len(exclude))
        
        recommendations = []
        for product_id, count in popular:
            if product_id in exclude:
                continue
            recommendations.append(Recommendation(
                product_id=product_id,
                score=count,
                reason="popular",
            ))
            if len(recommendations) >= limit:
                break
        
        return recommendations
    
    async def get_frequently_bought_together(
        self,
        product_id: int,
        limit: int = 5,
    ) -> List[Recommendation]:
        """
        Get products frequently bought together with a product.
        
        Args:
            product_id: Product ID
            limit: Number of recommendations
            
        Returns:
            List of recommendations
        """
        if product_id not in self._frequently_bought_together:
            return []
        
        related = self._frequently_bought_together[product_id][:limit]
        
        return [
            Recommendation(
                product_id=rel_id,
                score=freq,
                reason="purchased_together",
            )
            for rel_id, freq in related
        ]
    
    async def get_similar_products(
        self,
        product_id: int,
        limit: int = 5,
    ) -> List[Recommendation]:
        """
        Get similar products based on content similarity.
        
        Args:
            product_id: Product ID
            limit: Number of recommendations
            
        Returns:
            List of recommendations
        """
        if product_id not in self._product_similarity:
            return []
        
        similar = self._product_similarity[product_id][:limit]
        
        return [
            Recommendation(
                product_id=sim_id,
                score=score,
                reason="similar",
            )
            for sim_id, score in similar
        ]
    
    async def get_personalized_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        exclude_ids: Optional[Set[int]] = None,
    ) -> List[Recommendation]:
        """
        Get personalized recommendations based on user history.
        
        Args:
            user_id: User ID
            limit: Number of recommendations
            exclude_ids: Product IDs to exclude
            
        Returns:
            List of recommendations
        """
        exclude = exclude_ids or set()
        purchased = self._user_purchase_history.get(user_id, set())
        
        if not purchased:
            # Fall back to popular recommendations
            return await self.get_popular_recommendations(limit, exclude)
        
        # Collaborative filtering: find products bought by similar users
        product_scores = defaultdict(float)
        
        # For each product the user purchased, find frequently bought together
        for purchased_id in purchased:
            together = self._frequently_bought_together.get(purchased_id, [])
            for rel_id, freq in together:
                if rel_id not in purchased and rel_id not in exclude:
                    product_scores[rel_id] += freq
        
        # Sort by score
        sorted_products = sorted(
            product_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        recommendations = []
        for product_id, score in sorted_products:
            recommendations.append(Recommendation(
                product_id=product_id,
                score=score,
                reason="personalized",
            ))
        
        # If not enough personalized, fill with popular
        if len(recommendations) < limit:
            remaining = limit - len(recommendations)
            exclude.update(purchased)
            exclude.update([r.product_id for r in recommendations])
            popular = await self.get_popular_recommendations(remaining, exclude)
            recommendations.extend(popular)
        
        return recommendations
    
    async def get_hybrid_recommendations(
        self,
        user_id: Optional[int] = None,
        product_id: Optional[int] = None,
        limit: int = 10,
        exclude_ids: Optional[Set[int]] = None,
    ) -> List[Recommendation]:
        """
        Get hybrid recommendations combining multiple strategies.
        
        Args:
            user_id: User ID (for personalized)
            product_id: Product ID (for similar products)
            limit: Number of recommendations
            exclude_ids: Product IDs to exclude
            
        Returns:
            List of recommendations
        """
        exclude = exclude_ids or set()
        
        if user_id:
            # Personalized recommendations
            return await self.get_personalized_recommendations(user_id, limit, exclude)
        elif product_id:
            # Similar products
            similar = await self.get_similar_products(product_id, limit)
            if len(similar) < limit:
                # Fill with frequently bought together
                together = await self.get_frequently_bought_together(product_id, limit - len(similar))
                similar.extend(together)
            return similar
        else:
            # Popular recommendations
            return await self.get_popular_recommendations(limit, exclude)
    
    async def get_recommendations_for_cart(
        self,
        cart_items: List[int],
        limit: int = 5,
    ) -> List[Recommendation]:
        """
        Get recommendations based on current cart items.
        
        Args:
            cart_items: List of product IDs in cart
            limit: Number of recommendations
            
        Returns:
            List of recommendations
        """
        if not cart_items:
            return await self.get_popular_recommendations(limit)
        
        product_scores = defaultdict(float)
        
        for item_id in cart_items:
            together = self._frequently_bought_together.get(item_id, [])
            for rel_id, freq in together:
                if rel_id not in cart_items:
                    product_scores[rel_id] += freq
        
        sorted_products = sorted(
            product_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            Recommendation(
                product_id=pid,
                score=score,
                reason="frequently_bought_together",
            )
            for pid, score in sorted_products
        ]
    
    async def update_cache(self) -> None:
        """Update recommendation cache in Redis."""
        try:
            redis = await self._get_redis()
            
            # Cache popular recommendations
            popular = await self.get_popular_recommendations(100)
            await redis.setex(
                "rec:popular",
                self._cache_ttl,
                str([r.product_id for r in popular])
            )
            
            logger.info("Updated recommendation cache")
            
        except Exception as e:
            logger.error(f"Failed to update recommendation cache: {e}")
    
    async def clear_cache(self) -> None:
        """Clear recommendation cache."""
        try:
            redis = await self._get_redis()
            keys = await redis.keys("rec:*")
            if keys:
                await redis.delete(*keys)
            logger.info("Cleared recommendation cache")
        except Exception as e:
            logger.error(f"Failed to clear recommendation cache: {e}")


# Global recommendation engine instance
recommendation_engine = RecommendationEngine()


async def get_product_recommendations(
    user_id: Optional[int] = None,
    limit: int = 10,
) -> List[Recommendation]:
    """Convenience function to get product recommendations."""
    return await recommendation_engine.get_hybrid_recommendations(user_id=user_id, limit=limit)


async def get_similar_products(product_id: int, limit: int = 5) -> List[Recommendation]:
    """Convenience function to get similar products."""
    return await recommendation_engine.get_similar_products(product_id, limit)


async def get_frequently_bought_together(product_id: int, limit: int = 5) -> List[Recommendation]:
    """Convenience function to get frequently bought together products."""
    return await recommendation_engine.get_frequently_bought_together(product_id, limit)


async def get_personalized_recommendations(user_id: int, limit: int = 10) -> List[Recommendation]:
    """Convenience function to get personalized recommendations."""
    return await recommendation_engine.get_personalized_recommendations(user_id, limit)


__all__ = [
    "RecommendationEngine",
    "Recommendation",
    "recommendation_engine",
    "get_product_recommendations",
    "get_similar_products",
    "get_frequently_bought_together",
    "get_personalized_recommendations",
]