from typing import Optional, Any
from utils.exceptions import SkipProductRepricing


class NewPriceProcessor:
    """Process new prices and apply pricing rules."""
    
    def __init__(self, product: Any) -> None:
        self.product = product

    def process_price(self, new_price: float, seller_id: Optional[str] = None, asin: Optional[str] = None) -> float:
        """
        Process the new_price and check if the new_price is out of range.

        Args:
            new_price: The new price to be submitted on Amazon
            seller_id: Optional seller ID for logging
            asin: Optional ASIN for logging

        Returns:
            float: The updated price based on the competitor rule.
        """
        if not new_price or new_price <= 0:
            raise SkipProductRepricing(
                f"Skipping Repricing! (Update Price ({new_price}) is None or Less than zero for ASIN: {asin}...)"
            )

        if self.product.max_price and (new_price > self.product.max_price):
            new_price = self._apply_price_rule('max_price_rule', seller_id, asin)
        elif self.product.min_price and (new_price < self.product.min_price):
            new_price = self._apply_price_rule('min_price_rule', seller_id, asin)

        return new_price

    def _apply_price_rule(self, rule_type: str, seller_id: Optional[str], asin: Optional[str]) -> float:
        """
        Apply the competitor rule to the given product.

        Args:
            rule_type: The rule to apply [min_price_rule, max_price_rule]
            seller_id: Optional seller ID for logging
            asin: Optional ASIN for logging

        Returns:
            float: The updated price based on the competitor rule.
        """
        rule = getattr(self.product.strategy, rule_type.lower())
        rule = f'_{rule.lower()}'

        if not all([rule, hasattr(self, rule)]):
            raise SkipProductRepricing(f"Rule is not set or Method '{rule}' is not defined for ASIN: {asin}...")

        method = getattr(self, rule)

        if rule == "_default_price":
            return method(seller_id, asin)
        
        return method()

    def _jump_to_avg(self) -> float:
        """Jump to average of min and max price."""
        if not (self.product.min_price and self.product.max_price):
            raise SkipProductRepricing(
                f'Rule is set to jump_to_avg, but {"max" if not self.product.max_price else "min"} price is missing for ASIN: {self.product.asin}...'
            )        

        average_price = (self.product.min_price + self.product.max_price) / 2
        return average_price

    def _jump_to_min(self) -> float:
        """Jump to minimum price."""
        if not self.product.min_price:
            raise SkipProductRepricing(
                f'Rule is set to jump_to_min, but min price is missing for ASIN: {self.product.asin}...'
            )
        return self.product.min_price

    def _jump_to_max(self) -> float:
        """Jump to maximum price."""
        if not self.product.max_price:
            raise SkipProductRepricing(
                f'Rule is set to jump_to_max, but max price is missing for ASIN: {self.product.asin}...'
            )
        return self.product.max_price

    def _match_competitor(self) -> float:
        """Match competitor price exactly."""
        if not self.product.competitor_price:
            raise SkipProductRepricing(
                f'Rule is set to competitor_price, but competitor price is missing for ASIN: {self.product.asin}...'
            )
        return self.product.competitor_price

    def _do_nothing(self) -> float:
        """Do nothing - skip repricing."""
        raise SkipProductRepricing(f'Rule is set to do_nothing, therefore, skipping repricing for ASIN: {self.product.asin}...')

    def _default_price(self, seller_id: Optional[str] = None, asin: Optional[str] = None) -> float:
        """Set default price if it exists and is in range."""
        default_price = self.product.default_price
        
        if not default_price or default_price <= 0:
            raise SkipProductRepricing(
                f'Rule is set to default_price, but default_price is missing for ASIN: {self.product.asin}...'
            )

        # TODO: Implement check_default_price_in_range function
        default_in_range = False
        message = "Default price check not implemented"

        if default_in_range:
            raise SkipProductRepricing(message)

        return self.product.default_price