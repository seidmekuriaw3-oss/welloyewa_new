#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Wolloyewa Store Bot - Main Entry Point
Ethiopian E-commerce Telegram Bot with Multi-Vendor Support

Author: Wolloyewa Team
Version: 1.0.0
License: Proprietary
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Load environment variables first
from core.config import settings
from core.logger import setup_logging
from core.lifespan import lifespan_manager
from core.monitoring.metrics import setup_metrics
from core.monitoring.health_checks import health_checker
from core.security.middleware import SecurityHeadersMiddleware

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} v{get_version()}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    try:
        # Initialize database connection pool
        from infrastructure.database.session import init_db, close_db
        await init_db()
        logger.info("Database connection pool initialized")
        
        # Initialize Redis connection (optional - bot works without it)
        try:
            from infrastructure.redis.client import init_redis, close_redis
            await init_redis()
            logger.info("Redis connection initialized")
        except Exception as redis_err:
            logger.warning(f"Redis unavailable (non-fatal): {redis_err}")
        
        # Setup monitoring metrics
        await setup_metrics()
        logger.info("Monitoring metrics initialized")
        
        # Initialize Telegram bot
        from bot.bot_instance import init_bot, shutdown_bot
        await init_bot()
        logger.info("Telegram bot initialized")
        
        # Setup background tasks (optional)
        try:
            from infrastructure.workers.celery_app import celery_app
            from infrastructure.queues.scheduled_tasks import scheduled_task_manager
            logger.info("Background task scheduler ready")
        except Exception as sched_err:
            logger.warning(f"Scheduler unavailable (non-fatal): {sched_err}")
        
        # Run lifespan manager
        await lifespan_manager.on_startup()
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    try:
        # Stop background tasks
        try:
            from infrastructure.queues.scheduled_tasks import scheduled_task_manager
            await scheduled_task_manager.stop_processor()
        except Exception:
            pass
        
        # Close database connections
        await close_db()
        
        # Close Redis connections
        await close_redis()
        
        # Shutdown bot
        await shutdown_bot()
        
        # Run lifespan manager shutdown
        await lifespan_manager.on_shutdown()
        
        logger.info("Application shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def get_version() -> str:
    """Return application version from pyproject.toml or default."""
    try:
        import tomllib
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data.get("tool", {}).get("poetry", {}).get("version", "1.0.0")
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return "1.0.0"


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=get_version(),
    description="Wolloyewa Store Bot - Ethiopian E-commerce Telegram Bot API",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)


# Add security middlewares
@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)


# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS if hasattr(settings, 'ALLOWED_HOSTS') else ["*"],
)


# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    """
    health_status = await health_checker.check_all()
    status_code = 200 if health_status["status"] == "healthy" else 503
    return health_status, status_code


@app.get("/")
async def root():
    """
    Root endpoint with basic information.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": get_version(),
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "documentation": "/api/docs" if settings.ENVIRONMENT != "production" else None,
    }


@app.get("/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.
    Checks if the application is ready to serve traffic.
    """
    is_ready = await health_checker.is_ready()
    return {"ready": is_ready}, 200 if is_ready else 503


@app.get("/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    Checks if the application is still running.
    """
    return {"alive": True}, 200


# Include API routers
def register_routers() -> None:
    """Register all API routers."""
    from infrastructure.api.v1.router import api_router
    
    # Include main API router
    app.include_router(api_router, prefix="/api/v1")
    
    # Include webhook router
    from bot.webhooks import webhook_router
    app.include_router(webhook_router, prefix="/webhook")
    
    # Include web app router if enabled
    if settings.ENABLE_WEB_APP:
        from bot.web_app.router import web_app_router
        app.include_router(web_app_router, prefix="/app")
    
    logger.info("All routers registered")


# Register routers on startup
register_routers()


def main() -> None:
    """
    Main entry point for the application.
    """
    try:
        import uvicorn
        
        uvicorn.run(
            "main:app",
            host=settings.HOST if hasattr(settings, 'HOST') else "0.0.0.0",
            port=settings.PORT if hasattr(settings, 'PORT') else 8000,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
            access_log=settings.DEBUG,
            workers=1,  # Use multiple workers with gunicorn in production
            loop="uvloop",
            http="httptools",
        )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# ============================
# Exception handlers
# ============================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if settings.DEBUG else "Contact support"},
    )


from fastapi.responses import JSONResponse