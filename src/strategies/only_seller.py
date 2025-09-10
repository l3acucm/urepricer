from statistics import mean
from typing import Any
from .new_price_processor import SkipProductRepricing


class OnlySeller:
    """Strategy for when there's only one seller (no competition)."""
    
    def __init__(self, product: Any) -> None:
        self.product = product

    def apply(self) -> None:
        """
        Apply the only seller strategy to the given product.
        """
        self._set_new_price(self.product)

        if not self.product.tiers:
            return

        [self._set_new_price(tier) for tier in self.product.tiers.values()]

    def _set_new_price(self, tier: Any) -> None:
        """
        Calculate new price of the product/tiers.
        b2b_standard is also considered as tier in this method.
        """
        if tier.default_price:
            tier.updated_price = round(tier.default_price, 2)
        else:
            updated_price = self._calculate_mean(tier)
            tier.updated_price = round(updated_price, 2) if updated_price else None
        
        if not tier.updated_price and not self.product.is_b2b:
            raise SkipProductRepricing(f"(OnlySeller Case, Default, Min or Max price is missing)")
        
        tier.strategy = self.product.strategy
        tier.strategy_id = self.product.strategy_id
        tier.message = self._get_product_pricing_message(tier, "ONLY_SELLER")

    def _calculate_mean(self, tier: Any) -> float | None:
        """
        Calculate the mean of the minimum and maximum prices of the product.

        Returns:
            float or None: The calculated mean value of the minimum and maximum prices.
        """
        values = [tier.min_price, tier.max_price]

        if not all(values):
            return None

        return mean(values)

    def _get_product_pricing_message(self, product: Any, strategy: str) -> str:
        """Get pricing message for product."""
        # TODO: Implement proper message generation
        return f"Applied {strategy} strategy to {product.asin}"