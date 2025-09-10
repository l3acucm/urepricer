"""Initial migration - create all tables

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create price_resets table
    op.create_table('price_resets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reset_time', sa.Time(), nullable=False),
        sa.Column('resume_time', sa.Time(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('reset_active', sa.Boolean(), nullable=True),
        sa.Column('product_condition', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_price_resets')
    )
    op.create_index(op.f('ix_price_resets_id'), 'price_resets', ['id'], unique=False)

    # Create user_accounts table
    op.create_table('user_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('seller_id', sa.String(length=100), nullable=False),
        sa.Column('marketplace_type', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('repricer_enabled', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(length=100), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('is_notifications_active', sa.Boolean(), nullable=True),
        sa.Column('anyoffer_changed_subscription_id', sa.String(length=100), nullable=True),
        sa.Column('feed_ready_notification_subscription_id', sa.String(length=100), nullable=True),
        sa.Column('anyoffer_changed_destination_id', sa.String(length=100), nullable=True),
        sa.Column('feed_ready_destination_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('price_reset_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['price_reset_id'], ['price_resets.id'], name='fk_user_accounts_price_reset_id_price_resets'),
        sa.PrimaryKeyConstraint('id', name='pk_user_accounts')
    )
    op.create_index(op.f('ix_user_accounts_id'), 'user_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_user_accounts_seller_id'), 'user_accounts', ['seller_id'], unique=False)
    op.create_index(op.f('ix_user_accounts_user_id'), 'user_accounts', ['user_id'], unique=True)

    # Create feeds table
    op.create_table('feeds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('feed_submission_id', sa.String(length=255), nullable=False),
        sa.Column('seller_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False),
        sa.Column('message', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_feeds')
    )
    op.create_index(op.f('ix_feeds_feed_submission_id'), 'feeds', ['feed_submission_id'], unique=True)
    op.create_index(op.f('ix_feeds_id'), 'feeds', ['id'], unique=False)
    op.create_index(op.f('ix_feeds_seller_id'), 'feeds', ['seller_id'], unique=False)

    # Create products table
    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asin', sa.String(length=255), nullable=False),
        sa.Column('sku', sa.String(length=255), nullable=True),
        sa.Column('seller_id', sa.String(length=255), nullable=False),
        sa.Column('old_price', sa.Float(), nullable=True),
        sa.Column('new_price', sa.Float(), nullable=True),
        sa.Column('min_price', sa.Float(), nullable=True),
        sa.Column('max_price', sa.Float(), nullable=True),
        sa.Column('competitor_price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('item_condition', sa.String(length=20), nullable=True),
        sa.Column('is_b2b', sa.Boolean(), nullable=True),
        sa.Column('price_type', sa.String(length=255), nullable=True),
        sa.Column('tier_identifier', sa.Integer(), nullable=True),
        sa.Column('strategy_id', sa.Integer(), nullable=True),
        sa.Column('repricer_type', sa.String(length=255), nullable=True),
        sa.Column('message', sa.String(length=200), nullable=True),
        sa.Column('feed_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['feed_id'], ['feeds.id'], name='fk_products_feed_id_feeds'),
        sa.PrimaryKeyConstraint('id', name='pk_products')
    )
    op.create_index(op.f('ix_products_asin'), 'products', ['asin'], unique=False)
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index(op.f('ix_products_seller_id'), 'products', ['seller_id'], unique=False)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=False)

    # Create price_change_logs table
    op.create_table('price_change_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asin', sa.String(length=255), nullable=False),
        sa.Column('sku', sa.String(length=255), nullable=True),
        sa.Column('seller_id', sa.String(length=255), nullable=False),
        sa.Column('old_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('new_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('min_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('max_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('competitor_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('update_on_platform', sa.Boolean(), nullable=True),
        sa.Column('is_b2b', sa.Boolean(), nullable=True),
        sa.Column('price_type', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_price_change_logs')
    )
    op.create_index(op.f('ix_price_change_logs_asin'), 'price_change_logs', ['asin'], unique=False)
    op.create_index(op.f('ix_price_change_logs_id'), 'price_change_logs', ['id'], unique=False)
    op.create_index(op.f('ix_price_change_logs_seller_id'), 'price_change_logs', ['seller_id'], unique=False)
    op.create_index(op.f('ix_price_change_logs_sku'), 'price_change_logs', ['sku'], unique=False)
    op.create_index(op.f('ix_price_change_logs_timestamp'), 'price_change_logs', ['timestamp'], unique=False)

    # Create repricing_strategies table
    op.create_table('repricing_strategies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.String(length=255), nullable=False),
        sa.Column('asin', sa.String(length=255), nullable=True),
        sa.Column('strategy_type', sa.String(length=50), nullable=False),
        sa.Column('compete_with', sa.String(length=50), nullable=True),
        sa.Column('beat_by', sa.Float(), nullable=True),
        sa.Column('markup_percentage', sa.Float(), nullable=True),
        sa.Column('min_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('max_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('conditions', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_repricing_strategies')
    )
    op.create_index(op.f('ix_repricing_strategies_asin'), 'repricing_strategies', ['asin'], unique=False)
    op.create_index(op.f('ix_repricing_strategies_id'), 'repricing_strategies', ['id'], unique=False)
    op.create_index(op.f('ix_repricing_strategies_seller_id'), 'repricing_strategies', ['seller_id'], unique=False)

    # Create product_listings table
    op.create_table('product_listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asin', sa.String(length=255), nullable=False),
        sa.Column('sku', sa.String(length=255), nullable=True),
        sa.Column('seller_id', sa.String(length=255), nullable=False),
        sa.Column('marketplace_type', sa.String(length=10), nullable=False),
        sa.Column('listed_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('min_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('max_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('default_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('product_name', sa.String(length=500), nullable=True),
        sa.Column('item_condition', sa.String(length=20), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('inventory_age', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('repricer_enabled', sa.Boolean(), nullable=True),
        sa.Column('strategy_id', sa.Integer(), nullable=True),
        sa.Column('compete_with', sa.String(length=50), nullable=True),
        sa.Column('is_b2b', sa.Boolean(), nullable=True),
        sa.Column('business_pricing', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_price_update', sa.DateTime(), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('data_freshness', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_product_listings')
    )
    op.create_index(op.f('ix_product_listings_asin'), 'product_listings', ['asin'], unique=False)
    op.create_index(op.f('ix_product_listings_data_freshness'), 'product_listings', ['data_freshness'], unique=False)
    op.create_index(op.f('ix_product_listings_id'), 'product_listings', ['id'], unique=False)
    op.create_index(op.f('ix_product_listings_marketplace_type'), 'product_listings', ['marketplace_type'], unique=False)
    op.create_index(op.f('ix_product_listings_seller_id'), 'product_listings', ['seller_id'], unique=False)
    op.create_index(op.f('ix_product_listings_sku'), 'product_listings', ['sku'], unique=False)

    # Create competitor_data table
    op.create_table('competitor_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asin', sa.String(length=255), nullable=False),
        sa.Column('marketplace_type', sa.String(length=10), nullable=False),
        sa.Column('competitor_seller_id', sa.String(length=255), nullable=True),
        sa.Column('competitor_price', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('shipping_cost', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('total_price', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('condition', sa.String(length=20), nullable=True),
        sa.Column('fulfillment_type', sa.String(length=20), nullable=True),
        sa.Column('is_buybox_winner', sa.Boolean(), nullable=True),
        sa.Column('is_prime', sa.Boolean(), nullable=True),
        sa.Column('is_b2b_offer', sa.Boolean(), nullable=True),
        sa.Column('quantity_tier', sa.Integer(), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_competitor_data')
    )
    op.create_index(op.f('ix_competitor_data_asin'), 'competitor_data', ['asin'], unique=False)
    op.create_index(op.f('ix_competitor_data_id'), 'competitor_data', ['id'], unique=False)
    op.create_index(op.f('ix_competitor_data_last_updated'), 'competitor_data', ['last_updated'], unique=False)

    # Create listing_alerts table
    op.create_table('listing_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asin', sa.String(length=255), nullable=False),
        sa.Column('seller_id', sa.String(length=255), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('current_value', sa.String(length=100), nullable=True),
        sa.Column('expected_value', sa.String(length=100), nullable=True),
        sa.Column('context_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('notification_sent', sa.Boolean(), nullable=True),
        sa.Column('notification_channels', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_listing_alerts')
    )
    op.create_index(op.f('ix_listing_alerts_asin'), 'listing_alerts', ['asin'], unique=False)
    op.create_index(op.f('ix_listing_alerts_id'), 'listing_alerts', ['id'], unique=False)
    op.create_index(op.f('ix_listing_alerts_seller_id'), 'listing_alerts', ['seller_id'], unique=False)


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('listing_alerts')
    op.drop_table('competitor_data')
    op.drop_table('product_listings')
    op.drop_table('repricing_strategies')
    op.drop_table('price_change_logs')
    op.drop_table('products')
    op.drop_table('feeds')
    op.drop_table('user_accounts')
    op.drop_table('price_resets')