"""Core repricing engine that makes decisions and calculates prices."""

import asyncio
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from ..schemas.messages import ProcessedOfferData, RepricingDecision, CalculatedPrice
from ..services.redis_service import RedisService
from ..strategies.new_price_processor import NewPriceProcessor
from ..strategies import ChaseBuyBox, MaximiseProfit, OnlySeller, PriceBoundsError
from ..tasks.set_competitor_info import SetCompetitorInfo


class Product:
    """Product model for repricing calculations."""
    
    def __init__(self, **kwargs):
        # Core identification
        self.asin = kwargs.get('asin')
        self.sku = kwargs.get('sku') 
        self.seller_id = kwargs.get('seller_id')
        
        # Pricing data
        self.listed_price = kwargs.get('listed_price')
        self.min_price = kwargs.get('min', kwargs.get('min_price'))
        self.max_price = kwargs.get('max', kwargs.get('max_price'))
        self.default_price = kwargs.get('default_price')
        
        # Competition data
        self.competitor_price = kwargs.get('competitor_price')
        self.no_of_offers = kwargs.get('no_of_offers', 0)
        self.is_seller_buybox_winner = kwargs.get('is_seller_buybox_winner', False)
        
        # Product details
        self.item_condition = kwargs.get('item_condition', 'new')
        self.mapped_item_condition = self.item_condition.lower()
        self.inventory_quantity = kwargs.get('inventory_quantity')
        self.inventory_age = kwargs.get('inventory_age', 0)
        self.fulfillment_type = kwargs.get('fullfilment_type', kwargs.get('fulfillment_type', 'AMAZON'))
        self.is_b2b = kwargs.get('is_b2b', False)
        
        # Strategy data
        self.strategy = None
        self.strategy_id = kwargs.get('strategy_id')
        self.repricer_type = "REPRICER"
        
        # Results
        self.updated_price = None
        self.message = ""
        
        # Add account-like object for backward compatibility
        self.account = type('Account', (), {'seller_id': self.seller_id})()
        
        # B2B tiers (if applicable)
        self.tiers = {}
        if 'b2b_rules' in kwargs:
            self._process_b2b_rules(kwargs['b2b_rules'])
    
    def _process_b2b_rules(self, b2b_rules: Dict[str, Any]):
        """Process B2B rules and tiers."""
        self.is_b2b = True
        
        # B2B standard pricing
        self.b2b_listed_price = b2b_rules.get('listed_price')
        self.b2b_min_price = b2b_rules.get('min')
        self.b2b_max_price = b2b_rules.get('max') 
        self.b2b_default_price = b2b_rules.get('default_price')
        self.b2b_strategy_id = b2b_rules.get('strategy_id')
        
        # Process tiers
        tiers_data = b2b_rules.get('tiers', {})
        for tier_key, tier_data in tiers_data.items():
            tier = Tier(
                quantity=int(tier_key),
                listed_price=tier_data.get('listed_price'),
                min_price=tier_data.get('min'),
                max_price=tier_data.get('max'),
                default_price=tier_data.get('default_price')
            )
            self.tiers[tier_key] = tier


class Tier:
    """B2B tier model for quantity-based pricing."""
    
    def __init__(self, quantity: int, **kwargs):
        self.quantity = quantity
        self.listed_price = kwargs.get('listed_price')
        self.min_price = kwargs.get('min_price', kwargs.get('min'))
        self.max_price = kwargs.get('max_price', kwargs.get('max'))
        self.default_price = kwargs.get('default_price')
        
        # Competition data (set during processing)
        self.competitor_price = None
        
        # Results
        self.updated_price = None
        self.strategy = None
        self.strategy_id = None
        self.message = ""


class Strategy:
    """Strategy configuration model."""
    
    def __init__(self, **kwargs):
        self.compete_with = kwargs.get('compete_with', 'MATCH_BUYBOX')
        self.beat_by = float(kwargs.get('beat_by', 0.0))
        self.min_price_rule = kwargs.get('min_price_rule', 'JUMP_TO_MIN')
        self.max_price_rule = kwargs.get('max_price_rule', 'JUMP_TO_MAX')
        self.b2b_compete_for = kwargs.get('b2b_compete_for', 'LOW')
        self.b2b_beat_by_rule = kwargs.get('b2b_beat_by_rule', 'BEAT_BY')


class RepricingEngine:
    """Core repricing engine that processes offers and calculates new prices."""
    
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
        self.logger = logger.bind(service="repricing_engine")
        
        # Strategy mapping
        self.strategies = {
            'WIN_BUYBOX': ChaseBuyBox,
            'ONLY_SELLER': OnlySeller, 
            'MAXIMISE_PROFIT': MaximiseProfit,
        }
    
    async def make_repricing_decision(self, offer_data: ProcessedOfferData) -> Optional[RepricingDecision]:
        """
        Step 3: Make decision about whether repricing is needed.
        
        Args:
            offer_data: Processed offer data from step 1
            
        Returns:
            RepricingDecision or None if no repricing needed
        """
        start_time = time.time()
        
        try:
            # For Amazon, we need to map ASIN to our product data
            # For Walmart, we need to find matching products by item_id
            
            if offer_data.platform == "AMAZON":
                decision = await self._make_amazon_decision(offer_data)
            elif offer_data.platform == "WALMART":
                decision = await self._make_walmart_decision(offer_data)
            else:
                self.logger.warning(f"Unsupported platform: {offer_data.platform}")
                return None
            
            if decision:
                processing_time = (time.time() - start_time) * 1000
                self.logger.info(
                    f"Repricing decision made: {decision.should_reprice}",
                    extra={
                        "asin": decision.asin,
                        "seller_id": decision.seller_id,
                        "should_reprice": decision.should_reprice,
                        "reason": decision.reason,
                        "processing_time_ms": processing_time
                    }
                )
            
            return decision
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.logger.error(
                f"Error making repricing decision: {str(e)}",
                extra={"processing_time_ms": processing_time}
            )
            return None
    
    async def _make_amazon_decision(self, offer_data: ProcessedOfferData) -> Optional[RepricingDecision]:
        """Make repricing decision for Amazon offer data."""
        asin = offer_data.product_id
        
        # For Amazon, we need to find all products with this ASIN
        # This is a simplified version - in practice you might want to get all sellers for an ASIN
        
        # For now, assume we're processing for a specific seller
        # In real implementation, you'd iterate through all sellers for this ASIN
        seller_id = offer_data.seller_id  # This comes from the notification
        
        # Get product data from Redis
        # Note: We need to find the SKU somehow - this could be from a mapping table
        # For now, we'll try to get all product data for this seller and ASIN
        
        # This is where you'd implement logic to find the correct SKU
        # For demonstration, let's assume we have a method to find it
        sku = await self._find_sku_for_asin_seller(asin, seller_id)
        if not sku:
            return None
        
        return await self._evaluate_product_for_repricing(asin, seller_id, sku, offer_data)
    
    async def _make_walmart_decision(self, offer_data: ProcessedOfferData) -> Optional[RepricingDecision]:
        """Make repricing decision for Walmart offer data."""
        item_id = offer_data.product_id
        seller_id = offer_data.seller_id
        
        # For Walmart, item_id might map directly to our ASIN/SKU system
        # This depends on your specific implementation
        
        # Find corresponding product in our system
        asin, sku = await self._find_product_for_walmart_item(item_id, seller_id)
        if not asin or not sku:
            return None
        
        return await self._evaluate_product_for_repricing(asin, seller_id, sku, offer_data)
    
    async def _evaluate_product_for_repricing(
        self, 
        asin: str, 
        seller_id: str, 
        sku: str, 
        offer_data: ProcessedOfferData
    ) -> Optional[RepricingDecision]:
        """Evaluate whether a specific product needs repricing."""
        
        # Get current product data
        product_data = await self.redis.get_product_data(asin, seller_id, sku)
        if not product_data:
            return RepricingDecision(
                should_reprice=False,
                reason=f"Product not found in catalog: {asin}",
                asin=asin,
                sku=sku,
                seller_id=seller_id,
                strategy_id="unknown",
                competitor_data=offer_data
            )
        
        # Check stock - only reprice if we have stock
        stock_quantity = await self.redis.get_stock_quantity(asin, seller_id, sku)
        if stock_quantity is not None and stock_quantity <= 0:
            return RepricingDecision(
                should_reprice=False,
                reason=f"Out of stock: {stock_quantity}",
                asin=asin,
                sku=sku,
                seller_id=seller_id,
                strategy_id=product_data.get('strategy_id', 'unknown'),
                current_price=product_data.get('listed_price'),
                stock_quantity=stock_quantity,
                competitor_data=offer_data
            )
        
        # Check if product is active
        if product_data.get('status', 'Active').lower() != 'active':
            return RepricingDecision(
                should_reprice=False,
                reason=f"Product not active: {product_data.get('status')}",
                asin=asin,
                sku=sku,
                seller_id=seller_id,
                strategy_id=product_data.get('strategy_id', 'unknown'),
                current_price=product_data.get('listed_price'),
                stock_quantity=stock_quantity,
                competitor_data=offer_data
            )
        
        # All checks passed - product should be repriced
        return RepricingDecision(
            should_reprice=True,
            reason="Product eligible for repricing",
            asin=asin,
            sku=sku,
            seller_id=seller_id,
            strategy_id=product_data.get('strategy_id', '1'),
            current_price=product_data.get('listed_price'),
            stock_quantity=stock_quantity,
            competitor_data=offer_data
        )
    
    async def calculate_new_price(self, decision: RepricingDecision) -> Optional[CalculatedPrice]:
        """
        Step 4: Apply strategies and calculate new price.
        
        Args:
            decision: Repricing decision from step 3
            
        Returns:
            CalculatedPrice or None if calculation failed
        """
        if not decision.should_reprice:
            return None
        
        start_time = time.time()
        
        try:
            # Get full product data and strategy
            product_data = await self.redis.get_product_data(
                decision.asin, decision.seller_id, decision.sku
            )
            
            if not product_data:
                self.logger.error(f"Product data not found during calculation: {decision.asin}")
                return None
            
            strategy_data = await self.redis.get_strategy_data(decision.strategy_id)
            if not strategy_data:
                self.logger.error(f"Strategy not found: {decision.strategy_id}")
                return None
            
            # Create product and strategy objects
            product = Product(
                asin=decision.asin,
                sku=decision.sku,
                seller_id=decision.seller_id,
                **product_data
            )
            
            product.strategy = Strategy(**strategy_data)
            product.strategy_id = decision.strategy_id
            
            # Set competitor information using offer data
            await self._set_competitor_info(product, decision.competitor_data)
            
            # Apply pricing strategy
            strategy_name = self._determine_strategy_name(product)
            strategy_class = self.strategies.get(strategy_name)
            
            if not strategy_class:
                self.logger.error(f"Unknown strategy: {strategy_name}")
                return None
            
            # Apply the strategy
            try:
                strategy_instance = strategy_class(product)
                strategy_instance.apply()
                
                # Check if price actually changed
                old_price = float(decision.current_price) if decision.current_price else 0.0
                new_price = float(product.updated_price) if product.updated_price else old_price
                price_changed = abs(new_price - old_price) > 0.01  # 1 cent threshold
                
            except PriceBoundsError as e:
                processing_time = (time.time() - start_time) * 1000
                self.logger.warning(
                    f"Price bounds violation: {e.message}",
                    extra={
                        "asin": decision.asin,
                        "calculated_price": e.calculated_price,
                        "min_price": e.min_price,
                        "max_price": e.max_price,
                        "strategy": strategy_name,
                        "processing_time_ms": processing_time
                    }
                )
                return None
            
            processing_time = (time.time() - start_time) * 1000
            
            result = CalculatedPrice(
                asin=decision.asin,
                sku=decision.sku, 
                seller_id=decision.seller_id,
                old_price=old_price,
                new_price=new_price,
                price_changed=price_changed,
                strategy_used=strategy_name,
                strategy_id=decision.strategy_id,
                competitor_price=product.competitor_price,
                processing_time_ms=processing_time
            )
            
            # Handle B2B tier pricing if applicable
            if product.is_b2b and product.tiers:
                tier_prices = {}
                for tier_key, tier in product.tiers.items():
                    if tier.updated_price is not None:
                        tier_prices[tier_key] = float(tier.updated_price)
                result.tier_prices = tier_prices
            
            self.logger.info(
                f"Price calculated: {old_price} → {new_price}",
                extra={
                    "asin": decision.asin,
                    "seller_id": decision.seller_id,
                    "old_price": old_price,
                    "new_price": new_price,
                    "price_changed": price_changed,
                    "strategy": strategy_name,
                    "processing_time_ms": processing_time
                }
            )
            
            return result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.logger.error(
                f"Error calculating price: {str(e)}",
                extra={
                    "asin": decision.asin,
                    "processing_time_ms": processing_time
                }
            )
            return None
    
    async def save_price_if_changed(self, calculated_price: CalculatedPrice) -> bool:
        """
        Save calculated price to Redis only if it changed.
        
        Args:
            calculated_price: Result of price calculation
            
        Returns:
            True if price was saved (because it changed), False otherwise
        """
        if not calculated_price.price_changed:
            self.logger.debug(
                f"Price unchanged for {calculated_price.asin}, not saving",
                extra={
                    "asin": calculated_price.asin,
                    "price": calculated_price.new_price
                }
            )
            return False
        
        # Prepare price data for Redis
        price_data = {
            "new_price": calculated_price.new_price,
            "old_price": calculated_price.old_price,
            "strategy_used": calculated_price.strategy_used,
            "strategy_id": calculated_price.strategy_id,
            "calculated_at": calculated_price.calculated_at.isoformat(),
            "competitor_price": calculated_price.competitor_price,
            "processing_time_ms": calculated_price.processing_time_ms
        }
        
        # Add B2B tier prices if applicable
        if calculated_price.tier_prices:
            price_data["tier_prices"] = calculated_price.tier_prices
        
        # Save to Redis with 2-hour TTL
        success = await self.redis.save_calculated_price(
            calculated_price.asin,
            calculated_price.seller_id,
            calculated_price.sku,
            price_data
        )
        
        if success:
            self.logger.info(
                f"Saved new price to Redis: {calculated_price.new_price}",
                extra={
                    "asin": calculated_price.asin,
                    "seller_id": calculated_price.seller_id,
                    "new_price": calculated_price.new_price
                }
            )
        
        return success
    
    async def _set_competitor_info(self, product: Product, offer_data: ProcessedOfferData):
        """Set competitor information on product using offer data."""
        # Create a mock payload structure for SetCompetitorInfo
        payload = {
            'Summary.TotalOfferCount': offer_data.total_offers or 1,
            'Offers': offer_data.raw_offers or [],
            'Summary.BuyBoxPrices': offer_data.raw_summary or [],
            'Summary.LowestPrices': offer_data.raw_summary or []
        }
        
        # Set basic competitor price from offer data
        if offer_data.competitor_price:
            product.competitor_price = offer_data.competitor_price
            product.no_of_offers = offer_data.total_offers or 1
        
        # Use SetCompetitorInfo for more detailed analysis if we have raw data
        if offer_data.raw_offers or offer_data.raw_summary:
            try:
                competitor_analyzer = SetCompetitorInfo(product, payload)
                competitor_analyzer.apply()
            except Exception as e:
                self.logger.warning(f"Competitor analysis failed: {str(e)}")
                # Fall back to basic competitor price from offer_data
    
    def _determine_strategy_name(self, product: Product) -> str:
        """Determine which strategy to apply based on market conditions."""
        if product.no_of_offers <= 1:
            return 'ONLY_SELLER'
        elif not product.is_b2b and product.is_seller_buybox_winner:
            return 'MAXIMISE_PROFIT'
        else:
            return 'WIN_BUYBOX'
    
    async def _find_sku_for_asin_seller(self, asin: str, seller_id: str) -> Optional[str]:
        """
        Find SKU for a given ASIN and seller.
        
        This is a simplified implementation. In reality, you might:
        1. Have a separate mapping table
        2. Scan Redis keys 
        3. Use a database query
        
        For now, this is a placeholder that would need to be implemented
        based on your specific data structure.
        """
        # TODO: Implement actual SKU lookup logic
        # This could involve scanning Redis keys or maintaining a separate mapping
        
        # Placeholder implementation
        return f"SKU_{asin}_{seller_id[:8]}"
    
    async def _find_product_for_walmart_item(self, item_id: str, seller_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Find corresponding ASIN and SKU for a Walmart item.
        
        This depends on how you map Walmart items to your internal product catalog.
        """
        # TODO: Implement Walmart item to ASIN/SKU mapping
        # This might involve a separate mapping table or API
        
        # Placeholder implementation
        return f"ASIN_{item_id}", f"SKU_{item_id}_{seller_id[:8]}"