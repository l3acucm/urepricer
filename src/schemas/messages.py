"""Message schemas for Amazon SQS and Walmart webhook notifications."""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


class AmazonOfferChange(BaseModel):
    """Amazon ANY_OFFER_CHANGED notification payload."""
    asin: str = Field(..., description="Amazon Standard Identification Number")
    marketplace_id: str = Field(..., description="Amazon marketplace identifier") 
    seller_id: str = Field(..., description="Amazon seller identifier")
    item_condition: str = Field(default="NEW", description="Product condition")
    time_of_offer_change: datetime = Field(..., description="When the offer changed")
    
    # Offer data from SP-API response
    offers: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of offers from SP-API")
    summary: Optional[Dict[str, Any]] = Field(default=None, description="Summary data from SP-API")


class AmazonSQSMessage(BaseModel):
    """Complete Amazon SQS message structure."""
    type: str = Field(..., description="Message type (usually 'Notification')")
    message_id: str = Field(..., description="SQS message ID")
    timestamp: datetime = Field(..., description="Message timestamp")
    
    # Parsed notification content
    notification_type: str = Field(..., description="Amazon notification type")
    payload_version: str = Field(default="1.0", description="Payload version")
    event_time: datetime = Field(..., description="Event timestamp")
    
    # The actual offer change data
    offer_change: AmazonOfferChange = Field(..., description="Offer change details")


class WalmartOfferChange(BaseModel):
    """Walmart buy box changed webhook payload."""
    item_id: str = Field(..., description="Walmart item identifier")
    seller_id: str = Field(..., description="Walmart seller identifier")
    marketplace: str = Field(default="US", description="Walmart marketplace")
    event_time: datetime = Field(..., description="When the event occurred")
    
    # Current buybox information
    current_buybox_price: Optional[float] = Field(None, description="Current buybox price")
    current_buybox_winner: Optional[str] = Field(None, description="Current buybox winner")
    
    # Additional offer data
    offers: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of competing offers")


class WalmartWebhookMessage(BaseModel):
    """Complete Walmart webhook message structure."""
    event_type: str = Field(..., description="Event type (e.g., 'buybox_changed')")
    webhook_id: str = Field(..., description="Webhook identifier")
    timestamp: datetime = Field(..., description="Webhook timestamp")
    
    # The actual offer change data
    offer_change: WalmartOfferChange = Field(..., description="Offer change details")


class ProcessedOfferData(BaseModel):
    """Cleaned and normalized offer data for processing pipeline."""
    
    # Normalized identifiers
    product_id: str = Field(..., description="ASIN for Amazon, item_id for Walmart")
    seller_id: str = Field(..., description="Seller identifier")
    marketplace: str = Field(..., description="Marketplace (US, UK, etc.)")
    platform: str = Field(..., description="Platform (AMAZON, WALMART)")
    
    # Timing information
    event_time: datetime = Field(..., description="When the price change occurred")
    processed_time: datetime = Field(default_factory=datetime.utcnow, description="When we processed it")
    
    # Product condition and type
    item_condition: str = Field(default="NEW", description="Product condition")
    
    # Competition data
    competitor_price: Optional[float] = Field(None, description="Best competitor price")
    buybox_winner: Optional[str] = Field(None, description="Current buybox winner")
    total_offers: Optional[int] = Field(None, description="Total number of offers")
    
    # Raw data for detailed analysis if needed
    raw_offers: Optional[List[Dict[str, Any]]] = Field(None, description="Raw offer data")
    raw_summary: Optional[Dict[str, Any]] = Field(None, description="Raw summary data")


class RepricingDecision(BaseModel):
    """Decision result about whether to reprice a product."""
    
    should_reprice: bool = Field(..., description="Whether repricing is needed")
    reason: str = Field(..., description="Reason for the decision")
    
    # Product identification
    asin: str = Field(..., description="Product ASIN")
    sku: str = Field(..., description="Product SKU") 
    seller_id: str = Field(..., description="Seller ID")
    
    # Current state
    current_price: Optional[float] = Field(None, description="Current listed price")
    stock_quantity: Optional[int] = Field(None, description="Available stock")
    
    # Strategy information
    strategy_id: str = Field(..., description="Strategy to apply")
    
    # Competition data
    competitor_data: ProcessedOfferData = Field(..., description="Processed competition data")


class CalculatedPrice(BaseModel):
    """Result of price calculation for a product."""
    
    # Product identification
    asin: str = Field(..., description="Product ASIN")
    sku: str = Field(..., description="Product SKU")
    seller_id: str = Field(..., description="Seller ID")
    
    # Pricing information
    old_price: float = Field(..., description="Previous price")
    new_price: float = Field(..., description="Calculated new price")
    price_changed: bool = Field(..., description="Whether price actually changed")
    
    # Strategy information
    strategy_used: str = Field(..., description="Strategy that was applied")
    strategy_id: str = Field(..., description="Strategy ID")
    
    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow, description="Calculation timestamp")
    competitor_price: Optional[float] = Field(None, description="Competitor price used")
    
    # B2B tier pricing (if applicable)
    tier_prices: Optional[Dict[str, float]] = Field(None, description="B2B tier pricing")
    
    # Processing info for logging
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")