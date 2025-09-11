"""SQS Consumer for Amazon notifications."""

import json
import asyncio
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger

from ..core.config import get_settings


class SQSConsumer:
    """SQS Consumer that works with both AWS SQS and LocalStack."""
    
    def __init__(self):
        self.settings = get_settings()
        self.sqs_client = None
        self.running = False
        self.queue_urls = {}
        
    async def initialize(self):
        """Initialize SQS client and discover queues."""
        try:
            # Configure SQS client (works with both AWS SQS and LocalStack)
            if self.settings.aws_endpoint_url:
                # Development/testing with LocalStack
                self.sqs_client = boto3.client(
                    'sqs',
                    endpoint_url=self.settings.aws_endpoint_url,
                    region_name='us-east-1',
                    aws_access_key_id='test',  # LocalStack doesn't validate these
                    aws_secret_access_key='test'
                )
            else:
                # Production with real AWS SQS
                self.sqs_client = boto3.client(
                    'sqs',
                    region_name='us-east-1'
                )
            
            # Discover available queues
            await self._discover_queues()
            logger.info(f"SQS Consumer initialized with queues: {list(self.queue_urls.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQS consumer: {e}")
            raise
    
    async def _discover_queues(self):
        """Discover available SQS queues."""
        try:
            response = self.sqs_client.list_queues()
            
            for queue_url in response.get('QueueUrls', []):
                queue_name = queue_url.split('/')[-1]
                self.queue_urls[queue_name] = queue_url
                logger.info(f"Discovered queue: {queue_name} -> {queue_url}")
                
        except ClientError as e:
            logger.warning(f"Could not discover queues: {e}")
            # Create default queues if they don't exist
            await self._create_default_queues()
    
    async def _create_default_queues(self):
        """Create default queues if they don't exist."""
        default_queues = [
            'amazon-any-offer-changed-queue',
            'feed-processing-queue',
            'processed-data-queue'
        ]
        
        for queue_name in default_queues:
            try:
                response = self.sqs_client.create_queue(
                    QueueName=queue_name,
                    Attributes={
                        'VisibilityTimeoutSeconds': '60',
                        'MessageRetentionPeriod': '1209600'  # 14 days
                    }
                )
                self.queue_urls[queue_name] = response['QueueUrl']
                logger.info(f"Created queue: {queue_name}")
                
            except ClientError as e:
                if e.response['Error']['Code'] != 'QueueAlreadyExists':
                    logger.error(f"Failed to create queue {queue_name}: {e}")
    
    async def start_consuming(self, queue_names: Optional[List[str]] = None):
        """Start consuming messages from specified queues."""
        if not self.sqs_client:
            await self.initialize()
        
        if not queue_names:
            queue_names = list(self.queue_urls.keys())
        
        self.running = True
        logger.info(f"Starting SQS consumer for queues: {queue_names}")
        
        # Start consumer tasks for each queue
        tasks = []
        for queue_name in queue_names:
            if queue_name in self.queue_urls:
                task = asyncio.create_task(self._consume_queue(queue_name))
                tasks.append(task)
        
        # Wait for all consumer tasks
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in SQS consumer: {e}")
        finally:
            self.running = False
    
    async def _consume_queue(self, queue_name: str):
        """Consume messages from a specific queue."""
        queue_url = self.queue_urls[queue_name]
        logger.info(f"Starting consumer for queue: {queue_name}")
        
        while self.running:
            try:
                # Poll for messages
                response = self.sqs_client.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=5,  # Long polling
                    VisibilityTimeoutSeconds=60
                )
                
                messages = response.get('Messages', [])
                
                if messages:
                    logger.info(f"Received {len(messages)} messages from {queue_name}")
                    
                    for message in messages:
                        await self._process_message(queue_name, message)
                        
                        # Delete processed message
                        self.sqs_client.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except ClientError as e:
                logger.error(f"Error consuming from {queue_name}: {e}")
                await asyncio.sleep(5)  # Back off on errors
            except Exception as e:
                logger.error(f"Unexpected error in queue consumer {queue_name}: {e}")
                await asyncio.sleep(1)
    
    async def _process_message(self, queue_name: str, message: Dict[str, Any]):
        """Process a single SQS message."""
        try:
            message_id = message.get('MessageId', 'unknown')
            body = message.get('Body', '{}')
            
            logger.info(f"Processing message {message_id} from {queue_name}")
            
            # Parse message body
            try:
                parsed_body = json.loads(body)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in message {message_id}: {body}")
                return
            
            # Route message based on queue name
            if 'amazon-any-offer-changed' in queue_name:
                await self._process_amazon_notification(parsed_body)
            elif 'feed-processing' in queue_name:
                await self._process_feed_notification(parsed_body)
            else:
                logger.info(f"Unknown queue type: {queue_name}, logging message")
                logger.debug(f"Message content: {parsed_body}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _process_amazon_notification(self, notification: Dict[str, Any]):
        """Process Amazon AnyOfferChanged notification."""
        try:
            # Extract ASIN and Seller info
            payload = notification.get('Payload', {})
            any_offer_changed = payload.get('AnyOfferChangedNotification', {})
            
            asin = any_offer_changed.get('ASIN')
            seller_id = any_offer_changed.get('SellerId')
            
            if asin and seller_id:
                logger.info(f"Processing Amazon notification for ASIN: {asin}, Seller: {seller_id}")
                
                # Here you would integrate with your repricing engine
                # For now, just simulate processing
                await asyncio.sleep(0.1)
                
                logger.info(f"Amazon notification processed successfully: ASIN={asin}")
            else:
                logger.warning("Amazon notification missing ASIN or SellerId")
                
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
    
    async def send_test_message(self, queue_name: str, message_body: Dict[str, Any]):
        """Send a test message to a queue (useful for testing)."""
        if not self.sqs_client:
            await self.initialize()
        
        if queue_name not in self.queue_urls:
            raise ValueError(f"Queue {queue_name} not found")
        
        try:
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_urls[queue_name],
                MessageBody=json.dumps(message_body)
            )
            
            logger.info(f"Test message sent to {queue_name}: {response['MessageId']}")
            return response['MessageId']
            
        except Exception as e:
            logger.error(f"Failed to send test message: {e}")
            raise
    
    async def stop(self):
        """Stop the consumer."""
        self.running = False
        logger.info("SQS consumer stopped")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the queues."""
        stats = {}
        
        if not self.sqs_client:
            return stats
        
        for queue_name, queue_url in self.queue_urls.items():
            try:
                response = self.sqs_client.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
                )
                
                stats[queue_name] = {
                    'url': queue_url,
                    'visible_messages': int(response['Attributes'].get('ApproximateNumberOfMessages', 0)),
                    'in_flight_messages': int(response['Attributes'].get('ApproximateNumberOfMessagesNotVisible', 0))
                }
                
            except Exception as e:
                logger.warning(f"Could not get stats for queue {queue_name}: {e}")
                stats[queue_name] = {'error': str(e)}
        
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