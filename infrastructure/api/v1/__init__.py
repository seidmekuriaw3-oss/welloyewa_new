# ============================
# WOLLOYEWA STORE BOT - API V1
# ============================
"""API version 1 routers and endpoints."""

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
)

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(webhook.router, tags=["webhooks"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

__all__ = [
    "api_router",
    "health",
    "webhook",
    "users",
    "products",
    "orders",
    "analytics",
    "payments",
    "admin",
]