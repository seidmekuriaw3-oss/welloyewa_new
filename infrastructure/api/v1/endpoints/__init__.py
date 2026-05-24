# ============================
# WOLLOYEWA STORE BOT - API V1 ENDPOINTS
# ============================
"""API v1 endpoint modules for all resources."""

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

__all__ = [
    "health",
    "webhook",
    "users",
    "products",
    "orders",
    "analytics",
    "payments",
    "admin",
    "dashboards",
]