# ============================
# WOLLOYEWA STORE BOT - ANALYTICS API ENDPOINTS
# ============================
"""REST API endpoints for analytics and reporting."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from datetime import datetime, timedelta

from core.dependencies import get_current_user, get_current_vendor, get_current_admin, get_db_session
from core.exceptions import NotFoundError, PermissionError
from apps.analytics.services import SalesAnalyticsService, UserAnalyticsService, ProductAnalyticsService, DashboardService
from apps.analytics.schemas import (
    SalesReportResponse,
    SalesSummaryResponse,
    UserActivityReport,
    ProductPerformanceReport,
    DashboardSummary,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ============================
# Dashboard Endpoints
# ============================

@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DashboardSummary:
    """
    Get dashboard summary for the current user.
    
    Returns key metrics and recent data for the dashboard.
    """
    dashboard_service = DashboardService(db)
    
    vendor_id = current_user.get("vendor_id") if current_user.get("is_vendor") else None
    
    summary = await dashboard_service.get_dashboard_summary(vendor_id)
    return DashboardSummary(**summary)


@router.get("/admin/dashboard", response_model=DashboardSummary)
async def get_admin_dashboard_summary(
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> DashboardSummary:
    """
    Get admin dashboard summary.
    
    Returns comprehensive metrics for the entire platform.
    """
    dashboard_service = DashboardService(db)
    
    summary = await dashboard_service.get_dashboard_summary()
    return DashboardSummary(**summary)


# ============================
# Sales Analytics Endpoints
# ============================

@router.get("/sales/daily", response_model=List[dict])
async def get_daily_sales(
    days: int = Query(30, ge=1, le=90),
    vendor_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> List[dict]:
    """
    Get daily sales for the last N days.
    """
    sales_service = SalesAnalyticsService(db)
    
    # Vendor can only see their own data
    if current_user.get("is_vendor") and not vendor_id:
        vendor_id = current_user.get("vendor_id")
    
    return await sales_service.get_daily_sales(days, vendor_id)


@router.get("/sales/monthly", response_model=List[dict])
async def get_monthly_sales(
    months: int = Query(12, ge=1, le=24),
    vendor_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> List[dict]:
    """
    Get monthly sales for the last N months.
    """
    sales_service = SalesAnalyticsService(db)
    
    if current_user.get("is_vendor") and not vendor_id:
        vendor_id = current_user.get("vendor_id")
    
    return await sales_service.get_monthly_sales(months, vendor_id)


@router.get("/sales/summary", response_model=SalesSummaryResponse)
async def get_sales_summary(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    vendor_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> SalesSummaryResponse:
    """
    Get sales summary for a date range.
    
    If no dates provided, defaults to last 30 days.
    """
    sales_service = SalesAnalyticsService(db)
    
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    if current_user.get("is_vendor") and not vendor_id:
        vendor_id = current_user.get("vendor_id")
    
    summary = await sales_service.get_sales_summary(start_date, end_date, vendor_id)
    return SalesSummaryResponse(**summary)


@router.get("/sales/top-products", response_model=List[dict])
async def get_top_products(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=90),
    vendor_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> List[dict]:
    """
    Get top selling products.
    """
    sales_service = SalesAnalyticsService(db)
    
    if current_user.get("is_vendor") and not vendor_id:
        vendor_id = current_user.get("vendor_id")
    
    return await sales_service.get_top_products(limit, days, vendor_id)


@router.get("/sales/top-categories", response_model=List[dict])
async def get_top_categories(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> List[dict]:
    """
    Get top selling categories (admin only).
    """
    sales_service = SalesAnalyticsService(db)
    return await sales_service.get_top_categories(limit, days)


# ============================
# User Analytics Endpoints
# ============================

@router.get("/users/growth", response_model=List[dict])
async def get_user_growth(
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> List[dict]:
    """
    Get user registration growth (admin only).
    """
    user_service = UserAnalyticsService(db)
    return await user_service.get_user_growth(days)


@router.get("/users/retention", response_model=dict)
async def get_user_retention(
    cohort_days: int = Query(30, ge=7, le=90),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get user retention metrics (admin only).
    """
    user_service = UserAnalyticsService(db)
    return await user_service.get_user_retention(cohort_days)


@router.get("/users/active", response_model=int)
async def get_active_users(
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> int:
    """
    Get number of active users (admin only).
    """
    user_service = UserAnalyticsService(db)
    return await user_service.get_active_users(days)


@router.get("/users/segments", response_model=dict)
async def get_user_segments(
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get user segmentation (admin only).
    """
    user_service = UserAnalyticsService(db)
    return await user_service.get_user_segments()


# ============================
# Product Analytics Endpoints
# ============================

@router.get("/products/{product_id}/performance", response_model=dict)
async def get_product_performance(
    product_id: int,
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get performance metrics for a specific product.
    """
    product_service = ProductAnalyticsService(db)
    
    try:
        return await product_service.get_product_performance(product_id, days)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/inventory/low-stock", response_model=List[dict])
async def get_low_stock_report(
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> List[dict]:
    """
    Get low stock products report.
    """
    product_service = ProductAnalyticsService(db)
    
    vendor_id = current_user.get("vendor_id") if current_user.get("is_vendor") else None
    
    return await product_service.get_low_stock_report(vendor_id)


@router.get("/inventory/summary", response_model=dict)
async def get_inventory_analytics(
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get inventory analytics summary.
    """
    product_service = ProductAnalyticsService(db)
    
    vendor_id = current_user.get("vendor_id") if current_user.get("is_vendor") else None
    
    return await product_service.get_inventory_analytics(vendor_id)


# ============================
# Report Generation Endpoints
# ============================

@router.get("/reports/sales/export")
async def export_sales_report(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    format: str = Query("json", pattern="^(json|csv|excel)$"),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Export sales report (admin only).
    
    Returns sales report in requested format.
    """
    analytics_service = AnalyticsService(db)
    
    report = await analytics_service.generate_sales_report(start_date, end_date)
    
    if format == "json":
        return report
    elif format == "csv":
        # Convert to CSV
        return {"message": "CSV export not implemented yet"}
    else:
        return {"message": "Excel export not implemented yet"}


__all__ = ["router"]