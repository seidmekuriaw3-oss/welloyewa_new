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
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.logger import setup_logging
from core.lifespan import lifespan_manager
from core.security.middleware import SecurityHeadersMiddleware

import os
os.makedirs("./logs", exist_ok=True)

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan - startup and shutdown."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{get_version()}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    close_db = None
    close_redis = None
    shutdown_bot = None
    stop_scheduler = None
    application_instance = None

    # Database
    try:
        from infrastructure.database.session import init_db, close_db
        await init_db()
        logger.info("Database connection pool initialized")
        # Ensure all tables exist (idempotent – skips existing tables/types)
        try:
            import re
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy.pool import NullPool
            from infrastructure.database.base import Base
            # Import all models so metadata is fully populated
            import apps.common.models  # noqa: F401
            import apps.users.models  # noqa: F401
            import apps.products.models  # noqa: F401
            import apps.orders.models  # noqa: F401
            import apps.inventory.models  # noqa: F401
            import apps.marketing.models  # noqa: F401
            import apps.support.models  # noqa: F401
            raw_url = str(settings.DATABASE_URL)
            raw_url = re.sub(r'[?&]sslmode=[^&]*', '', raw_url).rstrip('?')
            db_url = raw_url.replace("postgresql://", "postgresql+asyncpg://")
            _schema_engine = create_async_engine(db_url, poolclass=NullPool)
            async with _schema_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all, checkfirst=True)
            await _schema_engine.dispose()
            logger.info("Database schema verified/created")
        except Exception as schema_err:
            logger.warning(f"Schema auto-create skipped: {schema_err}")
    except Exception as e:
        logger.warning(f"Database initialization failed (continuing): {e}")

    # Redis (optional)
    try:
        from infrastructure.redis.client import init_redis, close_redis
        await init_redis()
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.warning(f"Redis initialization failed (continuing): {e}")

    # Telegram Bot with retry
    try:
        from bot.bot_instance import init_bot, shutdown_bot

        for attempt in range(3):
            try:
                application_instance = await init_bot()
                logger.info("Telegram bot initialized")
                break
            except Exception as net_err:
                if attempt < 2:
                    logger.warning(f"Bot init attempt {attempt + 1} failed, retrying in 3s: {net_err}")
                    await asyncio.sleep(3)
                else:
                    raise net_err

        # Start polling in development mode
        if settings.ENVIRONMENT == "development" and application_instance:
            logger.info("Starting Telegram bot in POLLING mode...")
            await application_instance.initialize()
            # Delete any existing webhook/poll before starting to avoid Conflict errors
            for _attempt in range(5):
                try:
                    await application_instance.bot.delete_webhook(drop_pending_updates=True)
                    logger.info("Webhook cleared, starting polling...")
                    break
                except Exception as wh_err:
                    logger.warning(f"Could not delete webhook (attempt {_attempt+1}): {wh_err}")
                    await asyncio.sleep(3)
            # Wait for Telegram to release any previous long-poll connection (~30s timeout)
            await asyncio.sleep(5)
            await application_instance.start()
            await application_instance.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "inline_query"],
                error_callback=lambda err: logger.warning(f"Polling error (will retry): {err}"),
            )
            logger.info("Telegram bot polling started!")

    except Exception as e:
        logger.warning(f"Telegram bot initialization failed (continuing): {e}")

    # Scheduler
    try:
        from infrastructure.queues.scheduled_tasks import start_scheduler, stop_scheduler
        await start_scheduler()
        logger.info("Background task scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler initialization failed (continuing): {e}")

    # Lifespan hooks
    try:
        await lifespan_manager.on_startup()
    except Exception as e:
        logger.warning(f"Lifespan manager startup failed (continuing): {e}")

    logger.info("Application startup completed")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    if application_instance and settings.ENVIRONMENT == "development":
        try:
            logger.info("Stopping Telegram bot polling...")
            if application_instance.updater and application_instance.updater.running:
                await application_instance.updater.stop()
            if application_instance.running:
                await application_instance.stop()
            await application_instance.shutdown()
        except Exception as e:
            logger.error(f"Error stopping bot polling: {e}")

    if stop_scheduler:
        try:
            await stop_scheduler()
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")

    if close_db:
        try:
            await close_db()
        except Exception as e:
            logger.error(f"Error closing DB: {e}")

    if close_redis:
        try:
            await close_redis()
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")

    if shutdown_bot:
        try:
            await shutdown_bot()
        except Exception as e:
            logger.error(f"Error shutting down bot: {e}")

    try:
        await lifespan_manager.on_shutdown()
    except Exception as e:
        logger.error(f"Error in lifespan shutdown: {e}")

    logger.info("Application shutdown completed")


def get_version() -> str:
    """Return application version."""
    try:
        import tomllib
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data.get("tool", {}).get("poetry", {}).get("version", "1.0.0")
    except Exception:
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept", "Origin"],
    expose_headers=["*"],
    max_age=600,
)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        from core.monitoring.health_checks import health_checker
        return await health_checker.check_all()
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": get_version(),
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "documentation": "/api/docs" if settings.ENVIRONMENT != "production" else None,
    }


@app.get("/ready")
async def readiness_probe():
    return {"ready": True}


@app.get("/live")
async def liveness_probe():
    return {"alive": True}


def register_routers() -> None:
    """Register all API routers."""
    try:
        from infrastructure.api.v1.router import api_router
        app.include_router(api_router, prefix="/api/v1")
        logger.info("API v1 router registered")
    except Exception as e:
        logger.warning(f"Failed to register API v1 router: {e}")

    try:
        from bot.webhooks import router as webhook_router
        app.include_router(webhook_router, prefix="/webhook")
        logger.info("Webhook router registered")
    except Exception as e:
        logger.warning(f"Failed to register webhook router: {e}")

    if settings.ENABLE_WEB_APP:
        try:
            from bot.web_app.router import web_app_router
            app.include_router(web_app_router)
            logger.info("Web app router registered")
        except Exception as e:
            logger.warning(f"Failed to register web app router: {e}")


register_routers()

# Mount web app static files
try:
    import os as _os
    _static_dir = _os.path.join(_os.path.dirname(__file__), "bot", "web_app", "static")
    if _os.path.isdir(_static_dir):
        app.mount("/app/static", StaticFiles(directory=_static_dir), name="web_app_static")
        logger.info("Web app static files mounted at /app/static")
except Exception as _e:
    logger.warning(f"Could not mount static files: {_e}")


def main() -> None:
    """Main entry point."""
    try:
        import uvicorn
        loop_policy = "asyncio" if sys.platform == "win32" else "uvloop"
        uvicorn.run(
            "main:app",
            host=settings.HOST if hasattr(settings, "HOST") else "0.0.0.0",
            port=settings.PORT if hasattr(settings, "PORT") else 5000,
            reload=False,
            log_level=settings.LOG_LEVEL.lower(),
            access_log=settings.DEBUG,
            workers=1,
            loop=loop_policy,
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


# Global exception handler — WolloyewaException subclasses (AuthenticationError,
# PermissionError, NotFoundError, RateLimitError, etc.) carry their own status_code.
# This handler must be registered BEFORE the generic Exception handler so FastAPI
# checks the more specific handler first.
from core.exceptions import WolloyewaException

@app.exception_handler(WolloyewaException)
async def wolloyewa_exception_handler(request, exc: WolloyewaException):
    status_code = getattr(exc, "status_code", 500)
    logger.warning(f"Application error [{status_code}]: {exc.message}")
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "error": exc.code},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )
