"""Core repricing engine that makes decisions and calculates prices."""

import time
from typing import Optional, Tuple
from loguru import logger

from schemas.messages import ProcessedOfferData, RepricingDecision, CalculatedPrice
from services.redis_service import RedisService
from strategies import ChaseBuyBox, MaximiseProfit, OnlySeller
from models.product import Product, Strategy
from utils.exceptions import SkipProductRepricing, PriceBoundsError
from utils.price_reset_utils import is_repricing_paused
from utils.reset_utils import should_skip_repricing_sync




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
            # Check if repricing should be skipped due to reset/resume rules
            if should_skip_repricing_sync(offer_data.seller_id):
                logger.info(
                    f"Skipping repricing due to reset window for seller {offer_data.seller_id}",
                    extra={
                        "seller_id": offer_data.seller_id,
                        "product_id": offer_data.product_id,
                        "platform": offer_data.platform
                    }
                )
                return None
            
            # Check if repricing is paused for this specific seller:asin combination
            asin = offer_data.product_id if offer_data.platform == "AMAZON" else None
            if asin:
                repricing_paused = await self._check_repricing_paused(offer_data.seller_id, asin)
                if repricing_paused:
                    logger.info(
                        f"Skipping repricing - repricing paused for {offer_data.seller_id}:{asin}",
                        extra={
                            "seller_id": offer_data.seller_id,
                            "asin": asin,
                            "platform": offer_data.platform
                        }
                    )
                    return None
            
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
                        "competitor_id": offer_data.buybox_winner,
                        "competitor_price": offer_data.competitor_price,
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
        seller_id = offer_data.seller_id
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
        strategy_id = product_data.get('strategy_id', 'unknown')
        if not product_data:
            return RepricingDecision(
                should_reprice=False,
                reason=f"Product not found in catalog: {asin}",
                asin=asin,
                sku=sku,
                seller_id=seller_id,
                strategy_id="unknown",
                competitor_data=offer_data,
                current_price=-1,
                stock_quantity=-1
            )

        # Prevent self competition - check if we are competing against ourselves using new method
        strategy_data = await self.redis.get_strategy_data(strategy_id)
        
        # Create product and strategy objects for the new self-competition check
        from decimal import Decimal
        
        strategy = Strategy(
            type=strategy_data.get('type', 'LOWEST_PRICE'),
            beat_by=Decimal(str(strategy_data.get('beat_by', 0.0))),
            min_price_rule=strategy_data.get('min_price_rule', 'JUMP_TO_MIN'),
            max_price_rule=strategy_data.get('max_price_rule', 'JUMP_TO_MAX')
        )
        
        # Convert numeric fields to Decimal as required by Product model
        product_data_converted = {}
        for key, value in product_data.items():
            if key in ['listed_price', 'min_price', 'max_price', 'default_price'] and value is not None:
                product_data_converted[key] = Decimal(str(value))
            else:
                product_data_converted[key] = value
        
        product = Product(
            asin=asin,
            seller_id=seller_id,
            sku=sku,
            strategy=strategy,
            **product_data_converted
        )
        
        if await self._check_self_competition(product, offer_data):
            return RepricingDecision(
                should_reprice=False,
                reason=f"Self-competition detected for {strategy.type} strategy",
                asin=asin,
                sku=sku,
                seller_id=seller_id,
                strategy_id=strategy_id,
                competitor_data=offer_data,
                current_price=product_data.get('listed_price'),
                stock_quantity=-1
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
            # Filter out conflicting keys from product_data
            filtered_product_data = {k: v for k, v in product_data.items() 
                                   if k not in ['asin', 'sku', 'seller_id']}
            
            product = Product.from_kwargs(
                asin=decision.asin,
                sku=decision.sku,
                seller_id=decision.seller_id,
                **filtered_product_data
            )
            
            product.strategy = Strategy.model_construct(**strategy_data)
            product.strategy_id = decision.strategy_id
            
            # Early strategy-aware self-competition detection
            if await self._check_self_competition(product, decision.competitor_data):
                raise SkipProductRepricing(f"Self-competition detected for {product.strategy.type} strategy on ASIN {product.asin} by seller {product.seller_id}")

            # Set clean competitor info for strategy (no self-competition)
            await self._set_clean_competitor_info(product, decision.competitor_data)

            # Select strategy dynamically based on competitive situation
            strategy_class = self._select_strategy_class(product)

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
                    f"Price bounds violation: {e.min_price} <= {e.calculated_price} <= {e.max_price}",
                    extra={
                        "asin": decision.asin,
                        "calculated_price": e.calculated_price,
                        "min_price": e.min_price,
                        "max_price": e.max_price,
                        "strategy": str(strategy_class),
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
                strategy_used=str(strategy_instance),
                strategy_id=decision.strategy_id,
                competitor_price=product.competitor_price,
                processing_time_ms=processing_time
            )

            self.logger.info(
                f"Price calculated: {old_price} → {new_price}",
                extra={
                    "asin": decision.asin,
                    "seller_id": decision.seller_id,
                    "old_price": old_price,
                    "new_price": new_price,
                    "price_changed": price_changed,
                    "strategy": str(strategy_instance),
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

    
    async def _check_self_competition(self, product: Product, offer_data: ProcessedOfferData) -> bool:
        """Check if we're competing against ourselves based on strategy type."""
        strategy_type = product.strategy.type
        our_seller_id = product.seller_id
        competition_data = offer_data.competition_data
        
        self.logger.debug(f"Checking self-competition for strategy {strategy_type}, seller {our_seller_id}")
        
        if strategy_type == 'LOWEST_PRICE':
            competitor = competition_data.lowest_price_competitor
            if competitor and competitor.seller_id == our_seller_id:
                self.logger.debug(f"Self-competition detected: we are the lowest price competitor")
                return True
                
        elif strategy_type == 'LOWEST_FBA_PRICE':
            competitor = competition_data.lowest_fba_competitor
            if competitor and competitor.seller_id == our_seller_id:
                self.logger.debug(f"Self-competition detected: we are the lowest FBA competitor")
                return True
                
        elif strategy_type == 'MATCH_BUYBOX':
            buybox_winner = competition_data.buybox_winner
            if buybox_winner and buybox_winner.seller_id == our_seller_id:
                self.logger.debug(f"Self-competition detected: we already have the buybox")
                return True
        
        return False

    async def _set_clean_competitor_info(self, product: Product, offer_data: ProcessedOfferData):
        """Set clean competitor information on product (no self-competition)."""
        strategy_type = product.strategy.type
        competition_data = offer_data.competition_data
        
        # Set strategy-specific competitor price and metadata
        if strategy_type == 'LOWEST_PRICE':
            competitor = competition_data.lowest_price_competitor
            if competitor:
                product.competitor_price = competitor.price
                self.logger.debug(f"Set LOWEST_PRICE competitor: {competitor.seller_id} at ${competitor.price}")
                
        elif strategy_type == 'LOWEST_FBA_PRICE':
            competitor = competition_data.lowest_fba_competitor
            if competitor:
                product.competitor_price = competitor.price
                self.logger.debug(f"Set LOWEST_FBA_PRICE competitor: {competitor.seller_id} at ${competitor.price}")
                
        elif strategy_type == 'MATCH_BUYBOX':
            buybox_winner = competition_data.buybox_winner
            if buybox_winner:
                product.competitor_price = buybox_winner.price
                self.logger.debug(f"Set MATCH_BUYBOX competitor: {buybox_winner.seller_id} at ${buybox_winner.price}")
        
        # Set total offers count
        product.no_of_offers = competition_data.total_offers or 1
        
        self.logger.debug(f"Final competitor price set: ${product.competitor_price}, total offers: {product.no_of_offers}")

    def _select_strategy_class(self, product: Product):
        """Select strategy class based on competitive situation."""
        if product.no_of_offers == 1:
            return OnlySeller
        elif getattr(product, 'is_seller_buybox_winner', False):
            return MaximiseProfit  
        else:
            return ChaseBuyBox

    async def _find_sku_for_asin_seller(self, asin: str, seller_id: str) -> Optional[str]:
        """
        Find SKU for a given ASIN and seller by scanning Redis hash fields.
        
        Args:
            asin: Amazon ASIN
            seller_id: Seller identifier
            
        Returns:
            SKU if found, None otherwise
        """
        try:
            # Get Redis client
            redis_client = await self.redis.get_connection()
            
            # Check if ASIN key exists
            redis_key = f"ASIN_{asin}"
            if not await redis_client.exists(redis_key):
                self.logger.debug(f"ASIN key does not exist: {redis_key}")
                return None
            
            # Get all field names in the hash - format is {seller_id}:{sku}
            field_names = await redis_client.hkeys(redis_key)
            
            # Find the field that starts with our seller_id
            for field_name in field_names:
                if field_name.startswith(f"{seller_id}:"):
                    # Extract SKU from field name format: seller_id:sku
                    sku = field_name.split(":", 1)[1]
                    self.logger.debug(f"Found SKU {sku} for ASIN {asin}, seller {seller_id}")
                    return sku
            
            self.logger.debug(f"No SKU found for ASIN {asin}, seller {seller_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding SKU for ASIN {asin}, seller {seller_id}: {str(e)}")
            return None
    
    async def _find_product_for_walmart_item(self, item_id: str, seller_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Find corresponding ASIN and SKU for a Walmart item.
        
        For Walmart webhooks, item_id is the ASIN, and we need to find the corresponding SKU
        for the specific seller from Redis.
        """
        try:
            redis_client = await self.redis.get_connection()
            
            # Use item_id as the ASIN directly
            asin = item_id
            redis_key = f"ASIN_{asin}"
            
            # Get all fields in the hash to find the one for this seller
            all_fields = await redis_client.hkeys(redis_key)
            
            # Look for a field that starts with the seller_id
            for field in all_fields:
                if field.startswith(f"{seller_id}:"):
                    # Extract SKU from the field format: "seller_id:sku"
                    sku = field.split(":", 1)[1]
                    self.logger.debug(
                        f"Found product mapping for Walmart item {item_id}",
                        extra={"asin": asin, "seller_id": seller_id, "sku": sku}
                    )
                    return asin, sku
            
            self.logger.warning(
                f"No product found for Walmart item {item_id} and seller {seller_id}",
                extra={"item_id": item_id, "seller_id": seller_id, "available_fields": all_fields}
            )
            return None, None
            
        except Exception as e:
            self.logger.error(f"Failed to find product for Walmart item {item_id}: {str(e)}")
            return None, None
    
    async def _check_repricing_paused(self, seller_id: str, asin: str) -> bool:
        """Check if repricing is paused for a specific seller:asin combination."""
        return await is_repricing_paused(self.redis, seller_id, asin)