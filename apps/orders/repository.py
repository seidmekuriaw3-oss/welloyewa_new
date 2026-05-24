# ============================
# WOLLOYEWA STORE BOT - ORDER REPOSITORIES
# ============================
"""Database repositories for Order and OrderItem models."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.repository import BaseRepository
from apps.orders.models import Order, OrderItem
from core.constants import OrderStatus, PaymentStatus


class OrderRepository(BaseRepository[Order]):
    """Repository for Order model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Order, db)
    
    async def get_by_order_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number."""
        query = select(Order).where(Order.order_number == order_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_user(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Order], int]:
        """Get orders by user ID."""
        conditions = [Order.user_id == user_id]
        if status:
            conditions.append(Order.status == status)
        
        # Count query
        count_query = select(func.count()).select_from(Order).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Main query
        query = select(Order).where(and_(*conditions))
        query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        
        return result.scalars().all(), total
    
    async def get_by_vendor(
        self,
        vendor_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Order], int]:
        """Get orders by vendor ID."""
        conditions = [Order.vendor_id == vendor_id]
        if status:
            conditions.append(Order.status == status)
        
        count_query = select(func.count()).select_from(Order).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        query = select(Order).where(and_(*conditions))
        query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        
        return result.scalars().all(), total
    
    async def get_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Order]:
        """Get orders by status."""
        query = select(Order).where(Order.status == status)
        query = query.order_by(Order.created_at.asc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_pending_orders(self, limit: int = 100) -> List[Order]:
        """Get pending orders."""
        return await self.get_by_status(OrderStatus.PENDING.value, limit)
    
    async def get_processing_orders(self, limit: int = 100) -> List[Order]:
        """Get processing orders."""
        return await self.get_by_status(OrderStatus.PROCESSING.value, limit)
    
    async def get_orders_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        status: Optional[str] = None,
    ) -> List[Order]:
        """Get orders within date range."""
        conditions = [
            Order.created_at >= start_date,
            Order.created_at <= end_date,
        ]
        if status:
            conditions.append(Order.status == status)
        
        query = select(Order).where(and_(*conditions))
        query = query.order_by(Order.created_at)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_recent_orders(self, hours: int = 24, limit: int = 50) -> List[Order]:
        """Get recent orders."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = select(Order).where(Order.created_at >= cutoff)
        query = query.order_by(Order.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get order statistics for a user."""
        query = select(
            func.count().label("total_orders"),
            func.sum(Order.total).label("total_spent"),
            func.avg(Order.total).label("avg_order_value"),
        ).where(Order.user_id == user_id, Order.payment_status == PaymentStatus.PAID.value)
        
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "total_orders": row.total_orders or 0,
            "total_spent": float(row.total_spent) if row.total_spent else 0,
            "avg_order_value": float(row.avg_order_value) if row.avg_order_value else 0,
        }
    
    async def get_vendor_stats(self, vendor_id: int) -> Dict[str, Any]:
        """Get order statistics for a vendor."""
        query = select(
            func.count().label("total_orders"),
            func.sum(Order.total).label("total_revenue"),
            func.sum(func.case((Order.status == OrderStatus.PENDING.value, 1), else_=0)).label("pending"),
            func.sum(func.case((Order.status == OrderStatus.PROCESSING.value, 1), else_=0)).label("processing"),
            func.sum(func.case((Order.status == OrderStatus.SHIPPED.value, 1), else_=0)).label("shipped"),
            func.sum(func.case((Order.status == OrderStatus.DELIVERED.value, 1), else_=0)).label("delivered"),
            func.sum(func.case((Order.status == OrderStatus.CANCELLED.value, 1), else_=0)).label("cancelled"),
        ).where(Order.vendor_id == vendor_id)
        
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "total_orders": row.total_orders or 0,
            "total_revenue": float(row.total_revenue) if row.total_revenue else 0,
            "pending": row.pending or 0,
            "processing": row.processing or 0,
            "shipped": row.shipped or 0,
            "delivered": row.delivered or 0,
            "cancelled": row.cancelled or 0,
        }
    
    async def get_daily_sales(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily sales for the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            func.date(Order.created_at).label("date"),
            func.count().label("order_count"),
            func.sum(Order.total).label("total_sales"),
        ).where(
            Order.created_at >= cutoff,
            Order.payment_status == PaymentStatus.PAID.value
        ).group_by(func.date(Order.created_at)).order_by("date")
        
        result = await self.db.execute(query)
        return [
            {"date": row.date, "order_count": row.order_count, "total_sales": float(row.total_sales)}
            for row in result.all()
        ]


class OrderItemRepository(BaseRepository[OrderItem]):
    """Repository for OrderItem model operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(OrderItem, db)
    
    async def get_by_order(self, order_id: int) -> List[OrderItem]:
        """Get all items for an order."""
        query = select(OrderItem).where(OrderItem.order_id == order_id)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_product(self, product_id: int, limit: int = 100) -> List[OrderItem]:
        """Get order items by product ID."""
        query = select(OrderItem).where(OrderItem.product_id == product_id)
        query = query.order_by(OrderItem.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_best_selling_products(
        self,
        limit: int = 10,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get best selling products."""
        conditions = []
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            conditions.append(OrderItem.created_at >= cutoff)
        
        query = select(
            OrderItem.product_id,
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.total_price).label("total_revenue"),
        ).where(and_(*conditions)).group_by(
            OrderItem.product_id, OrderItem.product_name
        ).order_by(func.sum(OrderItem.quantity).desc()).limit(limit)
        
        result = await self.db.execute(query)
        return [
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "total_quantity": row.total_quantity,
                "total_revenue": float(row.total_revenue),
            }
            for row in result.all()
        ]


__all__ = ["OrderRepository", "OrderItemRepository"]