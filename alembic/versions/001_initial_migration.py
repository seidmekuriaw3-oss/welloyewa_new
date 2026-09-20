# ============================
# WOLLOYEWA STORE BOT - INITIAL MIGRATION
# ============================
"""Initial database schema for Wolloyewa Store Bot

Revision ID: 001_initial_migration
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision: str = '001_initial_migration'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database tables."""
    
    # ============================
    # ENUM Types
    # ============================
    
    # User related enums
    op.execute("CREATE TYPE user_role AS ENUM ('customer', 'vendor', 'admin', 'super_admin')")
    op.execute("CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended', 'banned')")
    op.execute("CREATE TYPE gender AS ENUM ('male', 'female', 'other')")
    
    # Order related enums
    op.execute("CREATE TYPE order_status AS ENUM ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')")
    op.execute("CREATE TYPE payment_status AS ENUM ('pending', 'paid', 'failed', 'refunded', 'partial')")
    op.execute("CREATE TYPE payment_method AS ENUM ('chapa', 'telebirr', 'cbe_birr', 'cash_on_delivery')")
    
    # Product related enums
    op.execute("CREATE TYPE product_status AS ENUM ('draft', 'active', 'out_of_stock', 'discontinued')")
    op.execute("CREATE TYPE product_category AS ENUM ('electronics', 'clothing', 'food', 'books', 'beauty', 'health', 'home', 'sports', 'toys', 'other')")
    
    # Other enums
    op.execute("CREATE TYPE shipping_method AS ENUM ('standard', 'express', 'pickup')")
    op.execute("CREATE TYPE notification_type AS ENUM ('email', 'sms', 'telegram', 'push')")
    
    # ============================
    # Users Table
    # ============================
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False, unique=True),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('role', sa.Enum('customer', 'vendor', 'admin', 'super_admin', name='user_role'), nullable=False, server_default='customer'),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', 'banned', name='user_status'), nullable=False, server_default='active'),
        sa.Column('gender', sa.Enum('male', 'female', 'other', name='gender'), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('profile_picture', sa.String(500), nullable=True),
        sa.Column('language', sa.String(10), nullable=False, server_default='am'),
        sa.Column('location_lat', sa.Float(), nullable=True),
        sa.Column('location_lng', sa.Float(), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('subcity', sa.String(100), nullable=True),
        sa.Column('woreda', sa.String(50), nullable=True),
        sa.Column('house_number', sa.String(50), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_active', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    
    op.create_index('idx_users_telegram_id', 'users', ['telegram_id'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('idx_users_phone', 'users', ['phone_number'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    
    # ============================
    # Vendors Table (Extended vendor info)
    # ============================
    op.create_table(
        'vendors',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('business_name', sa.String(200), nullable=False),
        sa.Column('business_license', sa.String(100), nullable=True),
        sa.Column('tin_number', sa.String(50), nullable=True),
        sa.Column('business_address', sa.Text(), nullable=True),
        sa.Column('business_phone', sa.String(20), nullable=True),
        sa.Column('business_email', sa.String(255), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('cover_image', sa.String(500), nullable=True),
        sa.Column('rating', sa.Float(), nullable=False, server_default='0'),
        sa.Column('total_sales', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_license'),
        sa.UniqueConstraint('tin_number')
    )
    
    op.create_index('idx_vendors_user_id', 'vendors', ['user_id'])
    op.create_index('idx_vendors_is_approved', 'vendors', ['is_approved'])
    op.create_index('idx_vendors_rating', 'vendors', ['rating'])
    
    # ============================
    # Products Table
    # ============================
    op.create_table(
        'products',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('vendor_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('short_description', sa.String(500), nullable=True),
        sa.Column('category', sa.Enum('electronics', 'clothing', 'food', 'books', 'beauty', 'health', 'home', 'sports', 'toys', 'other', name='product_category'), nullable=False),
        sa.Column('subcategory', sa.String(100), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('compare_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('cost_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('stock_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('low_stock_threshold', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('sku', sa.String(100), nullable=False, unique=True),
        sa.Column('barcode', sa.String(100), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('dimensions', sa.String(100), nullable=True),
        sa.Column('images', sa.JSON(), nullable=True),
        sa.Column('video_url', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('draft', 'active', 'out_of_stock', 'discontinued', name='product_status'), nullable=False, server_default='draft'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_on_sale', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sale_start_date', sa.DateTime(), nullable=True),
        sa.Column('sale_end_date', sa.DateTime(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('meta_title', sa.String(255), nullable=True),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('views_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('sales_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('rating', sa.Float(), nullable=False, server_default='0'),
        sa.Column('reviews_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_products_vendor_id', 'products', ['vendor_id'])
    op.create_index('idx_products_category', 'products', ['category'])
    op.create_index('idx_products_status', 'products', ['status'])
    op.create_index('idx_products_price', 'products', ['price'])
    op.create_index('idx_products_slug', 'products', ['slug'])
    op.create_index('idx_products_sku', 'products', ['sku'])
    op.create_index('idx_products_created_at', 'products', ['created_at'])
    
    # ============================
    # Product Images Table
    # ============================
    op.create_table(
        'product_images',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.BigInteger(), nullable=False),
        sa.Column('image_url', sa.String(500), nullable=False),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('alt_text', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_product_images_product_id', 'product_images', ['product_id'])
    
    # ============================
    # Orders Table
    # ============================
    op.create_table(
        'orders',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_number', sa.String(50), nullable=False, unique=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('vendor_id', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded', name='order_status'), nullable=False, server_default='pending'),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False),
        sa.Column('shipping_fee', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('tax', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('discount', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(10, 2), nullable=False),
        sa.Column('payment_method', sa.Enum('chapa', 'telebirr', 'cbe_birr', 'cash_on_delivery', name='payment_method'), nullable=False),
        sa.Column('payment_status', sa.Enum('pending', 'paid', 'failed', 'refunded', 'partial', name='payment_status'), nullable=False, server_default='pending'),
        sa.Column('payment_transaction_id', sa.String(255), nullable=True),
        sa.Column('shipping_address', sa.Text(), nullable=False),
        sa.Column('shipping_city', sa.String(100), nullable=False),
        sa.Column('shipping_phone', sa.String(20), nullable=False),
        sa.Column('shipping_method', sa.Enum('standard', 'express', 'pickup', name='shipping_method'), nullable=False, server_default='standard'),
        sa.Column('tracking_number', sa.String(100), nullable=True),
        sa.Column('customer_notes', sa.Text(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_reason', sa.Text(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_orders_user_id', 'orders', ['user_id'])
    op.create_index('idx_orders_vendor_id', 'orders', ['vendor_id'])
    op.create_index('idx_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_order_number', 'orders', ['order_number'])
    op.create_index('idx_orders_payment_status', 'orders', ['payment_status'])
    op.create_index('idx_orders_created_at', 'orders', ['created_at'])
    
    # ============================
    # Order Items Table
    # ============================
    op.create_table(
        'order_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=False),
        sa.Column('product_id', sa.BigInteger(), nullable=False),
        sa.Column('product_name', sa.String(255), nullable=False),
        sa.Column('product_sku', sa.String(100), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('total_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('discount', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_order_items_order_id', 'order_items', ['order_id'])
    op.create_index('idx_order_items_product_id', 'order_items', ['product_id'])
    
    # ============================
    # Carts Table
    # ============================
    op.create_table(
        'carts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('items', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('total', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_carts_user_id', 'carts', ['user_id'])
    op.create_index('idx_carts_session_id', 'carts', ['session_id'])
    
    # ============================
    # Wishlists Table
    # ============================
    op.create_table(
        'wishlists',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('product_id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'product_id', name='unique_user_product_wishlist')
    )
    
    op.create_index('idx_wishlists_user_id', 'wishlists', ['user_id'])
    op.create_index('idx_wishlists_product_id', 'wishlists', ['product_id'])
    
    # ============================
    # Reviews Table
    # ============================
    op.create_table(
        'reviews',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('product_id', sa.BigInteger(), nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('images', sa.JSON(), nullable=True),
        sa.Column('is_verified_purchase', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_reviews_user_id', 'reviews', ['user_id'])
    op.create_index('idx_reviews_product_id', 'reviews', ['product_id'])
    op.create_index('idx_reviews_rating', 'reviews', ['rating'])
    
    # ============================
    # Notifications Table
    # ============================
    op.create_table(
        'notifications',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('idx_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('idx_notifications_created_at', 'notifications', ['created_at'])


def downgrade() -> None:
    """Drop all tables and enums."""
    
    # Drop tables in reverse order
    op.drop_table('notifications')
    op.drop_table('reviews')
    op.drop_table('wishlists')
    op.drop_table('carts')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('product_images')
    op.drop_table('products')
    op.drop_table('vendors')
    op.drop_table('users')
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS notification_type")
    op.execute("DROP TYPE IF EXISTS shipping_method")
    op.execute("DROP TYPE IF EXISTS product_category")
    op.execute("DROP TYPE IF EXISTS product_status")
    op.execute("DROP TYPE IF EXISTS payment_method")
    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute("DROP TYPE IF EXISTS order_status")
    op.execute("DROP TYPE IF EXISTS gender")
    op.execute("DROP TYPE IF EXISTS user_status")
    op.execute("DROP TYPE IF EXISTS user_role")