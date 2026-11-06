"""Add user token version for JWT revocation."""

import sqlalchemy as sa

from alembic import op

revision = "015_user_token_revocation"
down_revision = "014_store_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
