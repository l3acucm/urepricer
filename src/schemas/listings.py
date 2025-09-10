"""
Pydantic schemas for listing-related API operations.
Handles product listings, inventory data, and alerts.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# Product listing schemas
class ProductListingBase(BaseModel):
    """Base schema for product listings."""
    asin: str = Field(..., max_length=255, description="Amazon Standard Identification Number")
    sku: Optional[str] = Field(None, max_length=255, description="Stock Keeping Unit")
    seller_id: str = Field(..., max_length=255, description="Amazon seller ID")
    marketplace_type: str = Field(..., max_length=10, description="Marketplace (US, UK, CA, AU)")
    
    # Pricing information
    listed_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Current listed price")
    min_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Minimum allowed price")
    max_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Maximum allowed price")
    default_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Default price to reset to")
    
    # Product details
    product_name: Optional[str] = Field(None, max_length=500, description="Product title")
    item_condition: str = Field(default="New", max_length=20, description="Product condition")
    quantity: int = Field(default=0, ge=0, description="Available quantity")
    status: str = Field(default="Active", max_length=20, description="Listing status")
    
    # Repricing settings
    repricer_enabled: bool = Field(default=True, description="Repricing enabled for this product")
    strategy_id: Optional[int] = Field(None, description="Custom strategy ID")
    compete_with: str = Field(default="LOWEST_PRICE", description="Competition strategy")
    
    @validator('marketplace_type')
    def validate_marketplace(cls, v):
        allowed_marketplaces = ['US', 'UK', 'CA', 'AU']
        if v not in allowed_marketplaces:
            raise ValueError(f'Marketplace must be one of: {allowed_marketplaces}')
        return v
    
    @validator('item_condition')
    def validate_condition(cls, v):
        allowed_conditions = ['New', 'Used', 'Collectible', 'Refurbished']
        if v not in allowed_conditions:
            raise ValueError(f'Item condition must be one of: {allowed_conditions}')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['Active', 'Inactive', 'Incomplete', 'Suppressed']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v
    
    @validator('compete_with')
    def validate_compete_with(cls, v):
        allowed_types = ['LOWEST_PRICE', 'LOWEST_FBA_PRICE', 'MATCH_BUYBOX']
        if v not in allowed_types:
            raise ValueError(f'Compete with must be one of: {allowed_types}')
        return v
    
    @validator('max_price')
    def validate_price_range(cls, v, values):
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v <= values['min_price']:
                raise ValueError('Max price must be greater than min price')
        return v


class ProductListingCreate(ProductListingBase):
    """Schema for creating product listing."""
    inventory_age: int = Field(default=0, ge=0, description="Days in inventory")
    is_b2b: bool = Field(default=False, description="Has business pricing")
    business_pricing: Optional[Dict[str, Any]] = Field(None, description="B2B pricing tiers")


class ProductListingUpdate(BaseModel):
    """Schema for updating product listing."""
    listed_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    min_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    max_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    default_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    product_name: Optional[str] = Field(None, max_length=500)
    item_condition: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None
    repricer_enabled: Optional[bool] = None
    strategy_id: Optional[int] = None
    compete_with: Optional[str] = None
    business_pricing: Optional[Dict[str, Any]] = None


class ProductListingResponse(ProductListingBase):
    """Schema for product listing response."""
    id: int
    inventory_age: int
    is_b2b: bool
    business_pricing: Optional[Dict[str, Any]] = None
    last_price_update: Optional[datetime] = None
    last_seen: datetime
    data_freshness: datetime
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    is_price_valid: bool = Field(description="Whether current price is within bounds")
    
    class Config:
        from_attributes = True


# Bulk operations schemas
class BulkListingUpdate(BaseModel):
    """Schema for bulk listing updates."""
    seller_id: str = Field(..., description="Amazon seller ID")
    marketplace_type: str = Field(..., description="Marketplace")
    updates: Dict[str, ProductListingUpdate] = Field(..., description="ASIN -> update data mapping")
    
    @validator('marketplace_type')
    def validate_marketplace(cls, v):
        allowed_marketplaces = ['US', 'UK', 'CA', 'AU']
        if v not in allowed_marketplaces:
            raise ValueError(f'Marketplace must be one of: {allowed_marketplaces}')
        return v


class BulkListingResponse(BaseModel):
    """Schema for bulk listing operation response."""
    total_requested: int
    total_updated: int
    total_errors: int
    updated_asins: List[str] = []
    errors: Dict[str, str] = Field(default={}, description="ASIN -> error message mapping")


# Listing filter and search schemas
class ListingFilter(BaseModel):
    """Schema for filtering product listings."""
    seller_id: Optional[str] = None
    marketplace_type: Optional[str] = None
    item_condition: Optional[str] = None
    status: Optional[str] = None
    repricer_enabled: Optional[bool] = None
    has_strategy: Optional[bool] = None
    price_min: Optional[Decimal] = Field(None, ge=0)
    price_max: Optional[Decimal] = Field(None, ge=0)
    quantity_min: Optional[int] = Field(None, ge=0)
    last_updated_days: Optional[int] = Field(None, ge=0, description="Products updated within N days")
    
    # Pagination
    limit: int = Field(default=50, le=1000, ge=1)
    offset: int = Field(default=0, ge=0)
    
    # Sorting
    sort_by: str = Field(default="updated_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order")
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        allowed_fields = ['asin', 'listed_price', 'quantity', 'updated_at', 'last_price_update', 'product_name']
        if v not in allowed_fields:
            raise ValueError(f'Sort by must be one of: {allowed_fields}')
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v


class ListingSearchResponse(BaseModel):
    """Schema for listing search response."""
    total: int
    listings: List[ProductListingResponse]
    filters: ListingFilter


# Competitor data schemas
class CompetitorDataBase(BaseModel):
    """Base schema for competitor data."""
    asin: str = Field(..., max_length=255, description="Amazon Standard Identification Number")
    marketplace_type: str = Field(..., max_length=10, description="Marketplace")
    competitor_seller_id: Optional[str] = Field(None, description="Competitor seller ID")
    competitor_price: Decimal = Field(..., ge=0, decimal_places=2, description="Competitor price")
    shipping_cost: Decimal = Field(default=Decimal('0.00'), ge=0, decimal_places=2, description="Shipping cost")
    condition: str = Field(default="New", description="Item condition")
    fulfillment_type: Optional[str] = Field(None, description="FBA/FBM fulfillment")
    is_buybox_winner: bool = Field(default=False, description="Current buybox winner")
    is_prime: bool = Field(default=False, description="Prime eligible")
    
    @validator('marketplace_type')
    def validate_marketplace(cls, v):
        allowed_marketplaces = ['US', 'UK', 'CA', 'AU']
        if v not in allowed_marketplaces:
            raise ValueError(f'Marketplace must be one of: {allowed_marketplaces}')
        return v
    
    @validator('condition')
    def validate_condition(cls, v):
        allowed_conditions = ['New', 'Used', 'Collectible', 'Refurbished']
        if v not in allowed_conditions:
            raise ValueError(f'Condition must be one of: {allowed_conditions}')
        return v


class CompetitorDataCreate(CompetitorDataBase):
    """Schema for creating competitor data."""
    is_b2b_offer: bool = Field(default=False, description="Business offer")
    quantity_tier: Optional[int] = Field(None, description="B2B quantity tier")
    data_source: str = Field(default="SP_API", description="Data source")


class CompetitorDataResponse(CompetitorDataBase):
    """Schema for competitor data response."""
    id: int
    total_price: Decimal = Field(description="Price + shipping")
    is_b2b_offer: bool
    quantity_tier: Optional[int] = None
    data_source: str
    last_updated: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Alert schemas
class ListingAlertBase(BaseModel):
    """Base schema for listing alerts."""
    asin: str = Field(..., max_length=255, description="Amazon Standard Identification Number")
    seller_id: str = Field(..., max_length=255, description="Amazon seller ID")
    alert_type: str = Field(..., max_length=50, description="Alert type")
    severity: str = Field(default="WARNING", max_length=20, description="Alert severity")
    title: str = Field(..., max_length=200, description="Alert title")
    message: Optional[str] = Field(None, description="Detailed alert message")
    
    @validator('alert_type')
    def validate_alert_type(cls, v):
        allowed_types = [
            'PRICE_OUT_OF_RANGE', 'INVENTORY_LOW', 'COMPETITOR_CHANGE', 
            'STRATEGY_ERROR', 'DATA_STALE', 'LISTING_INACTIVE'
        ]
        if v not in allowed_types:
            raise ValueError(f'Alert type must be one of: {allowed_types}')
        return v
    
    @validator('severity')
    def validate_severity(cls, v):
        allowed_severities = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v not in allowed_severities:
            raise ValueError(f'Severity must be one of: {allowed_severities}')
        return v


class ListingAlertCreate(ListingAlertBase):
    """Schema for creating listing alert."""
    current_value: Optional[str] = Field(None, max_length=100, description="Current problematic value")
    expected_value: Optional[str] = Field(None, max_length=100, description="Expected value")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ListingAlertUpdate(BaseModel):
    """Schema for updating listing alert."""
    resolved: bool = Field(description="Alert resolved status")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")


class ListingAlertResponse(ListingAlertBase):
    """Schema for listing alert response."""
    id: int
    current_value: Optional[str] = None
    expected_value: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    resolved: bool
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    notification_sent: bool
    notification_channels: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Data import/export schemas
class ListingImportRequest(BaseModel):
    """Schema for importing listing data."""
    seller_id: str = Field(..., description="Amazon seller ID")
    marketplace_type: str = Field(..., description="Marketplace")
    import_format: str = Field(..., description="Import format (CSV, JSON)")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing data")
    data: str = Field(..., description="Import data (CSV string or JSON)")
    
    @validator('import_format')
    def validate_import_format(cls, v):
        if v not in ['CSV', 'JSON']:
            raise ValueError('Import format must be CSV or JSON')
        return v


class ListingImportResponse(BaseModel):
    """Schema for listing import response."""
    total_rows: int
    imported_count: int
    updated_count: int
    error_count: int
    errors: List[Dict[str, str]] = Field(default=[], description="Import errors")


class ListingExportRequest(BaseModel):
    """Schema for exporting listing data."""
    seller_id: str = Field(..., description="Amazon seller ID")
    marketplace_type: str = Field(..., description="Marketplace")
    export_format: str = Field(..., description="Export format (CSV, JSON)")
    include_competitor_data: bool = Field(default=False, description="Include competitor data")
    filters: Optional[ListingFilter] = Field(None, description="Export filters")
    
    @validator('export_format')
    def validate_export_format(cls, v):
        if v not in ['CSV', 'JSON']:
            raise ValueError('Export format must be CSV or JSON')
        return v


# Analytics schemas
class ListingAnalytics(BaseModel):
    """Schema for listing analytics data."""
    seller_id: str
    marketplace_type: str
    analysis_period_start: datetime
    analysis_period_end: datetime
    
    # Summary statistics
    total_listings: int
    active_listings: int
    repricing_enabled_listings: int
    out_of_stock_listings: int
    price_violations: int
    
    # Price analytics
    avg_listing_price: Optional[Decimal] = None
    price_range_min: Optional[Decimal] = None
    price_range_max: Optional[Decimal] = None
    
    # Performance metrics
    listings_with_recent_updates: int
    stale_data_count: int
    competitor_data_coverage: float = Field(description="Percentage of listings with competitor data")
    
    # Trends
    price_trends: Dict[str, Any] = Field(default={}, description="Price trend analysis")
    volume_trends: Dict[str, Any] = Field(default={}, description="Volume/quantity trends")
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)