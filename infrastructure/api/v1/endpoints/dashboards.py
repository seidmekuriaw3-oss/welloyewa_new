# ============================
# WOLLOYEWA STORE BOT - DASHBOARDS API ENDPOINTS
# ============================
"""Dashboard API endpoints for data visualization and reporting."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from core.dependencies import get_current_user, get_current_vendor, get_current_admin, get_db_session
from core.exceptions import NotFoundError, PermissionError
from apps.analytics.services import DashboardService, SalesAnalyticsService
from apps.analytics.schemas import DashboardSummary, SalesSummaryResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ============================
# Main Dashboard Endpoints
# ============================

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DashboardSummary:
    """
    Get main dashboard summary.
    
    Returns key metrics for the dashboard based on user role.
    """
    dashboard_service = DashboardService(db)
    
    # Determine user type for filtering
    vendor_id = None
    if current_user.get("is_vendor"):
        vendor_id = current_user.get("vendor_id")
    
    summary = await dashboard_service.get_dashboard_summary(vendor_id)
    return DashboardSummary(**summary)


@router.get("/kpi", response_model=Dict[str, Any])
async def get_kpi_metrics(
    period: str = Query("today", pattern="^(today|week|month|year)$"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get KPI metrics for dashboard.
    
    Returns key performance indicators for the selected period.
    """
    sales_service = SalesAnalyticsService(db)
    now = datetime.utcnow()
    
    if period == "today":
        start_date = datetime(now.year, now.month, now.day)
        end_date = now
    elif period == "week":
        start_date = now - timedelta(days=7)
        end_date = now
    elif period == "month":
        start_date = now - timedelta(days=30)
        end_date = now
    else:  # year
        start_date = now - timedelta(days=365)
        end_date = now
    
    vendor_id = current_user.get("vendor_id") if current_user.get("is_vendor") else None
    
    summary = await sales_service.get_sales_summary(start_date, end_date, vendor_id)
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "revenue": summary.get("total_revenue", 0),
        "orders": summary.get("total_orders", 0),
        "average_order_value": summary.get("avg_order_value", 0),
        "growth": {
            "revenue": 0,  # Would calculate growth from previous period
            "orders": 0,
        },
    }


# ============================
# Sales Dashboard Endpoints
# ============================

@router.get("/sales/overview", response_model=Dict[str, Any])
async def get_sales_overview(
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get sales overview chart data.
    
    Returns daily sales data for the last N days.
    """
    sales_service = SalesAnalyticsService(db)
    
    vendor_id = current_user.get("vendor_id") if current_user.get("is_vendor") else None
    
    daily_sales = await sales_service.get_daily_sales(days, vendor_id)
    
    # Prepare chart data
    dates = [s["date"] for s in daily_sales]
    revenues = [s["total_sales"] for s in daily_sales]
    orders = [s["order_count"] for s in daily_sales]
    
    return {
        "labels": dates,
        "datasets": [
            {
                "label": "Revenue (ETB)",
                "data": revenues,
                "type": "line",
                "color": "#1a5276",
            },
            {
                "label": "Orders",
                "data": orders,
                "type": "bar",
                "color": "#2ecc71",
            },
        ],
        "summary": {
            "total_revenue": sum(revenues),
            "total_orders": sum(orders),
            "average_daily_revenue": sum(revenues) / len(revenues) if revenues else 0,
        },
    }


@router.get("/sales/top-products", response_model=List[Dict[str, Any]])
async def get_top_products_dashboard(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """
    Get top products for dashboard.
    
    Returns best-selling products for the period.
    """
    sales_service = SalesAnalyticsService(db)
    
    vendor_id = current_user.get("vendor_id") if current_user.get("is_vendor") else None
    
    return await sales_service.get_top_products(limit, days, vendor_id)


@router.get("/sales/payment-methods", response_model=List[Dict[str, Any]])
async def get_payment_method_breakdown(
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """
    Get payment method breakdown (admin only).
    
    Returns revenue distribution by payment method.
    """
    sales_service = SalesAnalyticsService(db)
    
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow()
    
    return await sales_service.get_revenue_by_payment_method(start_date, end_date)


# ============================
# User Dashboard Endpoints
# ============================

@router.get("/users/activity", response_model=Dict[str, Any])
async def get_user_activity_dashboard(
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get user activity dashboard (admin only).
    """
    user_service = UserAnalyticsService(db)
    
    growth = await user_service.get_user_growth(days)
    active_users = await user_service.get_active_users()
    
    return {
        "user_growth": growth,
        "active_users": active_users,
        "total_users": sum(g["new_users"] for g in growth),
    }


@router.get("/users/segments", response_model=Dict[str, Any])
async def get_user_segments_dashboard(
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get user segments for dashboard (admin only).
    """
    user_service = UserAnalyticsService(db)
    return await user_service.get_user_segments()


# ============================
# Inventory Dashboard Endpoints
# ============================

@router.get("/inventory/summary", response_model=Dict[str, Any])
async def get_inventory_dashboard(
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get inventory dashboard for vendor.
    """
    product_service = ProductAnalyticsService(db)
    
    vendor_id = current_user.get("vendor_id")
    
    stats = await product_service.get_inventory_analytics(vendor_id)
    low_stock = await product_service.get_low_stock_report(vendor_id)
    
    return {
        "summary": stats,
        "low_stock_count": len(low_stock),
        "low_stock_products": low_stock[:5],
        "status": {
            "healthy": stats.get("in_stock_count", 0) > 0,
            "needs_attention": stats.get("low_stock_count", 0) > 0,
            "critical": stats.get("out_of_stock_count", 0) > 0,
        },
    }


# ============================
# Customer Dashboard Endpoints
# ============================

@router.get("/customer/orders-summary", response_model=Dict[str, Any])
async def get_customer_orders_summary(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get customer order summary.
    
    Returns order statistics for the authenticated customer.
    """
    order_service = OrderService(db)
    
    orders, total = await order_service.get_user_orders(current_user["id"])
    
    # Calculate total spent
    total_spent = sum(o.total for o in orders if o.payment_status == "paid")
    
    # Count by status
    status_counts = {}
    for order in orders:
        status_counts[order.status] = status_counts.get(order.status, 0) + 1
    
    return {
        "total_orders": total,
        "total_spent": float(total_spent),
        "average_order_value": float(total_spent / total) if total > 0 else 0,
        "status_breakdown": status_counts,
        "recent_orders": [
            {
                "order_number": o.order_number,
                "total": float(o.total),
                "status": o.status,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders[:5]
        ],
    }


from apps.analytics.services import ProductAnalyticsService, UserAnalyticsService
from apps.orders.services import OrderService

__all__ = ["router"]