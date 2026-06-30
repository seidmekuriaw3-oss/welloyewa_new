import asyncio
import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from infrastructure.database.base import Base
from apps.common.models import *
from apps.users.models import *
from apps.products.models import *
from apps.orders.models import *
from apps.inventory.models import *
from apps.marketing.models import *
from apps.support.models import *

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_async_database_url() -> str:
    """Return a clean asyncpg-compatible URL (no sslmode query param)."""
    url = os.environ.get("DATABASE_URL", "")
    # Ensure asyncpg driver
    url = re.sub(r"^postgresql://", "postgresql+asyncpg://", url)
    url = re.sub(r"^postgres://",   "postgresql+asyncpg://", url)
    # Strip sslmode — asyncpg doesn't accept it as a query param
    url = re.sub(r"[?&]sslmode=[^&]*", "", url)
    url = re.sub(r"\?$", "", url)
    return url


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(
        get_async_database_url(),
        poolclass=pool.NullPool,
    )
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_offline() -> None:
    url = get_async_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
