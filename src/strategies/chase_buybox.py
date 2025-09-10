from typing import Any
from .new_price_processor import NewPriceProcessor, SkipProductRepricing


WIN_BUYBOX_STRATEGY = "WIN_BUYBOX"


class ChaseBuyBox:
    """Strategy to chase the buybox by beating competitor prices."""
    
    def __init__(self, product: Any) -> None:
        self.product = product

    def apply(self) -> None:
        """Apply the GetBuyBox strategy to the given product."""
        product = self.product
        seller_id = product.account.seller_id
        asin = product.asin

        new_price_processor = NewPriceProcessor(self.product)
        
        if not product.is_b2b:
            new_price = eval(f"{product.competitor_price} + {product.strategy.beat_by}")
            new_price = round(new_price, 2)

            product.updated_price = round(
                new_price_processor.process_price(new_price, seller_id, asin), 2
            )
            product.message = self._get_product_pricing_message(product, WIN_BUYBOX_STRATEGY)
        else:
            # For Business Standard Price
            if product.competitor_price:
                try:
                    new_price = eval(f"{product.competitor_price} + {product.strategy.beat_by}")
                    new_price = round(new_price, 2)
                    product.updated_price = round(
                        new_price_processor.process_price(new_price, seller_id, asin), 2
                    )
                except SkipProductRepricing as e:
                    print(f'Business price is skipped... {e}')

            # For Business Quantity Tiers
            for tier in product.tiers.values():
                try:
                    new_price_processor = NewPriceProcessor(tier)
                    if not tier.competitor_price:
                        continue
                    
                    new_price = eval(f"{tier.competitor_price}+{product.strategy.beat_by}")
                    new_price = round(new_price, 2)

                    tier.strategy = product.strategy
                    tier.strategy_id = product.strategy_id
                    tier.updated_price = round(
                        new_price_processor.process_price(new_price, seller_id, asin), 2
                    )
                except SkipProductRepricing as e:
                    print(f'Tier is skipped... {e}')

    def _get_product_pricing_message(self, product: Any, strategy: str) -> str:
        """Get pricing message for product."""
        # TODO: Implement proper message generation
        return f"Applied {strategy} strategy to {product.asin}"