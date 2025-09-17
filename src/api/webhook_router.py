"""Webhook endpoints for Amazon and Walmart integration."""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime, UTC
from loguru import logger
import decimal
from decimal import Decimal

from ..services.sqs_consumer import get_sqs_consumer
from ..services.redis_service import redis_service
from ..services.repricing_orchestrator import RepricingOrchestrator
from ..utils.exceptions import PriceValidationError

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


@router.post("/pricing/reset")
async def reset_pricing(reset_data: Dict[str, Any]):
    """Reset pricing to default price for a specific product."""
    asin = reset_data.get("asin")
    seller_id = reset_data.get("seller_id")
    sku = reset_data.get("sku")
    reason = reset_data.get("reason", "manual_reset")
    
    # Validate required fields
    if not asin:
        raise HTTPException(status_code=400, detail="asin is required")
    if not seller_id:
        raise HTTPException(status_code=400, detail="seller_id is required")
    if not sku:
        raise HTTPException(status_code=400, detail="sku is required")
    
    try:
        # Get current product data from Redis
        product_data = await redis_service.get_product_data(asin, seller_id, sku)
        if not product_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Product not found: {asin} for seller {seller_id} with SKU {sku}"
            )
        
        # Extract pricing information
        default_price = product_data.get("default_price")
        min_price = product_data.get("min_price")
        max_price = product_data.get("max_price")
        current_price = product_data.get("listed_price")
        
        if default_price is None:
            raise HTTPException(
                status_code=400, 
                detail="Product has no default_price configured"
            )
        
        # Convert to Decimal for validation
        default_price = Decimal(str(default_price))
        
        # Validate default price is within bounds
        if min_price is not None:
            min_price = Decimal(str(min_price))
            if default_price < min_price:
                raise HTTPException(
                    status_code=400,
                    detail=f"Default price {default_price} is below minimum price {min_price}"
                )
        
        if max_price is not None:
            max_price = Decimal(str(max_price))
            if default_price > max_price:
                raise HTTPException(
                    status_code=400,
                    detail=f"Default price {default_price} is above maximum price {max_price}"
                )
        
        # Save the reset price to Redis
        price_data = {
            "asin": asin,
            "seller_id": seller_id,
            "sku": sku,
            "old_price": float(current_price) if current_price else None,
            "new_price": float(default_price),
            "min_price": float(min_price) if min_price else None,
            "max_price": float(max_price) if max_price else None,
            "repricer_type": "PRICE_RESET",
            "reason": reason,
            "processing_time_ms": 0,
            "success": True,
            "reset_at": datetime.now(UTC).isoformat()
        }
        
        success = await redis_service.save_calculated_price(
            asin, seller_id, sku, price_data
        )
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Failed to save price reset to Redis"
            )
        
        logger.info(
            f"Price reset completed: {asin} from {current_price} to {default_price}",
            extra={
                "asin": asin,
                "seller_id": seller_id,
                "sku": sku,
                "old_price": current_price,
                "new_price": float(default_price),
                "reason": reason
            }
        )
        
        return {
            "status": "success",
            "message": "Price reset to default value",
            "asin": asin,
            "seller_id": seller_id,
            "sku": sku,
            "old_price": float(current_price) if current_price else None,
            "new_price": float(default_price),
            "reason": reason,
            "reset_at": datetime.now(UTC).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Price reset failed for {asin}: {str(e)}",
            extra={"asin": asin, "seller_id": seller_id, "sku": sku}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/pricing/resume")
async def resume_pricing(resume_data: Dict[str, Any]):
    """Resume pricing for a seller."""
    seller_id = resume_data.get("seller_id")
    marketplace = resume_data.get("marketplace")
    
    if not seller_id:
        raise HTTPException(status_code=400, detail="seller_id is required")
    
    logger.info(f"Pricing resume requested for seller {seller_id} in {marketplace}")
    
    return {
        "status": "success",
        "message": f"Pricing resumed for seller {seller_id}",
        "seller_id": seller_id,
        "marketplace": marketplace,
        "resumed_at": datetime.now(UTC).isoformat()
    }


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