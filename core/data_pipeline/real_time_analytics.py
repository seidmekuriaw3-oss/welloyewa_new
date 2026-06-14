# ============================
# WOLLOYEWA STORE BOT - REAL-TIME ANALYTICS
# ============================
"""Real-time analytics tracking for user behavior and business metrics."""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field

from core.config import settings
from core.logger import logger
from infrastructure.redis.client import get_redis_client


@dataclass
class UserAction:
    """Record of a user action."""
    
    user_id: int
    action_type: str  # 'view', 'click', 'purchase', 'search', 'add_to_cart'
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    ip_address: Optional[str] = None


class RealTimeAnalytics:
    """
    Real-time analytics tracking system.
    
    Features:
    - Track user actions in real-time
    - Calculate popular products
    - Monitor user engagement
    - Session tracking
    - Hot product detection
    """
    
    def __init__(self):
        self._redis = None
        self._action_buffer: deque = deque(maxlen=10000)
        self._product_views: Dict[int, int] = defaultdict(int)
        self._product_purchases: Dict[int, int] = defaultdict(int)
        self._user_sessions: Dict[int, Dict[str, Any]] = {}
        self._active_users: Dict[int, float] = {}
        
        # Time windows for analytics
        self._hot_window_seconds = 3600  # Last hour
        self._trending_window_seconds = 86400  # Last 24 hours
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def track_action(self, action: UserAction) -> None:
        """
        Track a user action in real-time.
        
        Args:
            action: UserAction record
        """
        # Store in buffer
        self._action_buffer.append(action)
        
        # Update in-memory counts
        if action.action_type == 'view':
            product_id = action.data.get('product_id')
            if product_id:
                self._product_views[product_id] = self._product_views.get(product_id, 0) + 1
        elif action.action_type == 'purchase':
            product_id = action.data.get('product_id')
            if product_id:
                self._product_purchases[product_id] = self._product_purchases.get(product_id, 0) + 1
        
        # Update user session
        if action.user_id:
            self._active_users[action.user_id] = action.timestamp
            if action.user_id not in self._user_sessions:
                self._user_sessions[action.user_id] = {
                    'start_time': action.timestamp,
                    'actions': [],
                }
            self._user_sessions[action.user_id]['actions'].append(action)
        
        # Store in Redis for persistence
        try:
            redis = await self._get_redis()
            key = f"analytics:action:{int(action.timestamp)}"
            await redis.hset(key, str(action.user_id), action.action_type)
            await redis.expire(key, 86400)  # Expire after 24 hours
        except Exception as e:
            logger.error(f"Failed to store action in Redis: {e}")
        
        logger.debug(f"Tracked action: {action.action_type} by user {action.user_id}")
    
    async def track_product_view(self, user_id: int, product_id: int, **kwargs) -> None:
        """Convenience method to track product view."""
        action = UserAction(
            user_id=user_id,
            action_type='view',
            data={'product_id': product_id, **kwargs},
        )
        await self.track_action(action)
    
    async def track_add_to_cart(self, user_id: int, product_id: int, quantity: int = 1, **kwargs) -> None:
        """Convenience method to track add to cart."""
        action = UserAction(
            user_id=user_id,
            action_type='add_to_cart',
            data={'product_id': product_id, 'quantity': quantity, **kwargs},
        )
        await self.track_action(action)
    
    async def track_purchase(self, user_id: int, product_id: int, order_id: int, price: float, **kwargs) -> None:
        """Convenience method to track purchase."""
        action = UserAction(
            user_id=user_id,
            action_type='purchase',
            data={
                'product_id': product_id,
                'order_id': order_id,
                'price': price,
                **kwargs
            },
        )
        await self.track_action(action)
    
    async def track_search(self, user_id: int, query: str, results_count: int, **kwargs) -> None:
        """Convenience method to track search."""
        action = UserAction(
            user_id=user_id,
            action_type='search',
            data={'query': query, 'results_count': results_count, **kwargs},
        )
        await self.track_action(action)
    
    async def get_hot_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get currently hot products based on recent views.
        
        Args:
            limit: Number of products to return
            
        Returns:
            List of product IDs with view counts
        """
        # Filter views within hot window
        current_time = time.time()
        cutoff = current_time - self._hot_window_seconds
        
        recent_views = defaultdict(int)
        for action in self._action_buffer:
            if action.action_type == 'view' and action.timestamp >= cutoff:
                product_id = action.data.get('product_id')
                if product_id:
                    recent_views[product_id] += 1
        
        # Sort by view count
        sorted_products = sorted(
            recent_views.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {'product_id': pid, 'view_count': count}
            for pid, count in sorted_products
        ]
    
    async def get_trending_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending products based on purchase velocity.
        
        Args:
            limit: Number of products to return
            
        Returns:
            List of product IDs with purchase counts
        """
        current_time = time.time()
        cutoff = current_time - self._trending_window_seconds
        
        recent_purchases = defaultdict(int)
        for action in self._action_buffer:
            if action.action_type == 'purchase' and action.timestamp >= cutoff:
                product_id = action.data.get('product_id')
                if product_id:
                    recent_purchases[product_id] += 1
        
        sorted_products = sorted(
            recent_purchases.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {'product_id': pid, 'purchase_count': count}
            for pid, count in sorted_products
        ]
    
    async def get_active_users(self, minutes: int = 5) -> int:
        """
        Get number of active users in the last N minutes.
        
        Args:
            minutes: Time window in minutes
            
        Returns:
            Number of active users
        """
        cutoff = time.time() - (minutes * 60)
        active = sum(1 for ts in self._active_users.values() if ts >= cutoff)
        return active
    
    async def get_user_activity_stats(self, user_id: int, hours: int = 24) -> Dict[str, Any]:
        """
        Get activity statistics for a specific user.
        
        Args:
            user_id: User ID
            hours: Time window in hours
            
        Returns:
            Dictionary with activity statistics
        """
        cutoff = time.time() - (hours * 3600)
        
        actions = [
            action for action in self._action_buffer
            if action.user_id == user_id and action.timestamp >= cutoff
        ]
        
        action_counts = defaultdict(int)
        for action in actions:
            action_counts[action.action_type] += 1
        
        return {
            'user_id': user_id,
            'total_actions': len(actions),
            'action_breakdown': dict(action_counts),
            'time_window_hours': hours,
            'is_active': len(actions) > 0,
        }
    
    async def get_conversion_rate(self, hours: int = 24) -> float:
        """
        Calculate conversion rate (purchases / views).
        
        Args:
            hours: Time window in hours
            
        Returns:
            Conversion rate as percentage
        """
        cutoff = time.time() - (hours * 3600)
        
        views = 0
        purchases = 0
        
        for action in self._action_buffer:
            if action.timestamp >= cutoff:
                if action.action_type == 'view':
                    views += 1
                elif action.action_type == 'purchase':
                    purchases += 1
        
        if views == 0:
            return 0.0
        
        return (purchases / views) * 100
    
    async def get_revenue_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get revenue statistics.
        
        Args:
            hours: Time window in hours
            
        Returns:
            Dictionary with revenue statistics
        """
        cutoff = time.time() - (hours * 3600)
        
        total_revenue = 0.0
        order_count = 0
        unique_orders = set()
        
        for action in self._action_buffer:
            if action.action_type == 'purchase' and action.timestamp >= cutoff:
                order_id = action.data.get('order_id')
                price = action.data.get('price', 0)
                
                if order_id not in unique_orders:
                    unique_orders.add(order_id)
                    total_revenue += price
                    order_count += 1
        
        return {
            'total_revenue': round(total_revenue, 2),
            'order_count': order_count,
            'average_order_value': round(total_revenue / order_count, 2) if order_count > 0 else 0,
            'time_window_hours': hours,
        }
    
    async def get_popular_search_queries(self, limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get popular search queries.
        
        Args:
            limit: Number of queries to return
            hours: Time window in hours
            
        Returns:
            List of popular search queries with counts
        """
        cutoff = time.time() - (hours * 3600)
        
        search_counts = defaultdict(int)
        for action in self._action_buffer:
            if action.action_type == 'search' and action.timestamp >= cutoff:
                query = action.data.get('query', '').lower()
                if query:
                    search_counts[query] += 1
        
        sorted_queries = sorted(
            search_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {'query': query, 'count': count}
            for query, count in sorted_queries
        ]
    
    async def clear_old_data(self, days: int = 7) -> None:
        """Clear analytics data older than specified days."""
        cutoff = time.time() - (days * 86400)
        
        # Clear action buffer
        self._action_buffer = deque(
            [a for a in self._action_buffer if a.timestamp >= cutoff],
            maxlen=10000
        )
        
        # Clear old sessions
        self._active_users = {
            uid: ts for uid, ts in self._active_users.items()
            if ts >= cutoff
        }
        
        logger.info(f"Cleared analytics data older than {days} days")


# Global analytics instance
real_time_analytics = RealTimeAnalytics()


async def track_user_action(user_id: int, action_type: str, data: Dict[str, Any]) -> None:
    """Convenience function to track user action."""
    action = UserAction(user_id=user_id, action_type=action_type, data=data)
    await real_time_analytics.track_action(action)


async def track_product_view(user_id: int, product_id: int) -> None:
    """Convenience function to track product view."""
    await real_time_analytics.track_product_view(user_id, product_id)


async def track_search_query(user_id: int, query: str, results_count: int) -> None:
    """Convenience function to track search query."""
    await real_time_analytics.track_search(user_id, query, results_count)


async def get_hot_products(limit: int = 10) -> List[Dict[str, Any]]:
    """Convenience function to get hot products."""
    return await real_time_analytics.get_hot_products(limit)


async def get_user_activity_stats(user_id: int) -> Dict[str, Any]:
    """Convenience function to get user activity stats."""
    return await real_time_analytics.get_user_activity_stats(user_id)


__all__ = [
    "RealTimeAnalytics",
    "UserAction",
    "real_time_analytics",
    "track_user_action",
    "track_product_view",
    "track_search_query",
    "get_hot_products",
    "get_user_activity_stats",
]