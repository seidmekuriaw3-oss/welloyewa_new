# ============================
# WOLLOYEWA STORE BOT - HEALTH CHECK ENDPOINTS
# ============================
"""Health check endpoints for monitoring and load balancers."""

from typing import Any

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST

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


@router.get("/metrics", response_class=Response)
async def get_metrics() -> Response:
    """
    Get basic service metrics.

    Returns:
        Service metrics
    """

    from core.monitoring.metrics import get_metrics as get_prometheus_metrics

    return Response(
        content=get_prometheus_metrics(),
        media_type=CONTENT_TYPE_LATEST,
    )


__all__ = ["router"]
