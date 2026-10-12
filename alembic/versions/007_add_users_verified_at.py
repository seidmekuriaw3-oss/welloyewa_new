"""Add the user verification timestamp column.

Revision ID: 007_add_users_verified_at
Revises: 006_add_vendor_order_item_fields
"""

from alembic import op
import sqlalchemy as sa


revision = "007_add_users_verified_at"
down_revision = "006_add_vendor_order_item_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("verified_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "verified_at")
