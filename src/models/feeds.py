"""
Feed-related SQLAlchemy models.
Handles Amazon feed submission tracking and product data.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship

from src.core.database import Base


class Feed(Base):
    """
    Amazon feed submission tracking.
    Records feed submission status and metadata.
    """
    __tablename__ = "feeds"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False, doc="Generated feed file name")
    feed_submission_id = Column(String(255), nullable=False, unique=True, index=True, doc="Amazon feed submission ID")
    seller_id = Column(String(255), nullable=False, index=True, doc="Amazon seller ID")
    status = Column(String(255), nullable=False, doc="Feed processing status")
    message = Column(String(255), nullable=True, doc="Status message from Amazon")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = relationship("Product", back_populates="feed", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Feed(id={self.id}, submission_id='{self.feed_submission_id}', status='{self.status}')>"


class Product(Base):
    """
    Product data for feed submissions.
    Tracks individual products within feeds and their pricing information.
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(255), nullable=False, index=True, doc="Amazon Standard Identification Number")
    sku = Column(String(255), nullable=True, index=True, doc="Stock Keeping Unit")
    seller_id = Column(String(255), nullable=False, index=True, doc="Amazon seller ID")
    
    # Pricing information
    old_price = Column(Float, nullable=True, doc="Previous price")
    new_price = Column(Float, nullable=True, doc="New calculated price")
    min_price = Column(Float, nullable=True, doc="Minimum allowed price")
    max_price = Column(Float, nullable=True, doc="Maximum allowed price")
    competitor_price = Column(Float, nullable=True, doc="Competitor price used for calculation")
    
    # Product details
    quantity = Column(Integer, default=1, doc="Product quantity")
    item_condition = Column(String(20), nullable=True, doc="Product condition (New, Used, etc.)")
    
    # B2B and pricing configuration
    is_b2b = Column(Boolean, default=False, doc="Business-to-business pricing")
    price_type = Column(String(255), nullable=True, doc="Type of pricing (standard, tier, etc.)")
    tier_identifier = Column(Integer, nullable=True, doc="B2B pricing tier identifier")
    
    # Strategy and processing
    strategy_id = Column(Integer, nullable=True, doc="Repricing strategy ID")
    repricer_type = Column(String(255), default="REPRICER", doc="Type of repricing logic")
    message = Column(String(200), nullable=True, doc="Processing message or error")
    
    # Foreign key to feed
    feed_id = Column(Integer, ForeignKey("feeds.id"), nullable=False)
    feed = relationship("Feed", back_populates="products")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Product(id={self.id}, asin='{self.asin}', sku='{self.sku}')>"


class PriceChangeLog(Base):
    """
    Historical log of price changes.
    Tracks all price updates for auditing and analysis.
    """
    __tablename__ = "price_change_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(255), nullable=False, index=True, doc="Amazon Standard Identification Number")
    sku = Column(String(255), nullable=True, index=True, doc="Stock Keeping Unit")
    seller_id = Column(String(255), nullable=False, index=True, doc="Amazon seller ID")
    
    # Pricing information (using DECIMAL for precision)
    old_price = Column(DECIMAL(10, 2), nullable=True, doc="Previous price")
    new_price = Column(DECIMAL(10, 2), nullable=True, doc="New price")
    min_price = Column(DECIMAL(10, 2), nullable=True, doc="Minimum allowed price")
    max_price = Column(DECIMAL(10, 2), nullable=True, doc="Maximum allowed price")
    competitor_price = Column(DECIMAL(10, 2), nullable=True, doc="Competitor price")
    
    # Product details
    quantity = Column(Integer, default=1, doc="Product quantity")
    
    # Processing information
    status = Column(String(255), nullable=True, doc="Processing status")
    message = Column(Text, nullable=True, doc="Processing message or error details")
    update_on_platform = Column(Boolean, default=False, doc="Whether price was updated on platform")
    
    # B2B information
    is_b2b = Column(Boolean, default=False, doc="Business-to-business pricing")
    price_type = Column(String(255), nullable=True, doc="Type of pricing")
    
    # Audit fields
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, doc="When the change occurred")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PriceChangeLog(id={self.id}, asin='{self.asin}', old_price={self.old_price}, new_price={self.new_price})>"


class RepricingStrategy(Base):
    """
    Repricing strategy configurations.
    Moved from Redis to PostgreSQL for better persistence and management.
    """
    __tablename__ = "repricing_strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(String(255), nullable=False, index=True, doc="Amazon seller ID")
    asin = Column(String(255), nullable=True, index=True, doc="ASIN-specific strategy (null for default)")
    
    # Strategy configuration
    strategy_type = Column(String(50), nullable=False, doc="Strategy type (CHASE_BUYBOX, MAXIMIZE_PROFIT, ONLY_SELLER)")
    compete_with = Column(String(50), default="LOWEST_PRICE", doc="Competition type (LOWEST_PRICE, LOWEST_FBA_PRICE, MATCH_BUYBOX)")
    beat_by = Column(Float, default=0.01, doc="Amount to beat competitor by")
    markup_percentage = Column(Float, nullable=True, doc="Markup percentage for ONLY_SELLER strategy")
    
    # Price boundaries
    min_price = Column(DECIMAL(10, 2), nullable=True, doc="Minimum price override")
    max_price = Column(DECIMAL(10, 2), nullable=True, doc="Maximum price override")
    
    # Strategy settings
    enabled = Column(Boolean, default=True, doc="Strategy enabled status")
    conditions = Column(String(20), default="New", doc="Product conditions to apply strategy")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<RepricingStrategy(id={self.id}, seller_id='{self.seller_id}', strategy_type='{self.strategy_type}')>"