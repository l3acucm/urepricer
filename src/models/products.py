"""
Redis OM models for product data.
Replaces SQLAlchemy models with Redis-based JsonModel architecture.
"""
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, UTC

from redis_om import JsonModel, EmbeddedJsonModel, Field
from pydantic import field_validator

from src.core.config import get_settings

# Configure Redis connection for tests
if get_settings().testing:
    import fakeredis
    import redis_om
    redis_om.get_redis_connection = lambda *args, **kwargs: fakeredis.FakeStrictRedis(decode_responses=True)


class B2BTier(EmbeddedJsonModel):
    """B2B pricing tier embedded model."""
    
    # Pricing fields
    competitor_price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    default_price: Optional[Decimal] = None
    
    # Strategy results
    updated_price: Optional[Decimal] = None
    strategy: Optional[str] = None
    strategy_id: Optional[str] = None
    message: str = ""
    
    @field_validator('max_price')
    @classmethod
    def validate_tier_price_bounds(cls, v, info):
        """Validate tier max_price >= min_price."""
        if hasattr(info, 'data') and info.data:
            min_price = info.data.get('min_price')
            if v is not None and min_price is not None and v < min_price:
                raise ValueError(f'Tier max_price ({v}) cannot be less than min_price ({min_price})')
        return v
    
    @field_validator('min_price', 'max_price', 'competitor_price', 'default_price', 'updated_price')
    @classmethod
    def validate_non_negative_prices(cls, v):
        """Validate all prices are non-negative."""
        if v is not None and v < 0:
            raise ValueError(f'Price must be non-negative, got {v}')
        return v


class ProductListing(JsonModel):
    """
    Product listing with pricing and strategy information.
    Uses Redis OM JsonModel for complex nested data and rich querying.
    """
    
    # Product identification - indexed for fast lookups
    asin: str = Field(index=True, description="Amazon Standard Identification Number")
    seller_id: str = Field(index=True, description="Amazon seller ID") 
    marketplace_type: str = Field(index=True, default="US", description="Marketplace (US, UK, CA, AU)")
    sku: Optional[str] = Field(index=True, default=None, description="Stock Keeping Unit")
    
    # Pricing information
    listed_price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    default_price: Optional[Decimal] = None
    competitor_price: Optional[Decimal] = None
    
    # Product details
    product_name: Optional[str] = None
    item_condition: str = "New"
    quantity: int = 0
    inventory_age: int = 0
    status: str = "Active"
    
    # Repricing settings
    repricer_enabled: bool = True
    strategy_id: Optional[str] = None
    compete_with: str = "LOWEST_PRICE"
    
    # Strategy results
    updated_price: Optional[Decimal] = None
    message: str = ""
    
    # Strategy mock for backward compatibility with tests
    strategy: Optional[Any] = None
    
    # Account mock for backward compatibility
    account: Optional[Any] = None
    
    # B2B pricing
    is_b2b: bool = False
    tiers: Dict[str, B2BTier] = {}
    
    # Timestamps
    last_price_update: Optional[datetime] = None
    last_seen: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_freshness: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    @field_validator('max_price')
    @classmethod
    def validate_price_bounds(cls, v, info):
        """Validate max_price >= min_price."""
        if hasattr(info, 'data') and info.data:
            min_price = info.data.get('min_price')
            if v is not None and min_price is not None and v < min_price:
                raise ValueError(f'max_price ({v}) cannot be less than min_price ({min_price})')
        return v
    
    @field_validator('min_price', 'max_price', 'listed_price', 'default_price', 'competitor_price', 'updated_price')
    @classmethod
    def validate_non_negative_prices(cls, v):
        """Validate all prices are non-negative."""
        if v is not None and v < 0:
            raise ValueError(f'Price must be non-negative, got {v}')
        return v
    
    @field_validator('listed_price')
    @classmethod
    def validate_listed_price_in_bounds(cls, v, info):
        """Validate listed_price is within min/max bounds."""
        if v is None:
            return v
            
        if hasattr(info, 'data') and info.data:
            min_price = info.data.get('min_price')
            max_price = info.data.get('max_price')
            
            if min_price is not None and v < min_price:
                raise ValueError(f'listed_price ({v}) is below min_price ({min_price})')
                
            if max_price is not None and v > max_price:
                raise ValueError(f'listed_price ({v}) is above max_price ({max_price})')
        
        return v
    
    @field_validator('default_price')
    @classmethod
    def validate_default_price_in_bounds(cls, v, info):
        """Validate default_price is within min/max bounds."""
        if v is None:
            return v
            
        if hasattr(info, 'data') and info.data:
            min_price = info.data.get('min_price')
            max_price = info.data.get('max_price')
            
            if min_price is not None and v < min_price:
                raise ValueError(f'default_price ({v}) is below min_price ({min_price})')
                
            if max_price is not None and v > max_price:
                raise ValueError(f'default_price ({v}) is above max_price ({max_price})')
        
        return v
    
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
    
    def validate_comprehensive_price_bounds(self) -> bool:
        """
        Comprehensive validation of all price bounds.
        
        Returns:
            bool: True if all price bounds are valid
            
        Raises:
            ValueError: If any price bounds are invalid with detailed message
        """
        errors = []
        
        # Check min <= max constraint
        if (self.min_price is not None and self.max_price is not None and 
            self.min_price > self.max_price):
            errors.append(f"min_price ({self.min_price}) cannot be greater than max_price ({self.max_price})")
        
        # Check if listed_price is within bounds
        if self.listed_price is not None:
            if self.min_price is not None and self.listed_price < self.min_price:
                errors.append(f"listed_price ({self.listed_price}) is below min_price ({self.min_price})")
                
            if self.max_price is not None and self.listed_price > self.max_price:
                errors.append(f"listed_price ({self.listed_price}) is above max_price ({self.max_price})")
        
        # Check if default_price is within bounds  
        if self.default_price is not None:
            if self.min_price is not None and self.default_price < self.min_price:
                errors.append(f"default_price ({self.default_price}) is below min_price ({self.min_price})")
                
            if self.max_price is not None and self.default_price > self.max_price:
                errors.append(f"default_price ({self.default_price}) is above max_price ({self.max_price})")
        
        if errors:
            raise ValueError("Price validation failed: " + "; ".join(errors))
        
        return True
    
    class Meta:
        global_key_prefix = "product"


# Custom exception for price validation errors
class PriceValidationError(ValueError):
    """Custom exception for price validation errors."""
    
    def __init__(self, message: str, asin: str = None, seller_id: str = None, 
                 min_price: float = None, max_price: float = None):
        super().__init__(message)
        self.asin = asin
        self.seller_id = seller_id
        self.min_price = min_price
        self.max_price = max_price
        
    def to_dict(self):
        """Convert exception to dictionary for logging/API responses."""
        return {
            "error": "price_validation_error",
            "message": str(self),
            "asin": self.asin,
            "seller_id": self.seller_id,
            "min_price": self.min_price,
            "max_price": self.max_price
        }