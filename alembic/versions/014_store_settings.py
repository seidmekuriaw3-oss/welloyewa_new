"""Add persistent operational store settings.

Revision ID: 014_store_settings
Revises: 013_vendor_application_details
"""

import sqlalchemy as sa

from alembic import op

revision = "014_store_settings"
down_revision = "013_vendor_application_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="ETB"),
        sa.Column(
            "enabled_payment_methods",
            sa.JSON(),
            nullable=False,
            server_default='["chapa","telebirr","cbe","cod"]',
        ),
        sa.Column(
            "notification_settings",
            sa.JSON(),
            nullable=False,
            server_default=(
                '{"customer_orders":true,"vendor_updates":true,'
                '"admin_alerts":true,"support_updates":true}'
            ),
        ),
        sa.Column("maintenance_message", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("store_settings")
