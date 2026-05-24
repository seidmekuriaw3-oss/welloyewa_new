# ============================
# WOLLOYEWA STORE BOT - ANALYTICS SERVICES
# ============================
"""Business intelligence and analytics services for reporting."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from core.exceptions import NotFoundError
from apps.analytics.repository import AnalyticsRepository, SalesRepository, UserActivityRepository
from apps.orders.repository import OrderRepository
from apps.users.repository import UserRepository
from apps.products.repository import ProductRepository
from apps.inventory.repository import InventoryRepository


class SalesAnalyticsService:
    """Service for sales analytics and reporting."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sales_repo = SalesRepository(db)
        self.order_repo = OrderRepository(db)
    
    async def get_daily_sales(
        self,
        days: int = 30,
        vendor_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get daily sales for the last N days."""
        return await self.sales_repo.get_daily_sales(days, vendor_id)
    
    async def get_weekly_sales(
        self,
        weeks: int = 12,
        vendor_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get weekly sales for the last N weeks."""
        return await self.sales_repo.get_weekly_sales(weeks, vendor_id)
    
    async def get_monthly_sales(
        self,
        months: int = 12,
        vendor_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get monthly sales for the last N months."""
        return await self.sales_repo.get_monthly_sales(months, vendor_id)
    
    async def get_sales_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        vendor_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get sales summary for a date range."""
        return await self.sales_repo.get_sales_summary(start_date, end_date, vendor_id)
    
    async def get_top_products(
        self,
        limit: int = 10,
        days: int = 30,
        vendor_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get top selling products."""
        return await self.sales_repo.get_top_products(limit, days, vendor_id)
    
    async def get_top_categories(
        self,
        limit: int = 10,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get top selling categories."""
        return await self.sales_repo.get_top_categories(limit, days)
    
    async def get_revenue_by_payment_method(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Get revenue breakdown by payment method."""
        return await self.sales_repo.get_revenue_by_payment_method(start_date, end_date)
    
    async def get_average_order_value(
        self,
        start_date: datetime,
        end_date: datetime,
        vendor_id: Optional[int] = None,
    ) -> float:
        """Get average order value for a date range."""
        summary = await self.get_sales_summary(start_date, end_date, vendor_id)
        total_orders = summary.get("total_orders", 0)
        total_revenue = summary.get("total_revenue", 0)
        
        if total_orders == 0:
            return 0.0
        
        return float(total_revenue) / total_orders


class UserAnalyticsService:
    """Service for user behavior analytics."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.activity_repo = UserActivityRepository(db)
        self.order_repo = OrderRepository(db)
    
    async def get_user_growth(
        self,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get daily user registration growth."""
        return await self.activity_repo.get_user_growth(days)
    
    async def get_user_retention(
        self,
        cohort_days: int = 30,
    ) -> Dict[str, Any]:
        """Get user retention metrics."""
        return await self.activity_repo.get_user_retention(cohort_days)
    
    async def get_active_users(
        self,
        days: int = 7,
    ) -> int:
        """Get number of active users in the last N days."""
        return await self.activity_repo.get_active_users_count(days)
    
    async def get_user_lifetime_value(
        self,
        user_id: int,
    ) -> float:
        """Get lifetime value for a specific user."""
        stats = await self.order_repo.get_user_stats(user_id)
        return stats.get("total_spent", 0)
    
    async def get_average_user_ltv(self) -> float:
        """Get average customer lifetime value."""
        users = await self.user_repo.get_active_users(limit=1000)
        total_ltv = 0.0
        count = 0
        
        for user in users:
            stats = await self.order_repo.get_user_stats(user.id)
            total_ltv += stats.get("total_spent", 0)
            count += 1
        
        return total_ltv / count if count > 0 else 0
    
    async def get_user_segments(self) -> Dict[str, int]:
        """Get user segmentation counts."""
        from apps.analytics.user_behavior import UserBehaviorAnalyzer
        
        analyzer = UserBehaviorAnalyzer(self.db)
        return await analyzer.get_user_segments()
    
    async def get_conversion_funnel(self) -> Dict[str, float]:
        """Get conversion funnel metrics."""
        return await self.activity_repo.get_conversion_funnel()


class ProductAnalyticsService:
    """Service for product performance analytics."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.inventory_repo = InventoryRepository(db)
        self.sales_repo = SalesRepository(db)
    
    async def get_product_performance(
        self,
        product_id: int,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get performance metrics for a specific product."""
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product", product_id)
        
        # Get sales data
        sales_data = await self.sales_repo.get_product_sales(product_id, days)
        
        return {
            "product_id": product_id,
            "product_name": product.name,
            "views": product.views_count,
            "sales": product.sales_count,
            "revenue": sales_data.get("total_revenue", 0),
            "conversion_rate": (product.sales_count / product.views_count * 100) if product.views_count > 0 else 0,
            "average_rating": product.rating,
            "stock_quantity": product.stock_quantity,
            "status": product.status,
        }
    
    async def get_inventory_analytics(
        self,
        vendor_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get inventory analytics."""
        stats = await self.inventory_repo.get_inventory_stats(vendor_id)
        value = await self.inventory_repo.get_inventory_value(vendor_id)
        
        stats["total_value"] = value
        return stats
    
    async def get_low_stock_report(
        self,
        vendor_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get low stock products report."""
        low_stock = await self.inventory_repo.get_low_stock(vendor_id, limit=100)
        
        report = []
        for inventory in low_stock:
            report.append({
                "product_id": inventory.product_id,
                "product_name": inventory.product.name if inventory.product else "Unknown",
                "current_stock": inventory.quantity,
                "threshold": inventory.low_stock_threshold,
                "sku": inventory.sku,
            })
        
        return report


class DashboardService:
    """Service for dashboard summaries and KPIs."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sales_service = SalesAnalyticsService(db)
        self.user_service = UserAnalyticsService(db)
        self.product_service = ProductAnalyticsService(db)
    
    async def get_dashboard_summary(
        self,
        vendor_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get main dashboard summary with key metrics."""
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        # Today's sales
        today_sales = await self.sales_service.get_sales_summary(today_start, now, vendor_id)
        
        # Weekly sales
        weekly_sales = await self.sales_service.get_sales_summary(week_start, now, vendor_id)
        
        # Monthly sales
        monthly_sales = await self.sales_service.get_sales_summary(month_start, now, vendor_id)
        
        # Orders
        recent_orders = await self.sales_service.sales_repo.get_recent_orders(limit=10)
        
        # Top products
        top_products = await self.sales_service.get_top_products(limit=5, days=30, vendor_id=vendor_id)
        
        # Active users
        active_users = await self.user_service.get_active_users(days=7)
        
        # Low stock
        low_stock = await self.product_service.get_low_stock_report(vendor_id)
        
        return {
            "today": {
                "revenue": float(today_sales.get("total_revenue", 0)),
                "orders": today_sales.get("total_orders", 0),
                "average_order_value": float(today_sales.get("avg_order_value", 0)),
            },
            "weekly": {
                "revenue": float(weekly_sales.get("total_revenue", 0)),
                "orders": weekly_sales.get("total_orders", 0),
                "average_order_value": float(weekly_sales.get("avg_order_value", 0)),
            },
            "monthly": {
                "revenue": float(monthly_sales.get("total_revenue", 0)),
                "orders": monthly_sales.get("total_orders", 0),
                "average_order_value": float(monthly_sales.get("avg_order_value", 0)),
            },
            "recent_orders": recent_orders,
            "top_products": top_products,
            "active_users": active_users,
            "low_stock_count": len(low_stock),
            "low_stock_products": low_stock[:5],
        }


class AnalyticsService:
    """Main analytics service combining all analytics features."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sales = SalesAnalyticsService(db)
        self.users = UserAnalyticsService(db)
        self.products = ProductAnalyticsService(db)
        self.dashboard = DashboardService(db)
    
    async def generate_sales_report(
        self,
        start_date: datetime,
        end_date: datetime,
        vendor_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive sales report."""
        summary = await self.sales.get_sales_summary(start_date, end_date, vendor_id)
        daily = await self.sales.get_daily_sales((end_date - start_date).days, vendor_id)
        top_products = await self.sales.get_top_products(limit=10, days=(end_date - start_date).days, vendor_id=vendor_id)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "summary": summary,
            "daily_breakdown": daily,
            "top_products": top_products,
        }


__all__ = [
    "SalesAnalyticsService",
    "UserAnalyticsService",
    "ProductAnalyticsService",
    "DashboardService",
    "AnalyticsService",
]