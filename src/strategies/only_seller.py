from .base_strategy import BaseStrategy, PriceBoundsError
from .new_price_processor import SkipProductRepricing


class OnlySeller(BaseStrategy):
    """Strategy for when there's only one seller (no competition)."""

    def get_strategy_name(self) -> str:
        """Return the strategy name."""
        return "ONLY_SELLER"

    def apply(self) -> None:
        """Apply the only seller strategy to the given product."""
        try:
            # Try default price first (check for not None to handle 0 as valid)
            if (
                hasattr(self.product, "default_price")
                and self.product.default_price is not None
            ):
                calculated_price = self.round_price(self.product.default_price)
            else:
                # Fall back to mean of min/max prices
                calculated_price = self.calculate_mean_price(self.product)

            if calculated_price is None:
                raise SkipProductRepricing(
                    "OnlySeller: Default, Min or Max price is missing"
                )

            # Validate price bounds
            self.validate_price_bounds(calculated_price)
            validated_price = calculated_price

            # Set the results
            self.product.updated_price = validated_price
            self.set_strategy_metadata(self.product)
            self.product.message = self.get_product_pricing_message(
                self.product, self.get_strategy_name()
            )

            self.logger.info(
                f"Only seller pricing applied: {validated_price}",
                extra={
                    "default_price": getattr(self.product, "default_price", None),
                    "calculated_price": calculated_price,
                    "final_price": validated_price,
                },
            )

        except (SkipProductRepricing, PriceBoundsError) as e:
            self.logger.warning(f"Only seller pricing failed: {e}")
            self.product.updated_price = None
            raise e
        except Exception as e:
            self.logger.error(f"Unexpected error in only seller pricing: {e}")
            self.product.updated_price = None
            raise SkipProductRepricing(f"Only seller pricing error: {e}")
