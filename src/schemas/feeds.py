"""
Pydantic schemas for feed-related API operations.
Handles Amazon feed submission and product pricing data validation.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# Base schemas
class ProductBase(BaseModel):
    """Base schema for product data."""
    asin: str = Field(..., max_length=255, description="Amazon Standard Identification Number")
    sku: Optional[str] = Field(None, max_length=255, description="Stock Keeping Unit")
    seller_id: str = Field(..., max_length=255, description="Amazon seller ID")
    
    # Pricing information
    new_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="New calculated price")
    min_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Minimum allowed price")
    max_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Maximum allowed price")
    competitor_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Competitor price")
    
    # Product details
    quantity: int = Field(default=1, ge=0, description="Product quantity")
    item_condition: Optional[str] = Field(None, max_length=20, description="Product condition")
    
    @validator('item_condition')
    def validate_condition(cls, v):
        if v is not None:
            allowed_conditions = ['New', 'Used', 'Collectible', 'Refurbished']
            if v not in allowed_conditions:
                raise ValueError(f'Item condition must be one of: {allowed_conditions}')
        return v
    
    @validator('max_price')
    def validate_price_range(cls, v, values):
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v <= values['min_price']:
                raise ValueError('Max price must be greater than min price')
        return v


class ProductCreate(ProductBase):
    """Schema for creating product in feed."""
    old_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Previous price")
    is_b2b: bool = Field(default=False, description="Business-to-business pricing")
    price_type: Optional[str] = Field(None, description="Type of pricing")
    tier_identifier: Optional[int] = Field(None, description="B2B pricing tier identifier")
    strategy_id: Optional[int] = Field(None, description="Repricing strategy ID")
    repricer_type: str = Field(default="REPRICER", description="Type of repricing logic")


class ProductUpdate(BaseModel):
    """Schema for updating product in feed."""
    new_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    min_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2) 
    max_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    quantity: Optional[int] = Field(None, ge=0)
    message: Optional[str] = Field(None, max_length=200)


class ProductResponse(ProductBase):
    """Schema for product response."""
    id: int
    old_price: Optional[Decimal] = None
    is_b2b: bool
    price_type: Optional[str] = None
    tier_identifier: Optional[int] = None
    strategy_id: Optional[int] = None
    repricer_type: str
    message: Optional[str] = None
    feed_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Feed schemas
class FeedBase(BaseModel):
    """Base schema for feed data."""
    seller_id: str = Field(..., max_length=255, description="Amazon seller ID")


class FeedCreate(FeedBase):
    """Schema for creating feed."""
    products: List[ProductCreate] = Field(..., min_items=1, description="Products to include in feed")


class FeedUpdate(BaseModel):
    """Schema for updating feed status."""
    status: str = Field(..., description="Feed processing status")
    message: Optional[str] = Field(None, description="Status message from Amazon")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['SUBMITTED', 'IN_PROGRESS', 'DONE', 'CANCELLED', 'FATAL']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v


class FeedResponse(FeedBase):
    """Schema for feed response."""
    id: int
    file_name: str
    feed_submission_id: str
    status: str
    message: Optional[str] = None
    products: List[ProductResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FeedSubmissionRequest(BaseModel):
    """Schema for manual feed submission request."""
    seller_id: Optional[str] = Field(None, description="Specific seller ID (optional)")
    force_submit: bool = Field(default=False, description="Force submission even if no changes")


class FeedSubmissionResponse(BaseModel):
    """Schema for feed submission response."""
    success: bool
    message: str
    feeds_submitted: int
    feed_ids: List[int] = []


# Price change log schemas  
class PriceChangeLogBase(BaseModel):
    """Base schema for price change log."""
    asin: str = Field(..., max_length=255, description="Amazon Standard Identification Number")
    sku: Optional[str] = Field(None, max_length=255, description="Stock Keeping Unit")
    seller_id: str = Field(..., max_length=255, description="Amazon seller ID")
    
    old_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Previous price")
    new_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="New price")
    min_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Minimum allowed price")
    max_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Maximum allowed price")
    competitor_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Competitor price")
    
    quantity: int = Field(default=1, ge=0, description="Product quantity")
    status: Optional[str] = Field(None, description="Processing status")
    message: Optional[str] = Field(None, description="Processing message or error")


class PriceChangeLogCreate(PriceChangeLogBase):
    """Schema for creating price change log."""
    update_on_platform: bool = Field(default=False, description="Whether price was updated on platform")
    is_b2b: bool = Field(default=False, description="Business-to-business pricing")
    price_type: Optional[str] = Field(None, description="Type of pricing")


class PriceChangeLogResponse(PriceChangeLogBase):
    """Schema for price change log response."""
    id: int
    update_on_platform: bool
    is_b2b: bool
    price_type: Optional[str] = None
    timestamp: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Repricing strategy schemas
class RepricingStrategyBase(BaseModel):
    """Base schema for repricing strategy."""
    seller_id: str = Field(..., max_length=255, description="Amazon seller ID")
    asin: Optional[str] = Field(None, max_length=255, description="ASIN-specific strategy (null for default)")
    
    strategy_type: str = Field(..., description="Strategy type")
    compete_with: str = Field(default="LOWEST_PRICE", description="Competition type")
    beat_by: Decimal = Field(default=Decimal('0.01'), ge=0, decimal_places=2, description="Amount to beat competitor by")
    markup_percentage: Optional[Decimal] = Field(None, ge=0, description="Markup percentage for ONLY_SELLER strategy")
    
    min_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Minimum price override")
    max_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Maximum price override")
    
    enabled: bool = Field(default=True, description="Strategy enabled status")
    conditions: str = Field(default="New", description="Product conditions to apply strategy")
    
    @validator('strategy_type')
    def validate_strategy_type(cls, v):
        allowed_types = ['CHASE_BUYBOX', 'MAXIMIZE_PROFIT', 'ONLY_SELLER']
        if v not in allowed_types:
            raise ValueError(f'Strategy type must be one of: {allowed_types}')
        return v
    
    @validator('compete_with')
    def validate_compete_with(cls, v):
        allowed_types = ['LOWEST_PRICE', 'LOWEST_FBA_PRICE', 'MATCH_BUYBOX']
        if v not in allowed_types:
            raise ValueError(f'Compete with must be one of: {allowed_types}')
        return v
    
    @validator('conditions')
    def validate_conditions(cls, v):
        allowed_conditions = ['New', 'Used', 'Collectible', 'Refurbished', 'All']
        if v not in allowed_conditions:
            raise ValueError(f'Conditions must be one of: {allowed_conditions}')
        return v


class RepricingStrategyCreate(RepricingStrategyBase):
    """Schema for creating repricing strategy."""
    pass


class RepricingStrategyUpdate(BaseModel):
    """Schema for updating repricing strategy."""
    strategy_type: Optional[str] = None
    compete_with: Optional[str] = None
    beat_by: Optional[Decimal] = None
    markup_percentage: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    enabled: Optional[bool] = None
    conditions: Optional[str] = None


class RepricingStrategyResponse(RepricingStrategyBase):
    """Schema for repricing strategy response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Feed history and statistics schemas
class FeedHistoryFilter(BaseModel):
    """Schema for filtering feed history."""
    seller_id: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, le=1000, ge=1)
    offset: int = Field(default=0, ge=0)


class FeedHistoryResponse(BaseModel):
    """Schema for feed history response."""
    total: int
    feeds: List[FeedResponse]
    filters: FeedHistoryFilter


class FeedStatistics(BaseModel):
    """Schema for feed statistics."""
    total_feeds: int
    successful_feeds: int
    failed_feeds: int
    in_progress_feeds: int
    total_products_processed: int
    success_rate: float = Field(description="Success rate as percentage")
    avg_processing_time: Optional[float] = Field(None, description="Average processing time in minutes")