"""Unified Product model combining ProductBase and Product classes."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class Strategy(BaseModel):
    """Unified Strategy model."""
    compete_with: str = Field(default="MATCH_BUYBOX", description="Competition type")
    beat_by: Decimal = Field(default=Decimal('0.0'), ge=0, decimal_places=2, description="Amount to beat competitor by")
    min_price_rule: str = Field(default="JUMP_TO_MIN", description="Min price rule")
    max_price_rule: str = Field(default="JUMP_TO_MAX", description="Max price rule")
    
    @field_validator('compete_with')
    @classmethod
    def validate_compete_with(cls, v):
        allowed = ['LOWEST_PRICE', 'LOWEST_FBA_PRICE', 'MATCH_BUYBOX', 'FBA_LOWEST']
        if v not in allowed:
            raise ValueError(f'compete_with must be one of: {allowed}')
        return v
    
    @field_validator('min_price_rule', 'max_price_rule')
    @classmethod 
    def validate_price_rules(cls, v):
        allowed = ['JUMP_TO_MIN', 'JUMP_TO_MAX', 'DO_NOTHING', 'DEFAULT_PRICE']
        if v not in allowed:
            raise ValueError(f'price rule must be one of: {allowed}')
        return v


class Product(BaseModel):
    """Unified Product model for all repricing operations."""
    
    # Core identification
    asin: str = Field(..., max_length=255, description="Amazon Standard Identification Number")
    sku: Optional[str] = Field(None, max_length=255, description="Stock Keeping Unit") 
    seller_id: str = Field(..., max_length=255, description="Amazon seller ID")
    
    # Essential pricing (8 fields from simplified schema)
    listed_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Current listed price")
    min_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Minimum allowed price")
    max_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Maximum allowed price")
    default_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Default fallback price")
    
    # Product details
    status: str = Field(default="Active", description="Product status")
    item_condition: str = Field(default="New", description="Product condition")
    quantity: int = Field(default=0, ge=0, description="Product quantity")
    
    # Strategy configuration
    strategy_id: Optional[str] = Field(None, description="Strategy ID")
    strategy: Optional[Strategy] = Field(None, description="Strategy configuration")
    
    # Competition data (from ANY_OFFER_CHANGED)
    competitor_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Competitor price")
    no_of_offers: int = Field(default=0, ge=0, description="Number of competing offers")
    is_seller_buybox_winner: bool = Field(default=False, description="Is seller winning buybox")
    
    # Repricing results
    updated_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="New calculated price")
    message: str = Field(default="", description="Repricing message or reason")
    
    @field_validator('item_condition')
    @classmethod
    def validate_condition(cls, v):
        allowed_conditions = ['New', 'Used', 'Collectible', 'Refurbished']
        if v not in allowed_conditions:
            raise ValueError(f'Item condition must be one of: {allowed_conditions}')
        return v
    
    @field_validator('max_price')
    @classmethod
    def validate_price_range(cls, v, info):
        if v is not None and hasattr(info, 'data') and info.data and 'min_price' in info.data and info.data['min_price'] is not None:
            if v <= info.data['min_price']:
                raise ValueError('Max price must be greater than min price')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['Active', 'Inactive', 'Paused', 'Deleted']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v
    
    @classmethod
    def from_redis(cls, redis_data: Dict[str, Any]) -> 'Product':
        """Create Product from Redis data without validation for performance."""
        # Use model_construct to bypass validation for high-frequency operations
        return cls.model_construct(**redis_data)
    
    @classmethod
    def from_kwargs(cls, **kwargs) -> 'Product':
        """Create Product from kwargs (backward compatibility)."""
        # Handle legacy field mappings
        if 'min' in kwargs and 'min_price' not in kwargs:
            kwargs['min_price'] = kwargs.pop('min')
        if 'max' in kwargs and 'max_price' not in kwargs:
            kwargs['max_price'] = kwargs.pop('max')
        if 'inventory_quantity' in kwargs and 'quantity' not in kwargs:
            kwargs['quantity'] = kwargs.pop('inventory_quantity')
            
        return cls.model_construct(**kwargs)
    
    def to_redis_dict(self) -> Dict[str, Any]:
        """Convert to Redis-compatible dictionary (simplified schema)."""
        return {
            "listed_price": str(self.listed_price) if self.listed_price else None,
            "min_price": str(self.min_price) if self.min_price else None,
            "max_price": str(self.max_price) if self.max_price else None,
            "default_price": str(self.default_price) if self.default_price else None,
            "strategy_id": self.strategy_id,
            "status": self.status,
            "item_condition": self.item_condition,
            "quantity": self.quantity
        }
    
    def validate_price_bounds(self) -> bool:
        """Validate that listed price is within min/max bounds."""
        if self.listed_price is None:
            return True
            
        if self.min_price is not None and self.listed_price < self.min_price:
            return False
            
        if self.max_price is not None and self.listed_price > self.max_price:
            return False
            
        return True
    
    def is_in_price_bounds(self, price: Decimal) -> bool:
        """Check if a price is within the product's min/max bounds."""
        if self.min_price is not None and price < self.min_price:
            return False
            
        if self.max_price is not None and price > self.max_price:
            return False
            
        return True
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True
        arbitrary_types_allowed = True
        str_strip_whitespace = True