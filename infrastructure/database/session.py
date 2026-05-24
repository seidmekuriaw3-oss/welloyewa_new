# ============================
# WOLLOYEWA STORE BOT - DATABASE SESSION
# ============================
"""Database session management with connection pooling."""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from core.config import settings
from core.logger import logger


class DatabaseSessionManager:
    """
    Manages database connections and sessions.
    
    Features:
    - Connection pooling
    - Async session management
    - Graceful shutdown handling
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database connection pool."""
        if self._initialized:
            return
        
        # Create engine with connection pool
        engine_kwargs = {
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
            "pool_recycle": settings.DATABASE_POOL_RECYCLE,
            "pool_pre_ping": settings.DATABASE_POOL_PRE_PING,
            "echo": settings.DEBUG,
        }
        
        # Use NullPool for testing to avoid connection leaks
        if settings.ENVIRONMENT == "testing":
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
        
        self._engine = create_async_engine(
            settings.DATABASE_URL,
            **engine_kwargs,
        )
        
        self._sessionmaker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        self._initialized = True
        logger.info(f"Database connection pool initialized (pool_size={settings.DATABASE_POOL_SIZE})")
    
    async def close(self) -> None:
        """Close all database connections."""
        if self._engine:
            await self._engine.dispose()
            self._initialized = False
            logger.info("Database connection pool closed")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session.
        
        Yields:
            AsyncSession: Database session
        """
        if not self._initialized:
            await self.initialize()
        
        async with self._sessionmaker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a session with transaction management.
        
        Yields:
            AsyncSession: Database session with transaction
        """
        if not self._initialized:
            await self.initialize()
        
        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._initialized


# Global session manager instance
_session_manager = DatabaseSessionManager()


async def init_db() -> None:
    """Initialize database connection pool."""
    await _session_manager.initialize()


async def close_db() -> None:
    """Close database connection pool."""
    await _session_manager.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async for session in _session_manager.get_session():
        yield session


async def get_transaction_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session with transaction auto-commit.
    
    Yields:
        AsyncSession: Database session with transaction
    """
    async with _session_manager.transaction() as session:
        yield session


__all__ = [
    "DatabaseSessionManager",
    "init_db",
    "close_db",
    "get_db_session",
    "get_transaction_session",
]