"""Add per-vendor ownership and status to order items.

Revision ID: 006_add_vendor_order_item_fields
"""

from alembic import op
import sqlalchemy as sa


revision = "006_add_vendor_order_item_fields"
down_revision = "005_add_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("vendor_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "order_items",
        sa.Column("vendor_status", sa.String(length=50), nullable=False, server_default="pending"),
    )
    op.create_index("ix_order_items_vendor_id", "order_items", ["vendor_id"])
    op.create_index("ix_order_items_vendor_status", "order_items", ["vendor_status"])
    op.create_foreign_key(
        "fk_order_items_vendor_id_vendors",
        "order_items",
        "vendors",
        ["vendor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE order_items
        SET vendor_id = products.vendor_id
        FROM products
        WHERE order_items.product_id = products.id
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_order_items_vendor_id_vendors", "order_items", type_="foreignkey")
    op.drop_index("ix_order_items_vendor_status", table_name="order_items")
    op.drop_index("ix_order_items_vendor_id", table_name="order_items")
    op.drop_column("order_items", "vendor_status")
    op.drop_column("order_items", "vendor_id")