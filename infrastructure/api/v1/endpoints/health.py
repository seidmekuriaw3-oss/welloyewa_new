# ============================
# WOLLOYEWA STORE BOT - HEALTH CHECK ENDPOINTS
# ============================
"""Health check endpoints for monitoring and load balancers."""

from typing import Any

from fastapi import APIRouter

from core.config import settings
from core.monitoring.health_checks import health_checker

router = APIRouter(tags=["health"])


@router.get("/")
async def health_check() -> dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/detailed")
async def detailed_health_check() -> dict[str, Any]:
    """
    Detailed health check with component status.

    Returns:
        Detailed health status for all components
    """
    return await health_checker.check_all()


@router.get("/ready")
async def readiness_probe() -> dict[str, Any]:
    """
    Kubernetes readiness probe.

    Returns:
        Ready status
    """
    is_ready = await health_checker.is_ready()
    return {
        "ready": is_ready,
        "service": settings.PROJECT_NAME,
    }


@router.get("/live")
async def liveness_probe() -> dict[str, Any]:
    """
    Kubernetes liveness probe.

    Returns:
        Live status
    """
    return {
        "alive": True,
        "service": settings.PROJECT_NAME,
    }


@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """
    Get basic service metrics.

    Returns:
        Service metrics
    """

    # In production, this would return Prometheus metrics
    return {
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": None,  # Would track actual uptime
    }


__all__ = ["router"]
