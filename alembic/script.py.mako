# ============================
# WOLLOYEWA STORE BOT - MIGRATION TEMPLATE
# ============================
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# Revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade database to this revision."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade database to previous revision."""
    ${downgrades if downgrades else "pass"}


# ============================
# Custom Helper Functions
# ============================

def table_exists(table_name: str, schema: str = None) -> bool:
    """Check if a table exists in the database."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def column_exists(table_name: str, column_name: str, schema: str = None) -> bool:
    """Check if a column exists in a table."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = inspector.get_columns(table_name, schema=schema)
    return any(c['name'] == column_name for c in columns)


def create_enum_if_not_exists(enum_name: str, values: list, schema: str = None):
    """Create an ENUM type if it doesn't exist."""
    from sqlalchemy.dialects.postgresql import ENUM
    
    enum = ENUM(*values, name=enum_name, create_type=False)
    if not enum_name in op.get_context().opts.get('pg_enums', {}):
        enum.create(op.get_bind(), checkfirst=True)


def safe_drop_column(table_name: str, column_name: str, schema: str = None):
    """Safely drop a column if it exists."""
    if column_exists(table_name, column_name, schema):
        op.drop_column(table_name, column_name, schema=schema)


def safe_add_column(table_name: str, column: sa.Column, schema: str = None):
    """Safely add a column if it doesn't exist."""
    if not column_exists(table_name, column.name, schema):
        op.add_column(table_name, column, schema=schema)


def execute_sql_file(file_path: str):
    """Execute SQL from a file."""
    with open(file_path, 'r') as f:
        sql = f.read()
        op.execute(sql)