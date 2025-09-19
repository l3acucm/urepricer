"""Utilities for price reset and resume time validation."""

import asyncio
from datetime import datetime, UTC
from typing import Optional, Dict, Any
from loguru import logger

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


def extract_user_info_from_seller_id(seller_id: str) -> tuple[Optional[int], str]:
    """
    Extract user ID and market from seller ID.
    
    Args:
        seller_id: Seller ID (e.g., "UK_SELLER_123", "US_SELLER_456", "A1234567890123")
        
    Returns:
        Tuple of (user_id, market) or (None, "unknown") if extraction fails
    """
    if seller_id.startswith("UK_SELLER_"):
        try:
            user_id = int(seller_id.replace("UK_SELLER_", ""))
            return user_id, "uk"
        except ValueError:
            return None, "unknown"
    elif seller_id.startswith("US_SELLER_"):
        try:
            user_id = int(seller_id.replace("US_SELLER_", ""))
            return user_id, "us"
        except ValueError:
            return None, "unknown"
    elif len(seller_id) > 10:  # Amazon seller ID pattern
        # For real Amazon seller IDs, we'd need to look them up in the user mapping
        # For now, return None to indicate no reset rules apply
        return None, "amazon"
    else:
        return None, "unknown"


async def should_skip_repricing_async(seller_id: str, current_time: Optional[datetime] = None) -> bool:
    """
    Check if repricing should be skipped based on reset rules.
    
    Args:
        seller_id: Seller ID to check
        current_time: Current time (defaults to now)
        
    Returns:
        True if repricing should be skipped, False if allowed
    """
    if current_time is None:
        current_time = datetime.now(UTC)
    
    current_hour = current_time.hour
    
    # Extract user info from seller ID
    user_id, market = extract_user_info_from_seller_id(seller_id)
    
    if user_id is None:
        # No reset rules apply for this seller
        return False
    
    try:
        redis_service = RedisService()
        reset_rules = await get_reset_rules_for_user(redis_service, user_id, market)
        
        if not reset_rules or not reset_rules["price_reset_enabled"]:
            return False
        
        reset_hour = reset_rules["price_reset_time"]
        resume_hour = reset_rules["price_resume_time"]
        
        # Check if we're in the reset window
        skip = is_in_reset_window(current_hour, reset_hour, resume_hour)
        
        if skip:
            logger.info(f"Skipping repricing for seller {seller_id} - in reset window ({reset_hour:02d}:00-{resume_hour:02d}:00)")
        
        return skip
        
    except Exception as e:
        logger.error(f"Error checking reset rules for seller {seller_id}: {e}")
        return False  # Default to allowing repricing on error


def should_skip_repricing_sync(seller_id: str, current_time: Optional[datetime] = None) -> bool:
    """
    Synchronous wrapper for reset rule checking.
    
    Args:
        seller_id: Seller ID to check
        current_time: Current time (defaults to now)
        
    Returns:
        True if repricing should be skipped, False if allowed
    """
    try:
        # Run the async function in a new event loop
        return asyncio.run(should_skip_repricing_async(seller_id, current_time))
    except Exception as e:
        logger.error(f"Error in sync reset rule check for seller {seller_id}: {e}")
        return False  # Default to allowing repricing on error