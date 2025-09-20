"""SQS Consumer for Amazon notifications."""

import asyncio
import json
import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from core.config import Settings

# Module-level logger for standalone functions
logger = logging.getLogger(__name__)


class SQSConsumer:
    """SQS Consumer that works with both AWS SQS and LocalStack."""

    def __init__(self, settings: Settings, logger: logging.Logger, redis_service=None, repricing_orchestrator=None):
        self.settings = settings
        self.logger = logger
        self.sqs_client = None
        self.running = False
        self.queue_urls = {self.settings.sqs_queue_url_any_offer}
        self.redis_service = redis_service
        self.repricing_orchestrator = repricing_orchestrator

    async def initialize(self):
        """Initialize SQS client and discover queues."""
        try:
            # Configure SQS client (works with both AWS SQS and LocalStack)
            if self.settings.aws_endpoint_url:
                # Development/testing with LocalStack
                self.sqs_client = boto3.client(
                    "sqs",
                    endpoint_url=self.settings.aws_endpoint_url,
                    region_name=self.settings.aws_region,
                    aws_access_key_id=self.settings.aws_access_key_id,
                    aws_secret_access_key=self.settings.aws_secret_access_key,
                )
            else:
                # Production with real AWS SQS
                self.sqs_client = boto3.client(
                    "sqs", region_name=self.settings.aws_region
                )

            # Discover available queues
            self.logger.info("sqs_consumer_initialized", 
                            queue_urls=list(self.queue_urls), endpoint_url=self.settings.aws_endpoint_url)

        except Exception as e:
            self.logger.error("sqs_consumer_init_failed",
                             error=str(e), error_type=type(e).__name__)
            raise

    async def start_consuming(self):
        """Start consuming messages from specified queues."""
        if not self.sqs_client:
            await self.initialize()

        self.running = True
        self.logger.info("sqs_consumer_starting", 
                         queue_count=len(self.queue_urls), queue_urls=list(self.queue_urls))

        # Start consumer tasks for each queue
        tasks = []
        for queue_url in self.queue_urls:
            task = asyncio.create_task(self._consume_queue(queue_url))
            tasks.append(task)

        # Wait for all consumer tasks
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error("sqs_consumer_error", extra={"error": str(e)})
        finally:
            self.running = False

    async def _consume_queue(self, queue_url: str):
        """Consume messages from a specific queue."""
        self.logger.info("queue_consumer_starting", 
                         queue_url=queue_url, queue_type=self._get_queue_type(queue_url))

        while self.running:
            try:
                # Poll for messages
                response = self.sqs_client.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=5,  # Long polling
                    VisibilityTimeout=60,
                )

                messages = response.get("Messages", [])

                if messages:

                    for message in messages:
                        self.logger.info("sqs_messages_received",
                                    message_count=len(messages), queue_url=queue_url,
                                    queue_type=self._get_queue_type(queue_url))
                        await self._process_message(queue_url, message)

                        # Delete processed message
                        self.sqs_client.delete_message(
                            QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"]
                        )

                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)

            except ClientError as e:
                self.logger.error("queue_consume_error", extra={"error": str(e), "queue_url": queue_url})
                await asyncio.sleep(5)  # Back off on errors
            except Exception as e:
                self.logger.error("queue_consumer_unexpected_error", extra={"error": str(e), "queue_url": queue_url})
                await asyncio.sleep(1)

    async def _process_message(self, queue_url: str, message: Dict[str, Any]):
        """Process a single SQS message."""
        try:
            message_id = message.get("MessageId", "unknown")
            body = message.get("Body", "{}")

            self.logger.info("sqs_message_processing_start", 
                            message_id=message_id, queue_url=queue_url, 
                            queue_type=self._get_queue_type(queue_url), body_length=len(body))

            # Parse message body
            try:
                parsed_body = json.loads(body)
            except json.JSONDecodeError:
                self.logger.warning("sqs_message_invalid_json", 
                                   message_id=message_id, queue_url=queue_url, body_preview=body[:200])
                return

            # Route message based on queue name
            if "amazon-any-offer-changed" in queue_url:
                await self._process_amazon_notification(
                    message
                )  # Pass full SQS message
            elif "feed-processing" in queue_url:
                await self._process_feed_notification(parsed_body)
            else:
                self.logger.info("sqs_unknown_queue_type", 
                                queue_url=queue_url, message_id=message_id)
                self.logger.debug("sqs_unknown_message_content", 
                                 message_id=message_id, content=parsed_body)

        except Exception as e:
            self.logger.error("message_processing_error", extra={"error": str(e)})

    async def _process_amazon_notification(self, sqs_message: Dict[str, Any]):
        """Process Amazon AnyOfferChanged notification with real repricing."""
        try:
            # Use dependency-injected services
            redis_service = self.redis_service
            orchestrator = self.repricing_orchestrator
            
            if not redis_service or not orchestrator:
                raise ValueError("Required services not properly injected via DI")

            # Parse the notification from the SQS message body
            message_body = json.loads(sqs_message.get("Body", "{}"))

            # Extract ASIN from SP-API format (OfferChangeTrigger only)
            payload = message_body.get("Payload", {})
            offer_change_trigger = payload.get("OfferChangeTrigger", {})
            asin = offer_change_trigger.get("ASIN")

            # Extract seller_id from offers or use default for processing
            seller_id = None
            offers = payload.get("Offers", [])
            if offers:
                # Use first non-buybox seller as target (message processor will handle this properly)
                for offer in offers:
                    if not offer.get("IsBuyBoxWinner", False):
                        seller_id = offer.get("SellerId")
                        break
                # If all are buybox winners, use the first one
                if not seller_id:
                    seller_id = offers[0].get("SellerId")
            if asin:
                self.logger.info("amazon_offer_notification_processing", 
                                asin=asin, seller_id=seller_id, offer_count=len(offers),
                                message_id=sqs_message.get("MessageId"))

                # Process the message using the orchestrator (pass the full SQS message)
                result = await orchestrator.process_amazon_message(sqs_message)

                # Log the result
                if result.get("success", False):
                    self.logger.info("amazon_notification_success",
                                    asin=asin, seller_id=seller_id,
                                    price_changed=result.get("price_changed", False),
                                    processing_time_ms=result.get("processing_time_ms"),
                                    strategy_used=result.get("strategy_used"),
                                    old_price=result.get("old_price"),
                                    new_price=result.get("new_price"),
                                    message_id=sqs_message.get("MessageId"))
                else:
                    self.logger.error("amazon_notification_failed",
                                     asin=asin, seller_id=seller_id,
                                     error=result.get("error", "Unknown error"),
                                     error_type=result.get("error_type"),
                                     processing_time_ms=result.get("processing_time_ms"),
                                     message_id=sqs_message.get("MessageId"))
            else:
                self.logger.warning("amazon_notification_missing_asin",
                                   message_id=sqs_message.get("MessageId"),
                                   payload_keys=list(payload.keys()) if payload else [])

        except Exception as e:
            self.logger.error("amazon_notification_processing_error", extra={"error": str(e)})

    async def _process_feed_notification(self, notification: Dict[str, Any]):
        """Process feed processing notification."""
        try:
            feed_id = notification.get("feedId", "unknown")
            status = notification.get("status", "unknown")

            self.logger.info("feed_notification_processing", extra={"feed_id": feed_id, "status": status})

            # Simulate feed processing
            await asyncio.sleep(0.1)

            self.logger.info("feed_notification_processed", extra={"feed_id": feed_id})

        except Exception as e:
            self.logger.error("feed_notification_processing_error", extra={"error": str(e)})

    async def stop(self):
        """Stop the consumer."""
        self.running = False
        self.logger.info("sqs_consumer_stopped")

    def _get_queue_type(self, queue_url: str) -> str:
        """Extract queue type from URL for logging."""
        if "amazon-any-offer-changed" in queue_url:
            return "amazon-offer-changed"
        elif "feed-processing" in queue_url:
            return "feed-processing"
        else:
            return "unknown"

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the queues."""
        stats = {}

        if not self.sqs_client:
            return stats

        for queue_url in self.queue_urls:
            try:
                response = self.sqs_client.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=[
                        "ApproximateNumberOfMessages",
                        "ApproximateNumberOfMessagesNotVisible",
                    ],
                )

                stats[queue_url] = {
                    "visible_messages": int(
                        response["Attributes"].get("ApproximateNumberOfMessages", 0)
                    ),
                    "in_flight_messages": int(
                        response["Attributes"].get(
                            "ApproximateNumberOfMessagesNotVisible", 0
                        )
                    ),
                }

            except Exception as e:
                self.logger.warning("queue_stats_get_failed", extra={"error": str(e), "queue_url": queue_url})
                stats[queue_url] = {"error": str(e)}

        return stats


# Use dependency injection container to get SQS consumer instances
# Example: container.sqs_consumer()


async def start_sqs_consumer(consumer: SQSConsumer):
    """Start the SQS consumer (to be called from main app)."""
    await consumer.start_consuming()


async def stop_sqs_consumer(consumer: SQSConsumer):
    """Stop the SQS consumer."""
    await consumer.stop()


# Note: Use dependency injection container to get SQS consumer instances
# Example: container.sqs_consumer()


async def main():
    """Main entry point for running SQS consumer standalone."""
    # Configure logging to suppress verbose boto3/botocore logs
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('botocore.endpoint').setLevel(logging.WARNING)
    logging.getLogger('botocore.auth').setLevel(logging.WARNING)
    logging.getLogger('botocore.retryhandler').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    logger.info("starting_sqs_consumer_service")

    # Create SQS consumer using DI container
    from containers import Container
    container = Container()
    sqs_consumer = container.sqs_consumer()

    try:
        await sqs_consumer.initialize()
        await sqs_consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("sqs_consumer_stopped_by_user")
    except Exception as e:
        logger.error("sqs_consumer_main_error", extra={"error": str(e)})
        raise
    finally:
        await sqs_consumer.stop()
        logger.info("sqs_consumer_shutdown_complete")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
