# ============================
# WOLLOYEWA STORE BOT - ANALYTICS REPOSITORIES
# ============================
"""Database repositories for analytics queries."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from apps.orders.models import Order, OrderItem
from apps.users.models import User
from apps.products.models import Product
from core.constants import OrderStatus, PaymentStatus


class SalesRepository:
    """Repository for sales analytics queries."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_daily_sales(
        self,
        days: int = 30,
        vendor_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get daily sales for the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            func.date(Order.created_at).label("date"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total).label("total_sales"),
            func.avg(Order.total).label("average_order"),
        ).where(
            Order.created_at >= cutoff,
            Order.payment_status == PaymentStatus.PAID.value
        )
        
        if vendor_id:
            query = query.where(Order.vendor_id == vendor_id)
        
        query = query.group_by(func.date(Order.created_at)).order_by("date")
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "date": row.date.isoformat() if row.date else None,
                "order_count": row.order_count or 0,
                "total_sales": float(row.total_sales) if row.total_sales else 0,
                "average_order": float(row.average_order) if row.average_order else 0,
            }
            for row in rows
        ]
    
    async def get_weekly_sales(
        self,
        weeks: int = 12,
        vendor_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get weekly sales for the last N weeks."""
        cutoff = datetime.utcnow() - timedelta(weeks=weeks)
        
        query = select(
            func.year(Order.created_at).label("year"),
            func.week(Order.created_at).label("week"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total).label("total_sales"),
        ).where(
            Order.created_at >= cutoff,
            Order.payment_status == PaymentStatus.PAID.value
        )
        
        if vendor_id:
            query = query.where(Order.vendor_id == vendor_id)
        
        query = query.group_by("year", "week").order_by("year", "week")
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "year": row.year,
                "week": row.week,
                "order_count": row.order_count or 0,
                "total_sales": float(row.total_sales) if row.total_sales else 0,
            }
            for row in rows
        ]
    
    async def get_monthly_sales(
        self,
        months: int = 12,
        vendor_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get monthly sales for the last N months."""
        cutoff = datetime.utcnow() - timedelta(days=months * 30)
        
        query = select(
            func.date_format(Order.created_at, '%Y-%m').label("month"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total).label("total_sales"),
        ).where(
            Order.created_at >= cutoff,
            Order.payment_status == PaymentStatus.PAID.value
        )
        
        if vendor_id:
            query = query.where(Order.vendor_id == vendor_id)
        
        query = query.group_by("month").order_by("month")
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "month": row.month,
                "order_count": row.order_count or 0,
                "total_sales": float(row.total_sales) if row.total_sales else 0,
            }
            for row in rows
        ]
    
    async def get_sales_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        vendor_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get sales summary for a date range."""
        query = select(
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total).label("total_revenue"),
            func.avg(Order.total).label("avg_order_value"),
            func.sum(Order.discount).label("total_discount"),
            func.sum(Order.shipping_fee).label("total_shipping"),
            func.sum(Order.tax).label("total_tax"),
        ).where(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.payment_status == PaymentStatus.PAID.value
        )
        
        if vendor_id:
            query = query.where(Order.vendor_id == vendor_id)
        
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "total_orders": row.total_orders or 0,
            "total_revenue": float(row.total_revenue) if row.total_revenue else 0,
            "avg_order_value": float(row.avg_order_value) if row.avg_order_value else 0,
            "total_discount": float(row.total_discount) if row.total_discount else 0,
            "total_shipping": float(row.total_shipping) if row.total_shipping else 0,
            "total_tax": float(row.total_tax) if row.total_tax else 0,
        }
    
    async def get_top_products(
        self,
        limit: int = 10,
        days: int = 30,
        vendor_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get top selling products."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            OrderItem.product_id,
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.total_price).label("total_revenue"),
        ).join(Order, OrderItem.order_id == Order.id).where(
            Order.created_at >= cutoff,
            Order.payment_status == PaymentStatus.PAID.value
        )
        
        if vendor_id:
            query = query.where(Order.vendor_id == vendor_id)
        
        query = query.group_by(OrderItem.product_id, OrderItem.product_name)
        query = query.order_by(func.sum(OrderItem.quantity).desc()).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "quantity_sold": row.total_quantity or 0,
                "revenue": float(row.total_revenue) if row.total_revenue else 0,
            }
            for row in rows
        ]
    
    async def get_top_categories(
        self,
        limit: int = 10,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get top selling categories."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            Product.category,
            func.count(OrderItem.id).label("items_sold"),
            func.sum(OrderItem.total_price).label("revenue"),
        ).join(OrderItem, Product.id == OrderItem.product_id).join(Order, OrderItem.order_id == Order.id).where(
            Order.created_at >= cutoff,
            Order.payment_status == PaymentStatus.PAID.value,
            Product.category.isnot(None)
        ).group_by(Product.category).order_by(func.sum(OrderItem.total_price).desc()).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "category": row.category,
                "items_sold": row.items_sold or 0,
                "revenue": float(row.revenue) if row.revenue else 0,
            }
            for row in rows
        ]
    
    async def get_revenue_by_payment_method(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Get revenue breakdown by payment method."""
        query = select(
            Order.payment_method,
            func.count(Order.id).label("order_count"),
            func.sum(Order.total).label("total_revenue"),
        ).where(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.payment_status == PaymentStatus.PAID.value
        ).group_by(Order.payment_method)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "payment_method": row.payment_method,
                "order_count": row.order_count or 0,
                "revenue": float(row.total_revenue) if row.total_revenue else 0,
            }
            for row in rows
        ]
    
    async def get_recent_orders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent orders for dashboard."""
        query = select(
            Order.id,
            Order.order_number,
            Order.total,
            Order.status,
            Order.created_at,
            User.first_name,
            User.last_name,
        ).join(User, Order.user_id == User.id).order_by(Order.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "order_id": row.id,
                "order_number": row.order_number,
                "total": float(row.total),
                "status": row.status,
                "created_at": row.created_at.isoformat(),
                "customer_name": f"{row.first_name} {row.last_name or ''}".strip(),
            }
            for row in rows
        ]
    
    async def get_product_sales(
        self,
        product_id: int,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get sales data for a specific product."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.total_price).label("total_revenue"),
        ).where(
            OrderItem.product_id == product_id,
            OrderItem.created_at >= cutoff
        )
        
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "total_quantity": row.total_quantity or 0,
            "total_revenue": float(row.total_revenue) if row.total_revenue else 0,
        }


class UserActivityRepository:
    """Repository for user activity analytics."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_growth(
        self,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get daily user registration growth."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("new_users"),
        ).where(User.created_at >= cutoff).group_by(func.date(User.created_at)).order_by("date")
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "date": row.date.isoformat(),
                "new_users": row.new_users or 0,
            }
            for row in rows
        ]
    
    async def get_user_retention(
        self,
        cohort_days: int = 30,
    ) -> Dict[str, Any]:
        """Get user retention metrics."""
        cutoff = datetime.utcnow() - timedelta(days=cohort_days)
        
        # Get users registered in the period
        query = select(User.id, User.created_at).where(User.created_at >= cutoff)
        result = await self.db.execute(query)
        users = result.all()
        
        if not users:
            return {"cohort_size": 0, "retention_rate": 0}
        
        # Check which users have returned (made an order)
        user_ids = [u.id for u in users]
        orders_query = select(Order.user_id).where(
            Order.user_id.in_(user_ids),
            Order.created_at >= cutoff,
            Order.status == OrderStatus.DELIVERED.value
        ).distinct()
        
        orders_result = await self.db.execute(orders_query)
        returning_users = set(r[0] for r in orders_result.all())
        
        return {
            "cohort_size": len(users),
            "returning_users": len(returning_users),
            "retention_rate": (len(returning_users) / len(users) * 100) if users else 0,
        }
    
    async def get_active_users_count(self, days: int = 7) -> int:
        """Get number of active users in the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(func.count(User.id.distinct())).where(
            User.last_active >= cutoff,
            User.is_deleted == False
        )
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def get_conversion_funnel(self) -> Dict[str, float]:
        """Get conversion funnel metrics."""
        # Total visitors (approximated by unique users who viewed products)
        viewers_query = select(func.count(Product.id)).select_from(Product)
        result = await self.db.execute(viewers_query)
        total_viewers = result.scalar() or 1
        
        # Cart additions
        # This would need a cart table - placeholder
        cart_additions = 0
        
        # Checkouts initiated
        orders_query = select(func.count(Order.id)).where(Order.status != OrderStatus.CANCELLED.value)
        result = await self.db.execute(orders_query)
        checkouts = result.scalar() or 0
        
        # Completed purchases
        purchases_query = select(func.count(Order.id)).where(Order.payment_status == PaymentStatus.PAID.value)
        result = await self.db.execute(purchases_query)
        purchases = result.scalar() or 0
        
        return {
            "view_to_cart": (cart_additions / total_viewers * 100) if total_viewers > 0 else 0,
            "cart_to_checkout": (checkouts / max(cart_additions, 1) * 100) if cart_additions > 0 else 0,
            "checkout_to_purchase": (purchases / max(checkouts, 1) * 100) if checkouts > 0 else 0,
            "overall_conversion": (purchases / total_viewers * 100) if total_viewers > 0 else 0,
        }


class AnalyticsRepository:
    """Main analytics repository combining all analytics queries."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sales = SalesRepository(db)
        self.user_activity = UserActivityRepository(db)


__all__ = [
    "SalesRepository",
    "UserActivityRepository",
    "AnalyticsRepository",
]