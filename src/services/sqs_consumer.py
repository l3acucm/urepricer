"""SQS Consumer for Amazon notifications."""

import asyncio
import json
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError
from loguru import logger

from core.config import get_settings
from services.redis_service import RedisService
from services.repricing_orchestrator import RepricingOrchestrator

settings = get_settings()

class SQSConsumer:
    """SQS Consumer that works with both AWS SQS and LocalStack."""
    
    def __init__(self):
        self.settings = get_settings()
        self.sqs_client = None
        self.running = False
        self.queue_urls = {settings.sqs_queue_url_any_offer}
        
    async def initialize(self):
        """Initialize SQS client and discover queues."""
        try:
            # Configure SQS client (works with both AWS SQS and LocalStack)
            if self.settings.aws_endpoint_url:
                # Development/testing with LocalStack
                self.sqs_client = boto3.client(
                    'sqs',
                    endpoint_url=settings.aws_endpoint_url,
                    region_name=settings.aws_region,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key
                )
            else:
                # Production with real AWS SQS
                self.sqs_client = boto3.client(
                    'sqs',
                    region_name=settings.aws_region
                )
            
            # Discover available queues
            logger.info("SQS Consumer initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQS consumer: {e}")
            raise
    
    async def start_consuming(self):
        """Start consuming messages from specified queues."""
        if not self.sqs_client:
            await self.initialize()

        
        self.running = True
        logger.info(f"Starting SQS consumer")
        
        # Start consumer tasks for each queue
        tasks = []
        for queue_url in self.queue_urls:
                task = asyncio.create_task(self._consume_queue(queue_url))
                tasks.append(task)
        
        # Wait for all consumer tasks
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in SQS consumer: {e}")
        finally:
            self.running = False
    
    async def _consume_queue(self, queue_url: str):
        """Consume messages from a specific queue."""
        logger.info(f"Starting consumer for queue: {queue_url}")
        
        while self.running:
            try:
                # Poll for messages
                response = self.sqs_client.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=5,  # Long polling
                    VisibilityTimeout=60
                )
                
                messages = response.get('Messages', [])
                
                if messages:
                    logger.info(f"Received {len(messages)} messages from {queue_url}")
                    
                    for message in messages:
                        await self._process_message(queue_url, message)
                        
                        # Delete processed message
                        self.sqs_client.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except ClientError as e:
                logger.error(f"Error consuming from {queue_url}: {e}")
                await asyncio.sleep(5)  # Back off on errors
            except Exception as e:
                logger.error(f"Unexpected error in queue consumer {queue_url}: {e}")
                await asyncio.sleep(1)
    
    async def _process_message(self, queue_url: str, message: Dict[str, Any]):
        """Process a single SQS message."""
        try:
            message_id = message.get('MessageId', 'unknown')
            body = message.get('Body', '{}')
            
            logger.info(f"Processing message {message_id} from {queue_url}")
            
            # Parse message body
            try:
                parsed_body = json.loads(body)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in message {message_id}: {body}")
                return
            
            # Route message based on queue name
            if 'amazon-any-offer-changed' in queue_url:
                await self._process_amazon_notification(message)  # Pass full SQS message
            elif 'feed-processing' in queue_url:
                await self._process_feed_notification(parsed_body)
            else:
                logger.info(f"Unknown queue type: {queue_url}, logging message")
                logger.debug(f"Message content: {parsed_body}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _process_amazon_notification(self, sqs_message: Dict[str, Any]):
        """Process Amazon AnyOfferChanged notification with real repricing."""
        try:
            # Create Redis service and repricing orchestrator instance
            redis_service = RedisService()
            orchestrator = RepricingOrchestrator(redis_service)
            
            # Parse the notification from the SQS message body
            message_body = json.loads(sqs_message.get('Body', '{}'))
            
            # Extract ASIN from SP-API format (OfferChangeTrigger only)
            payload = message_body.get('Payload', {})
            offer_change_trigger = payload.get('OfferChangeTrigger', {})
            asin = offer_change_trigger.get('ASIN')
            
            # Extract seller_id from offers or use default for processing
            seller_id = None
            offers = payload.get('Offers', [])
            if offers:
                # Use first non-buybox seller as target (message processor will handle this properly)
                for offer in offers:
                    if not offer.get('IsBuyBoxWinner', False):
                        seller_id = offer.get('SellerId')
                        break
                # If all are buybox winners, use the first one
                if not seller_id:
                    seller_id = offers[0].get('SellerId')
            if asin:
                logger.info(f"Processing Amazon notification for ASIN: {asin}, Seller: {seller_id}")
                
                # Process the message using the orchestrator (pass the full SQS message)
                result = await orchestrator.process_amazon_message(sqs_message)
                
                # Log the result
                if result.get("success", False):
                    logger.info(
                        f"Amazon notification processed successfully",
                        extra={
                            "asin": asin,
                            "seller_id": seller_id,
                            "price_changed": result.get("price_changed", False),
                            "processing_time_ms": result.get("processing_time_ms")
                        }
                    )
                else:
                    logger.error(
                        f"Amazon notification processing failed: {result.get('error', 'Unknown error')}",
                        extra={
                            "asin": asin,
                            "seller_id": seller_id,
                            "error": result.get("error")
                        }
                    )
            else:
                logger.warning("Amazon notification missing ASIN in OfferChangeTrigger (SP-API format required)")
                
        except Exception as e:
            logger.error(f"Error processing Amazon notification: {e}")
    
    async def _process_feed_notification(self, notification: Dict[str, Any]):
        """Process feed processing notification."""
        try:
            feed_id = notification.get('feedId', 'unknown')
            status = notification.get('status', 'unknown')
            
            logger.info(f"Processing feed notification: {feed_id} - {status}")
            
            # Simulate feed processing
            await asyncio.sleep(0.1)
            
            logger.info(f"Feed notification processed: {feed_id}")
            
        except Exception as e:
            logger.error(f"Error processing feed notification: {e}")

    
    async def stop(self):
        """Stop the consumer."""
        self.running = False
        logger.info("SQS consumer stopped")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the queues."""
        stats = {}
        
        if not self.sqs_client:
            return stats
        
        for queue_url in self.queue_urls:
            try:
                response = self.sqs_client.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
                )
                
                stats[queue_url] = {
                    'visible_messages': int(response['Attributes'].get('ApproximateNumberOfMessages', 0)),
                    'in_flight_messages': int(response['Attributes'].get('ApproximateNumberOfMessagesNotVisible', 0))
                }
                
            except Exception as e:
                logger.warning(f"Could not get stats for queue {queue_url}: {e}")
                stats[queue_url] = {'error': str(e)}
        
        return stats


# Global instance
sqs_consumer = SQSConsumer()


async def start_sqs_consumer():
    """Start the SQS consumer (to be called from main app)."""
    await sqs_consumer.start_consuming()


async def stop_sqs_consumer():
    """Stop the SQS consumer."""
    await sqs_consumer.stop()


def get_sqs_consumer() -> SQSConsumer:
    """Get the global SQS consumer instance."""
    return sqs_consumer


async def main():
    """Main entry point for running SQS consumer standalone."""
    logger.info("Starting SQS Consumer service...")
    
    try:
        await sqs_consumer.initialize()
        await sqs_consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("SQS Consumer stopped by user")
    except Exception as e:
        logger.error(f"SQS Consumer error: {e}")
        raise
    finally:
        await sqs_consumer.stop()
        logger.info("SQS Consumer shutdown complete")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())