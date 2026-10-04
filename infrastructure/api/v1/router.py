# ============================
# WOLLOYEWA STORE BOT - API V1 ROUTER
# ============================
"""Main API router aggregating all endpoint routers."""

from fastapi import APIRouter, Depends

from core.dependencies import check_rate_limit

from infrastructure.api.v1.endpoints import (
    admin,
    analytics,
    dashboards,
    health,
    orders,
    payments,
    products,
    users,
    webhook,
)

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(
    webhook.router,
    prefix="/webhook",
    tags=["Webhooks"],
    dependencies=[Depends(check_rate_limit)],
)
api_router.include_router(
    users.router, prefix="/users", tags=["Users"], dependencies=[Depends(check_rate_limit)]
)
api_router.include_router(
    products.router,
    prefix="/products",
    tags=["Products"],
    dependencies=[Depends(check_rate_limit)],
)
api_router.include_router(
    orders.router, prefix="/orders", tags=["Orders"], dependencies=[Depends(check_rate_limit)]
)
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=[Depends(check_rate_limit)],
)
api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["Payments"],
    dependencies=[Depends(check_rate_limit)],
)
api_router.include_router(
    admin.router, prefix="/admin", tags=["Admin"], dependencies=[Depends(check_rate_limit)]
)
api_router.include_router(
    dashboards.router,
    prefix="/dashboards",
    tags=["Dashboards"],
    dependencies=[Depends(check_rate_limit)],
)

__all__ = ["api_router"]
