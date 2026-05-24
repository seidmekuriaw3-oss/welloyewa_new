# ============================
# WOLLOYEWA STORE BOT - USER BEHAVIOR ANALYTICS
# ============================
"""User behavior analysis for personalization and insights."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from core.logger import logger
from apps.orders.models import Order, OrderItem
from apps.users.models import User
from apps.products.models import Product, Review
from core.constants import OrderStatus


class UserBehaviorAnalyzer:
    """
    User behavior analysis for insights and personalization.
    
    Features:
    - User segmentation
    - Purchase pattern analysis
    - Preference detection
    - Churn risk assessment
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_segments(self) -> Dict[str, int]:
        """Get user segmentation counts."""
        segments = {
            "new_users": 0,
            "active_users": 0,
            "regular_buyers": 0,
            "high_value": 0,
            "at_risk": 0,
            "churned": 0,
        }
        
        now = datetime.utcnow()
        month_ago = now - timedelta(days=30)
        week_ago = now - timedelta(days=7)
        
        # Get all users
        users = await self.db.execute(select(User))
        users = users.scalars().all()
        
        for user in users:
            # Get order stats
            orders = await self.db.execute(
                select(Order).where(
                    Order.user_id == user.id,
                    Order.status == OrderStatus.DELIVERED.value
                )
            )
            orders = orders.scalars().all()
            
            order_count = len(orders)
            total_spent = sum(o.total for o in orders)
            
            # Determine segment
            if order_count == 0:
                if user.created_at >= month_ago:
                    segments["new_users"] += 1
                else:
                    segments["churned"] += 1
            elif order_count >= 5:
                segments["regular_buyers"] += 1
                if total_spent >= 10000:
                    segments["high_value"] += 1
            elif user.last_active and user.last_active >= week_ago:
                segments["active_users"] += 1
            elif user.last_active and user.last_active < month_ago:
                segments["at_risk"] += 1
            else:
                segments["active_users"] += 1
        
        return segments
    
    async def get_user_purchase_patterns(
        self,
        user_id: int,
    ) -> Dict[str, Any]:
        """Analyze purchase patterns for a user."""
        # Get user's orders
        orders = await self.db.execute(
            select(Order).where(
                Order.user_id == user_id,
                Order.status == OrderStatus.DELIVERED.value
            ).order_by(Order.created_at)
        )
        orders = orders.scalars().all()
        
        if not orders:
            return {
                "has_purchases": False,
                "message": "No purchase history found",
            }
        
        # Calculate metrics
        order_count = len(orders)
        total_spent = sum(o.total for o in orders)
        avg_order_value = total_spent / order_count
        
        # Calculate frequency
        if order_count > 1:
            days_between = []
            for i in range(1, len(orders)):
                delta = orders[i].created_at - orders[i-1].created_at
                days_between.append(delta.days)
            avg_days_between = sum(days_between) / len(days_between)
        else:
            avg_days_between = 0
        
        # Get preferred categories
        category_counts = defaultdict(int)
        for order in orders:
            items = await self.db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            items = items.scalars().all()
            for item in items:
                product = await self.db.get(Product, item.product_id)
                if product and product.category:
                    category_counts[product.category] += item.quantity
        
        top_categories = sorted(
            category_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            "has_purchases": True,
            "total_orders": order_count,
            "total_spent": float(total_spent),
            "average_order_value": float(avg_order_value),
            "average_days_between_orders": round(avg_days_between, 1),
            "first_purchase": orders[0].created_at.isoformat(),
            "last_purchase": orders[-1].created_at.isoformat(),
            "preferred_categories": [
                {"category": cat, "items": count}
                for cat, count in top_categories
            ],
        }
    
    async def get_product_recommendations(
        self,
        user_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get product recommendations based on user behavior.
        
        Args:
            user_id: User ID
            limit: Number of recommendations
            
        Returns:
            List of recommended products
        """
        # Get user's purchase history
        user_orders = await self.db.execute(
            select(Order).where(Order.user_id == user_id)
        )
        user_orders = user_orders.scalars().all()
        
        if not user_orders:
            # Return popular products for new users
            return await self._get_popular_products(limit)
        
        # Get products user has already bought
        purchased_product_ids = set()
        for order in user_orders:
            items = await self.db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            items = items.scalars().all()
            for item in items:
                purchased_product_ids.add(item.product_id)
        
        # Get user's preferred categories
        category_preferences = await self._get_user_category_preferences(user_id)
        
        # Find products in preferred categories that user hasn't bought
        recommendations = []
        
        for category, weight in category_preferences:
            products = await self.db.execute(
                select(Product).where(
                    Product.category == category,
                    Product.id.notin_(purchased_product_ids),
                    Product.status == "active",
                    Product.stock_quantity > 0
                ).limit(limit)
            )
            products = products.scalars().all()
            
            for product in products:
                recommendations.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "price": float(product.price),
                    "category": product.category,
                    "score": weight,
                })
        
        # Sort by score and limit
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:limit]
    
    async def _get_user_category_preferences(
        self,
        user_id: int,
    ) -> List[Tuple[str, float]]:
        """Get user's category preferences based on purchase history."""
        category_counts = defaultdict(int)
        
        # Get user's orders
        orders = await self.db.execute(
            select(Order).where(Order.user_id == user_id)
        )
        orders = orders.scalars().all()
        
        for order in orders:
            items = await self.db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            items = items.scalars().all()
            
            for item in items:
                product = await self.db.get(Product, item.product_id)
                if product and product.category:
                    category_counts[product.category] += item.quantity
        
        total = sum(category_counts.values())
        if total == 0:
            return []
        
        # Calculate preference weights (normalized)
        preferences = [
            (cat, count / total)
            for cat, count in category_counts.items()
        ]
        preferences.sort(key=lambda x: x[1], reverse=True)
        
        return preferences
    
    async def _get_popular_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular products for new users."""
        popular = await self.db.execute(
            select(Product).where(
                Product.status == "active",
                Product.stock_quantity > 0
            ).order_by(Product.sales_count.desc()).limit(limit)
        )
        popular = popular.scalars().all()
        
        return [
            {
                "product_id": p.id,
                "product_name": p.name,
                "price": float(p.price),
                "category": p.category,
                "score": 1.0,
            }
            for p in popular
        ]
    
    async def get_similar_users(
        self,
        user_id: int,
        limit: int = 10,
    ) -> List[int]:
        """Find users with similar purchase behavior."""
        # Get user's purchased categories
        user_prefs = await self._get_user_category_preferences(user_id)
        user_categories = {cat for cat, _ in user_prefs[:3]}
        
        if not user_categories:
            return []
        
        # Find other users who bought from similar categories
        similar_users = await self.db.execute(
            select(Order.user_id, func.count(Order.id))
            .join(OrderItem, Order.id == OrderItem.order_id)
            .join(Product, OrderItem.product_id == Product.id)
            .where(
                Product.category.in_(user_categories),
                Order.user_id != user_id
            )
            .group_by(Order.user_id)
            .order_by(func.count(Order.id).desc())
            .limit(limit)
        )
        
        return [row[0] for row in similar_users.all()]



__all__ = ["UserBehaviorAnalyzer"]