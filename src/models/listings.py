"""
Listing-related SQLAlchemy models.
Handles product listings and inventory data.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, DECIMAL
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class ProductListing(Base):
    """
    Product listing information.
    Replaces Redis storage with persistent database storage for product data.
    """
    __tablename__ = "product_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(255), nullable=False, index=True, doc="Amazon Standard Identification Number")
    sku = Column(String(255), nullable=True, index=True, doc="Stock Keeping Unit")
    seller_id = Column(String(255), nullable=False, index=True, doc="Amazon seller ID")
    marketplace_type = Column(String(10), nullable=False, index=True, doc="Marketplace (US, UK, CA, AU)")
    
    # Pricing information
    listed_price = Column(DECIMAL(10, 2), nullable=True, doc="Current listed price")
    min_price = Column(DECIMAL(10, 2), nullable=True, doc="Minimum allowed price")
    max_price = Column(DECIMAL(10, 2), nullable=True, doc="Maximum allowed price")
    default_price = Column(DECIMAL(10, 2), nullable=True, doc="Default price to reset to")
    
    # Product details
    product_name = Column(String(500), nullable=True, doc="Product title")
    item_condition = Column(String(20), default="New", doc="Product condition")
    quantity = Column(Integer, default=0, doc="Available quantity")
    inventory_age = Column(Integer, default=0, doc="Days in inventory")
    status = Column(String(20), default="Active", doc="Listing status")
    
    # Repricing settings
    repricer_enabled = Column(Boolean, default=True, doc="Repricing enabled for this product")
    strategy_id = Column(Integer, nullable=True, doc="Custom strategy ID")
    compete_with = Column(String(50), default="LOWEST_PRICE", doc="Competition strategy")
    
    # B2B pricing (stored as JSON for flexibility)
    is_b2b = Column(Boolean, default=False, doc="Has business pricing")
    business_pricing = Column(JSONB, nullable=True, doc="B2B pricing tiers as JSON")
    
    # Timestamps and freshness
    last_price_update = Column(DateTime, nullable=True, doc="Last time price was updated")
    last_seen = Column(DateTime, default=datetime.utcnow, doc="Last time listing was processed")
    data_freshness = Column(DateTime, default=datetime.utcnow, index=True, doc="Data freshness timestamp")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite index for efficient lookups
    __table_args__ = (
        {"comment": "Product listings with pricing and strategy information"}
    )
    
    def __repr__(self):
        return f"<ProductListing(asin='{self.asin}', seller_id='{self.seller_id}', price={self.listed_price})>"
    
    @property
    def is_price_valid(self) -> bool:
        """Check if current price is within min/max bounds."""
        if not self.listed_price:
            return False
        
        if self.min_price and self.listed_price < self.min_price:
            return False
            
        if self.max_price and self.listed_price > self.max_price:
            return False
            
        return True
    
    def get_b2b_pricing_tiers(self) -> Dict[str, Any]:
        """Get B2B pricing tiers as dictionary."""
        if not self.business_pricing:
            return {}
        return self.business_pricing if isinstance(self.business_pricing, dict) else {}


class CompetitorData(Base):
    """
    Competitor pricing data for products.
    Tracks competitor offers and pricing information.
    """
    __tablename__ = "competitor_data"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(255), nullable=False, index=True, doc="Amazon Standard Identification Number")
    marketplace_type = Column(String(10), nullable=False, doc="Marketplace")
    
    # Competitor information
    competitor_seller_id = Column(String(255), nullable=True, doc="Competitor seller ID")
    competitor_price = Column(DECIMAL(10, 2), nullable=False, doc="Competitor price")
    shipping_cost = Column(DECIMAL(10, 2), default=0, doc="Shipping cost")
    total_price = Column(DECIMAL(10, 2), nullable=False, doc="Price + shipping")
    
    # Offer details
    condition = Column(String(20), default="New", doc="Item condition")
    fulfillment_type = Column(String(20), nullable=True, doc="FBA/FBM fulfillment")
    is_buybox_winner = Column(Boolean, default=False, doc="Current buybox winner")
    is_prime = Column(Boolean, default=False, doc="Prime eligible")
    
    # B2B information
    is_b2b_offer = Column(Boolean, default=False, doc="Business offer")
    quantity_tier = Column(Integer, nullable=True, doc="B2B quantity tier")
    
    # Data metadata
    data_source = Column(String(50), default="SP_API", doc="Data source (SP_API, SQS, etc.)")
    last_updated = Column(DateTime, default=datetime.utcnow, index=True, doc="When data was last updated")
    
    # Audit fields  
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<CompetitorData(asin='{self.asin}', price={self.competitor_price}, buybox={self.is_buybox_winner})>"


class ListingAlert(Base):
    """
    Alerts for listing issues.
    Tracks price violations, inventory issues, and other problems.
    """
    __tablename__ = "listing_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(255), nullable=False, index=True, doc="Amazon Standard Identification Number")
    seller_id = Column(String(255), nullable=False, index=True, doc="Amazon seller ID")
    
    # Alert information
    alert_type = Column(String(50), nullable=False, doc="Alert type (PRICE_OUT_OF_RANGE, INVENTORY_LOW, etc.)")
    severity = Column(String(20), default="WARNING", doc="Alert severity (INFO, WARNING, ERROR, CRITICAL)")
    title = Column(String(200), nullable=False, doc="Alert title")
    message = Column(Text, nullable=True, doc="Detailed alert message")
    
    # Context data
    current_value = Column(String(100), nullable=True, doc="Current problematic value")
    expected_value = Column(String(100), nullable=True, doc="Expected/correct value")
    context_data = Column(JSONB, nullable=True, doc="Additional context as JSON")
    
    # Resolution tracking
    resolved = Column(Boolean, default=False, doc="Alert resolved status")
    resolved_at = Column(DateTime, nullable=True, doc="When alert was resolved")
    resolution_notes = Column(Text, nullable=True, doc="Resolution notes")
    
    # Notification tracking
    notification_sent = Column(Boolean, default=False, doc="Notification sent status")
    notification_channels = Column(String(100), nullable=True, doc="Channels notified (slack, email, etc.)")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ListingAlert(id={self.id}, type='{self.alert_type}', severity='{self.severity}')>"