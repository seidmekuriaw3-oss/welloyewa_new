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
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Load environment variables first
from core.config import settings
from core.logger import setup_logging
from core.lifespan import lifespan_manager
from core.security.middleware import SecurityHeadersMiddleware

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    Handles startup and shutdown events with Polling fallback for development.
    """
    logger.info(f"Starting {settings.PROJECT_NAME} v{get_version()}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    close_db = None
    close_redis = None
    shutdown_bot = None
    stop_scheduler = None
    application_instance = None  # To keep track of the telegram application

    # Initialize database connection pool
    try:
        from infrastructure.database.session import init_db, close_db
        await init_db()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed (continuing): {e}")

    # Initialize Redis connection
    try:
        from infrastructure.redis.client import init_redis, close_redis
        await init_redis()
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.warning(f"Redis initialization failed (continuing): {e}")

    # Initialize Telegram bot
    try:
        from bot.bot_instance import init_bot, shutdown_bot
        
        # የኢንተርኔት መቆራረጥ ካለ ቦቱ ወዲያው ተስፋ ቆርጦ ዋርኒንግ እንዳይጥል Retry Loop እንጨምራለን
        retry_count = 3
        for attempt in range(retry_count):
            try:
                application_instance = await init_bot()
                logger.info("Telegram bot initialized")
                break
            except Exception as net_err:
                if attempt < retry_count - 1:
                    logger.warning(f"Bot init connection attempt {attempt + 1} failed. Retrying in 3 seconds... ({net_err})")
                    await asyncio.sleep(3)
                else:
                    raise net_err
        
        # ሎካል ላይ (development) ሲሰሩ መልእክቶችን ቀጥታ እንዲስብ Polling እዚህ እንጀምራለን
        if settings.ENVIRONMENT == "development" and application_instance:
            logger.info("Starting Telegram bot in POLLING mode for local development...")
            
            # ========================================================
            # 🔍 የሙከራ ሃንድለር (HANDLER DIAGNOSTIC) - እዚህ ጋር ተጨምሯል
            # ========================================================
            try:
                from telegram import Update
                from telegram.ext import CommandHandler
                
                async def test_start_response(update: Update, context):
                    logger.info(f"🎯 ቴሌግራም ላይ የ /start ሙከራ መጥቷል! User ID: {update.effective_user.id}")
                    await update.message.reply_text("አለሁልህ! አሁን በትክክል ተገናኝተናል! 🚀 (ይህ ቀጥታ ምላሽ ነው)")
                
                # በቅድሚያ እንዲይዘው group=-1 ላይ እንጨምረዋለን
                application_instance.add_handler(CommandHandler("start", test_start_response), group=-1)
                logger.info("Temporary diagnostic /start handler injected successfully")
            except Exception as test_err:
                logger.warning(f"Failed to inject diagnostic handler: {test_err}")
            # ========================================================

            await application_instance.initialize()
            await application_instance.start()
            await application_instance.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram bot polling started successfully!")
            
    except Exception as e:
        logger.warning(f"Telegram bot initialization failed (continuing): {e}")

    # Setup background tasks
    try:
        from infrastructure.queues.scheduled_tasks import start_scheduler, stop_scheduler
        await start_scheduler()
        logger.info("Background task scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler initialization failed (continuing): {e}")

    # Run lifespan manager
    try:
        await lifespan_manager.on_startup()
    except Exception as e:
        logger.warning(f"Lifespan manager startup failed (continuing): {e}")

    logger.info("Application startup completed")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Polling ን በንጽህና ማቆም
    if application_instance and settings.ENVIRONMENT == "development":
        try:
            logger.info("Stopping Telegram bot polling...")
            if application_instance.updater and application_instance.updater.running:
                await application_instance.updater.stop()
            await application_instance.stop()
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
            try:
                await close_redis()
            except Exception as e:
                logger.error(f"Error closing Redis: {e}")
        except Exception:
            pass

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
    """Return application version from pyproject.toml or default."""
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


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept", "Origin"],
    expose_headers=["*"],
    max_age=600,
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    """
    try:
        from core.monitoring.health_checks import health_checker
        health_status = await health_checker.check_all()
        return health_status
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


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
    """
    return {"ready": True}


@app.get("/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    """
    return {"alive": True}


# Include API routers
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
            app.include_router(web_app_router, prefix="/app")
            logger.info("Web app router registered")
        except Exception as e:
            logger.warning(f"Failed to register web app router: {e}")


# Register routers on startup
register_routers()


def main() -> None:
    """
    Main entry point for the application.
    """
    try:
        import uvicorn

        # ዊንዶውስ ላይ ከሆነ ሉፑን "asyncio" ማድረግ፣ ካልሆነ "uvloop"
        loop_policy = "asyncio" if sys.platform == "win32" else "uvloop"

        uvicorn.run(
            "main:app",
            host=settings.HOST if hasattr(settings, 'HOST') else "0.0.0.0",
            port=settings.PORT if hasattr(settings, 'PORT') else 5000,
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