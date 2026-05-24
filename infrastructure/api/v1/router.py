# ============================
# WOLLOYEWA STORE BOT - API V1 ROUTER
# ============================
"""Main API router aggregating all endpoint routers."""

from fastapi import APIRouter

from infrastructure.api.v1.endpoints import (
    health,
    webhook,
    users,
    products,
    orders,
    analytics,
    payments,
    admin,
    dashboards,
)

# Create main API router
api_router = APIRouter()

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