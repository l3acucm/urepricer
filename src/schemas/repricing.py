"""
Pydantic schemas for repricing-related API operations.
Handles repricing calculations, strategies, and price optimization.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# Competitor data schemas
class CompetitorOffer(BaseModel):
    """Schema for competitor offer data."""
    seller_id: Optional[str] = Field(None, description="Competitor seller ID")
    price: Decimal = Field(..., ge=0, decimal_places=2, description="Competitor price")
    shipping_cost: Decimal = Field(default=Decimal('0.00'), ge=0, decimal_places=2, description="Shipping cost")
    condition: str = Field(default="New", description="Item condition")
    fulfillment_type: Optional[str] = Field(None, description="FBA/FBM fulfillment")
    is_buybox_winner: bool = Field(default=False, description="Current buybox winner")
    is_prime: bool = Field(default=False, description="Prime eligible")
    is_b2b_offer: bool = Field(default=False, description="Business offer")
    quantity_tier: Optional[int] = Field(None, description="B2B quantity tier")
    
    @validator('condition')
    def validate_condition(cls, v):
        allowed_conditions = ['New', 'Used', 'Collectible', 'Refurbished']
        if v not in allowed_conditions:
            raise ValueError(f'Condition must be one of: {allowed_conditions}')
        return v
    
    @validator('fulfillment_type')
    def validate_fulfillment(cls, v):
        if v is not None:
            allowed_types = ['FBA', 'FBM']
            if v not in allowed_types:
                raise ValueError(f'Fulfillment type must be one of: {allowed_types}')
        return v


class PriceCalculationRequest(BaseModel):
    """Schema for price calculation request."""
    asin: str = Field(..., description="Amazon Standard Identification Number")
    seller_id: str = Field(..., description="Amazon seller ID")
    marketplace_type: str = Field(..., description="Marketplace (US, UK, CA, AU)")
    
    # Current product data
    current_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Current listed price")
    min_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Minimum allowed price")
    max_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Maximum allowed price")
    
    # Competitor data
    competitors: List[CompetitorOffer] = Field(default=[], description="Competitor offers")
    
    # Strategy override
    strategy_override: Optional[str] = Field(None, description="Override default strategy")
    
    # Force calculation even if price is current
    force_calculation: bool = Field(default=False, description="Force recalculation")
    
    @validator('marketplace_type')
    def validate_marketplace(cls, v):
        allowed_marketplaces = ['US', 'UK', 'CA', 'AU']
        if v not in allowed_marketplaces:
            raise ValueError(f'Marketplace must be one of: {allowed_marketplaces}')
        return v
    
    @validator('strategy_override')
    def validate_strategy(cls, v):
        if v is not None:
            allowed_strategies = ['CHASE_BUYBOX', 'MAXIMIZE_PROFIT', 'ONLY_SELLER']
            if v not in allowed_strategies:
                raise ValueError(f'Strategy must be one of: {allowed_strategies}')
        return v


class PriceCalculationResult(BaseModel):
    """Schema for price calculation result."""
    asin: str
    seller_id: str
    
    # Price results
    recommended_price: Optional[Decimal] = Field(None, description="Calculated optimal price")
    current_price: Optional[Decimal] = Field(None, description="Current listed price")
    price_change: Optional[Decimal] = Field(None, description="Price difference (positive = increase)")
    price_change_percentage: Optional[float] = Field(None, description="Percentage change")
    
    # Strategy information
    strategy_used: str = Field(description="Strategy used for calculation")
    compete_with_type: str = Field(description="Competition type used")
    
    # Competitor analysis
    lowest_competitor_price: Optional[Decimal] = Field(None, description="Lowest competitor price found")
    buybox_price: Optional[Decimal] = Field(None, description="Current buybox price")
    total_competitors: int = Field(default=0, description="Total number of competitors")
    fba_competitors: int = Field(default=0, description="Number of FBA competitors")
    
    # Decision factors
    decision_factors: List[str] = Field(default=[], description="Factors influencing the price decision")
    warnings: List[str] = Field(default=[], description="Warnings about the pricing decision")
    
    # Metadata
    calculation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    should_update: bool = Field(description="Whether price should be updated")
    
    class Config:
        from_attributes = True


class BulkPriceCalculationRequest(BaseModel):
    """Schema for bulk price calculation request."""
    seller_id: str = Field(..., description="Amazon seller ID")
    marketplace_type: str = Field(..., description="Marketplace")
    asins: List[str] = Field(..., min_items=1, max_items=1000, description="List of ASINs to calculate")
    force_calculation: bool = Field(default=False, description="Force recalculation for all ASINs")
    
    @validator('marketplace_type')
    def validate_marketplace(cls, v):
        allowed_marketplaces = ['US', 'UK', 'CA', 'AU']
        if v not in allowed_marketplaces:
            raise ValueError(f'Marketplace must be one of: {allowed_marketplaces}')
        return v


class BulkPriceCalculationResponse(BaseModel):
    """Schema for bulk price calculation response."""
    total_requested: int
    total_calculated: int
    total_errors: int
    results: List[PriceCalculationResult] = []
    errors: List[Dict[str, str]] = []  # {"asin": "error_message"}
    processing_time_seconds: float


# Strategy testing schemas
class StrategyTestRequest(BaseModel):
    """Schema for testing repricing strategies."""
    seller_id: str = Field(..., description="Amazon seller ID")
    strategy_config: Dict[str, Any] = Field(..., description="Strategy configuration to test")
    test_scenarios: List[Dict[str, Any]] = Field(..., description="Test scenarios with competitor data")


class StrategyTestResult(BaseModel):
    """Schema for strategy test results."""
    scenario_id: int
    scenario_description: str
    input_data: Dict[str, Any]
    calculated_price: Optional[Decimal]
    strategy_decision: str
    decision_factors: List[str]
    warnings: List[str]


class StrategyTestResponse(BaseModel):
    """Schema for strategy test response."""
    strategy_config: Dict[str, Any]
    test_results: List[StrategyTestResult]
    summary: Dict[str, Any]  # Statistics about test results


# Price monitoring schemas
class PriceAlert(BaseModel):
    """Schema for price alerts."""
    asin: str
    seller_id: str
    alert_type: str = Field(description="Type of alert (PRICE_OUT_OF_RANGE, COMPETITOR_CHANGE, etc.)")
    current_price: Optional[Decimal] = None
    competitor_price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    message: str
    severity: str = Field(default="WARNING", description="Alert severity (INFO, WARNING, ERROR, CRITICAL)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PriceMonitoringReport(BaseModel):
    """Schema for price monitoring reports."""
    seller_id: str
    marketplace_type: str
    report_period_start: datetime
    report_period_end: datetime
    
    # Summary statistics
    total_products_monitored: int
    price_changes_made: int
    price_alerts_generated: int
    avg_price_change: Optional[Decimal] = None
    
    # Recent activities
    recent_price_changes: List[PriceCalculationResult] = []
    recent_alerts: List[PriceAlert] = []
    
    # Performance metrics
    strategy_performance: Dict[str, Dict[str, Any]] = Field(default={}, description="Performance by strategy type")


# Marketplace analysis schemas  
class MarketplaceAnalysis(BaseModel):
    """Schema for marketplace analysis data."""
    asin: str
    marketplace_type: str
    
    # Competition analysis
    total_offers: int
    fba_offers: int
    fbm_offers: int
    prime_offers: int
    
    # Price analysis
    lowest_price: Optional[Decimal] = None
    highest_price: Optional[Decimal] = None
    avg_price: Optional[Decimal] = None
    median_price: Optional[Decimal] = None
    price_range: Optional[Decimal] = None
    
    # Buybox analysis
    buybox_winner_price: Optional[Decimal] = None
    buybox_winner_fulfillment: Optional[str] = None
    buybox_win_probability: Optional[float] = Field(None, description="Estimated probability of winning buybox")
    
    # Market positioning
    our_price_rank: Optional[int] = Field(None, description="Our price rank among competitors (1 = lowest)")
    price_competitiveness: Optional[str] = Field(None, description="How competitive our price is (HIGH, MEDIUM, LOW)")
    
    # Recommendations
    recommended_actions: List[str] = Field(default=[], description="Recommended actions based on analysis")
    
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


class MarketplaceAnalysisRequest(BaseModel):
    """Schema for requesting marketplace analysis."""
    asin: str = Field(..., description="ASIN to analyze")
    seller_id: str = Field(..., description="Amazon seller ID")
    marketplace_type: str = Field(..., description="Marketplace to analyze")
    include_historical: bool = Field(default=False, description="Include historical data in analysis")
    
    @validator('marketplace_type')
    def validate_marketplace(cls, v):
        allowed_marketplaces = ['US', 'UK', 'CA', 'AU']
        if v not in allowed_marketplaces:
            raise ValueError(f'Marketplace must be one of: {allowed_marketplaces}')
        return v