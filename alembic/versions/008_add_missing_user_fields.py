"""Add user model fields missing from the initial schema.

Revision ID: 008_add_missing_user_fields
Revises: 007_add_users_verified_at
"""

from alembic import op
import sqlalchemy as sa


revision = "008_add_missing_user_fields"
down_revision = "007_add_users_verified_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_login_ip", sa.String(length=45), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("reset_token", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("reset_token_expires", sa.DateTime(), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("extra_data", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "extra_data")
    op.drop_column("users", "is_deleted")
    op.drop_column("users", "reset_token_expires")
    op.drop_column("users", "reset_token")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "last_login_ip")
