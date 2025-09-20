"""High-throughput async orchestrator for the complete repricing pipeline."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any, Dict, List

import structlog

from core.config import Settings
from schemas import ProcessedOfferData
from services.message_processor import MessageProcessor
from services.redis_service import RedisService
from services.repricing_engine import RepricingEngine


class RepricingOrchestrator:
    """
    High-throughput orchestrator for the complete 4-step repricing pipeline:
    1. Extract message fields from SQS/webhook
    2. Read product data from Redis
    3. Make repricing decisions
    4. Apply strategies and save to Redis
    """

    def __init__(
        self,
        redis_service: RedisService,
        settings: Settings,
        logger: structlog.BoundLogger,
        message_processor: MessageProcessor,
        repricing_engine: RepricingEngine,
        max_concurrent_workers: int = 50,
        batch_size: int = 100,
    ):
        self.redis = redis_service
        self.settings = settings
        self.logger = logger
        
        # Use dependency-injected services
        self.message_processor = message_processor
        self.repricing_engine = repricing_engine

        # Concurrency settings for high throughput
        self.max_concurrent_workers = max_concurrent_workers
        self.batch_size = batch_size

        # Thread pool for CPU-intensive tasks
        self.thread_pool = ThreadPoolExecutor(max_workers=max_concurrent_workers)

        # Processing metrics
        self.stats = {
            "messages_processed": 0,
            "successful_repricings": 0,
            "failed_repricings": 0,
            "prices_updated": 0,
            "total_processing_time": 0.0,
        }

    async def process_amazon_message(
        self, raw_sqs_message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single Amazon SQS message through the complete pipeline.

        Args:
            raw_sqs_message: Raw SQS message from ANY_OFFER_CHANGED notification

        Returns:
            Processing result with metrics
        """
        start_time = time.time()

        try:
            # Step 1: Extract and validate message fields
            processed_data: ProcessedOfferData = (
                await self.message_processor.process_amazon_sqs_message(raw_sqs_message)
            )

            # Step 2-4: Run through repricing pipeline
            result = await self._run_repricing_pipeline(processed_data)

            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self.stats["messages_processed"] += 1
            self.stats["total_processing_time"] += processing_time

            if result["success"]:
                self.stats["successful_repricings"] += 1
                if result["price_changed"]:
                    self.stats["prices_updated"] += 1
            else:
                self.stats["failed_repricings"] += 1

            self.logger.info(
                "amazon_message_processed",
                asin=processed_data.product_id,
                seller_id=processed_data.seller_id,
                success=result["success"],
                price_changed=result.get("price_changed", False),
                processing_time_ms=processing_time,
            )

            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.stats["failed_repricings"] += 1
            self.stats["messages_processed"] += 1
            self.stats["total_processing_time"] += processing_time

            error_result = {
                "success": False,
                "error": str(e),
                "processing_time_ms": processing_time,
                "message_type": "amazon_sqs",
            }

            self.logger.error(
                "failed_to_process_amazon_message",
                error=str(e), processing_time_ms=processing_time
            )

            return error_result

    async def process_walmart_webhook(
        self, raw_webhook_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single Walmart webhook through the complete pipeline.

        Args:
            raw_webhook_payload: Raw webhook payload from buy box change

        Returns:
            Processing result with metrics
        """
        start_time = time.time()

        try:
            # Step 1: Extract and validate message fields
            processed_data = await self.message_processor.process_walmart_webhook(
                raw_webhook_payload
            )

            # Step 2-4: Run through repricing pipeline
            result = await self._run_repricing_pipeline(processed_data)

            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self.stats["messages_processed"] += 1
            self.stats["total_processing_time"] += processing_time

            if result["success"]:
                self.stats["successful_repricings"] += 1
                if result["price_changed"]:
                    self.stats["prices_updated"] += 1
            else:
                self.stats["failed_repricings"] += 1

            self.logger.info(
                "walmart_webhook_processed",
                item_id=processed_data.product_id,
                seller_id=processed_data.seller_id,
                success=result["success"],
                price_changed=result.get("price_changed", False),
                processing_time_ms=processing_time,
            )

            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.stats["failed_repricings"] += 1
            self.stats["messages_processed"] += 1
            self.stats["total_processing_time"] += processing_time

            error_result = {
                "success": False,
                "error": str(e),
                "processing_time_ms": processing_time,
                "message_type": "walmart_webhook",
            }

            self.logger.error(
                "failed_to_process_walmart_webhook",
                error=str(e), processing_time_ms=processing_time
            )

            return error_result

    async def process_message_batch(
        self, messages: List[Dict[str, Any]], message_type: str = "amazon"
    ) -> List[Dict[str, Any]]:
        """
        Process multiple messages concurrently for high throughput.

        Args:
            messages: List of raw messages to process
            message_type: "amazon" or "walmart"

        Returns:
            List of processing results
        """
        start_time = time.time()

        # Create semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(self.max_concurrent_workers)

        async def process_single_message(message: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                if message_type == "amazon":
                    return await self.process_amazon_message(message)
                else:
                    return await self.process_walmart_webhook(message)

        # Process all messages concurrently
        tasks = [process_single_message(msg) for msg in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions that occurred
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = {
                    "success": False,
                    "error": str(result),
                    "message_index": i,
                    "message_type": message_type,
                }
                processed_results.append(error_result)
                self.logger.error("message_batch_processing_failed", message_index=i, error=str(result))
            else:
                processed_results.append(result)

        batch_time = (time.time() - start_time) * 1000
        successful_count = sum(1 for r in processed_results if r.get("success", False))

        self.logger.info(
            "batch_processed",
            batch_size=len(messages),
            successful_count=successful_count,
            batch_processing_time_ms=batch_time,
            message_type=message_type,
        )

        return processed_results

    async def _run_repricing_pipeline(
        self, processed_data: ProcessedOfferData
    ) -> Dict[str, Any]:
        """
        Run the 3-step repricing pipeline: read data → make decision → calculate price.

        Args:
            processed_data: Processed offer data from step 1

        Returns:
            Pipeline result with success status and metrics
        """
        pipeline_start = time.time()

        try:
            # Step 2: Make repricing decision
            decision = await self.repricing_engine.make_repricing_decision(
                processed_data
            )

            if not decision or not decision.should_reprice:
                return {
                    "success": True,
                    "repricing_needed": False,
                    "reason": decision.reason if decision else "No decision made",
                    "price_changed": False,
                    "pipeline_time_ms": (time.time() - pipeline_start) * 1000,
                }

            # Step 3: Calculate new price using strategies
            calculated_price = await self.repricing_engine.calculate_new_price(decision)

            if not calculated_price:
                return {
                    "success": False,
                    "error": "Price calculation failed",
                    "repricing_needed": True,
                    "price_changed": False,
                    "pipeline_time_ms": (time.time() - pipeline_start) * 1000,
                }

            # Step 4: Save price if it changed
            price_saved = await self.repricing_engine.save_price_if_changed(
                calculated_price
            )

            pipeline_time = (time.time() - pipeline_start) * 1000

            return {
                "success": True,
                "repricing_needed": True,
                "price_changed": calculated_price.price_changed,
                "price_saved": price_saved,
                "old_price": calculated_price.old_price,
                "new_price": calculated_price.new_price,
                "strategy_used": calculated_price.strategy_used,
                "asin": calculated_price.asin,
                "sku": calculated_price.sku,
                "seller_id": calculated_price.seller_id,
                "pipeline_time_ms": pipeline_time,
            }

        except Exception as e:
            pipeline_time = (time.time() - pipeline_start) * 1000

            return {
                "success": False,
                "error": f"Pipeline error: {str(e)}",
                "repricing_needed": True,
                "price_changed": False,
                "pipeline_time_ms": pipeline_time,
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all pipeline components."""
        health_status = {
            "orchestrator": "healthy",
            "redis": await self.redis.health_check(),
            "message_processor": "healthy",
            "repricing_engine": "healthy",
            "stats": self.stats.copy(),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Calculate average processing time
        if self.stats["messages_processed"] > 0:
            avg_time = (
                self.stats["total_processing_time"] / self.stats["messages_processed"]
            )
            health_status["average_processing_time_ms"] = round(avg_time, 2)

        overall_healthy = all(
            status == "healthy" or status is True
            for key, status in health_status.items()
            if key not in ["stats", "timestamp", "average_processing_time_ms"]
        )

        health_status["overall_status"] = "healthy" if overall_healthy else "unhealthy"

        return health_status

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        stats = self.stats.copy()
        stats["timestamp"] = datetime.now(UTC).isoformat()

        if stats["messages_processed"] > 0:
            stats["success_rate"] = round(
                (stats["successful_repricings"] / stats["messages_processed"]) * 100, 2
            )
            stats["average_processing_time_ms"] = round(
                stats["total_processing_time"] / stats["messages_processed"], 2
            )
        else:
            stats["success_rate"] = 0.0
            stats["average_processing_time_ms"] = 0.0

        return stats

    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            "messages_processed": 0,
            "successful_repricings": 0,
            "failed_repricings": 0,
            "prices_updated": 0,
            "total_processing_time": 0.0,
        }

        self.logger.info("processing_statistics_reset")

    async def shutdown(self):
        """Gracefully shutdown the orchestrator."""
        self.logger.info("shutting_down_repricing_orchestrator")

        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)

        # Close Redis connections
        await self.redis.close_connection()

        self.logger.info("orchestrator_shutdown_complete")
