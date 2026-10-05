# ============================
# WOLLOYEWA STORE BOT - API V1 ROUTER
# ============================
"""Main API router aggregating all endpoint routers."""

from functools import partial

from fastapi import APIRouter, Depends

from core.config import settings
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

# Apply shared, configured limits without exposing limits as caller-controlled query params.
api_router = APIRouter(
    dependencies=[
        Depends(
            partial(
                check_rate_limit,
                key_prefix="api:minute",
                limit=settings.RATE_LIMIT_PER_MINUTE,
                window=60,
            )
        ),
        Depends(
            partial(
                check_rate_limit,
                key_prefix="api:hour",
                limit=settings.RATE_LIMIT_PER_HOUR,
                window=3600,
            )
        ),
    ]
)

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["Webhooks"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["Dashboards"])

__all__ = ["api_router"]
