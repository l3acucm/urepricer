from datetime import datetime
from typing import Any, Dict, TypedDict

import structlog

from core.config import Settings
from models.product import Product
from services.redis_service import RedisService


class LogEntry(TypedDict, total=False):
    """Type definition for product log entries."""
    asin: str
    sku: str
    seller_id: str
    updated_price: float
    listed_price: float
    time: datetime
    quantity: int
    product_type: str


class AmazonProductPrice:
    def __init__(self, redis_service: RedisService, settings: Settings, logger: structlog.BoundLogger):
        self.redis_service = redis_service
        self.settings = settings
        self.logger = logger
        self.debug = getattr(settings, "debug", False)

    def call(self, product: Product, testing: bool = False) -> None:
        sku = product.sku
        redis_list = f"{product.account.seller_id}_repriced_products"
        data_hash = {
            "asin": product.asin,
            "sku": product.sku,
            "seller_id": product.account.seller_id,
        }

        # Standard product data only (B2B support removed)
        data_hash["Standard"] = self._get_dataclass_attrs(
            product, self._get_amazon_output_list()
        )
        log_entry = self._get_dataclass_attrs(product, self._get_amazon_logs())
        log_entry["quantity"] = 1
        log_entry["product_type"] = "Standard"
        log_entry["time"] = datetime.now()

        if not self.debug:
            self._save_data_in_redis(redis_list, sku, data_hash)
        else:
            self._send_repricer_output_notification(log_entry)

        print(f"Repriced data: {data_hash}")

    def _get_dataclass_attrs(
        self, product: Product, output_list: list
    ) -> Dict[str, Any]:
        data_hash = {}
        for data in output_list:
            try:
                data_hash[data] = getattr(product, data)
            except AttributeError:
                data_hash[data] = None
        return data_hash

    def _save_log_entry(self, log_entry: LogEntry) -> None:
        print(f"Saving log entry: {log_entry}")

    async def _save_data_in_redis(
        self, redis_list: str, sku: str, data: Dict[str, Any]
    ) -> None:
        """Save repricing data to Redis cache for monitoring and analytics."""
        try:
            redis_client = await self.redis_service.get_connection()
            
            # Save to a list for batch processing
            cache_key = f"repricing_cache:{redis_list}"
            
            # Prepare data with timestamp
            cache_data = {
                **data,
                "sku": sku,
                "cached_at": datetime.now().isoformat(),
                "list_name": redis_list
            }
            
            # Save as JSON string to Redis list
            import json
            await redis_client.lpush(cache_key, json.dumps(cache_data))
            
            # Trim list to keep only recent entries (last 1000)
            await redis_client.ltrim(cache_key, 0, 999)
            
            # Set expiration to 7 days for cache cleanup
            await redis_client.expire(cache_key, 7 * 24 * 3600)
            
            # Also save latest product update in a hash for quick access
            product_key = f"product_updates:{data.get('seller_id', 'unknown')}:{sku}"
            await redis_client.hset(product_key, mapping={
                "last_update": datetime.now().isoformat(),
                "asin": data.get("asin", ""),
                "updated_price": str(data.get("updated_price", "")),
                "listed_price": str(data.get("listed_price", "")),
                "data": json.dumps(cache_data)
            })
            await redis_client.expire(product_key, 24 * 3600)  # 1 day expiration
            
            self.logger.info(
                f"Saved repricing data to Redis cache: {cache_key}",
                extra={
                    "sku": sku,
                    "asin": data.get("asin"),
                    "cache_key": cache_key
                }
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to save data to Redis cache: {str(e)}",
                extra={
                    "sku": sku,
                    "redis_list": redis_list,
                    "error": str(e)
                }
            )
            # Don't raise - caching failure shouldn't break repricing

    async def _send_repricer_output_notification(self, log_entry: Dict[str, Any]) -> None:
        """Send notification about repricing output for monitoring."""
        try:
            # Channel 1: Structured logging for ELK stack
            self.logger.info(
                "Repricing output notification",
                extra={
                    **log_entry,
                    "notification_type": "repricing_output",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Channel 2: Redis pubsub for real-time monitoring
            if hasattr(self.settings, 'redis_notifications_enabled') and getattr(self.settings, 'redis_notifications_enabled', True):
                await self._send_redis_notification(log_entry)
            
            # Channel 3: File-based notifications for external systems
            if hasattr(self.settings, 'file_notifications_enabled') and getattr(self.settings, 'file_notifications_enabled', False):
                await self._send_file_notification(log_entry)
                
        except Exception as e:
            self.logger.error("repricing_output_notification_failed", extra={"error": str(e)})
            # Don't raise - notification failure shouldn't break repricing
    
    async def _send_redis_notification(self, log_entry: Dict[str, Any]) -> None:
        """Send notification via Redis pubsub."""
        try:
            redis_client = await self.redis_service.get_connection()
            
            notification_data = {
                "type": "repricing_output",
                "timestamp": datetime.now().isoformat(),
                "data": log_entry
            }
            
            import json
            channel = "repricing_notifications"
            await redis_client.publish(channel, json.dumps(notification_data))
            
            self.logger.debug("redis_notification_sent", extra={"channel": channel})
            
        except Exception as e:
            self.logger.warning("redis_notification_send_failed", extra={"error": str(e)})
    
    async def _send_file_notification(self, log_entry: Dict[str, Any]) -> None:
        """Send notification to file for external processing."""
        try:
            import json
            from pathlib import Path

            import aiofiles
            
            notifications_dir = Path(getattr(self.settings, 'notifications_directory', '/tmp/urepricer_notifications'))
            notifications_dir.mkdir(exist_ok=True)
            
            notification_file = notifications_dir / f"repricing_{datetime.now().strftime('%Y%m%d_%H')}.jsonl"
            
            notification_data = {
                "timestamp": datetime.now().isoformat(),
                "type": "repricing_output",
                "data": log_entry
            }
            
            async with aiofiles.open(notification_file, 'a') as f:
                await f.write(json.dumps(notification_data) + '\n')
                
            self.logger.debug("file_notification_written", extra={"file_path": str(notification_file)})
            
        except Exception as e:
            self.logger.warning("file_notification_write_failed", extra={"error": str(e)})


    def _get_amazon_output_list(self) -> list:
        """Get Amazon output fields from configuration."""
        return self.settings.amazon_output_fields

    def _get_amazon_logs(self) -> list:
        """Get Amazon log fields from configuration."""
        return self.settings.amazon_log_fields
