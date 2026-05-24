# ============================
# WOLLOYEWA STORE BOT - ALEMBIC ENVIRONMENT
# ============================

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Import all models for Alembic to detect
from infrastructure.database.base import Base
from apps.common.models import *
from apps.users.models import *
from apps.products.models import *
from apps.orders.models import *
from apps.inventory.models import *
from apps.marketing.models import *
from apps.support.models import *

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support
target_metadata = Base.metadata

# Import settings for database URL
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.config import settings


def get_database_url() -> str:
    """Get database URL from settings."""
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # For SQLite support
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations with connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()
    
    connectable = create_async_engine(
        get_database_url(),
        poolclass=pool.NullPool,
        echo=True if settings.DEBUG else False,
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())


# ============================
# Custom Migration Helpers
# ============================

def include_object(object, name, type_, reflected, compare_to):
    """
    Filter which objects should be included in migration.
    
    Skip any objects that shouldn't be version controlled.
    """
    if type_ == "table" and name in ["spatial_ref_sys", "geography_columns"]:
        return False
    
    # Include all other objects
    return True


def upgrade():
    """Alias for running upgrades."""
    pass


def downgrade():
    """Alias for running downgrades."""
    pass


# Register custom comparators for better migration detection
from alembic.autogenerate import comparators

@comparators.dispatch_for("schema")
def compare_foreign_keys(autogen_context, upgrade_ops, schemas):
    """Custom foreign key comparator."""
    return []


# Add version table configuration
from alembic import op
import sqlalchemy as sa

def create_version_table():
    """Create version table if it doesn't exist."""
    op.create_table(
        'alembic_version',
        sa.Column('version_num', sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint('version_num', name='alembic_version_pkc')
    )