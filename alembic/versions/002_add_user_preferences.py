"""Add user preferences table

Revision ID: 002_add_user_preferences
Revises: 001_initial_migration
Create Date: 2024-01-15 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision: str = '002_add_user_preferences'
down_revision: Union[str, None] = '001_initial_migration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user preferences table and related columns."""
    
    # Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('email_notifications', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sms_notifications', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_notifications', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('marketing_emails', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('promotional_sms', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('language', sa.String(10), nullable=False, server_default='am'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='ETB'),
        sa.Column('default_shipping_address_id', sa.BigInteger(), nullable=True),
        sa.Column('preferred_categories', sa.JSON(), nullable=True),
        sa.Column('share_activity', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_user_preferences_user_id')
    )
    
    # Create indexes
    op.create_index('idx_user_preferences_user_id', 'user_preferences', ['user_id'])
    op.create_index('idx_user_preferences_language', 'user_preferences', ['language'])
    
    # Add notification_settings column to users table (JSON for flexibility)
    op.add_column('users', sa.Column('notification_settings', sa.JSON(), nullable=True))
    
    # Add preferred_language column to users (redundant but useful for quick access)
    op.add_column('users', sa.Column('preferred_language', sa.String(10), server_default='am', nullable=True))
    
    # Migrate existing user language data
    op.execute("""
        UPDATE users 
        SET preferred_language = language 
        WHERE language IS NOT NULL
    """)
    
    # Create notification_tokens table for push notifications
    op.create_table(
        'notification_tokens',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('token', sa.String(500), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),  # android, ios, web
        sa.Column('device_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token', name='uq_notification_tokens_token')
    )
    
    op.create_index('idx_notification_tokens_user_id', 'notification_tokens', ['user_id'])
    op.create_index('idx_notification_tokens_token', 'notification_tokens', ['token'])


def downgrade() -> None:
    """Remove user preferences table and related columns."""
    
    # Drop notification_tokens table
    op.drop_index('idx_notification_tokens_token', table_name='notification_tokens')
    op.drop_index('idx_notification_tokens_user_id', table_name='notification_tokens')
    op.drop_table('notification_tokens')
    
    # Remove columns from users
    op.drop_column('users', 'preferred_language')
    op.drop_column('users', 'notification_settings')
    
    # Drop user_preferences table
    op.drop_index('idx_user_preferences_language', table_name='user_preferences')
    op.drop_index('idx_user_preferences_user_id', table_name='user_preferences')
    op.drop_table('user_preferences')