"""Webhook endpoints for Amazon and Walmart integration."""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime, UTC
from loguru import logger

from ..services.sqs_consumer import get_sqs_consumer

router = APIRouter()

# Simplified webhook endpoints for quickstart compatibility


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
    """Reset pricing for a seller."""
    seller_id = reset_data.get("seller_id")
    marketplace = reset_data.get("marketplace")
    reason = reset_data.get("reason", "manual_reset")
    
    if not seller_id:
        raise HTTPException(status_code=400, detail="seller_id is required")
    
    logger.info(f"Pricing reset requested for seller {seller_id} in {marketplace}: {reason}")
    
    return {
        "status": "success",
        "message": f"Pricing reset for seller {seller_id}",
        "seller_id": seller_id,
        "marketplace": marketplace,
        "reason": reason,
        "reset_at": datetime.now(UTC).isoformat()
    }


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
        await sqs_consumer._create_default_queues()
        
        # Refresh the queue discovery
        await sqs_consumer._discover_queues()
        
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


# Amazon SQS processing moved to dedicated SQS consumer service


async def _process_walmart_webhook_async(webhook_data: Dict[str, Any]):
    """Background task to process Walmart webhook."""
    try:
        item_id = webhook_data.get("itemId", "unknown")
        seller_id = webhook_data.get("sellerId", "unknown")
        
        # Simulate processing time
        import asyncio
        await asyncio.sleep(0.1)
        
        logger.info(
            f"Walmart webhook processed successfully: {item_id}",
            extra={"item_id": item_id, "seller_id": seller_id}
        )
        
    except Exception as e:
        logger.error(
            f"Background processing failed for Walmart webhook: {str(e)}",
            extra={"item_id": webhook_data.get("itemId", "unknown")}
        )