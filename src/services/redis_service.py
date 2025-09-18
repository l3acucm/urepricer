"""Redis service for product and strategy data management."""

import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC
import redis.asyncio as redis
from loguru import logger

from core.config import get_settings


class RedisService:
    """Async Redis service for product and strategy data operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logger.bind(service="redis_service")
        self._pool = None
        self._redis = None
        
        # TTL settings
        self.default_ttl = 2 * 60 * 60  # 2 hours in seconds
    
    async def get_connection(self) -> redis.Redis:
        """Get Redis connection with connection pooling."""
        if self._redis is None:
            self._pool = redis.ConnectionPool(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                password=getattr(self.settings, 'redis_password', None),
                decode_responses=True,
                max_connections=20,  # For high throughput
                retry_on_timeout=True
            )
            self._redis = redis.Redis(connection_pool=self._pool)
        
        return self._redis
    
    async def close_connection(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()
    
    async def get_product_data(self, asin: str, seller_id: str, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get product listing data from Redis.
        
        Redis structure: ASIN -> SELLER_ID -> SKU -> {product_data}
        
        Args:
            asin: Product ASIN
            seller_id: Seller identifier
            sku: Product SKU
            
        Returns:
            Product data dict or None if not found
        """
        try:
            redis_client = await self.get_connection()
            
            # Redis key structure: ASIN_{asin}
            redis_key = f"ASIN_{asin}"
            
            # Get the nested data: seller_id -> sku -> product_data
            product_data_json = await redis_client.hget(redis_key, f"{seller_id}:{sku}")
            
            if product_data_json:
                product_data = json.loads(product_data_json)
                
                self.logger.debug(
                    f"Retrieved product data for {asin}",
                    extra={"asin": asin, "seller_id": seller_id, "sku": sku}
                )
                
                return product_data
            
            self.logger.warning(
                f"Product data not found for {asin}",
                extra={"asin": asin, "seller_id": seller_id, "sku": sku}
            )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get product data: {str(e)}")
            return None
    
    async def get_strategy_data(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get strategy configuration from Redis.
        
        Redis structure: strategy.{id} -> {strategy_config}
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Strategy configuration dict or None if not found
        """
        try:
            redis_client = await self.get_connection()
            
            # Redis key structure: strategy.{id}
            redis_key = f"strategy.{strategy_id}"
            
            # Get all strategy fields
            strategy_data = await redis_client.hgetall(redis_key)
            
            if strategy_data:
                # Convert string values back to appropriate types
                processed_strategy = self._process_strategy_data(strategy_data)
                
                self.logger.debug(
                    f"Retrieved strategy {strategy_id}",
                    extra={"strategy_id": strategy_id}
                )
                
                return processed_strategy
            
            self.logger.warning(f"Strategy not found: {strategy_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get strategy data: {str(e)}")
            return None
    
    async def get_current_price(self, asin: str, seller_id: str, sku: str) -> Optional[float]:
        """
        Get current listed price for a product.
        
        Args:
            asin: Product ASIN
            seller_id: Seller identifier
            sku: Product SKU
            
        Returns:
            Current price or None if not found
        """
        product_data = await self.get_product_data(asin, seller_id, sku)
        
        if product_data:
            # Try to get listed_price from product data
            current_price = product_data.get("listed_price")
            if current_price is not None:
                return float(current_price)
        
        return None
    
    async def get_stock_quantity(self, asin: str, seller_id: str, sku: str) -> Optional[int]:
        """
        Get current stock quantity for a product.
        
        Args:
            asin: Product ASIN
            seller_id: Seller identifier
            sku: Product SKU
            
        Returns:
            Stock quantity or None if not found/unlimited
        """
        product_data = await self.get_product_data(asin, seller_id, sku)
        
        if product_data:
            inventory_quantity = product_data.get("inventory_quantity")
            if inventory_quantity is not None and inventory_quantity != "":
                try:
                    return int(inventory_quantity)
                except (ValueError, TypeError):
                    pass
        
        return None
    
    async def save_calculated_price(
        self, 
        asin: str, 
        seller_id: str, 
        sku: str, 
        price_data: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Save calculated price to Redis.
        
        Redis structure: CALCULATED_PRICES:{seller_id} -> {sku} -> {price_data}
        
        Args:
            asin: Product ASIN
            seller_id: Seller identifier
            sku: Product SKU
            price_data: Calculated price information
            ttl_seconds: TTL in seconds (default: 2 hours)
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            redis_client = await self.get_connection()
            ttl = ttl_seconds or self.default_ttl
            
            # Simplified calculated price data (only essential fields)
            essential_price_data = {
                "new_price": price_data.get("new_price"),
                "old_price": price_data.get("old_price"),
                "strategy_used": price_data.get("strategy_used"),
                "strategy_id": price_data.get("strategy_id"),
                "competitor_price": price_data.get("competitor_price"),
                "calculated_at": price_data.get("calculated_at", datetime.now(UTC).isoformat())
            }
            
            # Redis key for calculated prices
            redis_key = f"CALCULATED_PRICES:{seller_id}"
            
            # Save the simplified price data
            await redis_client.hset(
                redis_key,
                sku,
                json.dumps(essential_price_data)
            )
            
            # Set TTL on the entire hash
            await redis_client.expire(redis_key, ttl)
            
            self.logger.info(
                f"Saved calculated price for {asin}",
                extra={
                    "asin": asin,
                    "seller_id": seller_id,
                    "sku": sku,
                    "new_price": price_data.get("new_price"),
                    "ttl_seconds": ttl
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save calculated price: {str(e)}")
            return False
    
    async def get_calculated_price(self, seller_id: str, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get previously calculated price data.
        
        Args:
            seller_id: Seller identifier
            sku: Product SKU
            
        Returns:
            Price data dict or None if not found/expired
        """
        try:
            redis_client = await self.get_connection()
            
            redis_key = f"CALCULATED_PRICES:{seller_id}"
            price_data_json = await redis_client.hget(redis_key, sku)
            
            if price_data_json:
                price_data = json.loads(price_data_json)
                
                # Check if data is still valid (extra safety check)
                expires_at_str = price_data.get("expires_at")
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now(UTC) > expires_at:
                        await redis_client.hdel(redis_key, sku)
                        return None
                
                return price_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get calculated price: {str(e)}")
            return None
    
    async def bulk_get_product_data(self, requests: List[Tuple[str, str, str]]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get multiple product data entries in one Redis operation for better performance.
        
        Args:
            requests: List of (asin, seller_id, sku) tuples
            
        Returns:
            Dict mapping "asin:seller_id:sku" -> product_data
        """
        try:
            redis_client = await self.get_connection()
            pipeline = redis_client.pipeline()
            
            # Build pipeline commands
            request_keys = []
            for asin, seller_id, sku in requests:
                redis_key = f"ASIN_{asin}"
                field_key = f"{seller_id}:{sku}"
                pipeline.hget(redis_key, field_key)
                request_keys.append(f"{asin}:{seller_id}:{sku}")
            
            # Execute pipeline
            results = await pipeline.execute()
            
            # Process results
            product_data_map = {}
            for i, result in enumerate(results):
                key = request_keys[i]
                if result:
                    try:
                        product_data_map[key] = json.loads(result)
                    except json.JSONDecodeError:
                        product_data_map[key] = None
                else:
                    product_data_map[key] = None
            
            self.logger.debug(f"Bulk retrieved {len(requests)} product data entries")
            return product_data_map
            
        except Exception as e:
            self.logger.error(f"Failed to bulk get product data: {str(e)}")
            return {f"{asin}:{seller_id}:{sku}": None for asin, seller_id, sku in requests}
    
    def _process_strategy_data(self, raw_strategy: Dict[str, str]) -> Dict[str, Any]:
        """
        Process raw strategy data from Redis, converting types appropriately.
        
        Args:
            raw_strategy: Raw strategy data from Redis (all string values)
            
        Returns:
            Processed strategy data with appropriate types
        """
        processed = {}
        
        for key, value in raw_strategy.items():
            if key in ["beat_by"]:
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
    
    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            redis_client = await self.get_connection()
            await redis_client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Redis health check failed: {str(e)}")
            return False


# Global Redis service instance
redis_service = RedisService()