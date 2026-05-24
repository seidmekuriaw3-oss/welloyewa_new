# ============================
# WOLLOYEWA STORE BOT - ADMIN API ENDPOINTS
# ============================
"""Admin API endpoints for system management and configuration."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from core.dependencies import get_current_admin, get_db_session
from core.exceptions import NotFoundError, ValidationError
from apps.users.services import UserService, VendorService
from apps.products.services import ProductService, CategoryService
from apps.orders.services import OrderService
from apps.analytics.services import DashboardService, SalesAnalyticsService
from infrastructure.backup.automated_backup import create_backup, list_backups, restore_backup
from infrastructure.backup.point_in_time_recovery import create_recovery_point, restore_to_point_in_time
from infrastructure.monitoring.metrics import get_metrics
from infrastructure.monitoring.health_checks import health_checker
from apps.common.schemas import PaginatedResponse, MessageResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ============================
# System Health Endpoints
# ============================

@router.get("/health", response_model=Dict[str, Any])
async def admin_health_check(
    current_user: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    """
    Get detailed system health status (admin only).
    """
    return await health_checker.check_all()


@router.get("/metrics", response_model=Dict[str, Any])
async def admin_get_metrics(
    current_user: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    """
    Get system metrics (admin only).
    """
    # In production, return Prometheus metrics
    return {
        "service": "wolloyewa",
        "metrics": {
            "requests_total": 0,
            "active_users": 0,
            "orders_today": 0,
        }
    }


# ============================
# Backup Management Endpoints
# ============================

@router.post("/backup/create", response_model=Dict[str, Any])
async def admin_create_backup(
    current_user: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    """
    Create a new database backup (admin only).
    """
    result = await create_backup()
    
    return {
        "backup_id": result.backup_id,
        "status": result.status.value,
        "size_bytes": result.size_bytes,
        "duration_seconds": result.duration_seconds,
        "file_path": result.file_path,
    }


@router.get("/backup/list", response_model=List[Dict[str, Any]])
async def admin_list_backups(
    current_user: dict = Depends(get_current_admin),
) -> List[Dict[str, Any]]:
    """
    List all available backups (admin only).
    """
    return await list_backups()


@router.post("/backup/restore", response_model=MessageResponse)
async def admin_restore_backup(
    backup_file: str = Query(..., description="Backup filename to restore"),
    current_user: dict = Depends(get_current_admin),
) -> MessageResponse:
    """
    Restore database from backup (admin only).
    
    Warning: This will overwrite current database.
    """
    success = await restore_backup(backup_file)
    
    if success:
        return MessageResponse(message=f"Backup restored successfully from {backup_file}")
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Restore failed")


@router.post("/backup/recovery-point", response_model=Dict[str, Any])
async def admin_create_recovery_point(
    current_user: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    """
    Create a point-in-time recovery point (admin only).
    """
    recovery_point = await create_recovery_point()
    
    return {
        "recovery_point_id": recovery_point.id,
        "timestamp": recovery_point.timestamp.isoformat(),
        "wal_file": recovery_point.wal_file,
    }


# ============================
# System Configuration Endpoints
# ============================

@router.get("/config", response_model=Dict[str, Any])
async def admin_get_config(
    current_user: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    """
    Get system configuration (admin only).
    
    Returns non-sensitive configuration settings.
    """
    from core.config import settings
    
    return {
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "project_name": settings.PROJECT_NAME,
        "timezone": settings.TIMEZONE,
        "features": {
            "enable_push_notifications": settings.ENABLE_PUSH_NOTIFICATIONS,
            "enable_web_app": settings.ENABLE_WEB_APP,
            "enable_ai_support_bot": settings.ENABLE_AI_SUPPORT_BOT,
            "enable_loyalty_program": settings.ENABLE_LOYALTY_PROGRAM,
            "enable_escrow_service": settings.ENABLE_ESCROW_SERVICE,
        },
        "rate_limits": {
            "per_minute": settings.RATE_LIMIT_PER_MINUTE,
            "per_hour": settings.RATE_LIMIT_PER_HOUR,
            "strategy": settings.RATE_LIMIT_STRATEGY,
        },
    }


# ============================
# User Management (Admin)
# ============================

@router.get("/users", response_model=PaginatedResponse[dict])
async def admin_get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[dict]:
    """
    Get all users with filters (admin only).
    """
    user_service = UserService(db)
    
    filters = {}
    if role:
        filters["role"] = role
    if status_filter:
        filters["status"] = status_filter
    
    users, total = await user_service.user_repo.get_all_with_count(
        filters=filters,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    
    return PaginatedResponse.create(
        items=[u.to_dict() for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=dict)
async def admin_get_user(
    user_id: int,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get user details by ID (admin only).
    """
    user_service = UserService(db)
    
    try:
        user = await user_service.get_user(user_id)
        return user.to_dict()
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/users/{user_id}/status", response_model=MessageResponse)
async def admin_update_user_status(
    user_id: int,
    status: str = Query(..., regex="^(active|inactive|suspended|banned)$"),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Update user account status (admin only).
    """
    user_service = UserService(db)
    
    try:
        await user_service.update_user(user_id, {"status": status})
        return MessageResponse(message=f"User {user_id} status updated to {status}")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================
# Vendor Management (Admin)
# ============================

@router.get("/vendors", response_model=PaginatedResponse[dict])
async def admin_get_vendors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_approved: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[dict]:
    """
    Get all vendors (admin only).
    """
    vendor_service = VendorService(db)
    
    if is_approved is not None:
        if is_approved:
            vendors = await vendor_service.vendor_repo.get_approved_vendors(limit=page_size, offset=(page - 1) * page_size)
            total = len(vendors)
        else:
            vendors = await vendor_service.vendor_repo.get_pending_vendors(limit=page_size)
            total = len(vendors)
    else:
        vendors, total = await vendor_service.vendor_repo.get_all_with_count(
            limit=page_size,
            offset=(page - 1) * page_size,
        )
    
    return PaginatedResponse.create(
        items=[v.to_dict() for v in vendors],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/vendors/{vendor_id}/approve", response_model=MessageResponse)
async def admin_approve_vendor(
    vendor_id: int,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Approve a vendor application (admin only).
    """
    vendor_service = VendorService(db)
    
    try:
        await vendor_service.approve_vendor(vendor_id, current_user["id"])
        return MessageResponse(message=f"Vendor {vendor_id} approved successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/vendors/{vendor_id}/reject", response_model=MessageResponse)
async def admin_reject_vendor(
    vendor_id: int,
    reason: str = Query(...),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Reject a vendor application (admin only).
    """
    vendor_service = VendorService(db)
    
    try:
        await vendor_service.reject_vendor(vendor_id, reason)
        return MessageResponse(message=f"Vendor {vendor_id} rejected")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================
# Platform Statistics
# ============================

@router.get("/stats", response_model=Dict[str, Any])
async def admin_get_platform_stats(
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get platform statistics (admin only).
    """
    dashboard_service = DashboardService(db)
    sales_service = SalesAnalyticsService(db)
    user_service = UserService(db)
    
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    
    # Get today's sales
    today_sales = await sales_service.get_sales_summary(today_start, now)
    
    # Get user stats
    user_count = await user_service.user_repo.count()
    vendor_count = await user_service.user_repo.count({"role": "vendor"})
    
    # Get order stats
    order_repo = OrderRepository(db)
    order_stats = await order_repo.get_all_stats()
    
    return {
        "users": {
            "total": user_count,
            "vendors": vendor_count,
            "customers": user_count - vendor_count,
        },
        "orders": order_stats,
        "sales_today": {
            "revenue": float(today_sales.get("total_revenue", 0)),
            "orders": today_sales.get("total_orders", 0),
        },
        "platform": {
            "environment": "production",
            "uptime_days": 0,  # Would track actual uptime
        },
    }


from apps.orders.repository import OrderRepository

__all__ = ["router"]