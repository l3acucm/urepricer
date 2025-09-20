"""Celery tasks for scheduled price reset functionality."""

import asyncio
from datetime import UTC, datetime
from typing import Any, Dict, Optional

import structlog

from celery_app import celery_app
from containers import Container
from services.redis_service import RedisService

# Module-level logger for Celery tasks
logger = structlog.get_logger(__name__)

# Module-level DI container for Celery tasks
container = Container()

# In-memory cache for reset rules (sync access)
_reset_rules_cache = {}
_cache_last_updated = None
_cache_ttl_minutes = 5  # Cache TTL in minutes


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


async def get_reset_rules_for_user(
    redis_service: RedisService, user_id: int, market: str
) -> Optional[Dict[str, Any]]:
    """Get reset rules for a specific user and market."""
    redis_client = await redis_service.get_connection()

    # Try specific market first, then fall back to 'all'
    for market_key in [market, "all"]:
        rule_key = f"reset_rules.{user_id}:{market_key}"
        rule_data = await redis_client.hgetall(rule_key)

        if rule_data:
            # Convert string values to appropriate types
            return {
                "price_reset_enabled": rule_data.get(
                    "price_reset_enabled", "false"
                ).lower()
                == "true",
                "price_reset_time": int(rule_data.get("price_reset_time", "0")),
                "price_resume_time": int(rule_data.get("price_resume_time", "0")),
                "product_condition": rule_data.get("product_condition", "ALL"),
                "market": rule_data.get("market", market_key),
            }

    return None


async def reset_product_to_default(
    redis_service: RedisService,
    asin: str,
    seller_id: str,
    sku: str,
    reason: str = "hourly_reset",
) -> bool:
    """Reset a product's price to its default price value."""
    try:
        # Get current product data
        product_data = await redis_service.get_product_data(asin, seller_id, sku)
        if not product_data:
            logger.warning(f"Product not found for reset: {asin}:{seller_id}:{sku}")
            return False

        default_price = product_data.get("default_price")
        current_price = product_data.get("listed_price")

        if default_price is None:
            logger.warning(f"No default price configured for {asin}:{seller_id}:{sku}")
            return False

        if current_price == default_price:
            logger.debug(f"Price already at default for {asin}:{seller_id}:{sku}")
            return True

        # Save the reset price
        price_data = {
            "asin": asin,
            "seller_id": seller_id,
            "sku": sku,
            "old_price": float(current_price) if current_price else None,
            "new_price": float(default_price),
            "strategy_used": "PRICE_RESET",
            "reason": reason,
            "calculated_at": datetime.now(UTC).isoformat(),
            "processing_time_ms": 0,
        }

        success = await redis_service.save_calculated_price(
            asin, seller_id, sku, price_data
        )

        if success:
            logger.info("price_reset_successfully_applied",
                       asin=asin, seller_id=seller_id, sku=sku,
                       old_price=current_price, new_price=default_price,
                       price_change=float(default_price) - float(current_price) if current_price else None,
                       strategy_used="PRICE_RESET", reason=reason,
                       calculated_at=datetime.now(UTC).isoformat(),
                       processing_time_ms=0)

        return success

    except Exception as e:
        logger.error("error_resetting_price", 
                    asin=asin, seller_id=seller_id, sku=sku,
                    reason=reason, error=str(e), error_type=type(e).__name__)
        return False


async def process_hourly_reset():
    """Main logic for hourly price reset processing."""
    current_time = datetime.now(UTC)
    _current_hour = current_time.hour

    logger.info(
        f"Starting hourly price reset check at {current_time.isoformat()} (hour: {_current_hour})"
    )

    # Get Redis service from DI container
    redis_service = container.redis_service()
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
                    reset_rules = await get_reset_rules_for_user(
                        redis_service, user_id, market
                    )

                    if not reset_rules or not reset_rules["price_reset_enabled"]:
                        continue

                    reset_hour = reset_rules["price_reset_time"]
                    resume_hour = reset_rules["price_resume_time"]

                    # Check if it's time to reset (only at the exact reset hour)
                    if _current_hour == reset_hour:
                        success = await reset_product_to_default(
                            redis_service,
                            asin,
                            seller_id,
                            sku,
                            f"hourly_reset_{_current_hour:02d}:00",
                        )
                        if success:
                            reset_count += 1
                        else:
                            error_count += 1
                    else:
                        # Check if we're in the skip window
                        if is_in_reset_window(_current_hour, reset_hour, resume_hour):
                            skip_count += 1
                            logger.debug(
                                f"Skipping repricing for {asin}:{seller_id}:{sku} (in reset window {reset_hour}-{resume_hour})"
                            )

                except Exception as e:
                    logger.error(f"Error processing product {asin}:{field}: {e}")
                    error_count += 1
                    continue

    except Exception as e:
        logger.error(f"Fatal error in hourly reset: {e}")
        raise

    finally:
        await redis_service.close_connection()

    logger.info(
        f"Hourly reset completed: {reset_count} resets, {skip_count} skips, {error_count} errors"
    )

    return {
        "reset_count": reset_count,
        "skip_count": skip_count,
        "error_count": error_count,
        "processed_at": current_time.isoformat(),
        "hour": _current_hour,
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


def should_skip_repricing(
    user_id: int, market: str, current_time: Optional[datetime] = None
) -> bool:
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

    _current_hour = current_time.hour

    try:
        # Use cached reset rules for synchronous access
        rules = _get_cached_reset_rules(user_id, market)
        
        if not rules or not rules.get("price_reset_enabled", False):
            return False  # No rules or rules disabled
        
        reset_hour = rules.get("price_reset_time", 0)
        resume_hour = rules.get("price_resume_time", 0)
        
        # Check if we're in the reset window
        skip = is_in_reset_window(_current_hour, reset_hour, resume_hour)
        
        if skip:
            logger.info(
                f"Skipping repricing for user {user_id} (market: {market}) - in reset window ({reset_hour:02d}:00-{resume_hour:02d}:00)"
            )
        
        return skip

    except Exception as e:
        logger.error(f"Error checking reset rules for user {user_id}: {e}")
        return False  # Default to allowing repricing on error


def _get_cached_reset_rules(user_id: int, market: str) -> Optional[Dict[str, Any]]:
    """Get reset rules from cache or refresh cache if stale."""
    global _reset_rules_cache, _cache_last_updated
    
    # Check if cache needs refresh
    current_time = datetime.now(UTC)
    if (_cache_last_updated is None or 
        (current_time - _cache_last_updated).total_seconds() > _cache_ttl_minutes * 60):
        
        # Refresh cache asynchronously in background
        try:
            import threading
            threading.Thread(target=_refresh_reset_rules_cache, daemon=True).start()
        except Exception as e:
            logger.warning(f"Failed to start cache refresh thread: {e}")
    
    # Try to get rules from cache
    cache_key = f"{user_id}:{market}"
    if cache_key in _reset_rules_cache:
        return _reset_rules_cache[cache_key]
    
    # Try fallback to 'all' market
    fallback_key = f"{user_id}:all"
    if fallback_key in _reset_rules_cache:
        return _reset_rules_cache[fallback_key]
    
    return None


def _refresh_reset_rules_cache():
    """Refresh the reset rules cache (runs in background thread)."""
    global _reset_rules_cache, _cache_last_updated
    
    try:
        import asyncio

        import redis.asyncio as redis

        from core.config import get_settings
        
        settings = get_settings()
        
        # Create event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def fetch_rules():
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                decode_responses=True,
            )
            
            try:
                # Get all reset rule keys
                rule_keys = await redis_client.keys("reset_rules.*")
                new_cache = {}
                
                for rule_key in rule_keys:
                    rule_data = await redis_client.hgetall(rule_key)
                    if rule_data:
                        # Extract user_id:market from key
                        cache_key = rule_key.replace("reset_rules.", "")
                        
                        # Convert string values to appropriate types
                        processed_rules = {
                            "price_reset_enabled": rule_data.get("price_reset_enabled", "false").lower() == "true",
                            "price_reset_time": int(rule_data.get("price_reset_time", "0")),
                            "price_resume_time": int(rule_data.get("price_resume_time", "0")),
                            "product_condition": rule_data.get("product_condition", "ALL"),
                            "market": rule_data.get("market", "all"),
                        }
                        new_cache[cache_key] = processed_rules
                
                # Update global cache atomically
                _reset_rules_cache.clear()
                _reset_rules_cache.update(new_cache)
                _cache_last_updated = datetime.now(UTC)
                
                logger.info(f"Reset rules cache refreshed with {len(new_cache)} rules")
                
            finally:
                await redis_client.close()
        
        # Run the async function
        loop.run_until_complete(fetch_rules())
        
    except Exception as e:
        logger.error(f"Failed to refresh reset rules cache: {e}")
    finally:
        try:
            loop.close()
        except Exception:
            pass


async def refresh_reset_rules_cache_async():
    """Async version to refresh cache during startup."""
    global _reset_rules_cache, _cache_last_updated
    
    try:
        redis_service = container.redis_service()
        redis_client = await redis_service.get_connection()
        
        # Get all reset rule keys
        rule_keys = await redis_client.keys("reset_rules.*")
        new_cache = {}
        
        for rule_key in rule_keys:
            rule_data = await redis_client.hgetall(rule_key)
            if rule_data:
                # Extract user_id:market from key
                cache_key = rule_key.replace("reset_rules.", "")
                
                # Convert string values to appropriate types
                processed_rules = {
                    "price_reset_enabled": rule_data.get("price_reset_enabled", "false").lower() == "true",
                    "price_reset_time": int(rule_data.get("price_reset_time", "0")),
                    "price_resume_time": int(rule_data.get("price_resume_time", "0")),
                    "product_condition": rule_data.get("product_condition", "ALL"),
                    "market": rule_data.get("market", "all"),
                }
                new_cache[cache_key] = processed_rules
        
        # Update global cache atomically
        _reset_rules_cache.clear()
        _reset_rules_cache.update(new_cache)
        _cache_last_updated = datetime.now(UTC)
        
        logger.info(f"Reset rules cache initialized with {len(new_cache)} rules")
        
    except Exception as e:
        logger.error(f"Failed to initialize reset rules cache: {e}")
        # Set empty cache to prevent repeated failures
        _reset_rules_cache.clear()
        _cache_last_updated = datetime.now(UTC)
