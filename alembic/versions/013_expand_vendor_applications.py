"""Add comprehensive vendor application details.

Revision ID: 013_vendor_application_details
Revises: 012_product_approval
"""

import sqlalchemy as sa
from alembic import op


revision = "013_vendor_application_details"
down_revision = "012_product_approval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vendors", sa.Column("license_document_file_id", sa.String(255), nullable=True))
    op.add_column("vendors", sa.Column("license_document_type", sa.String(20), nullable=True))
    op.add_column("vendors", sa.Column("business_category", sa.String(100), nullable=True))
    op.add_column("vendors", sa.Column("region", sa.String(100), nullable=True))
    op.add_column("vendors", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("vendors", sa.Column("subcity", sa.String(100), nullable=True))
    op.add_column("vendors", sa.Column("specific_location", sa.Text(), nullable=True))
    op.add_column("vendors", sa.Column("maps_link", sa.String(500), nullable=True))
    op.add_column("vendors", sa.Column("bank_name", sa.String(100), nullable=True))
    op.add_column("vendors", sa.Column("bank_account_name", sa.String(200), nullable=True))
    op.add_column("vendors", sa.Column("bank_account_number", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("vendors", "bank_account_number")
    op.drop_column("vendors", "bank_account_name")
    op.drop_column("vendors", "bank_name")
    op.drop_column("vendors", "maps_link")
    op.drop_column("vendors", "specific_location")
    op.drop_column("vendors", "subcity")
    op.drop_column("vendors", "city")
    op.drop_column("vendors", "region")
    op.drop_column("vendors", "business_category")
    op.drop_column("vendors", "license_document_type")
    op.drop_column("vendors", "license_document_file_id")
