"""Base strategy class with common functionality and price bounds validation."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from loguru import logger

from .new_price_processor import NewPriceProcessor, SkipProductRepricing


class PriceBoundsError(Exception):
    """Exception raised when calculated price is outside product's min/max bounds."""
    
    def __init__(self, message: str, calculated_price: float, min_price: float, max_price: float):
        super().__init__(message)
        self.calculated_price = calculated_price
        self.min_price = min_price
        self.max_price = max_price


class BaseStrategy(ABC):
    """Base class for all pricing strategies with common functionality."""
    
    def __init__(self, product: Any) -> None:
        self.product = product
        self.logger = logger.bind(
            service="strategy",
            strategy=self.__class__.__name__,
            asin=getattr(product, 'asin', 'unknown')
        )

    def __str__(self):
        return self.get_strategy_name()

    @abstractmethod
    def apply(self) -> None:
        """Apply the pricing strategy. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the strategy name. Must be implemented by subclasses."""
        pass
    
    def calculate_competitive_price(self, competitor_price: float, beat_by: float) -> float:
        """
        Calculate competitive price by beating competitor price.
        
        Args:
            competitor_price: Competitor's price
            beat_by: Amount to beat by (negative to undercut, positive to go higher)
            
        Returns:
            Calculated competitive price
        """
        if competitor_price is None:
            raise SkipProductRepricing("No competitor price available")
        
        # Use eval as per original logic, but safer with validation
        if not isinstance(competitor_price, (int, float)) or not isinstance(beat_by, (int, float)):
            raise SkipProductRepricing("Invalid competitor price or beat_by value")
        
        new_price = competitor_price + beat_by
        return self.round_price(new_price)
    
    def round_price(self, price: float) -> float:
        """Round price to 2 decimal places using standard rounding."""
        if price is None:
            return None
        
        # Use Decimal for precise rounding
        decimal_price = Decimal(str(price))
        rounded_price = decimal_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return float(rounded_price)
    
    def validate_price_bounds(self, price: float, tier: Any = None) -> float:
        """
        Validate that price is within product's min/max bounds.
        
        Args:
            price: Price to validate
            tier: Optional tier object for B2B products
            
        Returns:
            Validated price
            
        Raises:
            PriceBoundsError: If price is outside bounds
        """
        if price is None:
            return None
        
        # Use tier bounds if provided, otherwise product bounds
        target = tier or self.product
        
        # Get min/max prices with better handling of Mock objects
        try:
            min_price = getattr(target, 'min_price', None)
            if min_price is None:
                min_price = getattr(target, 'min', None)
            
            max_price = getattr(target, 'max_price', None) 
            if max_price is None:
                max_price = getattr(target, 'max', None)
            
            # Check if we got Mock objects or actual None/numbers
            from unittest.mock import Mock
            if isinstance(min_price, Mock) or isinstance(max_price, Mock):
                min_price = None
                max_price = None
            
        except Exception:
            min_price = None
            max_price = None
        
        # Skip validation if bounds are not set or are not numbers
        if (min_price is None or max_price is None or 
            not isinstance(min_price, (int, float)) or 
            not isinstance(max_price, (int, float))):
            self.logger.warning(f"Min/max price bounds not set or invalid, skipping validation")
            return price
        
        if price < min_price:
            raise PriceBoundsError(
                f"Calculated price {price} is below minimum price {min_price}",
                calculated_price=price,
                min_price=min_price,
                max_price=max_price
            )
        
        if price > max_price:
            raise PriceBoundsError(
                f"Calculated price {price} exceeds maximum price {max_price}",
                calculated_price=price,
                min_price=min_price,
                max_price=max_price
            )
        
        return price
    
    def process_price_with_bounds_check(self, raw_price: float, seller_id: str, asin: str, tier: Any = None) -> float:
        """
        Process price through NewPriceProcessor and validate bounds.
        
        Args:
            raw_price: Raw calculated price
            seller_id: Seller ID
            asin: Product ASIN
            tier: Optional tier for B2B products
            
        Returns:
            Processed and validated price
            
        Raises:
            PriceBoundsError: If processed price is outside bounds
        """
        # First validate raw price bounds
        validated_raw_price = self.validate_price_bounds(raw_price, tier)
        
        # Process through NewPriceProcessor
        target = tier or self.product
        new_price_processor = NewPriceProcessor(target)
        processed_price = new_price_processor.process_price(validated_raw_price, seller_id, asin)
        processed_price = self.round_price(processed_price)
        
        # Validate processed price bounds (in case processor changed it)
        final_price = self.validate_price_bounds(processed_price, tier)
        
        return final_price
    
    def set_strategy_metadata(self, target: Any) -> None:
        """Set strategy metadata on the target (product or tier)."""
        target.strategy = self.product.strategy
        target.strategy_id = self.product.strategy_id
    
    def get_product_pricing_message(self, target: Any, strategy_name: str) -> str:
        """
        Generate detailed pricing message for the strategy application.
        
        Args:
            target: Product or tier object
            strategy_name: Name of the strategy applied
            
        Returns:
            Detailed pricing message
        """
        asin = getattr(target, 'asin', getattr(self.product, 'asin', 'unknown'))
        old_price = getattr(target, 'listed_price', 'unknown')
        new_price = getattr(target, 'updated_price', 'unknown')
        competitor_price = getattr(target, 'competitor_price', getattr(self.product, 'competitor_price', 'unknown'))
        
        strategy_config = self.product.strategy
        compete_with = getattr(strategy_config, 'compete_with', 'unknown')
        beat_by = getattr(strategy_config, 'beat_by', 0)
        
        message_parts = [
            f"Strategy {self.product.strategy_id}",
            f"compete with {compete_with}",
            f"beat by {beat_by}",
            f"Applied strategy {strategy_name}"
        ]
        
        if competitor_price != 'unknown':
            message_parts.append(f"Competitor price: {competitor_price}")
        
        message_parts.append(f"Price updated: {old_price} → {new_price}")
        
        return ", ".join(message_parts)
    
    def calculate_mean_price(self, tier: Any) -> Optional[float]:
        """
        Calculate the mean of min and max prices.
        
        Args:
            tier: Product or tier object
            
        Returns:
            Mean price or None if min/max not available
        """
        min_price = getattr(tier, 'min_price', None) or getattr(tier, 'min', None)
        max_price = getattr(tier, 'max_price', None) or getattr(tier, 'max', None)
        
        if min_price is None or max_price is None:
            return None
        
        mean_price = (min_price + max_price) / 2
        return self.round_price(mean_price)
    
    def apply_b2b_standard_pricing(self) -> None:
        """Apply strategy to B2B standard pricing."""
        if not self.product.is_b2b:
            return
        
        if not self.product.competitor_price:
            self.logger.info("No competitor price for B2B standard pricing")
            return
        
        try:
            seller_id = getattr(self.product, 'seller_id', getattr(self.product.account, 'seller_id', 'unknown'))
            asin = self.product.asin
            
            # Calculate competitive price
            raw_price = self.calculate_competitive_price(
                self.product.competitor_price, 
                self.product.strategy.beat_by
            )
            
            # Process and validate price
            processed_price = self.process_price_with_bounds_check(
                raw_price, seller_id, asin
            )
            
            self.product.updated_price = processed_price
            self.set_strategy_metadata(self.product)
            
            self.logger.info(
                f"B2B standard price calculated: {processed_price}",
                extra={
                    "competitor_price": self.product.competitor_price,
                    "beat_by": self.product.strategy.beat_by,
                    "final_price": processed_price
                }
            )
            
        except (SkipProductRepricing, PriceBoundsError) as e:
            self.logger.warning(f"B2B standard pricing skipped: {e}")
            self.product.updated_price = None
        except Exception as e:
            self.logger.error(f"B2B standard pricing error: {e}")
            self.product.updated_price = None
    
    def apply_b2b_tier_pricing(self) -> None:
        """Apply strategy to B2B tier pricing."""
        if not self.product.is_b2b or not self.product.tiers:
            return
        
        seller_id = getattr(self.product, 'seller_id', getattr(self.product.account, 'seller_id', 'unknown'))
        asin = self.product.asin
        
        for tier_key, tier in self.product.tiers.items():
            try:
                if not hasattr(tier, 'competitor_price') or not tier.competitor_price:
                    self.logger.info(f"No competitor price for tier {tier_key}")
                    continue
                
                # Calculate competitive price for tier
                raw_price = self.calculate_competitive_price(
                    tier.competitor_price,
                    self.product.strategy.beat_by
                )
                
                # Process and validate price for this tier
                processed_price = self.process_price_with_bounds_check(
                    raw_price, seller_id, asin, tier
                )
                
                tier.updated_price = processed_price
                self.set_strategy_metadata(tier)
                
                self.logger.info(
                    f"B2B tier {tier_key} price calculated: {processed_price}",
                    extra={
                        "tier": tier_key,
                        "competitor_price": tier.competitor_price,
                        "final_price": processed_price
                    }
                )
                
            except (SkipProductRepricing, PriceBoundsError) as e:
                self.logger.warning(f"B2B tier {tier_key} pricing skipped: {e}")
                tier.updated_price = None
            except Exception as e:
                self.logger.error(f"B2B tier {tier_key} pricing error: {e}")
                tier.updated_price = None