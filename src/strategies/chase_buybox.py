from typing import Any
from .base_strategy import BaseStrategy, PriceBoundsError
from .new_price_processor import SkipProductRepricing


class ChaseBuyBox(BaseStrategy):
    """Strategy to chase the buybox by beating competitor prices."""
    
    def get_strategy_name(self) -> str:
        """Return the strategy name."""
        return "WIN_BUYBOX"
    
    def apply(self) -> None:
        self._apply_standard_pricing()
    
    def _apply_standard_pricing(self) -> None:
        """Apply strategy to standard product."""
        if not self.product.competitor_price:
            raise SkipProductRepricing("No competitor price available")
        
        # Calculate new price: competitor price + beat_by
        new_price = self.product.competitor_price + self.product.strategy.beat_by
        
        # Validate bounds
        self.validate_price_bounds(new_price)
        
        # Set results
        self.product.updated_price = new_price
        self.set_strategy_metadata(self.product)
        self.product.message = self.get_product_pricing_message(self.product, self.get_strategy_name())
