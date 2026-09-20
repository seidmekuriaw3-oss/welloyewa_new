"""Add audit logs and activity tracking tables

Revision ID: 005_add_audit_logs
Revises: 004_add_payment_reconciliation
Create Date: 2024-01-18 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision: str = '005_add_audit_logs'
down_revision: Union[str, None] = '004_add_payment_reconciliation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add audit logs and activity tracking tables."""
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=True),
        sa.Column('old_data', sa.JSON(), nullable=True),
        sa.Column('new_data', sa.JSON(), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_logs_request_id', 'audit_logs', ['request_id'])
    
    # Create user_activity_log table
    op.create_table(
        'user_activity_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('activity_data', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_user_activity_log_user_id', 'user_activity_log', ['user_id'])
    op.create_index('idx_user_activity_log_type', 'user_activity_log', ['activity_type'])
    op.create_index('idx_user_activity_log_created_at', 'user_activity_log', ['created_at'])
    
    # Create api_access_log table
    op.create_table(
        'api_access_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('api_key_id', sa.BigInteger(), nullable=True),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('endpoint', sa.String(500), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_body', sa.Text(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_api_access_log_request_id', 'api_access_log', ['request_id'])
    op.create_index('idx_api_access_log_user_id', 'api_access_log', ['user_id'])
    op.create_index('idx_api_access_log_endpoint', 'api_access_log', ['endpoint'])
    op.create_index('idx_api_access_log_created_at', 'api_access_log', ['created_at'])
    op.create_index('idx_api_access_log_status', 'api_access_log', ['status_code'])
    
    # Create failed_login_attempts table
    op.create_table(
        'failed_login_attempts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('telegram_id', sa.BigInteger(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('attempt_data', sa.JSON(), nullable=True),
        sa.Column('reason', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_failed_login_user_id', 'failed_login_attempts', ['user_id'])
    op.create_index('idx_failed_login_telegram_id', 'failed_login_attempts', ['telegram_id'])
    op.create_index('idx_failed_login_ip', 'failed_login_attempts', ['ip_address'])
    op.create_index('idx_failed_login_created_at', 'failed_login_attempts', ['created_at'])
    
    # Create data_export_log table
    op.create_table(
        'data_export_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('export_type', sa.String(100), nullable=False),
        sa.Column('export_format', sa.String(20), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('downloaded_at', sa.DateTime(), nullable=True),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_data_export_user_id', 'data_export_log', ['user_id'])
    op.create_index('idx_data_export_status', 'data_export_log', ['status'])
    op.create_index('idx_data_export_created_at', 'data_export_log', ['created_at'])
    
    # Create system_health_log table
    op.create_table(
        'system_health_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('service_name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_system_health_service', 'system_health_log', ['service_name'])
    op.create_index('idx_system_health_status', 'system_health_log', ['status'])
    op.create_index('idx_system_health_created_at', 'system_health_log', ['created_at'])
    
    # Add retention policy columns
    op.add_column('audit_logs', sa.Column('retention_date', sa.DateTime(), nullable=True))
    op.add_column('user_activity_log', sa.Column('retention_date', sa.DateTime(), nullable=True))
    op.add_column('api_access_log', sa.Column('retention_date', sa.DateTime(), nullable=True))
    
    # Create function to set retention date
    op.execute("""
        CREATE OR REPLACE FUNCTION set_retention_date()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.retention_date = NEW.created_at + INTERVAL '365 days';
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create triggers for retention date
    op.execute("""
        CREATE TRIGGER set_audit_log_retention_date
        BEFORE INSERT ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION set_retention_date();
    """)
    
    op.execute("""
        CREATE TRIGGER set_user_activity_retention_date
        BEFORE INSERT ON user_activity_log
        FOR EACH ROW
        EXECUTE FUNCTION set_retention_date();
    """)
    
    op.execute("""
        CREATE TRIGGER set_api_access_retention_date
        BEFORE INSERT ON api_access_log
        FOR EACH ROW
        EXECUTE FUNCTION set_retention_date();
    """)


def downgrade() -> None:
    """Remove audit logs and activity tracking tables."""
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS set_api_access_retention_date ON api_access_log")
    op.execute("DROP TRIGGER IF EXISTS set_user_activity_retention_date ON user_activity_log")
    op.execute("DROP TRIGGER IF EXISTS set_audit_log_retention_date ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS set_retention_date")
    
    # Drop columns
    op.drop_column('api_access_log', 'retention_date')
    op.drop_column('user_activity_log', 'retention_date')
    op.drop_column('audit_logs', 'retention_date')
    
    # Drop tables in reverse order
    op.drop_index('idx_system_health_created_at', table_name='system_health_log')
    op.drop_index('idx_system_health_status', table_name='system_health_log')
    op.drop_index('idx_system_health_service', table_name='system_health_log')
    op.drop_table('system_health_log')
    
    op.drop_index('idx_data_export_created_at', table_name='data_export_log')
    op.drop_index('idx_data_export_status', table_name='data_export_log')
    op.drop_index('idx_data_export_user_id', table_name='data_export_log')
    op.drop_table('data_export_log')
    
    op.drop_index('idx_failed_login_created_at', table_name='failed_login_attempts')
    op.drop_index('idx_failed_login_ip', table_name='failed_login_attempts')
    op.drop_index('idx_failed_login_telegram_id', table_name='failed_login_attempts')
    op.drop_index('idx_failed_login_user_id', table_name='failed_login_attempts')
    op.drop_table('failed_login_attempts')
    
    op.drop_index('idx_api_access_log_status', table_name='api_access_log')
    op.drop_index('idx_api_access_log_created_at', table_name='api_access_log')
    op.drop_index('idx_api_access_log_endpoint', table_name='api_access_log')
    op.drop_index('idx_api_access_log_user_id', table_name='api_access_log')
    op.drop_index('idx_api_access_log_request_id', table_name='api_access_log')
    op.drop_table('api_access_log')
    
    op.drop_index('idx_user_activity_log_created_at', table_name='user_activity_log')
    op.drop_index('idx_user_activity_log_type', table_name='user_activity_log')
    op.drop_index('idx_user_activity_log_user_id', table_name='user_activity_log')
    op.drop_table('user_activity_log')
    
    op.drop_index('idx_audit_logs_request_id', table_name='audit_logs')
    op.drop_index('idx_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('idx_audit_logs_action', table_name='audit_logs')
    op.drop_index('idx_audit_logs_entity', table_name='audit_logs')
    op.drop_index('idx_audit_logs_user_id', table_name='audit_logs')
    op.drop_table('audit_logs')