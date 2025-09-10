from typing import Any
from .base_strategy import BaseStrategy, PriceBoundsError
from .new_price_processor import SkipProductRepricing


class MaximiseProfit(BaseStrategy):
    """Strategy to maximise profit by matching competitor prices when winning buybox."""
    
    def get_strategy_name(self) -> str:
        """Return the strategy name."""
        return "MAXIMISE_PROFIT"
    
    def apply(self) -> None:
        """Apply the maximise profit strategy to the given product."""
        try:
            if not self.product.competitor_price:
                raise SkipProductRepricing("No competitor price available")
            
            # Check if competitor price is higher than our current price
            if self.product.competitor_price <= self.product.listed_price:
                raise SkipProductRepricing(
                    f'Competitor ({self.product.competitor_price}) is at lower price than us ({self.product.listed_price})'
                )
            
            # For maximize profit, we match competitor price exactly
            competitor_price = self.round_price(self.product.competitor_price)
            
            # Validate price bounds
            validated_price = self.validate_price_bounds(competitor_price)
            
            # Set the results
            self.product.updated_price = validated_price
            self.set_strategy_metadata(self.product)
            self.product.message = self.get_product_pricing_message(self.product, self.get_strategy_name())
            
            self.logger.info(
                f"Maximize profit pricing applied: {validated_price}",
                extra={
                    "competitor_price": self.product.competitor_price,
                    "our_price": self.product.listed_price,
                    "final_price": validated_price
                }
            )
            
        except (SkipProductRepricing, PriceBoundsError) as e:
            self.logger.warning(f"Maximize profit pricing failed: {e}")
            # Re-raise the exception so caller knows pricing failed
            raise e
        except Exception as e:
            self.logger.error(f"Unexpected error in maximize profit pricing: {e}")
            raise SkipProductRepricing(f"Maximize profit pricing error: {e}")