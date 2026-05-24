# ============================
# WOLLOYEWA STORE BOT - ORDERS API ENDPOINTS
# ============================
"""REST API endpoints for order management."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from decimal import Decimal

from core.dependencies import get_current_user, get_current_vendor, get_current_admin, get_db_session
from core.exceptions import NotFoundError, ValidationError, PermissionError, InsufficientStockError
from apps.orders.services import OrderService, OrderTrackingService
from apps.orders.schemas import (
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderStatusUpdate,
    OrderTrackingResponse,
    OrderTrackRequest,
)
from apps.common.schemas import PaginatedResponse, MessageResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ============================
# Order Endpoints
# ============================

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrderResponse:
    """
    Create a new order.
    
    Creates an order with the specified items and payment method.
    """
    order_service = OrderService(db)
    
    try:
        order = await order_service.create_order(current_user["id"], data)
        return OrderResponse.model_validate(order)
    except (ValidationError, InsufficientStockError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=PaginatedResponse[OrderResponse])
async def get_my_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[OrderResponse]:
    """
    Get current user's orders.
    
    Returns paginated list of orders for the authenticated user.
    """
    order_service = OrderService(db)
    
    orders, total = await order_service.get_user_orders(
        user_id=current_user["id"],
        status=status,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    
    return PaginatedResponse.create(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrderResponse:
    """
    Get order by ID.
    
    Returns detailed order information.
    """
    order_service = OrderService(db)
    
    try:
        order = await order_service.get_order(order_id, current_user["id"])
        return OrderResponse.model_validate(order)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.put("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    reason: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrderResponse:
    """
    Cancel an order.
    
    Cancels the order if it's still in pending or confirmed status.
    """
    order_service = OrderService(db)
    
    try:
        order = await order_service.cancel_order(order_id, current_user["id"], reason)
        return OrderResponse.model_validate(order)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================
# Order Tracking Endpoints
# ============================

@router.get("/track/{order_number}", response_model=OrderTrackingResponse)
async def track_order(
    order_number: str,
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> OrderTrackingResponse:
    """
    Track order by order number.
    
    Public endpoint for order tracking without authentication.
    """
    tracking_service = OrderTrackingService(db)
    
    # Validate input
    if not email and not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone is required for tracking"
        )
    
    order = await tracking_service.track_order(order_number, email or phone)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or verification failed"
        )
    
    tracking_info = await tracking_service.get_tracking_status(order.id)
    return OrderTrackingResponse(**tracking_info)


# ============================
# Vendor Order Endpoints
# ============================

@router.get("/vendor/orders", response_model=PaginatedResponse[OrderResponse])
async def get_vendor_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[OrderResponse]:
    """
    Get vendor's orders.
    
    Returns orders for the authenticated vendor.
    """
    order_service = OrderService(db)
    
    orders, total = await order_service.get_vendor_orders(
        vendor_id=current_user["vendor_id"],
        status=status,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    
    return PaginatedResponse.create(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put("/vendor/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    current_user: dict = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db_session),
) -> OrderResponse:
    """
    Update order status (vendor only).
    
    Updates the status of an order (e.g., processing, shipped, delivered).
    """
    order_service = OrderService(db)
    
    try:
        order = await order_service.update_order_status(order_id, data, current_user["id"])
        return OrderResponse.model_validate(order)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================
# Admin Order Endpoints
# ============================

@router.get("/admin/orders", response_model=PaginatedResponse[OrderResponse])
async def admin_get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    vendor_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[OrderResponse]:
    """
    Get all orders (admin only).
    
    Returns paginated list of all orders with filters.
    """
    order_repo = OrderRepository(db)
    
    filters = {}
    if status:
        filters["status"] = status
    if user_id:
        filters["user_id"] = user_id
    if vendor_id:
        filters["vendor_id"] = vendor_id
    
    orders, total = await order_repo.get_all_with_count(
        filters=filters,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    
    return PaginatedResponse.create(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put("/admin/orders/{order_id}/status", response_model=OrderResponse)
async def admin_update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> OrderResponse:
    """
    Update order status (admin only).
    
    Admin can update any order's status.
    """
    order_service = OrderService(db)
    
    try:
        order = await order_service.update_order_status(order_id, data, current_user["id"])
        return OrderResponse.model_validate(order)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


from apps.orders.repository import OrderRepository

__all__ = ["router"]