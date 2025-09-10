"""
Account-related SQLAlchemy models.
Consolidates user account and price reset functionality from Django models.
"""
from datetime import datetime, time
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, Text, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base


class PriceReset(Base):
    """
    Price reset configuration for user accounts.
    Handles scheduled price reset and resume functionality.
    """
    __tablename__ = "price_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    reset_time = Column(Time, nullable=False, doc="Time to reset prices")
    resume_time = Column(Time, nullable=False, doc="Time to resume normal pricing")
    enabled = Column(Boolean, default=False, doc="Whether price reset is active")
    reset_active = Column(Boolean, default=False, doc="Current reset state")
    product_condition = Column(String(100), nullable=False, doc="Product condition filter")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to user account
    user_account = relationship("UserAccount", back_populates="price_reset", uselist=False)
    
    def __repr__(self):
        return f"<PriceReset(id={self.id}, reset_time={self.reset_time}, enabled={self.enabled})>"


class UserAccount(Base):
    """
    User account model with Amazon marketplace integration.
    Consolidates authentication and notification settings.
    """
    __tablename__ = "user_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), unique=True, index=True, doc="Unique user identifier")
    seller_id = Column(String(100), nullable=False, index=True, doc="Amazon seller ID")
    marketplace_type = Column(String(100), nullable=False, doc="Amazon marketplace (US, UK, CA, AU)")
    
    # Account settings
    enabled = Column(Boolean, default=True, doc="Account enabled status")
    repricer_enabled = Column(Boolean, default=True, doc="Repricing functionality enabled")
    status = Column(String(100), default="ACTIVE", doc="Account status (ACTIVE, INACTIVE)")
    
    # Amazon SP-API credentials
    refresh_token = Column(Text, nullable=False, doc="Amazon SP-API refresh token")
    
    # Notification settings
    is_notifications_active = Column(Boolean, default=False, doc="Notifications enabled")
    anyoffer_changed_subscription_id = Column(String(100), default="", doc="ANY_OFFER_CHANGED subscription ID")
    feed_ready_notification_subscription_id = Column(String(100), default="", doc="FEED_PROCESSING_FINISHED subscription ID")
    anyoffer_changed_destination_id = Column(String(100), default="", doc="ANY_OFFER_CHANGED destination ID")
    feed_ready_destination_id = Column(String(100), default="", doc="FEED_PROCESSING_FINISHED destination ID")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    price_reset_id = Column(Integer, ForeignKey("price_resets.id"), nullable=True)
    price_reset = relationship("PriceReset", back_populates="user_account")
    
    # Indexes and constraints
    __table_args__ = (
        # Unique constraint on refresh_token and seller_id combination
        {"sqlite_autoincrement": True}
    )
    
    def __repr__(self):
        return f"<UserAccount(id={self.id}, seller_id='{self.seller_id}', marketplace='{self.marketplace_type}')>"
    
    @property
    def credentials(self) -> Dict[str, Any]:
        """Get credentials dictionary for Amazon SP-API."""
        from src.core.config import get_settings
        settings = get_settings()
        return {
            "refresh_token": self.refresh_token,
            "lwa_app_id": settings.amazon_client_id,
            "lwa_client_secret": settings.amazon_client_secret,
        }
    
    @property
    def marketplace_id(self) -> str:
        """Get marketplace ID for Amazon SP-API."""
        from src.core.config import get_settings
        settings = get_settings()
        return settings.marketplace_ids.get(self.marketplace_type, "")
    
    @property
    def timezone_str(self) -> str:
        """Get timezone string for this marketplace."""
        from src.core.config import get_settings
        settings = get_settings()
        return settings.marketplace_timezones.get(self.marketplace_type, "UTC")