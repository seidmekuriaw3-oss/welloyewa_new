# ============================
# WOLLOYEWA STORE BOT - API V1 ENDPOINTS
# ============================
"""API v1 endpoint modules for all resources."""

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

__all__ = [
    "admin",
    "analytics",
    "dashboards",
    "health",
    "orders",
    "payments",
    "products",
    "users",
    "webhook",
]
