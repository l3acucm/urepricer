"""Amazon SQS consumer for ANY_OFFER_CHANGED notifications."""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from loguru import logger
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from ..services.repricing_orchestrator import RepricingOrchestrator
from ..services.redis_service import RedisService
from ..core.config import get_settings


class SQSConsumer:
    """
    High-throughput SQS consumer for Amazon ANY_OFFER_CHANGED notifications.
    
    This consumer polls SQS queues continuously and processes messages through
    the repricing pipeline with proper error handling and dead letter queue support.
    """
    
    def __init__(
        self,
        orchestrator: RepricingOrchestrator,
        max_concurrent_messages: int = 50,
        batch_size: int = 10,
        visibility_timeout: int = 300,  # 5 minutes
        wait_time_seconds: int = 20,    # Long polling
        max_retries: int = 3
    ):
        self.settings = get_settings()
        self.orchestrator = orchestrator
        self.logger = logger.bind(service="sqs_consumer")
        
        # SQS settings
        self.batch_size = min(batch_size, 10)  # SQS limit is 10
        self.visibility_timeout = visibility_timeout
        self.wait_time_seconds = wait_time_seconds
        self.max_retries = max_retries
        self.max_concurrent_messages = max_concurrent_messages
        
        # Initialize SQS client
        self.sqs = boto3.client(
            'sqs',
            region_name=getattr(self.settings, 'aws_region', 'us-east-1'),
            aws_access_key_id=getattr(self.settings, 'aws_access_key_id', None),
            aws_secret_access_key=getattr(self.settings, 'aws_secret_access_key', None)
        )
        
        # Consumer state
        self.is_running = False
        self.consumer_tasks = []
        
        # Processing metrics
        self.consumer_stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "messages_sent_to_dlq": 0,
            "empty_polls": 0,
            "processing_errors": 0,
            "start_time": None
        }
        
        # Semaphore for concurrency control
        self.processing_semaphore = asyncio.Semaphore(max_concurrent_messages)
    
    async def start_consuming(
        self,
        queue_urls: List[str],
        num_consumers_per_queue: int = 2
    ):
        """
        Start consuming messages from SQS queues.
        
        Args:
            queue_urls: List of SQS queue URLs to consume from
            num_consumers_per_queue: Number of concurrent consumers per queue
        """
        if self.is_running:
            self.logger.warning("SQS consumer is already running")
            return
        
        self.is_running = True
        self.consumer_stats["start_time"] = datetime.utcnow()
        
        self.logger.info(
            f"Starting SQS consumer for {len(queue_urls)} queues",
            extra={
                "queue_count": len(queue_urls),
                "consumers_per_queue": num_consumers_per_queue,
                "batch_size": self.batch_size,
                "max_concurrent": self.max_concurrent_messages
            }
        )
        
        # Start consumer tasks for each queue
        for queue_url in queue_urls:
            for consumer_id in range(num_consumers_per_queue):
                task = asyncio.create_task(
                    self._consume_queue_messages(queue_url, consumer_id),
                    name=f"sqs_consumer_{queue_url.split('/')[-1]}_{consumer_id}"
                )
                self.consumer_tasks.append(task)
        
        # Start stats reporting task
        stats_task = asyncio.create_task(
            self._report_stats_periodically(),
            name="sqs_consumer_stats"
        )
        self.consumer_tasks.append(stats_task)
        
        try:
            # Wait for all consumer tasks
            await asyncio.gather(*self.consumer_tasks)
        except asyncio.CancelledError:
            self.logger.info("SQS consumer tasks cancelled")
        except Exception as e:
            self.logger.error(f"SQS consumer error: {str(e)}")
        finally:
            await self._cleanup()
    
    async def stop_consuming(self):
        """Stop consuming messages and cleanup resources."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping SQS consumer...")
        self.is_running = False
        
        # Cancel all consumer tasks
        for task in self.consumer_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete with timeout
        if self.consumer_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.consumer_tasks, return_exceptions=True),
                    timeout=30.0  # 30 second shutdown timeout
                )
            except asyncio.TimeoutError:
                self.logger.warning("Some consumer tasks did not shutdown gracefully")
        
        await self._cleanup()
        self.logger.info("SQS consumer stopped")
    
    async def _consume_queue_messages(self, queue_url: str, consumer_id: int):
        """Main consumer loop for a specific queue."""
        queue_name = queue_url.split('/')[-1]
        consumer_logger = self.logger.bind(queue=queue_name, consumer_id=consumer_id)
        
        consumer_logger.info(f"Started SQS consumer for queue {queue_name}")
        
        consecutive_empty_polls = 0
        max_empty_polls = 5  # Back off after empty polls
        
        while self.is_running:
            try:
                # Receive messages from SQS
                messages = await self._receive_messages(queue_url)
                
                if not messages:
                    consecutive_empty_polls += 1
                    self.consumer_stats["empty_polls"] += 1
                    
                    # Progressive backoff for empty polls
                    if consecutive_empty_polls >= max_empty_polls:
                        await asyncio.sleep(min(consecutive_empty_polls * 2, 30))
                    
                    continue
                
                consecutive_empty_polls = 0
                self.consumer_stats["messages_received"] += len(messages)
                
                consumer_logger.debug(
                    f"Received {len(messages)} messages from {queue_name}"
                )
                
                # Process messages concurrently
                await self._process_message_batch(messages, queue_url, consumer_logger)
                
            except asyncio.CancelledError:
                consumer_logger.info(f"Consumer for {queue_name} cancelled")
                break
            except Exception as e:
                consumer_logger.error(
                    f"Error in consumer loop for {queue_name}: {str(e)}"
                )
                self.consumer_stats["processing_errors"] += 1
                
                # Brief pause before retrying to avoid tight error loops
                await asyncio.sleep(5)
    
    async def _receive_messages(self, queue_url: str) -> List[Dict[str, Any]]:
        """Receive messages from SQS queue."""
        try:
            loop = asyncio.get_event_loop()
            
            # Run SQS receive_message in thread pool to avoid blocking
            response = await loop.run_in_executor(
                None,
                lambda: self.sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=self.batch_size,
                    WaitTimeSeconds=self.wait_time_seconds,
                    VisibilityTimeoutSeconds=self.visibility_timeout,
                    AttributeNames=['All'],
                    MessageAttributeNames=['All']
                )
            )
            
            messages = response.get('Messages', [])
            return messages
            
        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"AWS error receiving messages: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error receiving messages: {str(e)}")
            return []
    
    async def _process_message_batch(
        self,
        messages: List[Dict[str, Any]],
        queue_url: str,
        consumer_logger
    ):
        """Process a batch of SQS messages concurrently."""
        semaphore = asyncio.Semaphore(self.max_concurrent_messages)
        
        async def process_single_message(message: Dict[str, Any]):
            async with semaphore:
                await self._process_single_message(message, queue_url, consumer_logger)
        
        # Process all messages in the batch concurrently
        tasks = [process_single_message(msg) for msg in messages]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_message(
        self,
        message: Dict[str, Any],
        queue_url: str,
        consumer_logger
    ):
        """Process a single SQS message through the repricing pipeline."""
        message_id = message.get('MessageId', 'unknown')
        receipt_handle = message.get('ReceiptHandle')
        
        start_time = time.time()
        
        try:
            # Process message through orchestrator
            result = await self.orchestrator.process_amazon_message(message)
            
            processing_time = (time.time() - start_time) * 1000
            
            if result["success"]:
                # Message processed successfully - delete from queue
                await self._delete_message(queue_url, receipt_handle)
                self.consumer_stats["messages_processed"] += 1
                
                consumer_logger.info(
                    f"Message {message_id} processed successfully",
                    extra={
                        "message_id": message_id,
                        "price_changed": result.get("price_changed", False),
                        "processing_time_ms": processing_time
                    }
                )
            else:
                # Message failed - check retry count
                await self._handle_failed_message(
                    message, queue_url, receipt_handle, result, consumer_logger
                )
                self.consumer_stats["messages_failed"] += 1
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            
            consumer_logger.error(
                f"Exception processing message {message_id}: {str(e)}",
                extra={
                    "message_id": message_id,
                    "processing_time_ms": processing_time
                }
            )
            
            await self._handle_failed_message(
                message, queue_url, receipt_handle, 
                {"error": str(e), "success": False}, consumer_logger
            )
            self.consumer_stats["messages_failed"] += 1
    
    async def _handle_failed_message(
        self,
        message: Dict[str, Any],
        queue_url: str,
        receipt_handle: str,
        result: Dict[str, Any],
        consumer_logger
    ):
        """Handle a message that failed processing."""
        message_id = message.get('MessageId', 'unknown')
        
        # Get current retry count from message attributes
        attributes = message.get('Attributes', {})
        receive_count = int(attributes.get('ApproximateReceiveCount', 1))
        
        if receive_count >= self.max_retries:
            # Max retries exceeded - send to dead letter queue (if configured)
            consumer_logger.warning(
                f"Message {message_id} exceeded max retries ({self.max_retries})",
                extra={
                    "message_id": message_id,
                    "receive_count": receive_count,
                    "error": result.get("error", "unknown")
                }
            )
            
            # Delete the message to prevent further processing
            # (SQS DLQ should be configured to handle these automatically)
            await self._delete_message(queue_url, receipt_handle)
            self.consumer_stats["messages_sent_to_dlq"] += 1
        else:
            # Let the message become visible again for retry
            # (after visibility timeout expires)
            consumer_logger.info(
                f"Message {message_id} will be retried (attempt {receive_count}/{self.max_retries})",
                extra={
                    "message_id": message_id,
                    "receive_count": receive_count,
                    "error": result.get("error", "unknown")
                }
            )
    
    async def _delete_message(self, queue_url: str, receipt_handle: str):
        """Delete a message from SQS queue."""
        try:
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                None,
                lambda: self.sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to delete message: {str(e)}")
    
    async def _report_stats_periodically(self):
        """Report consumer statistics periodically."""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Report every minute
                
                if self.consumer_stats["start_time"]:
                    uptime = datetime.utcnow() - self.consumer_stats["start_time"]
                    uptime_seconds = uptime.total_seconds()
                    
                    messages_per_second = (
                        self.consumer_stats["messages_processed"] / uptime_seconds
                        if uptime_seconds > 0 else 0
                    )
                    
                    self.logger.info(
                        "SQS Consumer Stats",
                        extra={
                            "uptime_seconds": int(uptime_seconds),
                            "messages_received": self.consumer_stats["messages_received"],
                            "messages_processed": self.consumer_stats["messages_processed"],
                            "messages_failed": self.consumer_stats["messages_failed"],
                            "messages_sent_to_dlq": self.consumer_stats["messages_sent_to_dlq"],
                            "empty_polls": self.consumer_stats["empty_polls"],
                            "processing_errors": self.consumer_stats["processing_errors"],
                            "messages_per_second": round(messages_per_second, 2),
                            "success_rate": round(
                                (self.consumer_stats["messages_processed"] / 
                                 max(self.consumer_stats["messages_received"], 1)) * 100, 2
                            )
                        }
                    )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error reporting stats: {str(e)}")
    
    async def _cleanup(self):
        """Cleanup resources."""
        self.is_running = False
        self.consumer_tasks.clear()
    
    def get_consumer_stats(self) -> Dict[str, Any]:
        """Get current consumer statistics."""
        stats = self.consumer_stats.copy()
        
        if stats["start_time"]:
            uptime = datetime.utcnow() - stats["start_time"]
            stats["uptime_seconds"] = int(uptime.total_seconds())
            
            if stats["uptime_seconds"] > 0:
                stats["messages_per_second"] = round(
                    stats["messages_processed"] / stats["uptime_seconds"], 2
                )
            else:
                stats["messages_per_second"] = 0.0
        
        if stats["messages_received"] > 0:
            stats["success_rate"] = round(
                (stats["messages_processed"] / stats["messages_received"]) * 100, 2
            )
        else:
            stats["success_rate"] = 0.0
        
        stats["timestamp"] = datetime.utcnow().isoformat()
        return stats


async def main():
    """Main function to run SQS consumer."""
    import signal
    import sys
    
    # Initialize services
    redis_service = RedisService()
    orchestrator = RepricingOrchestrator(redis_service)
    consumer = SQSConsumer(orchestrator)
    
    # Example queue URLs (replace with actual queue URLs)
    queue_urls = [
        "https://sqs.us-east-1.amazonaws.com/123456789012/ah-repricer-notifications"
        # Add more queue URLs as needed
    ]
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        asyncio.create_task(consumer.stop_consuming())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("Starting SQS consumer...")
        await consumer.start_consuming(queue_urls)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"SQS consumer error: {str(e)}")
    finally:
        await consumer.stop_consuming()
        await orchestrator.shutdown()
        logger.info("SQS consumer shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())