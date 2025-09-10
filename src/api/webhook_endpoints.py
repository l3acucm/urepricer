"""FastAPI endpoints for Walmart webhook processing."""

from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, UTC
from loguru import logger

from ..services.repricing_orchestrator import RepricingOrchestrator
from ..services.redis_service import RedisService


# Global services (will be initialized on startup)
redis_service = None
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    global redis_service, orchestrator
    
    # Startup
    redis_service = RedisService()
    orchestrator = RepricingOrchestrator(
        redis_service=redis_service,
        max_concurrent_workers=100,  # High concurrency for webhooks
        batch_size=50
    )
    logger.info("FastAPI application started with repricing services")
    
    yield
    
    # Shutdown
    if orchestrator:
        await orchestrator.shutdown()
    logger.info("FastAPI application shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="Arbitrage Hero Repricer API",
    description="High-throughput repricing API for Amazon and Walmart",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_orchestrator() -> RepricingOrchestrator:
    """Dependency to get orchestrator instance."""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    return orchestrator


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Arbitrage Hero Repricer API", "status": "running"}


@app.get("/health")
async def health_check(orchestrator: RepricingOrchestrator = Depends(get_orchestrator)):
    """Health check endpoint."""
    health_status = await orchestrator.health_check()
    
    status_code = 200 if health_status["overall_status"] == "healthy" else 503
    
    return JSONResponse(
        status_code=status_code,
        content=health_status
    )


@app.get("/stats")
async def get_stats(orchestrator: RepricingOrchestrator = Depends(get_orchestrator)):
    """Get processing statistics."""
    return orchestrator.get_processing_stats()


@app.post("/stats/reset")
async def reset_stats(orchestrator: RepricingOrchestrator = Depends(get_orchestrator)):
    """Reset processing statistics."""
    orchestrator.reset_stats()
    return {"message": "Statistics reset successfully"}


@app.post("/walmart/webhook")
async def process_walmart_webhook(
    webhook_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    orchestrator: RepricingOrchestrator = Depends(get_orchestrator)
):
    """
    Process Walmart buy box changed webhook.
    
    This endpoint receives Walmart webhooks about buy box changes and processes them
    through the complete repricing pipeline asynchronously for high throughput.
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
        
        # Add processing metadata
        webhook_data["webhook_received_at"] = start_time.isoformat()
        
        # Process webhook in background for immediate response
        background_tasks.add_task(
            _process_walmart_webhook_async,
            webhook_data,
            orchestrator
        )
        
        # Return immediate response
        response = {
            "status": "accepted",
            "message": "Walmart webhook received and queued for processing",
            "item_id": webhook_data["itemId"],
            "seller_id": webhook_data["sellerId"],
            "received_at": start_time.isoformat()
        }
        
        logger.info(
            f"Walmart webhook accepted for item {webhook_data['itemId']}",
            extra={
                "item_id": webhook_data["itemId"],
                "seller_id": webhook_data["sellerId"],
                "event_type": webhook_data.get("eventType", "unknown")
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting Walmart webhook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/walmart/webhook/batch")
async def process_walmart_webhook_batch(
    webhooks: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    orchestrator: RepricingOrchestrator = Depends(get_orchestrator)
):
    """
    Process multiple Walmart webhooks in batch for higher throughput.
    
    This endpoint allows processing multiple webhook notifications at once,
    which is more efficient for high-volume scenarios.
    """
    start_time = datetime.now(UTC)
    
    try:
        if not webhooks:
            raise HTTPException(
                status_code=400,
                detail="Empty webhook batch"
            )
        
        if len(webhooks) > 1000:  # Reasonable batch size limit
            raise HTTPException(
                status_code=400,
                detail="Batch size too large (max 1000 webhooks)"
            )
        
        # Validate all webhooks in batch
        for i, webhook in enumerate(webhooks):
            if not webhook.get("itemId"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Webhook {i}: Missing required field itemId"
                )
            if not webhook.get("sellerId"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Webhook {i}: Missing required field sellerId"
                )
            
            # Add batch metadata
            webhook["batch_received_at"] = start_time.isoformat()
            webhook["batch_index"] = i
        
        # Process batch in background
        background_tasks.add_task(
            _process_walmart_webhook_batch_async,
            webhooks,
            orchestrator
        )
        
        # Return immediate response
        response = {
            "status": "accepted",
            "message": f"Batch of {len(webhooks)} Walmart webhooks accepted for processing",
            "batch_size": len(webhooks),
            "received_at": start_time.isoformat()
        }
        
        logger.info(
            f"Walmart webhook batch accepted: {len(webhooks)} webhooks",
            extra={
                "batch_size": len(webhooks),
                "first_item_id": webhooks[0]["itemId"] if webhooks else "none"
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting Walmart webhook batch: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/amazon/test-sqs")
async def process_test_amazon_sqs(
    sqs_message: Dict[str, Any],
    background_tasks: BackgroundTasks,
    orchestrator: RepricingOrchestrator = Depends(get_orchestrator)
):
    """
    Test endpoint for Amazon SQS message processing.
    
    This is primarily for testing the Amazon SQS processing logic.
    In production, SQS messages would be consumed by the SQS consumer service.
    """
    start_time = datetime.now(UTC)
    
    try:
        # Validate basic SQS message structure
        if not sqs_message.get("Body"):
            raise HTTPException(
                status_code=400,
                detail="Missing required field: Body"
            )
        
        # Add processing metadata
        sqs_message["test_received_at"] = start_time.isoformat()
        
        # Process SQS message in background
        background_tasks.add_task(
            _process_amazon_sqs_async,
            sqs_message,
            orchestrator
        )
        
        # Return immediate response
        response = {
            "status": "accepted",
            "message": "Amazon SQS test message received and queued for processing",
            "message_id": sqs_message.get("MessageId", "unknown"),
            "received_at": start_time.isoformat()
        }
        
        logger.info(
            f"Amazon SQS test message accepted: {sqs_message.get('MessageId', 'unknown')}",
            extra={
                "message_id": sqs_message.get("MessageId", "unknown")
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting Amazon SQS test message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def _process_walmart_webhook_async(
    webhook_data: Dict[str, Any],
    orchestrator: RepricingOrchestrator
):
    """Background task to process single Walmart webhook."""
    try:
        result = await orchestrator.process_walmart_webhook(webhook_data)
        
        # Log the result (could also send to monitoring system)
        if result["success"]:
            logger.info(
                f"Walmart webhook processed successfully",
                extra={
                    "item_id": webhook_data["itemId"],
                    "price_changed": result.get("price_changed", False),
                    "processing_time_ms": result.get("processing_time_ms")
                }
            )
        else:
            logger.error(
                f"Walmart webhook processing failed: {result.get('error')}",
                extra={
                    "item_id": webhook_data["itemId"],
                    "error": result.get("error")
                }
            )
            
    except Exception as e:
        logger.error(
            f"Background processing failed for Walmart webhook: {str(e)}",
            extra={"item_id": webhook_data.get("itemId", "unknown")}
        )


async def _process_walmart_webhook_batch_async(
    webhooks: List[Dict[str, Any]],
    orchestrator: RepricingOrchestrator
):
    """Background task to process batch of Walmart webhooks."""
    try:
        results = await orchestrator.process_message_batch(webhooks, "walmart")
        
        # Log batch results
        successful = sum(1 for r in results if r.get("success", False))
        
        logger.info(
            f"Walmart webhook batch processed: {successful}/{len(webhooks)} successful",
            extra={
                "batch_size": len(webhooks),
                "successful_count": successful,
                "failed_count": len(webhooks) - successful
            }
        )
        
    except Exception as e:
        logger.error(
            f"Background batch processing failed for Walmart webhooks: {str(e)}",
            extra={"batch_size": len(webhooks)}
        )


async def _process_amazon_sqs_async(
    sqs_message: Dict[str, Any],
    orchestrator: RepricingOrchestrator
):
    """Background task to process single Amazon SQS message."""
    try:
        result = await orchestrator.process_amazon_message(sqs_message)
        
        # Log the result
        if result["success"]:
            logger.info(
                f"Amazon SQS message processed successfully",
                extra={
                    "message_id": sqs_message.get("MessageId", "unknown"),
                    "price_changed": result.get("price_changed", False),
                    "processing_time_ms": result.get("processing_time_ms")
                }
            )
        else:
            logger.error(
                f"Amazon SQS message processing failed: {result.get('error')}",
                extra={
                    "message_id": sqs_message.get("MessageId", "unknown"),
                    "error": result.get("error")
                }
            )
            
    except Exception as e:
        logger.error(
            f"Background processing failed for Amazon SQS message: {str(e)}",
            extra={"message_id": sqs_message.get("MessageId", "unknown")}
        )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions."""
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}: {str(exc)}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params)
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now(UTC).isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run with high concurrency settings for production
    uvicorn.run(
        "webhook_endpoints:app",
        host="0.0.0.0",
        port=8000,
        workers=4,  # Multiple worker processes
        loop="uvloop",  # High-performance event loop
        access_log=False,  # Disable access logs for performance
        log_config=None  # Use loguru instead of uvicorn's logger
    )