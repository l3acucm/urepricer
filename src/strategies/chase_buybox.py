from typing import Any
from .base_strategy import BaseStrategy, PriceBoundsError
from .new_price_processor import SkipProductRepricing


class ChaseBuyBox(BaseStrategy):
    """Strategy to chase the buybox by beating competitor prices."""
    
    def get_strategy_name(self) -> str:
        """Return the strategy name."""
        return "WIN_BUYBOX"
    
    def apply(self) -> None:
        """Apply the ChaseBuyBox strategy to the given product."""
        if not self.product.is_b2b:
            # Standard product pricing
            self._apply_standard_pricing()
        else:
            # B2B pricing (both standard and tiers)
            self.apply_b2b_standard_pricing()
            self.apply_b2b_tier_pricing()
    
    def _apply_standard_pricing(self) -> None:
        """Apply strategy to standard (non-B2B) product."""
        try:
            if not self.product.competitor_price:
                raise SkipProductRepricing("No competitor price available")
            
            seller_id = getattr(self.product, 'seller_id', getattr(self.product.account, 'seller_id', 'unknown'))
            asin = self.product.asin
            
            # Calculate competitive price
            raw_price = self.calculate_competitive_price(
                self.product.competitor_price,
                self.product.strategy.beat_by
            )
            
            # Check if we're already in a better position than the calculated price
            # This prevents price spiral when we're already winning
            if (self.product.listed_price is not None and 
                self.product.listed_price < raw_price):
                raise SkipProductRepricing(
                    f"Already winning with better price: our price ({self.product.listed_price}) "
                    f"is better than calculated price ({raw_price})"
                )
            
            # Process price with bounds checking
            processed_price = self.process_price_with_bounds_check(
                raw_price, seller_id, asin
            )
            
            # Set the results
            self.product.updated_price = processed_price
            self.set_strategy_metadata(self.product)
            self.product.message = self.get_product_pricing_message(self.product, self.get_strategy_name())
            
            self.logger.info(
                f"Standard pricing applied: {processed_price}",
                extra={
                    "competitor_price": self.product.competitor_price,
                    "beat_by": self.product.strategy.beat_by,
                    "final_price": processed_price
                }
            )
            
        except (SkipProductRepricing, PriceBoundsError) as e:
            self.logger.warning(f"Standard pricing failed: {e}")
            # Re-raise the exception so caller knows pricing failed
            raise e
        except Exception as e:
            self.logger.error(f"Unexpected error in standard pricing: {e}")
            raise SkipProductRepricing(f"Standard pricing error: {e}")

    def apply_b2b_tier_pricing(self) -> None:
        """Apply ChaseBuyBox strategy to B2B tiers with winner detection."""
        if not self.product.is_b2b or not self.product.tiers:
            return
        
        seller_id = getattr(self.product, 'seller_id', getattr(self.product.account, 'seller_id', 'unknown'))
        asin = self.product.asin
        
        for tier_key, tier in self.product.tiers.items():
            try:
                if not hasattr(tier, 'competitor_price') or not tier.competitor_price:
                    self.logger.info(f"No competitor price for tier {tier_key}")
                    continue
                
                # Calculate competitive price for tier
                raw_price = self.calculate_competitive_price(
                    tier.competitor_price,
                    self.product.strategy.beat_by
                )
                
                # Check if tier is already in a better position (same logic as standard pricing)
                if (hasattr(tier, 'listed_price') and tier.listed_price is not None and 
                    tier.listed_price < raw_price):
                    self.logger.info(
                        f"B2B tier {tier_key} already winning: current ({tier.listed_price}) "
                        f"better than calculated ({raw_price})"
                    )
                    continue
                
                # Process and validate price for this tier
                processed_price = self.process_price_with_bounds_check(
                    raw_price, seller_id, asin, tier
                )
                
                tier.updated_price = processed_price
                self.set_strategy_metadata(tier)
                
                self.logger.info(
                    f"B2B tier {tier_key} price calculated: {processed_price}",
                    extra={
                        "tier": tier_key,
                        "competitor_price": tier.competitor_price,
                        "final_price": processed_price
                    }
                )
                
            except (SkipProductRepricing, PriceBoundsError) as e:
                self.logger.warning(f"B2B tier {tier_key} pricing skipped: {e}")
                tier.updated_price = None
            except Exception as e:
                self.logger.error(f"B2B tier {tier_key} pricing error: {e}")
                tier.updated_price = None