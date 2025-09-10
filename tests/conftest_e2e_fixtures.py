"""
End-to-end test configuration with LocalStack and Redis integration.
"""
import os
import asyncio
import json
import time
from unittest.mock import patch

import pytest
import httpx
import boto3
import redis
from fastapi.testclient import TestClient

# Set up environment for LocalStack and testing
os.environ.update({
    'TESTING': 'true',
    'AWS_ENDPOINT_URL': 'http://localhost:4566',
    'AWS_ACCESS_KEY_ID': 'test',
    'AWS_SECRET_ACCESS_KEY': 'test',
    'AWS_DEFAULT_REGION': 'us-east-1',
    'REDIS_URL': 'redis://localhost:6380',  # Test Redis port
    'DATABASE_URL': 'sqlite:///./test.db',
    'SECRET_KEY': 'test-secret-key-for-e2e-tests',
    'JWT_SECRET_KEY': 'test-jwt-secret',
})

# Import after setting environment
from src.api.webhook_endpoints import app
from src.services.sqs_consumer import SQSConsumer
from src.services.repricing_orchestrator import RepricingOrchestrator
from src.services.redis_service import RedisService
from src.models.products import ProductListing, B2BTier


# LocalStack configuration
LOCALSTACK_ENDPOINT = 'http://localhost:4566'
TEST_QUEUE_NAME = 'ah-repricer-any-offer-changed'
TEST_TOPIC_NAME = 'ah-repricer-any-offer-changed-topic'

# Test data templates
SAMPLE_AMAZON_PRODUCT = {
    "asin": "B07XQXZXYX",
    "seller_id": "A1SELLER123", 
    "sku": "TEST-SKU-001",
    "listed_price": 29.99,
    "min_price": 25.00,
    "max_price": 45.00,
    "default_price": 30.00,
    "strategy_id": "1",
    "inventory_quantity": 150,
    "inventory_age": 30,
    "status": "Active",
    "is_b2b": False
}

SAMPLE_WALMART_PRODUCT = {
    "asin": "W12345678901",  # Using ASIN field for consistency 
    "seller_id": "WM_SELLER_123",
    "sku": "TEST-WAL-SKU-001", 
    "listed_price": 28.99,
    "min_price": 22.00,
    "max_price": 40.00,
    "default_price": 29.00,
    "strategy_id": "2",
    "inventory_quantity": 200,
    "inventory_age": 45,
    "status": "Active",
    "is_b2b": False
}


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def localstack_services():
    """
    Ensure LocalStack services are running and configured.
    This fixture assumes LocalStack is already started via docker-compose.
    """
    # Wait for LocalStack to be ready
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = httpx.get(f"{LOCALSTACK_ENDPOINT}/health", timeout=5.0)
            if response.status_code == 200:
                health = response.json()
                if health.get("services", {}).get("sqs") == "available":
                    print("LocalStack SQS service is ready")
                    break
        except Exception as e:
            print(f"Waiting for LocalStack (attempt {retry_count + 1}): {e}")
            
        retry_count += 1
        time.sleep(2)
    
    if retry_count >= max_retries:
        pytest.skip("LocalStack is not available - run docker-compose up localstack")
    
    yield
    
    
@pytest.fixture(scope="session")  
def redis_client():
    """Create a Redis client for testing."""
    client = redis.Redis(host='localhost', port=6380, decode_responses=True, db=0)
    
    # Wait for Redis to be ready
    max_retries = 15
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            client.ping()
            print("Redis is ready for testing")
            break
        except Exception as e:
            print(f"Waiting for Redis (attempt {retry_count + 1}): {e}")
            retry_count += 1
            time.sleep(1)
    
    if retry_count >= max_retries:
        pytest.skip("Redis is not available - run docker-compose up redis")
    
    # Clear any existing test data
    client.flushdb()
    
    yield client
    
    # Cleanup after all tests
    client.flushdb()
    client.close()


@pytest.fixture
def sqs_client(localstack_services):
    """Create boto3 SQS client configured for LocalStack."""
    return boto3.client(
        'sqs',
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name='us-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )


@pytest.fixture
def sns_client(localstack_services):
    """Create boto3 SNS client configured for LocalStack.""" 
    return boto3.client(
        'sns',
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name='us-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )


@pytest.fixture
async def redis_service(redis_client):
    """Create RedisService instance for testing."""
    # Mock the Redis connection to use our test client
    with patch('src.services.redis_service.redis.Redis') as mock_redis:
        mock_redis.return_value = redis_client
        service = RedisService()
        yield service


@pytest.fixture
async def repricing_orchestrator(redis_service):
    """Create RepricingOrchestrator for testing."""
    orchestrator = RepricingOrchestrator(
        redis_service=redis_service,
        max_concurrent_workers=10,  # Lower for testing
        batch_size=5
    )
    yield orchestrator
    await orchestrator.shutdown()


@pytest.fixture
def fastapi_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def sqs_consumer(repricing_orchestrator):
    """Create SQS consumer for testing."""
    consumer = SQSConsumer(
        orchestrator=repricing_orchestrator,
        max_concurrent_messages=5,  # Lower for testing
        batch_size=5,
        visibility_timeout=30,  # Shorter for testing
        wait_time_seconds=1,    # Shorter polling for testing
        max_retries=2
    )
    yield consumer


@pytest.fixture
def sample_amazon_sqs_message():
    """Generate sample Amazon ANY_OFFER_CHANGED SQS message."""
    return {
        "MessageId": "12345678-1234-1234-1234-123456789012",
        "ReceiptHandle": "test-receipt-handle",
        "Body": json.dumps({
            "Type": "Notification",
            "MessageId": "sns-msg-12345",
            "TopicArn": "arn:aws:sns:us-east-1:123456789012:any-offer-changed",
            "Message": json.dumps({
                "notificationType": "AnyOfferChanged",
                "payloadVersion": "1.0",
                "eventTime": "2025-01-15T14:30:00.000Z",
                "payload": {
                    "anyOfferChangedNotification": {
                        "sellerId": "A1SELLER123",
                        "asin": "B07XQXZXYX",
                        "marketplaceId": "ATVPDKIKX0DER",
                        "itemCondition": "NEW",
                        "timeOfOfferChange": "2025-01-15T14:30:00.000Z"
                    }
                }
            }),
            "Timestamp": "2025-01-15T14:30:00.000Z"
        }),
        "Attributes": {
            "ApproximateReceiveCount": "1",
            "SentTimestamp": "1705409400000",
            "ApproximateFirstReceiveTimestamp": "1705409400000"
        }
    }


@pytest.fixture  
def sample_walmart_webhook():
    """Generate sample Walmart buy box changed webhook."""
    return {
        "eventType": "buybox_changed",
        "webhookId": "wh_12345",
        "timestamp": "2025-01-15T14:30:00.000Z",
        "itemId": "W12345678901",
        "sellerId": "WM_SELLER_123", 
        "marketplace": "US",
        "eventTime": "2025-01-15T14:30:00.000Z",
        "currentBuyboxPrice": 27.99,
        "currentBuyboxWinner": "WM_COMPETITOR_456",
        "offers": [
            {
                "sellerId": "WM_SELLER_123",
                "price": 28.99,
                "shipping": 0.00,
                "condition": "NEW",
                "fulfillmentType": "WALMART"
            },
            {
                "sellerId": "WM_COMPETITOR_456",
                "price": 27.99,
                "shipping": 0.00,
                "condition": "NEW", 
                "fulfillmentType": "WALMART"
            }
        ]
    }


@pytest.fixture
def setup_test_products(redis_client):
    """Set up test product data in Redis."""
    
    def _setup_products(products_list):
        """Setup multiple products in Redis."""
        for product_data in products_list:
            # Store product data
            asin_key = f"ASIN_{product_data['asin']}"
            seller_sku_key = f"{product_data['seller_id']}:{product_data['sku']}"
            
            redis_client.hset(
                asin_key,
                seller_sku_key,
                json.dumps(product_data)
            )
            
            # Set TTL (2 hours like production)
            redis_client.expire(asin_key, 7200)
            
            # Store strategy configuration
            strategy_key = f"strategy.{product_data['strategy_id']}"
            strategy_config = {
                "compete_with": "MATCH_BUYBOX",
                "beat_by": "-0.01",  # Beat by 1 cent
                "min_price_rule": "JUMP_TO_MIN",
                "max_price_rule": "JUMP_TO_MAX"
            }
            
            for field, value in strategy_config.items():
                redis_client.hset(strategy_key, field, value)
                
            redis_client.expire(strategy_key, 7200)
    
    return _setup_products


@pytest.fixture
def verify_price_in_redis(redis_client):
    """Helper to verify calculated prices are saved in Redis."""
    
    def _verify_price(seller_id: str, sku: str, expected_price: float = None, should_exist: bool = True):
        """Verify price calculation results in Redis."""
        calculated_prices_key = f"CALCULATED_PRICES:{seller_id}"
        
        if should_exist:
            assert redis_client.hexists(calculated_prices_key, sku), \
                f"No calculated price found for {seller_id}:{sku}"
                
            price_data = json.loads(redis_client.hget(calculated_prices_key, sku))
            
            assert "new_price" in price_data, "new_price not found in calculated price data"
            assert "calculated_at" in price_data, "calculated_at timestamp not found"
            assert "strategy_used" in price_data, "strategy_used not found"
            
            if expected_price is not None:
                actual_price = float(price_data["new_price"])
                assert abs(actual_price - expected_price) < 0.01, \
                    f"Expected price {expected_price}, got {actual_price}"
            
            return price_data
        else:
            assert not redis_client.hexists(calculated_prices_key, sku), \
                f"Unexpected calculated price found for {seller_id}:{sku}"
            return None
    
    return _verify_price


@pytest.fixture  
def wait_for_processing():
    """Helper to wait for asynchronous processing to complete."""
    
    def _wait(timeout_seconds: float = 5.0):
        """Wait for background processing with timeout."""
        import asyncio
        import time
        
        start_time = time.time()
        
        # Give some time for async processing 
        while time.time() - start_time < timeout_seconds:
            time.sleep(0.1)  # Small sleep to allow processing
            
        # Additional small delay to ensure completion
        time.sleep(0.2)
    
    return _wait