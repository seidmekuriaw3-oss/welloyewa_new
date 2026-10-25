"""Add product approval statuses.

Revision ID: 012_product_approval
Revises: 011_normalize_legacy_enum_labels
"""

from alembic import op


revision = "012_product_approval"
down_revision = "011_normalize_legacy_enum_labels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE product_status ADD VALUE IF NOT EXISTS 'pending'")
    op.execute("ALTER TYPE product_status ADD VALUE IF NOT EXISTS 'rejected'")


def downgrade() -> None:
    op.execute(
        """
        UPDATE products
        SET status = 'draft'
        WHERE status IN ('pending', 'rejected')
        """
    )
    op.execute("ALTER TABLE products ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE product_status RENAME TO product_status_old")
    op.execute(
        """
        CREATE TYPE product_status AS ENUM (
            'draft',
            'active',
            'out_of_stock',
            'discontinued'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE products
        ALTER COLUMN status TYPE product_status
        USING status::text::product_status
        """
    )
    op.execute("ALTER TABLE products ALTER COLUMN status SET DEFAULT 'draft'")
    op.execute("DROP TYPE product_status_old")
