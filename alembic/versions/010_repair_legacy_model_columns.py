"""Add model columns absent from legacy create_all databases.

Revision ID: 010_repair_legacy_model_columns
Revises: 009_align_model_schema
"""

from alembic import op


revision = "010_repair_legacy_model_columns"
down_revision = "009_align_model_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_language "
        "VARCHAR(10) DEFAULT 'am'"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_settings JSON"
    )
    op.execute(
        "UPDATE users SET preferred_language = language "
        "WHERE language IS NOT NULL"
    )

    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_attempts "
        "INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS last_payment_error TEXT"
    )
    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS reconciliation_status "
        "VARCHAR(50)"
    )
    op.execute(
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS reserved_quantity "
        "INTEGER NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.drop_column("products", "reserved_quantity")
    op.drop_column("orders", "reconciliation_status")
    op.drop_column("orders", "last_payment_error")
    op.drop_column("orders", "payment_attempts")
    op.drop_column("users", "notification_settings")
    op.drop_column("users", "preferred_language")
