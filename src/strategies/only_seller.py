from typing import Any, Optional
from .base_strategy import BaseStrategy, PriceBoundsError
from .new_price_processor import SkipProductRepricing


class OnlySeller(BaseStrategy):
    """Strategy for when there's only one seller (no competition)."""
    
    def get_strategy_name(self) -> str:
        """Return the strategy name."""
        return "ONLY_SELLER"
    
    def apply(self) -> None:
        """Apply the only seller strategy to the given product."""
        # Apply to main product
        self._set_new_price(self.product)
        
        # Apply to B2B tiers if they exist
        if self.product.tiers:
            for tier in self.product.tiers.values():
                self._set_new_price(tier)
    
    def _set_new_price(self, tier: Any) -> None:
        """
        Calculate new price of the product/tiers.
        B2B standard product is also considered as tier in this method.
        """
        try:
            # Try default price first (check for not None to handle 0 as valid)
            if hasattr(tier, 'default_price') and tier.default_price is not None:
                calculated_price = self.round_price(tier.default_price)
            else:
                # Fall back to mean of min/max prices
                calculated_price = self.calculate_mean_price(tier)
            
            if calculated_price is None:
                if not self.product.is_b2b:
                    # For standard products, require a price
                    raise SkipProductRepricing("OnlySeller: Default, Min or Max price is missing")
                else:
                    # For B2B, it's acceptable to have no price for some tiers
                    self.logger.info(f"No price available for B2B tier, skipping")
                    tier.updated_price = None
                    return
            
            # Validate price bounds
            validated_price = self.validate_price_bounds(calculated_price, tier)
            
            # Set the results
            tier.updated_price = validated_price
            self.set_strategy_metadata(tier)
            tier.message = self.get_product_pricing_message(tier, self.get_strategy_name())
            
            self.logger.info(
                f"Only seller pricing applied: {validated_price}",
                extra={
                    "tier_type": "main" if tier == self.product else "b2b_tier",
                    "default_price": getattr(tier, 'default_price', None),
                    "calculated_price": calculated_price,
                    "final_price": validated_price
                }
            )
            
        except (SkipProductRepricing, PriceBoundsError) as e:
            self.logger.warning(f"Only seller pricing failed for tier: {e}")
            tier.updated_price = None
            # For main product, re-raise the exception
            if tier == self.product:
                raise e
        except Exception as e:
            self.logger.error(f"Unexpected error in only seller pricing: {e}")
            tier.updated_price = None
            if tier == self.product:
                raise SkipProductRepricing(f"Only seller pricing error: {e}")