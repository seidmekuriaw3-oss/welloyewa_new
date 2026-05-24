"""Add payment reconciliation tables

Revision ID: 004_add_payment_reconciliation
Revises: 003_add_inventory_tracking
Create Date: 2024-01-17 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision: str = '004_add_payment_reconciliation'
down_revision: Union[str, None] = '003_add_inventory_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add payment reconciliation tables."""
    
    # Create payment_transactions table
    op.create_table(
        'payment_transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('transaction_id', sa.String(255), nullable=False, unique=True),
        sa.Column('order_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='ETB'),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('gateway_response', sa.JSON(), nullable=True),
        sa.Column('gateway_transaction_id', sa.String(255), nullable=True),
        sa.Column('reference', sa.String(255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('failed_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_payment_transactions_txn_id', 'payment_transactions', ['transaction_id'])
    op.create_index('idx_payment_transactions_order_id', 'payment_transactions', ['order_id'])
    op.create_index('idx_payment_transactions_user_id', 'payment_transactions', ['user_id'])
    op.create_index('idx_payment_transactions_status', 'payment_transactions', ['status'])
    op.create_index('idx_payment_transactions_created_at', 'payment_transactions', ['created_at'])
    
    # Create refunds table
    op.create_table(
        'refunds',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('refund_id', sa.String(255), nullable=False, unique=True),
        sa.Column('transaction_id', sa.BigInteger(), nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('gateway_refund_id', sa.String(255), nullable=True),
        sa.Column('gateway_response', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('processed_by', sa.BigInteger(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transaction_id'], ['payment_transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_refunds_refund_id', 'refunds', ['refund_id'])
    op.create_index('idx_refunds_transaction_id', 'refunds', ['transaction_id'])
    op.create_index('idx_refunds_order_id', 'refunds', ['order_id'])
    op.create_index('idx_refunds_status', 'refunds', ['status'])
    
    # Create payment_reconciliation table
    op.create_table(
        'payment_reconciliation',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('reconciliation_id', sa.String(255), nullable=False, unique=True),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('total_transactions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('matched_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('matched_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('unmatched_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unmatched_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('discrepancy_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('report_data', sa.JSON(), nullable=True),
        sa.Column('processed_by', sa.BigInteger(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_payment_reconciliation_dates', 'payment_reconciliation', ['start_date', 'end_date'])
    op.create_index('idx_payment_reconciliation_status', 'payment_reconciliation', ['status'])
    
    # Add payment tracking columns to orders table
    op.add_column('orders', sa.Column('payment_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('orders', sa.Column('last_payment_error', sa.Text(), nullable=True))
    op.add_column('orders', sa.Column('reconciliation_status', sa.String(50), nullable=True))
    
    # Create function to update order payment status
    op.execute("""
        CREATE OR REPLACE FUNCTION update_order_payment_status()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE orders 
            SET 
                payment_status = NEW.status,
                payment_transaction_id = NEW.transaction_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.order_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for payment transactions
    op.execute("""
        CREATE TRIGGER update_order_payment_status_trigger
        AFTER INSERT OR UPDATE OF status ON payment_transactions
        FOR EACH ROW
        EXECUTE FUNCTION update_order_payment_status();
    """)


def downgrade() -> None:
    """Remove payment reconciliation tables."""
    
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_order_payment_status_trigger ON payment_transactions")
    op.execute("DROP FUNCTION IF EXISTS update_order_payment_status")
    
    # Drop columns from orders
    op.drop_column('orders', 'reconciliation_status')
    op.drop_column('orders', 'last_payment_error')
    op.drop_column('orders', 'payment_attempts')
    
    # Drop tables in reverse order
    op.drop_index('idx_payment_reconciliation_status', table_name='payment_reconciliation')
    op.drop_index('idx_payment_reconciliation_dates', table_name='payment_reconciliation')
    op.drop_table('payment_reconciliation')
    
    op.drop_index('idx_refunds_status', table_name='refunds')
    op.drop_index('idx_refunds_order_id', table_name='refunds')
    op.drop_index('idx_refunds_transaction_id', table_name='refunds')
    op.drop_index('idx_refunds_refund_id', table_name='refunds')
    op.drop_table('refunds')
    
    op.drop_index('idx_payment_transactions_created_at', table_name='payment_transactions')
    op.drop_index('idx_payment_transactions_status', table_name='payment_transactions')
    op.drop_index('idx_payment_transactions_user_id', table_name='payment_transactions')
    op.drop_index('idx_payment_transactions_order_id', table_name='payment_transactions')
    op.drop_index('idx_payment_transactions_txn_id', table_name='payment_transactions')
    op.drop_table('payment_transactions')