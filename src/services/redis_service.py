"""Redis service with optimized structure for the arbitrage repricer."""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import redis.asyncio as redis
import structlog

from core.config import Settings


class RedisService:
    """
    Redis service with optimized structure and performance optimizations.

    Redis Structure:
    - product:{asin}:{seller_id}:{sku}        # Individual product (Hash)
    - seller:{seller_id}:products             # Seller's product index (Set)
    - strategy:{strategy_id}                  # Strategy config (Hash)
    - price:{seller_id}:{sku}                 # Calculated prices (Hash with TTL)
    - pause:{seller_id}:{asin}               # Pause flags (String with TTL)
    - reset_rules:{user_id}:{market}         # Reset rules (Hash)
    - indexes:asins                          # All ASINs (Set)
    - indexes:sellers                        # All sellers (Set)
    """

    def __init__(self, settings: Settings, logger: structlog.BoundLogger):
        self.settings = settings
        self.logger = logger
        self._pool = None
        self._redis = None

        # TTL settings
        self.default_price_ttl = 2 * 60 * 60  # 2 hours for calculated prices
        self.default_pause_ttl = 24 * 60 * 60  # 24 hours for pause flags
        self.strategy_cache_ttl = 60 * 60  # 1 hour for strategy cache

        # Redis structure configuration
        self.enable_ttl = True

    async def get_connection(self) -> redis.Redis:
        """Get Redis connection with connection pooling."""
        if self._redis is None:
            self._pool = redis.ConnectionPool(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                password=getattr(self.settings, "redis_password", None),
                decode_responses=True,
                max_connections=30,  # Increased for better concurrency
                retry_on_timeout=True,
                health_check_interval=30,
            )
            self._redis = redis.Redis(connection_pool=self._pool)

        return self._redis

    async def close_connection(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()

    # ============ PRODUCT DATA OPERATIONS ============

    async def get_product_data(
        self, asin: str, seller_id: str, sku: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get product data from Redis using optimized structure.
        """
        try:
            redis_client = await self.get_connection()

            # Get product data
            product_key = f"product:{asin}:{seller_id}:{sku}"
            product_data = await redis_client.hgetall(product_key)

            if product_data:
                # Convert string values back to appropriate types
                processed_data = self._process_product_data(product_data)
                self.logger.debug(
                    f"Retrieved product data for {asin}:{seller_id}:{sku}"
                )
                return processed_data

            return None

        except Exception as e:
            self.logger.error("product_data_get_failed", 
                             extra={"error": str(e), "asin": asin, "seller_id": seller_id, "sku": sku})
            return None

    async def save_product_data(
        self, asin: str, seller_id: str, sku: str, data: Dict[str, Any]
    ) -> bool:
        """
        Save product data using optimized Redis structure.
        """
        try:
            redis_client = await self.get_connection()
            pipeline = redis_client.pipeline()

            # Save product data
            product_key = f"product:{asin}:{seller_id}:{sku}"

            # Flatten data for hash storage (convert nested objects to strings)
            flattened_data = self._flatten_product_data(data)
            pipeline.hmset(product_key, flattened_data)

            # Update indexes atomically
            pipeline.sadd("indexes:asins", asin)
            pipeline.sadd("indexes:sellers", seller_id)
            pipeline.sadd(f"seller:{seller_id}:products", f"{asin}:{sku}")

            await pipeline.execute()

            self.logger.debug("product_data_saved", 
                             extra={"asin": asin, "seller_id": seller_id, "sku": sku})
            return True

        except Exception as e:
            self.logger.error("product_data_save_failed", 
                             extra={"error": str(e), "asin": asin, "seller_id": seller_id, "sku": sku})
            return False

    async def bulk_get_product_data(
        self, requests: List[Tuple[str, str, str]]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Bulk get product data with improved performance using pipelines.
        """
        try:
            redis_client = await self.get_connection()
            pipeline = redis_client.pipeline()

            request_keys = []

            # Use optimized structure
            for asin, seller_id, sku in requests:
                product_key = f"product:{asin}:{seller_id}:{sku}"
                pipeline.hgetall(product_key)
                request_keys.append(f"{asin}:{seller_id}:{sku}")

            results = await pipeline.execute()

            # Process results
            product_data_map = {}
            for i, result in enumerate(results):
                key = request_keys[i]
                if result:
                    product_data_map[key] = self._process_product_data(result)
                else:
                    product_data_map[key] = None

            self.logger.debug("bulk_product_data_retrieved", 
                             extra={"request_count": len(requests)})
            return product_data_map

        except Exception as e:
            self.logger.error("bulk_product_data_get_failed", 
                             extra={"error": str(e), "request_count": len(requests)})
            return {
                f"{asin}:{seller_id}:{sku}": None for asin, seller_id, sku in requests
            }

    # ============ STRATEGY OPERATIONS ============

    async def get_strategy_data(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get strategy data with caching."""
        try:
            redis_client = await self.get_connection()

            # Try new format first (strategy:{id})
            strategy_key = f"strategy:{strategy_id}"
            strategy_data = await redis_client.hgetall(strategy_key)

            # Fallback to old format (strategy.{id}) if new format not found
            if not strategy_data:
                strategy_key = f"strategy.{strategy_id}"
                strategy_data = await redis_client.hgetall(strategy_key)

            if strategy_data:
                processed_strategy = self._process_strategy_data(strategy_data)
                self.logger.debug("strategy_data_retrieved", 
                                 extra={"strategy_id": strategy_id, "key_format": strategy_key})
                return processed_strategy

            return None

        except Exception as e:
            self.logger.error("strategy_data_get_failed", 
                             extra={"error": str(e), "strategy_id": strategy_id})
            return None

    async def bulk_get_strategies(
        self, strategy_ids: Set[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Bulk get strategies with improved performance."""
        try:
            redis_client = await self.get_connection()
            pipeline = redis_client.pipeline()

            strategy_ids_list = list(strategy_ids)

            # Try new format first (strategy:{id})
            for strategy_id in strategy_ids_list:
                pipeline.hgetall(f"strategy:{strategy_id}")

            results = await pipeline.execute()

            strategies = {}
            missing_strategies = []

            for i, result in enumerate(results):
                strategy_id = strategy_ids_list[i]
                if result:
                    strategies[strategy_id] = self._process_strategy_data(result)
                else:
                    missing_strategies.append(strategy_id)

            # Fallback to old format (strategy.{id}) for missing strategies
            if missing_strategies:
                pipeline = redis_client.pipeline()
                for strategy_id in missing_strategies:
                    pipeline.hgetall(f"strategy.{strategy_id}")

                fallback_results = await pipeline.execute()

                for i, result in enumerate(fallback_results):
                    strategy_id = missing_strategies[i]
                    if result:
                        strategies[strategy_id] = self._process_strategy_data(result)
                    else:
                        strategies[strategy_id] = None

            return strategies

        except Exception as e:
            self.logger.error("bulk_strategies_get_failed", 
                             extra={"error": str(e), "strategy_ids": strategy_ids})
            return {sid: None for sid in strategy_ids}

    # ============ CALCULATED PRICE OPERATIONS ============

    async def save_calculated_price(
        self,
        asin: str,
        seller_id: str,
        sku: str,
        price_data: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Save calculated price with optimized structure."""
        try:
            redis_client = await self.get_connection()
            ttl = ttl_seconds or self.default_price_ttl

            # Prepare price data
            essential_price_data = {
                "new_price": str(price_data.get("new_price", "")),
                "old_price": str(price_data.get("old_price", "")),
                "strategy_used": price_data.get("strategy_used", ""),
                "strategy_id": price_data.get("strategy_id", ""),
                "competitor_price": str(price_data.get("competitor_price", "")),
                "calculated_at": price_data.get(
                    "calculated_at", datetime.now(UTC).isoformat()
                ),
            }

            pipeline = redis_client.pipeline()

            # Use optimized structure: individual keys with TTL
            price_key = f"price:{seller_id}:{sku}"
            pipeline.hmset(price_key, essential_price_data)
            pipeline.expire(price_key, ttl)

            # Update seller index
            pipeline.sadd(f"seller:{seller_id}:calculated_prices", sku)
            pipeline.expire(f"seller:{seller_id}:calculated_prices", ttl)

            await pipeline.execute()

            self.logger.info("calculated_price_saved_to_redis", 
                             asin=asin, seller_id=seller_id, sku=sku,
                             old_price=price_data.get("old_price"),
                             new_price=price_data.get("new_price"),
                             strategy_used=price_data.get("strategy_used"),
                             strategy_id=price_data.get("strategy_id"),
                             competitor_price=price_data.get("competitor_price"),
                             price_change=float(price_data.get("new_price", 0)) - float(price_data.get("old_price", 0)) if price_data.get("new_price") and price_data.get("old_price") else None,
                             reason=price_data.get("reason"),
                             processing_time_ms=price_data.get("processing_time_ms"),
                             calculated_at=price_data.get("calculated_at"))
            return True

        except Exception as e:
            self.logger.error("failed_to_save_calculated_price_to_redis", 
                             asin=asin, seller_id=seller_id, sku=sku,
                             error=str(e), error_type=type(e).__name__,
                             strategy_used=price_data.get("strategy_used"),
                             new_price=price_data.get("new_price"))
            return False

    async def get_calculated_price(
        self, seller_id: str, sku: str
    ) -> Optional[Dict[str, Any]]:
        """Get calculated price with optimized structure."""
        try:
            redis_client = await self.get_connection()

            # Use optimized structure
            price_key = f"price:{seller_id}:{sku}"
            price_data = await redis_client.hgetall(price_key)

            if price_data:
                return self._process_price_data(price_data)

            return None

        except Exception as e:
            self.logger.error("calculated_price_get_failed", 
                             extra={"error": str(e), "seller_id": seller_id, "sku": sku})
            return None

    # ============ PAUSE OPERATIONS ============

    async def set_repricing_paused(
        self, seller_id: str, asin: str, paused: bool
    ) -> bool:
        """Set/unset repricing pause with optimized structure."""
        try:
            redis_client = await self.get_connection()
            pipeline = redis_client.pipeline()

            # Use correct pause key format
            pause_key = f"repricing_paused:{seller_id}:{asin}"

            if paused:
                pipeline.set(pause_key, datetime.now(UTC).isoformat())
                pipeline.expire(pause_key, self.default_pause_ttl)
                pipeline.sadd(f"seller:{seller_id}:paused", asin)
                pipeline.expire(f"seller:{seller_id}:paused", self.default_pause_ttl)
            else:
                pipeline.delete(pause_key)
                pipeline.srem(f"seller:{seller_id}:paused", asin)

            await pipeline.execute()

            action = "paused" if paused else "resumed"
            self.logger.info("repricing_pause_state_changed", 
                           extra={"seller_id": seller_id, "asin": asin,
                           "pause_action": action,
                           "pause_key": pause_key, 
                           "timestamp": datetime.now(UTC).isoformat() if paused else None})
            return True

        except Exception as e:
            self.logger.error("repricing_pause_set_failed", 
                             extra={"error": str(e), "seller_id": seller_id, "asin": asin, "paused": paused})
            return False

    async def is_repricing_paused(self, seller_id: str, asin: str) -> bool:
        """Check if repricing is paused."""
        try:
            redis_client = await self.get_connection()

            # Use correct pause key format
            pause_key = f"repricing_paused:{seller_id}:{asin}"
            result = await redis_client.get(pause_key)
            return result is not None

        except Exception as e:
            self.logger.error("repricing_pause_check_failed", 
                             extra={"error": str(e), "seller_id": seller_id, "asin": asin})
            return False

    # ============ EFFICIENT LISTING OPERATIONS ============

    async def list_entries_efficient(
        self,
        seller_id: Optional[str] = None,
        region: Optional[str] = None,
        asin: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Efficiently list entries using new index structure.
        Falls back to scanning if indexes not available.
        """
        try:
            redis_client = await self.get_connection()
            entries = []

            if seller_id:
                # Use seller index for efficient filtering
                products = await redis_client.smembers(f"seller:{seller_id}:products")

                # Filter by ASIN if specified
                if asin:
                    products = [p for p in products if p.startswith(f"{asin}:")]

                # Apply pagination
                paginated_products = list(products)[offset : offset + limit]

                # Bulk get product data
                pipeline = redis_client.pipeline()
                for product in paginated_products:
                    asin_sku = product.split(":", 1)
                    if len(asin_sku) == 2:
                        product_asin, sku = asin_sku
                        product_key = f"product:{product_asin}:{seller_id}:{sku}"
                        pipeline.hgetall(product_key)

                results = await pipeline.execute()

                # Process results
                for i, result in enumerate(results):
                    if result:
                        product_asin, sku = paginated_products[i].split(":", 1)

                        # Apply region filter
                        product_region = result.get("region")
                        if region and product_region != region:
                            continue

                        entry = await self._build_entry_from_data(
                            product_asin, seller_id, sku, result
                        )
                        if entry:
                            entries.append(entry)

                return entries

            # Fallback to current data structure (ASIN_* keys)
            return await self._list_from_asin_keys(
                seller_id, region, asin, limit, offset
            )

        except Exception as e:
            self.logger.error("entries_list_failed", 
                             extra={"error": str(e), "seller_id": seller_id, "region": region, "asin": asin})
            return []


    async def _list_from_asin_keys(
        self,
        seller_id: Optional[str] = None,
        region: Optional[str] = None,
        asin: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List entries from current ASIN_* data structure."""
        try:
            redis_client = await self.get_connection()
            entries = []
            processed_count = 0

            # Get pattern for ASIN keys
            pattern = f"ASIN_{asin}" if asin else "ASIN_*"
            
            async for keys_batch in self._scan_keys(pattern):
                for key in keys_batch:
                    if len(entries) >= limit:
                        break

                    asin_value = key.replace("ASIN_", "")
                    asin_data = await redis_client.hgetall(key)

                    for field, product_json in asin_data.items():
                        if ":" not in field:
                            continue

                        if processed_count < offset:
                            processed_count += 1
                            continue

                        if len(entries) >= limit:
                            break

                        product_seller_id, sku = field.split(":", 1)

                        # Apply seller filter
                        if seller_id and product_seller_id != seller_id:
                            continue

                        try:
                            import json
                            product_data = json.loads(product_json)
                        except json.JSONDecodeError:
                            continue

                        # Apply region filter
                        detected_region = product_data.get("region")
                        if region and detected_region != region:
                            continue

                        entry = await self._build_entry_from_asin_data(
                            asin_value, product_seller_id, sku, product_data
                        )
                        if entry:
                            entries.append(entry)

                        processed_count += 1

                if len(entries) >= limit:
                    break

            return entries

        except Exception as e:
            self.logger.error("asin_keys_list_failed", 
                             extra={"error": str(e), "seller_id": seller_id, "region": region, "asin": asin})
            return []

    async def _scan_keys(self, pattern: str, count: int = 100):
        """Non-blocking key scanning."""
        redis_client = await self.get_connection()
        cursor = 0

        while True:
            cursor, keys = await redis_client.scan(cursor, pattern, count)
            if keys:
                yield keys
            if cursor == 0:
                break

    # ============ HELPER METHODS ============

    def _flatten_product_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Flatten product data for hash storage."""
        flattened = {}
        for key, value in data.items():
            if value is not None:
                flattened[key] = str(value)
        return flattened

    def _process_product_data(self, raw_data: Dict[str, str]) -> Dict[str, Any]:
        """Process raw product data from Redis hash."""
        processed = {}

        for key, value in raw_data.items():
            if not value:
                processed[key] = None
                continue

            if key in ["listed_price", "min_price", "max_price", "default_price"]:
                try:
                    processed[key] = float(value)
                except (ValueError, TypeError):
                    processed[key] = None
            elif key in ["quantity", "inventory_quantity"]:
                try:
                    processed[key] = int(value)
                except (ValueError, TypeError):
                    processed[key] = None
            else:
                processed[key] = value

        return processed

    def _process_price_data(self, raw_data: Dict[str, str]) -> Dict[str, Any]:
        """Process calculated price data."""
        processed = {}

        for key, value in raw_data.items():
            if key in ["new_price", "old_price", "competitor_price"]:
                try:
                    processed[key] = float(value) if value else None
                except (ValueError, TypeError):
                    processed[key] = None
            else:
                processed[key] = value

        return processed

    def _process_strategy_data(self, raw_strategy: Dict[str, str]) -> Dict[str, Any]:
        """Process strategy data with type conversion."""
        processed = {}

        for key, value in raw_strategy.items():
            if key == "beat_by":
                try:
                    processed[key] = float(value)
                except (ValueError, TypeError):
                    processed[key] = 0.0
            elif key in ["inventory_age_threshold"]:
                try:
                    processed[key] = int(value)
                except (ValueError, TypeError):
                    processed[key] = 0
            else:
                processed[key] = value

        return processed

    async def _build_entry_from_data(
        self, asin: str, seller_id: str, sku: str, product_data: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Build entry dict from optimized structure data."""
        try:
            _redis_client = await self.get_connection()

            # Get strategy data
            strategy_id = product_data.get("strategy_id")
            strategy_data = {}
            if strategy_id:
                strategy_data = await self.get_strategy_data(strategy_id) or {}

            # Get calculated price
            calculated_price = await self.get_calculated_price(seller_id, sku)

            # Check repricing pause status
            repricing_paused = await self.is_repricing_paused(seller_id, asin)

            # Process product data
            processed_product = self._process_product_data(product_data)

            return {
                "asin": asin,
                "seller_id": seller_id,
                "sku": sku,
                "region": processed_product.get("region"),
                "product_data": processed_product,
                "strategy": strategy_data,
                "calculated_price": calculated_price,
                "repricing_paused": repricing_paused,
            }

        except Exception as e:
            self.logger.error("entry_build_failed", 
                             extra={"error": str(e), "asin": asin, "seller_id": seller_id, "sku": sku})
            return None

    async def _build_entry_from_asin_data(
        self, asin: str, seller_id: str, sku: str, product_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Build entry dict from ASIN_* structure data."""
        try:
            # Get strategy data
            strategy_id = product_data.get("strategy_id")
            strategy_data = {}
            if strategy_id:
                strategy_data = await self.get_strategy_data(strategy_id) or {}

            # Get calculated price
            calculated_price = await self.get_calculated_price(seller_id, sku)

            # Check repricing pause status
            repricing_paused = await self.is_repricing_paused(seller_id, asin)

            return {
                "asin": asin,
                "seller_id": seller_id,
                "sku": sku,
                "region": product_data.get("region"),
                "product_data": product_data,
                "strategy": strategy_data,
                "calculated_price": calculated_price,
                "repricing_paused": repricing_paused,
            }

        except Exception as e:
            self.logger.error("asin_entry_build_failed", 
                             extra={"error": str(e), "asin": asin, "seller_id": seller_id, "sku": sku})
            return None


    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            redis_client = await self.get_connection()
            await redis_client.ping()
            return True
        except Exception as e:
            self.logger.error("redis_health_check_failed", 
                             extra={"error": str(e)})
            return False

    # ============ BACKWARD COMPATIBILITY METHODS ============

    async def get_current_price(
        self, asin: str, seller_id: str, sku: str
    ) -> Optional[float]:
        """Backward compatible method for getting current price."""
        product_data = await self.get_product_data(asin, seller_id, sku)

        if product_data:
            current_price = product_data.get("listed_price")
            if current_price is not None:
                return float(current_price)

        return None

    async def get_stock_quantity(
        self, asin: str, seller_id: str, sku: str
    ) -> Optional[int]:
        """Backward compatible method for getting stock quantity."""
        product_data = await self.get_product_data(asin, seller_id, sku)

        if product_data:
            inventory_quantity = product_data.get("inventory_quantity")
            if inventory_quantity is not None and inventory_quantity != "":
                try:
                    return int(inventory_quantity)
                except (ValueError, TypeError):
                    pass

        return None


# Use dependency injection container to get Redis service instances
# Example: container.redis_service()
