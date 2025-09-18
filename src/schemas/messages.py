"""Message schemas for Amazon SQS and Walmart webhook notifications."""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


# Simplified Amazon SP-API structures for repricing decisions
class OfferChangeTrigger(BaseModel):
    """Trigger information for the offer change."""
    marketplace_id: str = Field(..., description="Amazon marketplace identifier")
    asin: str = Field(..., description="Amazon Standard Identification Number")
    item_condition: str = Field(default="New", description="Product condition")
    time_of_offer_change: datetime = Field(..., description="When the offer changed")
    offer_change_type: str = Field(default="External", description="Type of offer change")

class LowestPrice(BaseModel):
    """Lowest price information."""
    condition: str = Field(..., description="Item condition")
    fulfillment_channel: str = Field(..., description="Fulfillment type (Amazon/Merchant)")
    listing_price: float = Field(..., description="Listing price amount")
    shipping: Optional[float] = Field(default=0.0, description="Shipping cost")
    landed_price: Optional[float] = Field(None, description="Total price including shipping")

class BuyBoxPrice(BaseModel):
    """Buy Box price information."""
    condition: str = Field(..., description="Item condition")
    listing_price: float = Field(..., description="Buy Box listing price")
    shipping: Optional[float] = Field(default=0.0, description="Shipping cost")
    landed_price: Optional[float] = Field(None, description="Total buy box price")

class NumberOfOffers(BaseModel):
    """Number of offers by condition and fulfillment."""
    condition: str = Field(..., description="Item condition")
    fulfillment_channel: str = Field(..., description="Fulfillment type")
    offer_count: int = Field(..., description="Number of offers")

class Summary(BaseModel):
    """Summary of competitive pricing data."""
    number_of_offers: Optional[List[NumberOfOffers]] = Field(default=None, description="Offer counts")
    lowest_prices: Optional[List[LowestPrice]] = Field(default=None, description="Lowest prices by condition")
    buy_box_prices: Optional[List[BuyBoxPrice]] = Field(default=None, description="Buy box prices")
    list_price: Optional[float] = Field(None, description="Manufacturer suggested retail price")

class Offer(BaseModel):
    """Individual offer details."""
    seller_id: str = Field(..., description="Seller identifier")
    sub_condition: str = Field(default="New", description="Sub-condition")
    listing_price: float = Field(..., description="Listing price amount")
    shipping: Optional[float] = Field(default=0.0, description="Shipping cost")
    landed_price: Optional[float] = Field(None, description="Total price including shipping")
    fulfillment_channel: str = Field(default="Merchant", description="Fulfillment type")
    is_buy_box_winner: Optional[bool] = Field(default=False, description="Is this offer the buy box winner")
    is_featured_merchant: Optional[bool] = Field(default=False, description="Is featured merchant")

class AmazonOfferChange(BaseModel):
    """Amazon ANY_OFFER_CHANGED notification payload with essential repricing fields."""
    # Core identification
    offer_change_trigger: OfferChangeTrigger = Field(..., description="Offer change trigger data")

    # Competitive pricing summary
    summary: Optional[Summary] = Field(default=None, description="Pricing summary data")

    # Top competing offers (simplified from official max 20)
    offers: Optional[List[Offer]] = Field(default=None, description="List of competing offers")



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


class CompetitorInfo(BaseModel):
    """Information about a specific competitor."""
    seller_id: str = Field(..., description="Competitor seller ID")
    price: float = Field(..., description="Competitor price")
    is_fba: Optional[bool] = Field(None, description="Whether fulfilled by Amazon")
    is_buybox_winner: Optional[bool] = Field(None, description="Whether this competitor has buybox")
    condition: Optional[str] = Field(None, description="Product condition")


class ComprehensiveCompetitionData(BaseModel):
    """Comprehensive competitive data for all strategy types."""

    # For LOWEST_PRICE strategy
    lowest_price_competitor: Optional[CompetitorInfo] = Field(None, description="Overall lowest price competitor")

    # For LOWEST_FBA_PRICE strategy
    lowest_fba_competitor: Optional[CompetitorInfo] = Field(None, description="Lowest FBA competitor")

    # For MATCH_BUYBOX strategy
    buybox_winner: Optional[CompetitorInfo] = Field(None, description="Current buybox winner")

    # Additional metadata
    total_offers: Optional[int] = Field(None, description="Total number of offers")
    all_competitors: List[CompetitorInfo] = Field(default_factory=list, description="All competitors")


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

    # Comprehensive competition data for all strategies
    competition_data: ComprehensiveCompetitionData = Field(default_factory=ComprehensiveCompetitionData, description="Strategy-aware competition data")

    # Primary competitor price field for repricing engine
    competitor_price: Optional[float] = Field(None, description="Primary competitor price for repricing decisions")

    # Legacy fields for backward compatibility (deprecated)
    lowest_price: Optional[float] = Field(None, description="Lowest competitor price (deprecated)")
    lowest_price_competitor: Optional[str] = Field(None, description="Lowest price competitor (deprecated)")
    buybox_winner: Optional[str] = Field(None, description="Current buybox winner (deprecated)")
    total_offers: Optional[int] = Field(None, description="Total number of offers (deprecated)")

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


    # Processing info for logging
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")