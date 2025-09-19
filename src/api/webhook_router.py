"""Webhook endpoints for Amazon and Walmart integration."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from datetime import datetime, UTC
from loguru import logger
import decimal
from decimal import Decimal
import json
import boto3
from botocore.exceptions import ClientError

from ..services.sqs_consumer import get_sqs_consumer
from ..services.redis_service import redis_service
from ..services.repricing_orchestrator import RepricingOrchestrator
from ..core.config import get_settings
from ..utils.price_reset_utils import (
    reset_seller_products, 
    resume_seller_products, 
    get_seller_reset_rules,
    is_repricing_paused,
    clear_calculated_price
)

router = APIRouter()

# Webhook endpoints for Amazon SP-API notifications


@router.get("/stats")
async def get_stats():
    """Get processing statistics."""
    return {
        "total_processed": 0,
        "successful": 0,
        "failed": 0,
        "average_processing_time_ms": 0,
        "last_reset": datetime.now(UTC).isoformat()
    }


# Removed old /pricing endpoints - replaced with /admin/trigger-reset and /admin/trigger-resume


# Amazon test endpoints removed - use dedicated SQS consumer service for real message processing


@router.get("/sqs/status")
async def get_sqs_status():
    """Get SQS queue status and statistics."""
    try:
        sqs_consumer = get_sqs_consumer()
        stats = sqs_consumer.get_queue_stats()
        
        return {
            "status": "success",
            "queues": stats,
            "checked_at": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get SQS status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sqs/initialize")
async def initialize_sqs_queues():
    """Manually initialize SQS queues in LocalStack."""
    try:
        sqs_consumer = get_sqs_consumer()
        
        return {
            "status": "success",
            "message": "SQS queues initialized",
            "queues": list(sqs_consumer.queue_urls.keys()),
            "initialized_at": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize SQS queues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/walmart/webhook")
async def process_walmart_webhook(
    webhook_data: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Process Walmart webhook for buy box change notifications.
    
    This endpoint simulates processing Walmart webhooks for development testing.
    """
    start_time = datetime.now(UTC)
    
    try:
        # Validate basic webhook structure
        if not webhook_data.get("itemId"):
            raise HTTPException(
                status_code=400,
                detail="Missing required field: itemId"
            )
        
        if not webhook_data.get("sellerId"):
            raise HTTPException(
                status_code=400,
                detail="Missing required field: sellerId"
            )
        
        # Add processing to background task
        background_tasks.add_task(_process_walmart_webhook_async, webhook_data)
        
        logger.info(f"Walmart webhook accepted for item {webhook_data['itemId']}")
        
        return {
            "status": "accepted",
            "message": "Walmart webhook received and queued for processing",
            "item_id": webhook_data["itemId"],
            "seller_id": webhook_data["sellerId"],
            "received_at": start_time.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting Walmart webhook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/pricing/manual")
async def manual_repricing(pricing_data: Dict[str, Any]):
    """Set price to exact provided value for a specific product."""
    asin = pricing_data.get("asin")
    seller_id = pricing_data.get("seller_id")
    sku = pricing_data.get("sku")
    new_price = pricing_data.get("new_price")
    reason = pricing_data.get("reason", "manual_repricing")
    
    # Validate required fields
    if not asin:
        raise HTTPException(status_code=400, detail="asin is required")
    if not seller_id:
        raise HTTPException(status_code=400, detail="seller_id is required")
    if not sku:
        raise HTTPException(status_code=400, detail="sku is required")
    if new_price is None:
        raise HTTPException(status_code=400, detail="new_price is required")
    
    try:
        # Validate new_price is a valid number
        new_price = Decimal(str(new_price))
        if new_price < 0:
            raise HTTPException(status_code=400, detail="new_price must be non-negative")
        
        # Get current product data from Redis
        product_data = await redis_service.get_product_data(asin, seller_id, sku)
        if not product_data:
            raise HTTPException(
                status_code=404,
                detail=f"Product not found: {asin} for seller {seller_id} with SKU {sku}"
            )
        
        # Extract pricing bounds for validation
        min_price = product_data.get("min_price")
        max_price = product_data.get("max_price")
        current_price = product_data.get("listed_price")
        
        # Validate new price is within bounds
        if min_price is not None:
            min_price = Decimal(str(min_price))
            if new_price < min_price:
                raise HTTPException(
                    status_code=400,
                    detail=f"New price {new_price} is below minimum price {min_price}"
                )
        
        if max_price is not None:
            max_price = Decimal(str(max_price))
            if new_price > max_price:
                raise HTTPException(
                    status_code=400,
                    detail=f"New price {new_price} is above maximum price {max_price}"
                )
        
        # Save the manual price to Redis
        price_data = {
            "asin": asin,
            "seller_id": seller_id,
            "sku": sku,
            "old_price": float(current_price) if current_price else None,
            "new_price": float(new_price),
            "min_price": float(min_price) if min_price else None,
            "max_price": float(max_price) if max_price else None,
            "repricer_type": "MANUAL",
            "reason": reason,
            "processing_time_ms": 0,
            "success": True,
            "updated_at": datetime.now(UTC).isoformat()
        }
        
        success = await redis_service.save_calculated_price(
            asin, seller_id, sku, price_data
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save manual price to Redis"
            )
        
        logger.info(
            f"Manual repricing completed: {asin} from {current_price} to {new_price}",
            extra={
                "asin": asin,
                "seller_id": seller_id,
                "sku": sku,
                "old_price": current_price,
                "new_price": float(new_price),
                "reason": reason
            }
        )
        
        return {
            "status": "success",
            "message": "Manual price set successfully",
            "asin": asin,
            "seller_id": seller_id,
            "sku": sku,
            "old_price": float(current_price) if current_price else None,
            "new_price": float(new_price),
            "reason": reason,
            "updated_at": datetime.now(UTC).isoformat()
        }
        
    except HTTPException:
        raise
    except (ValueError, TypeError, decimal.InvalidOperation) as e:
        raise HTTPException(status_code=400, detail=f"Invalid new_price: {str(e)}")
    except Exception as e:
        logger.error(
            f"Manual repricing failed for {asin}: {str(e)}",
            extra={"asin": asin, "seller_id": seller_id, "sku": sku}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# Amazon SQS processing moved to dedicated SQS consumer service


async def _process_walmart_webhook_async(webhook_data: Dict[str, Any]):
    """Background task to process Walmart webhook with real repricing."""
    try:
        # Create Redis service and repricing orchestrator instance
        from ..services.redis_service import RedisService
        redis_service = RedisService()
        orchestrator = RepricingOrchestrator(redis_service)
        
        # Process the webhook using the orchestrator
        result = await orchestrator.process_walmart_webhook(webhook_data)
        
        # Log the result
        if result.get("success", False):
            logger.info(
                f"Walmart webhook processed successfully",
                extra={
                    "item_id": webhook_data.get("itemId", "unknown"),
                    "seller_id": webhook_data.get("sellerId", "unknown"),
                    "price_changed": result.get("price_changed", False),
                    "processing_time_ms": result.get("processing_time_ms")
                }
            )
        else:
            logger.error(
                f"Walmart webhook processing failed: {result.get('error', 'Unknown error')}",
                extra={
                    "item_id": webhook_data.get("itemId", "unknown"),
                    "seller_id": webhook_data.get("sellerId", "unknown"),
                    "error": result.get("error")
                }
            )
        
    except Exception as e:
        logger.error(
            f"Background processing failed for Walmart webhook: {str(e)}",
            extra={"item_id": webhook_data.get("itemId", "unknown")}
        )


# Admin endpoints for MySQL population and data management

@router.post("/admin/populate-from-mysql")
async def populate_from_mysql(
    batch_size: int = Query(1000, description="Number of records to process per batch")
):
    """
    Populate Redis with data from MySQL database.
    This will clear all existing Redis data and repopulate from MySQL.
    """
    logger.info("MySQL to Redis population requested")
    
    try:
        # Run population synchronously
        from scripts.populate_from_mysql import MySQLRedisPopulator
        
        populator = MySQLRedisPopulator()
        results = await populator.populate_all_data(batch_size)
        
        logger.info(
            f"MySQL to Redis population completed",
            extra={
                "strategies_saved": results["strategies_saved"],
                "reset_rules_saved": results["reset_rules_saved"],
                "uk_products_saved": results["uk_products_saved"],
                "us_products_saved": results["us_products_saved"],
                "total_products_saved": results["total_products_saved"],
                "errors_count": len(results["errors"])
            }
        )
        
        return {
            "status": "success",
            "message": "MySQL to Redis population completed",
            "batch_size": batch_size,
            "results": results,
            "completed_at": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"MySQL to Redis population failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Population failed: {str(e)}")


@router.get("/admin/list-entries")
async def list_redis_entries(
    seller_id: Optional[str] = Query(None, description="Filter by seller ID"),
    region: Optional[str] = Query(None, description="Filter by region (uk/us)"),
    asin: Optional[str] = Query(None, description="Filter by specific ASIN"),
    limit: int = Query(100, description="Maximum number of entries to return"),
    offset: int = Query(0, description="Number of entries to skip")
):
    """
    List Redis entries with their strategies and calculated prices.
    Supports filtering by seller ID, region, and ASIN.
    """
    try:
        # Get Redis connection
        redis_client = await redis_service.get_connection()
        
        # Get all ASIN keys
        pattern = f"ASIN_{asin}" if asin else "ASIN_*"
        asin_keys = await redis_client.keys(pattern)
        
        # Apply pagination
        paginated_keys = asin_keys[offset:offset + limit] if not asin else asin_keys
        
        entries = []
        for key in paginated_keys:
            # Extract ASIN from key
            asin_value = key.replace("ASIN_", "")
            
            # Get all fields (seller_id:sku pairs) for this ASIN
            asin_data = await redis_client.hgetall(key)
            
            for field, product_json in asin_data.items():
                if ":" not in field:
                    continue
                    
                product_seller_id, sku = field.split(":", 1)
                
                # Apply seller ID filter
                if seller_id and product_seller_id != seller_id:
                    continue
                
                # Parse product data
                try:
                    product_data = json.loads(product_json)
                except json.JSONDecodeError:
                    continue
                
                # Get strategy information
                strategy_id = product_data.get("strategy_id")
                strategy_data = {}
                if strategy_id:
                    strategy_key = f"strategy.{strategy_id}"
                    strategy_data = await redis_client.hgetall(strategy_key)
                
                # Get calculated prices if any
                calc_price_key = f"CALCULATED_PRICES:{product_seller_id}"
                calculated_prices = await redis_client.hgetall(calc_price_key)
                calculated_price = None
                
                if sku in calculated_prices:
                    try:
                        calculated_price = json.loads(calculated_prices[sku])
                    except json.JSONDecodeError:
                        pass
                
                # Check if repricing is paused for this seller:asin combination
                repricing_paused = await is_repricing_paused(redis_service, product_seller_id, asin_value)
                
                # Determine region based on seller ID pattern
                detected_region = product_data.get("region")
                
                # Apply region filter
                if region and detected_region != region:
                    continue
                
                entry = {
                    "asin": asin_value,
                    "seller_id": product_seller_id,
                    "sku": sku,
                    "region": detected_region,
                    "product_data": product_data,
                    "strategy": strategy_data,
                    "calculated_price": calculated_price,
                    "repricing_paused": repricing_paused
                }
                
                entries.append(entry)
        
        return {
            "status": "success",
            "total_keys_found": len(asin_keys),
            "entries_returned": len(entries),
            "offset": offset,
            "limit": limit,
            "filters_applied": {
                "seller_id": seller_id,
                "region": region,
                "asin": asin
            },
            "entries": entries
        }
        
    except Exception as e:
        logger.error(f"Failed to list Redis entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/send-test-sqs")
async def send_test_sqs_message(
    message_data: Dict[str, Any],
    queue_type: str = Query("any_offer", description="Queue type: any_offer or feed_processing")
):
    """
    Send a test SQS message to the specified queue.
    """
    try:
        settings = get_settings()
        
        # Determine queue URL
        if queue_type == "any_offer":
            queue_url = settings.sqs_queue_url_any_offer
        elif queue_type == "feed_processing":
            queue_url = settings.sqs_queue_url_feed_processing
        else:
            raise HTTPException(status_code=400, detail="Invalid queue_type. Use 'any_offer' or 'feed_processing'")
        
        # Create SQS client
        if settings.aws_endpoint_url:
            # LocalStack
            sqs_client = boto3.client(
                'sqs',
                endpoint_url=settings.aws_endpoint_url,
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
        else:
            # Production AWS
            sqs_client = boto3.client('sqs', region_name=settings.aws_region)
        
        # Send message
        message_body = json.dumps(message_data)
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body
        )
        
        logger.info(f"Test SQS message sent to {queue_type} queue")
        
        return {
            "status": "success",
            "message": "Test SQS message sent successfully",
            "queue_url": queue_url,
            "queue_type": queue_type,
            "message_id": response.get("MessageId"),
            "sent_at": datetime.now(UTC).isoformat()
        }
        
    except ClientError as e:
        error_msg = f"AWS SQS error: {e.response['Error']['Message']}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        logger.error(f"Failed to send test SQS message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/get-reset-rules")
async def get_reset_rules(seller_id: str = Query(..., description="Seller ID to get reset rules for")):
    """
    Get price reset rules for a specific seller.
    """
    try:
        reset_rules = await get_seller_reset_rules(redis_service, seller_id)
        
        if reset_rules is None:
            return {
                "status": "success",
                "seller_id": seller_id,
                "reset_rules": None,
                "message": "No reset rules found for this seller"
            }
        
        return {
            "status": "success",
            "seller_id": seller_id,
            "reset_rules": reset_rules
        }
        
    except Exception as e:
        logger.error(f"Failed to get reset rules for seller {seller_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/trigger-reset")
async def trigger_seller_reset(seller_id: str = Query(..., description="Seller ID to reset prices for")):
    """
    Trigger price reset for all products of a specific seller.
    This will reset all products to their default prices and pause repricing.
    """
    try:
        if not seller_id:
            raise HTTPException(status_code=400, detail="seller_id is required")
        
        logger.info(f"Triggering price reset for seller: {seller_id}")
        
        # Reset all products for this seller
        results = await reset_seller_products(redis_service, seller_id, "admin_manual_reset")
        
        return {
            "status": "success",
            "message": f"Price reset triggered for seller {seller_id}",
            "seller_id": seller_id,
            "results": results,
            "triggered_at": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger reset for seller {seller_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/trigger-resume")
async def trigger_seller_resume(seller_id: str = Query(..., description="Seller ID to resume repricing for")):
    """
    Trigger repricing resume for all products of a specific seller.
    This will remove all repricing pause flags for the seller's products.
    """
    try:
        if not seller_id:
            raise HTTPException(status_code=400, detail="seller_id is required")
        
        logger.info(f"Triggering repricing resume for seller: {seller_id}")
        
        # Resume repricing for all products of this seller
        results = await resume_seller_products(redis_service, seller_id)
        
        return {
            "status": "success",
            "message": f"Repricing resume triggered for seller {seller_id}",
            "seller_id": seller_id,
            "results": results,
            "triggered_at": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger resume for seller {seller_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/clear-calculated-price")
async def clear_product_calculated_price(
    asin: str = Query(..., description="ASIN of the product"),
    seller_id: str = Query(..., description="Seller ID"),
    sku: str = Query(..., description="SKU of the product")
):
    """
    Clear the calculated price for a specific product.
    """
    try:
        success = await clear_calculated_price(redis_service, asin, seller_id, sku)
        
        if success:
            return {
                "status": "success",
                "message": f"Calculated price cleared for {asin}",
                "asin": asin,
                "seller_id": seller_id,
                "sku": sku,
                "cleared_at": datetime.now(UTC).isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clear calculated price")
        
    except Exception as e:
        logger.error(f"Failed to clear calculated price for {asin}:{seller_id}:{sku}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _populate_from_mysql_async(batch_size: int):
    """Background task to populate Redis from MySQL."""
    try:
        from scripts.populate_from_mysql import MySQLRedisPopulator
        
        populator = MySQLRedisPopulator()
        results = await populator.populate_all_data(batch_size)
        
        logger.info(
            f"MySQL to Redis population completed",
            extra={
                "strategies_saved": results["strategies_saved"],
                "uk_products_saved": results["uk_products_saved"],
                "us_products_saved": results["us_products_saved"],
                "total_products_saved": results["total_products_saved"],
                "errors_count": len(results["errors"])
            }
        )
        
    except Exception as e:
        logger.error(f"MySQL to Redis population failed: {str(e)}")
        raise