"""Add inventory tracking tables

Revision ID: 003_add_inventory_tracking
Revises: 002_add_user_preferences
Create Date: 2024-01-16 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision: str = '003_add_inventory_tracking'
down_revision: Union[str, None] = '002_add_user_preferences'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add inventory tracking tables."""
    
    # Create inventory table
    op.create_table(
        'inventories',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.BigInteger(), nullable=False, unique=True),
        sa.Column('vendor_id', sa.BigInteger(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reserved_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('low_stock_threshold', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('critical_stock_threshold', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('sku', sa.String(100), nullable=False, unique=True),
        sa.Column('barcode', sa.String(100), nullable=True),
        sa.Column('warehouse_location', sa.String(100), nullable=True),
        sa.Column('shelf_location', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_tracking_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_counted_at', sa.DateTime(), nullable=True),
        sa.Column('last_restocked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_inventories_product_id', 'inventories', ['product_id'])
    op.create_index('idx_inventories_vendor_id', 'inventories', ['vendor_id'])
    op.create_index('idx_inventories_sku', 'inventories', ['sku'])
    op.create_index('idx_inventories_low_stock', 'inventories', ['quantity', 'low_stock_threshold'])
    
    # Create inventory_movements table
    op.create_table(
        'inventory_movements',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('inventory_id', sa.BigInteger(), nullable=False),
        sa.Column('movement_type', sa.String(50), nullable=False),  # purchase, sale, return, adjustment, restock
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('previous_quantity', sa.Integer(), nullable=False),
        sa.Column('new_quantity', sa.Integer(), nullable=False),
        sa.Column('reference_id', sa.BigInteger(), nullable=True),
        sa.Column('reference_type', sa.String(50), nullable=True),  # order, return, adjustment
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('performed_by', sa.BigInteger(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['inventory_id'], ['inventories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_inventory_movements_inventory_id', 'inventory_movements', ['inventory_id'])
    op.create_index('idx_inventory_movements_created_at', 'inventory_movements', ['created_at'])
    op.create_index('idx_inventory_movements_type', 'inventory_movements', ['movement_type'])
    
    # Create stock_reservations table
    op.create_table(
        'stock_reservations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('inventory_id', sa.BigInteger(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('reference_id', sa.BigInteger(), nullable=True),
        sa.Column('reference_type', sa.String(50), nullable=False),  # order, cart
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('expires_in_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['inventory_id'], ['inventories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_stock_reservations_inventory_id', 'stock_reservations', ['inventory_id'])
    op.create_index('idx_stock_reservations_reference', 'stock_reservations', ['reference_type', 'reference_id'])
    op.create_index('idx_stock_reservations_status', 'stock_reservations', ['status'])
    op.create_index('idx_stock_reservations_expires_at', 'stock_reservations', ['expires_at'])
    
    # Add stock columns to products table (denormalized for quick access)
    op.add_column('products', sa.Column('reserved_quantity', sa.Integer(), nullable=False, server_default='0'))
    
    # Create function to update product reserved quantity
    op.execute("""
        CREATE OR REPLACE FUNCTION update_product_reserved_quantity()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE products 
            SET reserved_quantity = (
                SELECT COALESCE(SUM(reserved_quantity), 0)
                FROM inventories 
                WHERE inventories.product_id = products.id
            )
            WHERE id = NEW.product_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for inventory updates
    op.execute("""
        CREATE TRIGGER update_product_reserved_quantity_trigger
        AFTER INSERT OR UPDATE OF reserved_quantity ON inventories
        FOR EACH ROW
        EXECUTE FUNCTION update_product_reserved_quantity();
    """)


def downgrade() -> None:
    """Remove inventory tracking tables."""
    
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_product_reserved_quantity_trigger ON inventories")
    op.execute("DROP FUNCTION IF EXISTS update_product_reserved_quantity")
    
    # Drop column from products
    op.drop_column('products', 'reserved_quantity')
    
    # Drop tables in reverse order
    op.drop_index('idx_stock_reservations_expires_at', table_name='stock_reservations')
    op.drop_index('idx_stock_reservations_status', table_name='stock_reservations')
    op.drop_index('idx_stock_reservations_reference', table_name='stock_reservations')
    op.drop_index('idx_stock_reservations_inventory_id', table_name='stock_reservations')
    op.drop_table('stock_reservations')
    
    op.drop_index('idx_inventory_movements_type', table_name='inventory_movements')
    op.drop_index('idx_inventory_movements_created_at', table_name='inventory_movements')
    op.drop_index('idx_inventory_movements_inventory_id', table_name='inventory_movements')
    op.drop_table('inventory_movements')
    
    op.drop_index('idx_inventories_low_stock', table_name='inventories')
    op.drop_index('idx_inventories_sku', table_name='inventories')
    op.drop_index('idx_inventories_vendor_id', table_name='inventories')
    op.drop_index('idx_inventories_product_id', table_name='inventories')
    op.drop_table('inventories')