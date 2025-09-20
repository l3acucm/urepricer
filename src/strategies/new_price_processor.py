from typing import Any, Optional

from utils.exceptions import SkipProductRepricing


class NewPriceProcessor:
    """Process new prices and apply pricing rules."""

    def __init__(self, product: Any) -> None:
        self.product = product

    def process_price(
        self,
        new_price: float,
        seller_id: Optional[str] = None,
        asin: Optional[str] = None,
    ) -> float:
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
            new_price = self._apply_price_rule("max_price_rule", seller_id, asin)
        elif self.product.min_price and (new_price < self.product.min_price):
            new_price = self._apply_price_rule("min_price_rule", seller_id, asin)

        return new_price

    def _apply_price_rule(
        self, rule_type: str, seller_id: Optional[str], asin: Optional[str]
    ) -> float:
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
        rule = f"_{rule.lower()}"

        if not all([rule, hasattr(self, rule)]):
            raise SkipProductRepricing(
                f"Rule is not set or Method '{rule}' is not defined for ASIN: {asin}..."
            )

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
                f"Rule is set to jump_to_min, but min price is missing for ASIN: {self.product.asin}..."
            )
        return self.product.min_price

    def _jump_to_max(self) -> float:
        """Jump to maximum price."""
        if not self.product.max_price:
            raise SkipProductRepricing(
                f"Rule is set to jump_to_max, but max price is missing for ASIN: {self.product.asin}..."
            )
        return self.product.max_price

    def _match_competitor(self) -> float:
        """Match competitor price exactly."""
        if not self.product.competitor_price:
            raise SkipProductRepricing(
                f"Rule is set to competitor_price, but competitor price is missing for ASIN: {self.product.asin}..."
            )
        return self.product.competitor_price

    def _do_nothing(self) -> float:
        """Do nothing - skip repricing."""
        raise SkipProductRepricing(
            f"Rule is set to do_nothing, therefore, skipping repricing for ASIN: {self.product.asin}..."
        )

    def _default_price(
        self, seller_id: Optional[str] = None, asin: Optional[str] = None
    ) -> float:
        """Set default price if it exists and is in range."""
        default_price = self.product.default_price

        if not default_price or default_price <= 0:
            raise SkipProductRepricing(
                f"Rule is set to default_price, but default_price is missing for ASIN: {self.product.asin}..."
            )

        # Check if default price is within min/max bounds
        default_in_range, message = self._check_default_price_in_range(default_price)

        if not default_in_range:
            raise SkipProductRepricing(message)

        return self.product.default_price

    def _check_default_price_in_range(self, default_price: float) -> tuple[bool, str]:
        """
        Check if default price is within the product's min/max price bounds.
        
        Args:
            default_price: The default price to validate
            
        Returns:
            Tuple of (is_in_range, message)
        """
        try:
            min_price = self.product.min_price
            max_price = self.product.max_price
            
            # If no bounds are set, default price is acceptable
            if min_price is None and max_price is None:
                return True, "No price bounds set"
            
            # Check minimum price bound
            if min_price is not None and default_price < float(min_price):
                return False, (
                    f"Default price {default_price} is below minimum price {min_price} "
                    f"for ASIN {self.product.asin}"
                )
            
            # Check maximum price bound
            if max_price is not None and default_price > float(max_price):
                return False, (
                    f"Default price {default_price} is above maximum price {max_price} "
                    f"for ASIN {self.product.asin}"
                )
            
            # Price is within bounds
            return True, f"Default price {default_price} is within bounds"
            
        except Exception as e:
            # If there's any error in validation, be conservative and reject
            return False, f"Error validating default price bounds: {str(e)}"
