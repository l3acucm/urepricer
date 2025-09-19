"""Celery tasks for scheduled price reset functionality."""

import asyncio
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from loguru import logger

from celery_app import celery_app
from services.redis_service import RedisService


def is_in_reset_window(current_hour: int, reset_hour: int, resume_hour: int) -> bool:
    """
    Check if current hour is within the reset window (repricing should be skipped).
    
    Handles cross-midnight scenarios:
    - If reset_hour=23, resume_hour=3: skip hours 23, 0, 1, 2, 3
    - If reset_hour=1, resume_hour=23: skip hours 1-23 (only allow hour 0)
    - If reset_hour=resume_hour: no reset window (always allow)
    
    Args:
        current_hour: Current hour (0-23)
        reset_hour: Hour to reset prices (0-23)
        resume_hour: Hour to resume repricing (0-23)
        
    Returns:
        True if repricing should be skipped, False if allowed
    """
    if reset_hour == resume_hour:
        return False  # No reset window defined
    
    if reset_hour < resume_hour:
        # Normal case: reset_hour=1, resume_hour=23 -> skip 1-23
        return reset_hour <= current_hour <= resume_hour
    else:
        # Cross-midnight case: reset_hour=23, resume_hour=3 -> skip 23,0,1,2,3
        return current_hour >= reset_hour or current_hour <= resume_hour


async def get_reset_rules_for_user(redis_service: RedisService, user_id: int, market: str) -> Optional[Dict[str, Any]]:
    """Get reset rules for a specific user and market."""
    redis_client = await redis_service.get_connection()
    
    # Try specific market first, then fall back to 'all'
    for market_key in [market, 'all']:
        rule_key = f"reset_rules.{user_id}:{market_key}"
        rule_data = await redis_client.hgetall(rule_key)
        
        if rule_data:
            # Convert string values to appropriate types
            return {
                "price_reset_enabled": rule_data.get("price_reset_enabled", "false").lower() == "true",
                "price_reset_time": int(rule_data.get("price_reset_time", "0")),
                "price_resume_time": int(rule_data.get("price_resume_time", "0")),
                "product_condition": rule_data.get("product_condition", "ALL"),
                "market": rule_data.get("market", market_key)
            }
    
    return None


async def reset_product_to_default(redis_service: RedisService, asin: str, seller_id: str, sku: str, reason: str = "hourly_reset") -> bool:
    """Reset a product's price to its max price value."""
    try:
        # Get current product data
        product_data = await redis_service.get_product_data(asin, seller_id, sku)
        if not product_data:
            logger.warning(f"Product not found for reset: {asin}:{seller_id}:{sku}")
            return False
        
        max_price = product_data.get("max_price")
        current_price = product_data.get("listed_price")
        
        if max_price is None:
            logger.warning(f"No max price configured for {asin}:{seller_id}:{sku}")
            return False
        
        if current_price == max_price:
            logger.debug(f"Price already at max for {asin}:{seller_id}:{sku}")
            return True
        
        # Save the reset price
        price_data = {
            "asin": asin,
            "seller_id": seller_id,
            "sku": sku,
            "old_price": float(current_price) if current_price else None,
            "new_price": float(max_price),
            "strategy_used": "PRICE_RESET",
            "reason": reason,
            "calculated_at": datetime.now(UTC).isoformat(),
            "processing_time_ms": 0
        }
        
        success = await redis_service.save_calculated_price(asin, seller_id, sku, price_data)
        
        if success:
            logger.info(f"Price reset: {asin}:{seller_id}:{sku} from {current_price} to {max_price}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error resetting price for {asin}:{seller_id}:{sku}: {e}")
        return False


async def process_hourly_reset():
    """Main logic for hourly price reset processing."""
    current_time = datetime.now(UTC)
    current_hour = current_time.hour
    
    logger.info(f"Starting hourly price reset check at {current_time.isoformat()} (hour: {current_hour})")
    
    redis_service = RedisService()
    redis_client = await redis_service.get_connection()
    
    reset_count = 0
    skip_count = 0
    error_count = 0
    
    try:
        # Get all product keys
        asin_keys = await redis_client.keys("ASIN_*")
        logger.info(f"Found {len(asin_keys)} products to check")
        
        for asin_key in asin_keys:
            asin = asin_key.replace("ASIN_", "")
            
            # Get all seller:sku pairs for this ASIN
            asin_data = await redis_client.hgetall(asin_key)
            
            for field, product_json in asin_data.items():
                if ":" not in field:
                    continue
                
                try:
                    seller_id, sku = field.split(":", 1)
                    
                    # Extract user ID from seller ID to get reset rules
                    # This assumes seller IDs follow patterns like "UK_SELLER_123" or Amazon seller IDs
                    user_id = None
                    market = "all"
                    
                    if seller_id.startswith("UK_SELLER_"):
                        user_id = int(seller_id.replace("UK_SELLER_", ""))
                        market = "uk"
                    elif seller_id.startswith("US_SELLER_"):
                        user_id = int(seller_id.replace("US_SELLER_", ""))
                        market = "us"
                    elif len(seller_id) > 10:  # Amazon seller ID pattern
                        # For real Amazon seller IDs, we'd need to look them up in the user mapping
                        # For now, skip Amazon sellers in reset logic
                        continue
                    
                    if user_id is None:
                        continue
                    
                    # Get reset rules for this user
                    reset_rules = await get_reset_rules_for_user(redis_service, user_id, market)
                    
                    if not reset_rules or not reset_rules["price_reset_enabled"]:
                        continue
                    
                    reset_hour = reset_rules["price_reset_time"]
                    resume_hour = reset_rules["price_resume_time"]
                    
                    # Check if it's time to reset (only at the exact reset hour)
                    if current_hour == reset_hour:
                        success = await reset_product_to_default(
                            redis_service, asin, seller_id, sku, 
                            f"hourly_reset_{current_hour:02d}:00"
                        )
                        if success:
                            reset_count += 1
                        else:
                            error_count += 1
                    else:
                        # Check if we're in the skip window
                        if is_in_reset_window(current_hour, reset_hour, resume_hour):
                            skip_count += 1
                            logger.debug(f"Skipping repricing for {asin}:{seller_id}:{sku} (in reset window {reset_hour}-{resume_hour})")
                
                except Exception as e:
                    logger.error(f"Error processing product {asin}:{field}: {e}")
                    error_count += 1
                    continue
    
    except Exception as e:
        logger.error(f"Fatal error in hourly reset: {e}")
        raise
    
    finally:
        await redis_service.close_connection()
    
    logger.info(f"Hourly reset completed: {reset_count} resets, {skip_count} skips, {error_count} errors")
    
    return {
        "reset_count": reset_count,
        "skip_count": skip_count,
        "error_count": error_count,
        "processed_at": current_time.isoformat(),
        "hour": current_hour
    }


@celery_app.task(bind=True, name="src.tasks.price_reset.check_and_reset_prices")
def check_and_reset_prices(self):
    """Celery task to check reset rules and reset prices if needed."""
    try:
        # Run the async function
        result = asyncio.run(process_hourly_reset())
        
        logger.info(f"Hourly price reset task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Hourly price reset task failed: {e}")
        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=60, max_retries=3)


def should_skip_repricing(user_id: int, market: str, current_time: Optional[datetime] = None) -> bool:
    """
    Synchronous helper function to check if repricing should be skipped.
    Used by the repricing engine during normal operation.
    
    Args:
        user_id: User ID to check reset rules for
        market: Market (uk/us/all) 
        current_time: Current time (defaults to now)
        
    Returns:
        True if repricing should be skipped, False if allowed
    """
    if current_time is None:
        current_time = datetime.now(UTC)
    
    current_hour = current_time.hour
    
    try:
        # This would need to be adapted to work synchronously
        # For now, return False to allow repricing
        # TODO: Implement sync version or cache reset rules
        return False
        
    except Exception as e:
        logger.error(f"Error checking reset rules for user {user_id}: {e}")
        return False  # Default to allowing repricing on error