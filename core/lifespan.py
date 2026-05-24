# ============================
# WOLLOYEWA STORE BOT - LIFESPAN MANAGER
# ============================
"""Application lifecycle management for startup and shutdown events."""

import asyncio
import signal
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional

from core.config import settings
from core.logger import logger, LoggerContext


class LifespanManager:
    """
    Manages application lifecycle events including startup and shutdown hooks.
    
    This class allows registering callbacks to be executed during application
    startup and shutdown phases, ensuring proper resource initialization and cleanup.
    """
    
    def __init__(self):
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
        self._startup_async_hooks: List[Callable] = []
        self._shutdown_async_hooks: List[Callable] = []
        self._is_running: bool = False
        self._shutdown_event = asyncio.Event()
    
    def register_startup(self, hook: Callable) -> None:
        """
        Register a synchronous startup hook.
        
        Args:
            hook: Function to call during startup
        """
        self._startup_hooks.append(hook)
        logger.debug(f"Registered startup hook: {hook.__name__}")
    
    def register_shutdown(self, hook: Callable) -> None:
        """
        Register a synchronous shutdown hook.
        
        Args:
            hook: Function to call during shutdown
        """
        self._shutdown_hooks.append(hook)
        logger.debug(f"Registered shutdown hook: {hook.__name__}")
    
    def register_startup_async(self, hook: Callable) -> None:
        """
        Register an asynchronous startup hook.
        
        Args:
            hook: Async function to call during startup
        """
        self._startup_async_hooks.append(hook)
        logger.debug(f"Registered async startup hook: {hook.__name__}")
    
    def register_shutdown_async(self, hook: Callable) -> None:
        """
        Register an asynchronous shutdown hook.
        
        Args:
            hook: Async function to call during shutdown
        """
        self._shutdown_async_hooks.append(hook)
        logger.debug(f"Registered async shutdown hook: {hook.__name__}")
    
    async def on_startup(self) -> None:
        """
        Execute all registered startup hooks.
        
        This method should be called when the application is starting up.
        """
        logger.info("Running startup hooks...")
        
        # Run synchronous hooks
        for hook in self._startup_hooks:
            try:
                hook()
                logger.debug(f"Executed startup hook: {hook.__name__}")
            except Exception as e:
                logger.error(f"Startup hook {hook.__name__} failed: {e}")
                raise
        
        # Run asynchronous hooks
        for hook in self._startup_async_hooks:
            try:
                await hook()
                logger.debug(f"Executed async startup hook: {hook.__name__}")
            except Exception as e:
                logger.error(f"Async startup hook {hook.__name__} failed: {e}")
                raise
        
        self._is_running = True
        logger.info("All startup hooks completed successfully")
    
    async def on_shutdown(self) -> None:
        """
        Execute all registered shutdown hooks.
        
        This method should be called when the application is shutting down.
        """
        logger.info("Running shutdown hooks...")
        self._is_running = False
        
        # Run shutdown hooks in reverse order
        for hook in reversed(self._shutdown_hooks):
            try:
                hook()
                logger.debug(f"Executed shutdown hook: {hook.__name__}")
            except Exception as e:
                logger.error(f"Shutdown hook {hook.__name__} failed: {e}")
        
        for hook in reversed(self._shutdown_async_hooks):
            try:
                await hook()
                logger.debug(f"Executed async shutdown hook: {hook.__name__}")
            except Exception as e:
                logger.error(f"Async shutdown hook {hook.__name__} failed: {e}")
        
        logger.info("All shutdown hooks completed")
    
    @property
    def is_running(self) -> bool:
        """Return whether the application is currently running."""
        return self._is_running
    
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()
    
    def trigger_shutdown(self) -> None:
        """Trigger application shutdown."""
        logger.info("Shutdown triggered")
        self._shutdown_event.set()


# Global lifespan manager instance
lifespan_manager = LifespanManager()


def setup_signal_handlers() -> None:
    """
    Set up signal handlers for graceful shutdown.
    
    Handles SIGTERM and SIGINT signals to trigger graceful shutdown.
    """
    def handle_signal(signum: int, frame: Any) -> None:
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        lifespan_manager.trigger_shutdown()
    
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)


# ============================
# Default Hooks Registration
# ============================

async def _default_startup_checks() -> None:
    """Run default startup checks."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Log configuration summary (without sensitive data)
    logger.debug(f"Database: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
    logger.debug(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    logger.debug(f"Telegram bot: {'Configured' if settings.TELEGRAM_BOT_TOKEN else 'Not configured'}")


async def _default_shutdown_cleanup() -> None:
    """Run default shutdown cleanup."""
    logger.info("Performing cleanup tasks...")


# Register default hooks
lifespan_manager.register_startup_async(_default_startup_checks)
lifespan_manager.register_shutdown_async(_default_shutdown_cleanup)


# ============================
# Convenience Context Manager
# ============================

@asynccontextmanager
async def lifespan_context():
    """
    Async context manager for application lifespan.
    
    Usage:
        async with lifespan_context():
            # Application code here
            pass
    """
    try:
        await lifespan_manager.on_startup()
        yield lifespan_manager
    finally:
        await lifespan_manager.on_shutdown()


__all__ = [
    "lifespan_manager",
    "LifespanManager",
    "setup_signal_handlers",
    "lifespan_context",
]