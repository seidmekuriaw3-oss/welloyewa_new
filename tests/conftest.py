# ============================
# WOLLOYEWA STORE BOT - PYTEST CONFIGURATION
# ============================
"""Pytest configuration and fixtures for testing."""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from core.dependencies import get_db_session
from infrastructure.database.base import Base
from main import app
from apps.products.models import Product

# ============================
# Test Database Setup
# ============================

# Prefer a local SQLite database when Postgres is unavailable so CI and local runs
# do not fail during test setup for a missing service or database.
TEST_DB_PATH = Path(__file__).resolve().parents[1] / ".pytest_cache" / "test_db.sqlite3"
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}",
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine_kwargs = {"echo": False}
    if TEST_DATABASE_URL.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        engine_kwargs.update(
            {
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            }
        )

    engine = create_async_engine(TEST_DATABASE_URL, **engine_kwargs)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(test_engine) -> AsyncGenerator:
    """Create test client for FastAPI app."""
    test_sessionmaker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db_session():
        async with test_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=app)
    try:
        async with test_sessionmaker() as session:
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(delete(table))
            session.add_all(
                [
                    Product(
                        vendor_id=1,
                        name="Seed Product 1",
                        slug="seed-product-1",
                        price=50,
                        stock_quantity=10,
                        sku="SEED001",
                    ),
                    Product(
                        vendor_id=1,
                        name="Seed Product 2",
                        slug="seed-product-2",
                        price=30,
                        stock_quantity=10,
                        sku="SEED002",
                    ),
                ]
            )
            await session.commit()
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# ============================
# Mock Data Fixtures
# ============================


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "phone_number": "0912345678",
        "email": "test@example.com",
        "language": "am",
    }


@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        "name": "Test Product",
        "price": 1000.00,
        "stock_quantity": 50,
        "sku": "TEST001",
        "category": "electronics",
        "description": "This is a test product",
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 2, "quantity": 1},
        ],
        "payment_method": "chapa",
        "shipping_address": "123 Test St, Addis Ababa",
        "shipping_city": "Addis Ababa",
        "shipping_phone": "0912345678",
    }


# ============================
# Authentication Fixtures
# ============================


@pytest.fixture
def auth_token():
    """Sample JWT token for testing."""
    from core.security import create_access_token

    token_data = {
        "sub": "1",
        "telegram_id": 123456789,
        "role": "customer",
    }
    return create_access_token(token_data)


@pytest.fixture
def admin_token():
    """Sample admin JWT token for testing."""
    from core.security import create_access_token

    token_data = {
        "sub": "1",
        "telegram_id": 123456789,
        "role": "admin",
    }
    return create_access_token(token_data)


# ============================
# Mock Services Fixtures
# ============================


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=False)

    return mock


@pytest.fixture
def mock_payment_provider():
    """Mock payment provider for testing."""
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.initialize_payment = AsyncMock(
        return_value={
            "success": True,
            "transaction_id": "test_txn_123",
            "payment_url": "https://test.com/pay",
        }
    )
    mock.verify_payment = AsyncMock(
        return_value={
            "verified": True,
            "status": "completed",
        }
    )

    return mock


# ============================
# Helper Functions
# ============================


@pytest.fixture
def create_test_user(db_session):
    """Create a test user in database."""

    async def _create_user(data: dict):
        from apps.users.models import User

        user = User(**data)
        db_session.add(user)
        await db_session.flush()
        return user

    return _create_user


@pytest.fixture
def create_test_product(db_session):
    """Create a test product in database."""

    async def _create_product(data: dict, vendor_id: int = 1):
        from apps.products.models import Product

        product = Product(vendor_id=vendor_id, **data)
        db_session.add(product)
        await db_session.flush()
        return product

    return _create_product


# ============================
# Pytest Configuration
# ============================


def pytest_configure(config):
    """Pytest configuration hook."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "api: marks tests as API tests")


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "testing")
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)


__all__ = [
    "admin_token",
    "auth_token",
    "client",
    "create_test_product",
    "create_test_user",
    "db_session",
    "mock_payment_provider",
    "mock_redis",
    "sample_order_data",
    "sample_product_data",
    "sample_user_data",
]
