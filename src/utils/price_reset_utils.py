"""Shared utilities for price reset/resume functionality."""

from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from loguru import logger

from services.redis_service import RedisService
from tasks.price_reset import get_reset_rules_for_user, reset_product_to_default


async def set_repricing_paused(redis_service: RedisService, seller_id: str, asin: str, paused: bool) -> bool:
    """Set or unset the repricing_paused flag for a specific seller:asin combination."""
    try:
        redis_client = await redis_service.get_connection()
        pause_key = f"repricing_paused:{seller_id}:{asin}"
        
        if paused:
            # Set the flag with current timestamp
            await redis_client.set(pause_key, datetime.now(UTC).isoformat())
            logger.info(f"Repricing paused for {seller_id}:{asin}")
        else:
            # Remove the flag
            await redis_client.delete(pause_key)
            logger.info(f"Repricing resumed for {seller_id}:{asin}")
        
        return True
    except Exception as e:
        logger.error(f"Error setting repricing_paused flag for {seller_id}:{asin}: {e}")
        return False


async def is_repricing_paused(redis_service: RedisService, seller_id: str, asin: str) -> bool:
    """Check if repricing is paused for a specific seller:asin combination."""
    try:
        redis_client = await redis_service.get_connection()
        pause_key = f"repricing_paused:{seller_id}:{asin}"
        
        result = await redis_client.get(pause_key)
        return result is not None
    except Exception as e:
        logger.error(f"Error checking repricing_paused flag for {seller_id}:{asin}: {e}")
        return False


async def reset_seller_products(redis_service: RedisService, seller_id: str, reason: str = "manual_reset") -> Dict[str, Any]:
    """Reset all products for a specific seller to their default prices and pause repricing."""
    results = {
        "reset_count": 0,
        "pause_count": 0,
        "error_count": 0,
        "errors": [],
        "processed_products": []
    }
    
    try:
        redis_client = await redis_service.get_connection()
        
        # Get all ASIN keys
        asin_keys = await redis_client.keys("ASIN_*")
        
        for asin_key in asin_keys:
            asin = asin_key.replace("ASIN_", "")
            
            # Get all seller:sku pairs for this ASIN
            asin_data = await redis_client.hgetall(asin_key)
            
            for field, product_json in asin_data.items():
                if ":" not in field:
                    continue
                
                try:
                    field_seller_id, sku = field.split(":", 1)
                    
                    if field_seller_id != seller_id:
                        continue
                    
                    # Reset product to default price
                    reset_success = await reset_product_to_default(
                        redis_service, asin, seller_id, sku, reason
                    )
                    
                    if reset_success:
                        results["reset_count"] += 1
                    else:
                        results["error_count"] += 1
                        results["errors"].append(f"Failed to reset {asin}:{seller_id}:{sku}")
                    
                    # Set repricing paused flag
                    pause_success = await set_repricing_paused(redis_service, seller_id, asin, True)
                    
                    if pause_success:
                        results["pause_count"] += 1
                    else:
                        results["error_count"] += 1
                        results["errors"].append(f"Failed to pause repricing for {asin}:{seller_id}")
                    
                    results["processed_products"].append({
                        "asin": asin,
                        "seller_id": seller_id,
                        "sku": sku,
                        "reset_success": reset_success,
                        "pause_success": pause_success
                    })
                
                except Exception as e:
                    logger.error(f"Error processing product {asin}:{field} for seller {seller_id}: {e}")
                    results["error_count"] += 1
                    results["errors"].append(f"Error processing {asin}:{field}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Fatal error resetting products for seller {seller_id}: {e}")
        results["errors"].append(f"Fatal error: {str(e)}")
        results["error_count"] += 1
    
    logger.info(f"Reset completed for seller {seller_id}: {results['reset_count']} resets, {results['pause_count']} pauses, {results['error_count']} errors")
    
    return results


async def resume_seller_products(redis_service: RedisService, seller_id: str) -> Dict[str, Any]:
    """Resume repricing for all products of a specific seller by removing pause flags."""
    results = {
        "resume_count": 0,
        "error_count": 0,
        "errors": [],
        "processed_products": []
    }
    
    try:
        redis_client = await redis_service.get_connection()
        
        # Get all repricing_paused keys for this seller
        pause_keys = await redis_client.keys(f"repricing_paused:{seller_id}:*")
        
        for pause_key in pause_keys:
            try:
                # Extract ASIN from the key
                asin = pause_key.replace(f"repricing_paused:{seller_id}:", "")
                
                # Remove the pause flag
                success = await set_repricing_paused(redis_service, seller_id, asin, False)
                
                if success:
                    results["resume_count"] += 1
                else:
                    results["error_count"] += 1
                    results["errors"].append(f"Failed to resume repricing for {asin}:{seller_id}")
                
                results["processed_products"].append({
                    "asin": asin,
                    "seller_id": seller_id,
                    "resume_success": success
                })
            
            except Exception as e:
                logger.error(f"Error processing pause key {pause_key}: {e}")
                results["error_count"] += 1
                results["errors"].append(f"Error processing {pause_key}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Fatal error resuming products for seller {seller_id}: {e}")
        results["errors"].append(f"Fatal error: {str(e)}")
        results["error_count"] += 1
    
    logger.info(f"Resume completed for seller {seller_id}: {results['resume_count']} resumes, {results['error_count']} errors")
    
    return results


async def clear_calculated_price(redis_service: RedisService, asin: str, seller_id: str, sku: str) -> bool:
    """Clear/remove the calculated price for a specific product."""
    try:
        redis_client = await redis_service.get_connection()
        calc_price_key = f"CALCULATED_PRICES:{seller_id}"
        
        # Remove the SKU field from the calculated prices hash
        result = await redis_client.hdel(calc_price_key, sku)
        
        if result:
            logger.info(f"Calculated price cleared for {asin}:{seller_id}:{sku}")
            return True
        else:
            logger.info(f"No calculated price found to clear for {asin}:{seller_id}:{sku}")
            return True  # Return True since the desired state is achieved
            
    except Exception as e:
        logger.error(f"Error clearing calculated price for {asin}:{seller_id}:{sku}: {e}")
        return False


async def get_seller_reset_rules(redis_service: RedisService, seller_id: str) -> Optional[Dict[str, Any]]:
    """Get reset rules for a seller based on their seller ID pattern."""
    try:
        # Extract user ID and market from seller ID
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
            # For now, return None for Amazon sellers
            return None
        
        if user_id is None:
            return None
        
        # Get reset rules for this user
        reset_rules = await get_reset_rules_for_user(redis_service, user_id, market)
        
        return reset_rules
    
    except Exception as e:
        logger.error(f"Error getting reset rules for seller {seller_id}: {e}")
        return None