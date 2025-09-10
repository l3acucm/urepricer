"""
Pydantic schemas for Arbitrage Hero API.
Provides request/response validation and serialization for all endpoints.
"""

# Import all schemas for easy access
from .accounts import (
    # Price Reset schemas
    PriceResetBase, PriceResetCreate, PriceResetUpdate, PriceResetResponse,
    
    # User Account schemas  
    UserAccountBase, UserAccountCreate, UserAccountUpdate, UserAccountResponse,
    
    # Authentication schemas
    Token, TokenData, LoginRequest, LoginResponse,
    
    # Notification schemas
    NotificationSubscriptionRequest, NotificationSubscriptionResponse,
    
    # Status and filtering schemas
    AccountStatusUpdate, AccountListFilter, AccountListResponse
)

from .feeds import (
    # Product schemas
    ProductBase, ProductCreate, ProductUpdate, ProductResponse,
    
    # Feed schemas
    FeedBase, FeedCreate, FeedUpdate, FeedResponse,
    FeedSubmissionRequest, FeedSubmissionResponse,
    
    # Price Change Log schemas
    PriceChangeLogBase, PriceChangeLogCreate, PriceChangeLogResponse,
    
    # Repricing Strategy schemas  
    RepricingStrategyBase, RepricingStrategyCreate, RepricingStrategyUpdate, RepricingStrategyResponse,
    
    # History and statistics
    FeedHistoryFilter, FeedHistoryResponse, FeedStatistics
)

from .repricing import (
    # Competitor and calculation schemas
    CompetitorOffer, PriceCalculationRequest, PriceCalculationResult,
    BulkPriceCalculationRequest, BulkPriceCalculationResponse,
    
    # Strategy testing schemas
    StrategyTestRequest, StrategyTestResult, StrategyTestResponse,
    
    # Monitoring schemas
    PriceAlert, PriceMonitoringReport,
    
    # Analysis schemas
    MarketplaceAnalysis, MarketplaceAnalysisRequest
)

from .listings import (
    # Product Listing schemas
    ProductListingBase, ProductListingCreate, ProductListingUpdate, ProductListingResponse,
    
    # Bulk operations
    BulkListingUpdate, BulkListingResponse,
    
    # Search and filtering
    ListingFilter, ListingSearchResponse,
    
    # Competitor data schemas
    CompetitorDataBase, CompetitorDataCreate, CompetitorDataResponse,
    
    # Alert schemas
    ListingAlertBase, ListingAlertCreate, ListingAlertUpdate, ListingAlertResponse,
    
    # Import/Export schemas
    ListingImportRequest, ListingImportResponse, ListingExportRequest,
    
    # Analytics schemas
    ListingAnalytics
)

# Export all schemas for easy importing
__all__ = [
    # Account schemas
    "PriceResetBase", "PriceResetCreate", "PriceResetUpdate", "PriceResetResponse",
    "UserAccountBase", "UserAccountCreate", "UserAccountUpdate", "UserAccountResponse", 
    "Token", "TokenData", "LoginRequest", "LoginResponse",
    "NotificationSubscriptionRequest", "NotificationSubscriptionResponse",
    "AccountStatusUpdate", "AccountListFilter", "AccountListResponse",
    
    # Feed schemas
    "ProductBase", "ProductCreate", "ProductUpdate", "ProductResponse",
    "FeedBase", "FeedCreate", "FeedUpdate", "FeedResponse",
    "FeedSubmissionRequest", "FeedSubmissionResponse",
    "PriceChangeLogBase", "PriceChangeLogCreate", "PriceChangeLogResponse",
    "RepricingStrategyBase", "RepricingStrategyCreate", "RepricingStrategyUpdate", "RepricingStrategyResponse",
    "FeedHistoryFilter", "FeedHistoryResponse", "FeedStatistics",
    
    # Repricing schemas
    "CompetitorOffer", "PriceCalculationRequest", "PriceCalculationResult",
    "BulkPriceCalculationRequest", "BulkPriceCalculationResponse",
    "StrategyTestRequest", "StrategyTestResult", "StrategyTestResponse",
    "PriceAlert", "PriceMonitoringReport",
    "MarketplaceAnalysis", "MarketplaceAnalysisRequest",
    
    # Listing schemas
    "ProductListingBase", "ProductListingCreate", "ProductListingUpdate", "ProductListingResponse",
    "BulkListingUpdate", "BulkListingResponse",
    "ListingFilter", "ListingSearchResponse", 
    "CompetitorDataBase", "CompetitorDataCreate", "CompetitorDataResponse",
    "ListingAlertBase", "ListingAlertCreate", "ListingAlertUpdate", "ListingAlertResponse",
    "ListingImportRequest", "ListingImportResponse", "ListingExportRequest",
    "ListingAnalytics"
]