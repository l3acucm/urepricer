from typing import Any
from .new_price_processor import SkipProductRepricing


class MaximiseProfit:
    """Strategy to maximise profit by matching competitor prices when winning buybox."""
    
    def __init__(self, product: Any) -> None:
        self.product = product

    def apply(self) -> None:
        """Apply the maximise profit strategy to the given product."""
        if self.product.competitor_price <= self.product.listed_price:
            raise SkipProductRepricing(
                f'Competitor ({self.product.competitor_price}) is at lower price than us ({self.product.listed_price})'
            )
        
        self.product.updated_price = round(self.product.competitor_price, 2)
        self.product.message = self._get_product_pricing_message(self.product, "MAXIMISE_PROFIT")

    def _get_product_pricing_message(self, product: Any, strategy: str) -> str:
        """Get pricing message for product."""
        # TODO: Implement proper message generation
        return f"Applied {strategy} strategy to {product.asin}"