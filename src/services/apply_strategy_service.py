from typing import Dict, Type
from ..strategies.chase_buybox import ChaseBuyBox
from ..strategies.maxmise_profit import MaximiseProfit
from ..strategies.only_seller import OnlySeller


class SkipProductRepricing(Exception):
    """Exception raised when product repricing should be skipped."""
    pass


strategies: Dict[str, Type] = {
    'WIN_BUYBOX': ChaseBuyBox,
    'ONLY_SELLER': OnlySeller,
    'MAXIMISE_PROFIT': MaximiseProfit,
}


class ApplyStrategyService:
    """
    Apply the strategy to the given product.

    Args:
        product (Product): The product to apply the strategy to.
    """

    def apply(self, product: Product) -> None:
        if product.no_of_offers == 1:
            strategy_type = 'ONLY_SELLER'
        elif not product.is_b2b and product.is_seller_buybox_winner:
            strategy_type = 'MAXIMISE_PROFIT'
        else:
            strategy_type = 'WIN_BUYBOX'

        product.repricer_type = "REPRICER"
        strategy = strategies[strategy_type]
        strategy(product).apply()

        if not product.is_b2b and product.updated_price == product.listed_price:
            raise SkipProductRepricing(
                f'New price and old price are same, therefore, skipping repricing for ASIN: {product.asin}...'
            )