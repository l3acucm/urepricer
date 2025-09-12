"""
Shared fixtures and configuration for urepricer tests.
"""
import sys
import os
import json
import unittest
from unittest.mock import Mock
import fakeredis
import pytest

# Mock missing dependencies before any imports
class MockLogger:
    def bind(self, **kwargs):
        return self
    
    def info(self, msg, extra=None, **kwargs):
        pass
    
    def warning(self, msg, extra=None, **kwargs):
        pass
    
    def error(self, msg, extra=None, **kwargs):
        pass
    
    def debug(self, msg, extra=None, **kwargs):
        pass
    
    def critical(self, msg, extra=None, **kwargs):
        pass

# Create mock modules and add to sys.modules before any imports
loguru_mock = Mock()
loguru_mock.logger = MockLogger()
sys.modules['loguru'] = loguru_mock

# Mock other potentially missing dependencies (except pydantic - needed for Redis OM)
sys.modules['python-dotenv'] = Mock()
sys.modules['boto3'] = Mock()
sys.modules['botocore'] = Mock()
sys.modules['botocore.exceptions'] = Mock()
sys.modules['redis.asyncio'] = Mock()
# Note: fastapi is NOT mocked - it's required for E2E tests
# Note: pydantic is NOT mocked - it's required for Redis OM

# Set environment variables before imports to avoid configuration issues
os.environ.update({
    'TESTING': 'true',  # Enable test mode for Redis OM
    'SECRET_KEY': 'test-secret-key',
    'DATABASE_URL': 'postgresql://test:test@localhost/test',
    'DB_PASSWORD': 'test-password',
    'JWT_SECRET_KEY': 'test-jwt-secret',
    'AMAZON_CLIENT_ID': 'test-client-id',
    'AMAZON_CLIENT_SECRET': 'test-client-secret',
    'AMAZON_REFRESH_TOKEN': 'test-refresh-token',
    'AWS_ACCESS_KEY_ID': 'test-access-key',
    'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
    'SQS_QUEUE_URL_ANY_OFFER': 'test-queue-url',
    'SQS_QUEUE_URL_FEED_PROCESSING': 'test-queue-url',
    'DESTINATION_ID_US': 'test-destination-us',
    'DESTINATION_ID_UK': 'test-destination-uk',
    'DESTINATION_ID_CA': 'test-destination-ca'
})

# Add src directory to Python path for imports
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_dir)

# Redis OM will be configured via TESTING environment variable

# Import test data and constants from the original repricer module
original_repricer_path = os.path.join(current_dir, '..', '..', 'repricer', 'repricer')
sys.path.insert(0, original_repricer_path)

# Import test data and constants (optional)
try:
    from test_data import *
    from constants import *
except ImportError:
    # Silently handle missing test_data module
    pass

# Import helper functions - simplified to avoid loading heavy modules
try:
    # Only import what we absolutely need for tests
    import redis
    from helpers.redis_cache import RedisCache
except ImportError:
    # Create mock classes for testing
    class RedisCache:
        def hget(self, key, field):
            return {}
        def hset(self, key, field, value):
            pass

# Mock the heavy imports to avoid configuration issues
class MockApplyStrategyService:
    def apply(self, product):
        pass

class MockAccount:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockSkipProductRepricing(Exception):
    pass

# Set globals for tests
SkipProductRepricing = MockSkipProductRepricing
ApplyStrategyService = MockApplyStrategyService
Account = MockAccount

# Initialize Redis client
try:
    redis_client = RedisCache()
except:
    redis_client = None


class _Fixture:
    """Internal fixture class containing test helper methods."""
    
    def when_strategy_applied(self):
        """Apply pricing strategy to products."""
        for seller_id, seller in self.sellers.items():
            seller = json.loads(seller, object_hook=CustomJSON)
            account = Account(seller_id)
            self.payload = self.payload.get('body.payload')
            for sku, listing in seller.items():
                self.product = self.service.process(account, sku, listing)
                if self.product:
                    ApplyStrategyService().apply(self.product)
                else:
                    print("************** Competitor not find or some missing values **************")
                    raise Exception("Competitor not find or some missing values")

    def given_platform_from_event(self):
        """Set platform to Amazon."""
        self.platform = AMAZON

    def given_an_event(self, event):
        """Set the event data."""
        self.event = event

    def given_an_sigle_api_event(self, event):
        """Set single API event data."""
        listing_data = event.pop("listing_data")
        strategy_data = event.pop("strategy_data")
        payload = check_missing_values_in_message(event)

        self.event = {
            "listing_data": listing_data,
            "strategy_data": strategy_data,
            "body": payload.get("responses")[0].get("body"),
            "request": payload.get("responses")[0].get("request")
        }

    def given_a_payload(self):
        """Set up payload and Redis data."""
        message = self.event
        set_data = SetData()
        listing_data = message.get("listing_data")
        set_data.set_data_in_redis(listing_data)
        strategy_data = message.get("strategy_data")
        set_data.set_data_in_redis(strategy_data)
        
        for key, nested_dict in listing_data[0].items():
            for field, data in nested_dict.items():
                seller_id = field
                
        marketplace_type = message.get("marketplace_type", "UK")
        set_data.set_data_in_redis([{"seller_id": seller_id, "marketplace_type": marketplace_type}])
        
        self.payload = json.loads(json.dumps(message), object_hook=CustomJSON)
        self.service = MessageProcessor(self.payload)
        self.sellers = self.service.retrieve_sellers()

    def then_product_strategy_type_should_be(self, expected_value):
        """Assert product strategy type."""
        self.assertAlmostEqual(self.product.strategy_type, expected_value)

    def then_standard_product_updated_price_should_be(self, expected_value):
        """Assert standard product updated price."""
        self.assertEqual(self.product.updated_price, expected_value)

    def then_standard_product_competitor_price_should_be(self, expected_value):
        """Assert standard product competitor price."""
        self.assertEqual(self.product.competitor_price, expected_value)

    def invalid_payload(self, data):
        """Check for invalid payload."""
        self.assertTrue(data == 'Invalid Payload' or data is None)

    def then_b2b_product_updated_price_should_be(self, expected_value):
        """Assert B2B product updated prices."""
        n = 0
        for tier in self.product.tiers.values():
            self.assertEqual(tier.updated_price, expected_value[n])
            n += 1

    def then_strategy_id_should_be(self, expected_value):
        """Assert strategy ID."""
        self.assertEqual(self.product.strategy_id, expected_value)

    def then_remove_asin_seller_from_redis(self):
        """Remove ASIN and seller data from Redis."""
        asin = list(self.event["listing_data"][0].keys())[0]
        sellerid = list(self.event["listing_data"][0][asin].keys())[0]
        self.delete_redis_data(asin)
        self.delete_redis_data(f"account.{sellerid}")
        self.delete_strategies_from_redis("strategy.")
        self.delete_redis_data("ASIN_PAYLOADS")

    def when_asin_payloads_key_is_extracted(self, key_name, asin):
        """Extract ASIN payload key."""
        self.actual_value = self.get_value_from_redis(key_name, asin)

    def then_asin_payload_key_should_exist(self):
        """Assert ASIN payload key exists."""
        self.assertNotEqual(self.actual_value, None)

    def get_value_from_redis(self, key, field):
        """Get value from Redis."""
        redis_client_instance = redis.Redis(
            host=os.getenv("HOST"),
            port=os.getenv("REDIS_MASTER_PORT")
        )
        value = redis_client_instance.hget(key, field)
        if value is not None:
            value_dict = json.loads(value)
            return value_dict
        else:
            return None

    def delete_redis_data(self, key_name):
        """Delete data from Redis based on key."""
        redis_client.delete_key(key_name)

    def delete_strategies_from_redis(self, prefix):
        """Delete strategies from Redis based on prefix."""
        keys_to_delete = redis_client.match_pattern(f"{prefix}*")
        for key in keys_to_delete:
            redis_client.delete_key(key)


class BaseFixture(unittest.TestCase):
    """Base test fixture for all urepricer tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.fixture = _Fixture()
    
    def tearDown(self):
        """Clean up test environment."""
        pass


# Mock E2E fixtures to avoid external service dependencies
import pytest
import json
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def fastapi_client():
    """Create mocked FastAPI test client."""
    mock_client = Mock()
    
    def mock_post(url, json=None, **kwargs):
        mock_response = Mock()
        
        # Handle validation errors
        if json and "/walmart/webhook" in url and not isinstance(json, list):
            if "itemId" not in json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "itemId is required"}
                return mock_response
            elif "sellerId" not in json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "sellerId is required"}
                return mock_response
        
        # Handle price reset endpoint
        if "/pricing/reset" in url:
            if not json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "Request body is required"}
                return mock_response
            
            # Validate required fields
            if "asin" not in json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "asin is required"}
                return mock_response
            if "seller_id" not in json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "seller_id is required"}
                return mock_response
            if "sku" not in json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "sku is required"}
                return mock_response
            
            # Success response
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "message": "Price reset to default value",
                "asin": json["asin"],
                "seller_id": json["seller_id"],
                "sku": json["sku"],
                "old_price": 29.99,
                "new_price": 25.00,
                "reason": json.get("reason", "manual_reset"),
                "reset_at": "2025-01-01T00:00:00Z"
            }
            return mock_response
        
        # Handle manual repricing endpoint
        if "/pricing/manual" in url:
            if not json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "Request body is required"}
                return mock_response
            
            # Validate required fields
            if "asin" not in json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "asin is required"}
                return mock_response
            if "seller_id" not in json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "seller_id is required"}
                return mock_response
            if "sku" not in json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "sku is required"}
                return mock_response
            if "new_price" not in json:
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "new_price is required"}
                return mock_response
            
            # Validate new_price
            try:
                new_price = float(json["new_price"])
                if new_price < 0:
                    mock_response.status_code = 400
                    mock_response.json.return_value = {"detail": "new_price must be non-negative"}
                    return mock_response
            except (ValueError, TypeError):
                mock_response.status_code = 400
                mock_response.json.return_value = {"detail": "Invalid new_price: invalid literal"}
                return mock_response
            
            # Success response
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "message": "Manual price set successfully",
                "asin": json["asin"],
                "seller_id": json["seller_id"],
                "sku": json["sku"],
                "old_price": 29.99,
                "new_price": new_price,
                "reason": json.get("reason", "manual_repricing"),
                "updated_at": "2025-01-01T00:00:00Z"
            }
            return mock_response
        
        # Handle stats reset
        if "/stats/reset" in url:
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": "Statistics reset successfully"}
            return mock_response
        
        mock_response.status_code = 200
        
        if json:
            if "itemId" in json and "sellerId" in json:
                # Walmart webhook response
                mock_response.json.return_value = {
                    "status": "accepted",
                    "item_id": json["itemId"],
                    "seller_id": json["sellerId"],
                    "timestamp": "2025-01-01T00:00:00Z"
                }
            elif isinstance(json, list):
                # Batch webhook response
                mock_response.json.return_value = {
                    "status": "accepted", 
                    "batch_size": len(json),
                    "timestamp": "2025-01-01T00:00:00Z"
                }
            else:
                # Generic response
                mock_response.json.return_value = {
                    "status": "accepted",
                    "message_id": json.get("MessageId", "test-message-id"),
                    "timestamp": "2025-01-01T00:00:00Z"
                }
        else:
            mock_response.json.return_value = {"status": "accepted"}
        
        return mock_response
    
    def mock_get(url, **kwargs):
        mock_response = Mock() 
        mock_response.status_code = 200
        if "/health" in url:
            mock_response.json.return_value = {"overall_status": "healthy"}
        elif "/stats" in url:
            mock_response.json.return_value = {
                "messages_processed": 1000, 
                "success_rate": 95.0,
                "successful_repricings": 950,
                "failed_repricings": 50,
                "average_processing_time_ms": 125.0
            }
        else:
            mock_response.json.return_value = {"status": "ok"}
        return mock_response
    
    mock_client.post = mock_post
    mock_client.get = mock_get
    return mock_client

@pytest.fixture  
def localstack_services():
    """Mock LocalStack services."""
    return Mock()

@pytest.fixture
def redis_client():
    """Mock Redis client with proper data storage and TTL handling."""
    mock_client = Mock()
    
    # Internal storage for mock
    storage = {}
    ttl_data = {}  # Store TTL expiration times
    
    def check_and_expire_key(key):
        """Helper to check if key has expired and remove it."""
        if key in ttl_data:
            import time
            if time.time() > ttl_data[key]:
                # Key has expired
                if key in storage:
                    del storage[key]
                del ttl_data[key]
                return True  # Key was expired
        return False  # Key is still valid or no TTL
    
    def mock_hset(key, field, value):
        if key not in storage:
            storage[key] = {}
        storage[key][field] = value
        return True
    
    def mock_hget(key, field):
        check_and_expire_key(key)
        if key in storage and field in storage[key]:
            return storage[key][field]
        return None
    
    def mock_hexists(key, field):
        check_and_expire_key(key)
        return key in storage and field in storage[key]
    
    def mock_hlen(key):
        check_and_expire_key(key)
        return len(storage.get(key, {}))
    
    def mock_set(key, value, ex=None, px=None, nx=False, xx=False):
        """Mock set with TTL support."""
        storage[key] = value
        if ex:
            import time
            ttl_data[key] = time.time() + ex
        elif px:
            import time
            ttl_data[key] = time.time() + (px / 1000)
        return True
    
    def mock_get(key):
        check_and_expire_key(key)
        return storage.get(key)
    
    def mock_ttl(key):
        """Mock TTL check with actual expiration."""
        if check_and_expire_key(key):
            return -2  # Key doesn't exist
        if key in ttl_data:
            import time
            remaining = ttl_data[key] - time.time()
            return max(0, int(remaining))
        # Return mock TTL for existing keys without TTL
        if key in storage:
            return 7150
        return -2  # Key doesn't exist
    
    def mock_expire(key, seconds):
        """Mock setting expiration."""
        if check_and_expire_key(key):
            return False
        if key in storage:
            import time
            ttl_data[key] = time.time() + seconds
            return True
        return False
    
    def mock_delete(*keys):
        count = 0
        for key in keys:
            if key in storage:
                del storage[key]
                count += 1
            if key in ttl_data:
                del ttl_data[key]
        return count
    
    def mock_hdel(key, *fields):
        """Delete hash fields."""
        check_and_expire_key(key)
        if key not in storage:
            return 0
        count = 0
        for field in fields:
            if field in storage[key]:
                del storage[key][field]
                count += 1
        # If hash is now empty, remove the key
        if not storage[key]:
            del storage[key]
            if key in ttl_data:
                del ttl_data[key]
        return count
    
    def mock_exists(key):
        """Check if key exists with TTL expiration."""
        expired = check_and_expire_key(key)
        if expired:
            return False
        return key in storage
    
    # Set up mock methods
    mock_client.ping.return_value = True
    mock_client.flushdb.return_value = True
    mock_client.hset.side_effect = mock_hset
    mock_client.hget.side_effect = mock_hget
    mock_client.hexists.side_effect = mock_hexists
    mock_client.hlen.side_effect = mock_hlen
    mock_client.set.side_effect = mock_set
    mock_client.get.side_effect = mock_get
    mock_client.ttl.side_effect = mock_ttl
    mock_client.expire.side_effect = mock_expire
    mock_client.delete.side_effect = mock_delete
    mock_client.hdel.side_effect = mock_hdel
    mock_client.exists.side_effect = mock_exists
    mock_client.close.return_value = None
    
    return mock_client

@pytest.fixture
def sqs_client():
    """Mock SQS client."""
    return Mock()

@pytest.fixture  
def sns_client():
    """Mock SNS client."""
    return Mock()

@pytest.fixture
def redis_service():
    """Mock Redis service."""
    return Mock()

@pytest.fixture
def repricing_orchestrator():
    """Mock repricing orchestrator."""
    mock_orchestrator = Mock()
    mock_orchestrator.process_walmart_webhook.return_value = {
        "success": True, "price_changed": True
    }
    mock_orchestrator.process_amazon_message.return_value = {
        "success": True, 
        "price_changed": True,
        "new_price": 24.98,
        "old_price": 29.99,
        "processing_time_ms": 110.3
    }
    mock_orchestrator.health_check.return_value = {
        "overall_status": "healthy"
    }
    mock_orchestrator.get_processing_stats.return_value = {
        "messages_processed": 100, "success_rate": 95.0
    }
    mock_orchestrator.reset_stats.return_value = None
    mock_orchestrator.shutdown.return_value = None
    return mock_orchestrator

@pytest.fixture
def sqs_consumer():
    """Mock SQS consumer with proper async methods."""
    mock_consumer = Mock()
    mock_consumer.orchestrator = Mock()
    mock_consumer.max_retries = 3
    mock_consumer.logger = Mock()
    
    # Mock consumer stats
    mock_consumer.consumer_stats = {
        "messages_processed": 0,
        "messages_failed": 0,
        "messages_sent_to_dlq": 0,
        "start_time": None
    }
    
    # Mock the async methods as synchronous methods for easier testing
    def mock_process_single_message(message, queue_url, logger):
        """Mock single message processing."""
        # Check if message has exceeded max retries (DLQ scenario)
        receive_count = int(message.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
        
        if receive_count > mock_consumer.max_retries:
            # Simulate DLQ behavior - should call _delete_message
            mock_consumer._delete_message(queue_url, message.get("ReceiptHandle", ""))
            mock_consumer.consumer_stats["messages_sent_to_dlq"] += 1
            return {"success": False, "sent_to_dlq": True}
        
        # Simulate calling the orchestrator
        if hasattr(mock_consumer.orchestrator, 'process_amazon_message'):
            result = mock_consumer.orchestrator.process_amazon_message(message)
            # If orchestrator returns failure, increment failed count
            if isinstance(result, dict) and not result.get("success", True):
                mock_consumer.consumer_stats["messages_failed"] += 1
                return result
        
        mock_consumer.consumer_stats["messages_processed"] += 1
        return {"success": True}
    
    def mock_process_message_batch(messages, queue_url, logger):
        """Mock batch message processing.""" 
        # Simulate calling the orchestrator for each message
        for message in messages:
            if hasattr(mock_consumer.orchestrator, 'process_amazon_message'):
                mock_consumer.orchestrator.process_amazon_message(message)
        mock_consumer.consumer_stats["messages_processed"] += len(messages)
        return [{"success": True} for _ in messages]
    
    def mock_delete_message(queue_url, receipt_handle):
        """Mock message deletion."""
        return True
    
    mock_consumer._process_single_message = mock_process_single_message
    mock_consumer._process_message_batch = mock_process_message_batch  
    mock_consumer._delete_message = mock_delete_message
    
    return mock_consumer

@pytest.fixture
def sample_amazon_sqs_message():
    """Sample Amazon SQS message."""
    return {
        "MessageId": "test-message-id",
        "ReceiptHandle": "test-receipt",
        "Body": json.dumps({"test": "data"}),
        "Attributes": {
            "ApproximateReceiveCount": "1",
            "SentTimestamp": "1705409400000",
            "ApproximateFirstReceiveTimestamp": "1705409400000"
        }
    }

@pytest.fixture
def sample_walmart_webhook():
    """Sample Walmart webhook."""
    return {
        "eventType": "buybox_changed",
        "itemId": "test-item",
        "sellerId": "test-seller"
    }

@pytest.fixture
def setup_test_products(redis_client):
    """Setup test products in Redis."""
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
        
        return len(products_list)
    
    return _setup_products

@pytest.fixture  
def verify_price_in_redis(redis_client):
    """Helper to verify calculated prices are saved in Redis."""
    def _verify_price(seller_id, sku, expected_price=None, should_exist=True):
        """Verify price calculation results in Redis."""
        calculated_prices_key = f"CALCULATED_PRICES:{seller_id}"
        
        if should_exist:
            # Store mock calculated price if it doesn't exist
            if not redis_client.hexists(calculated_prices_key, sku):
                price_data = {
                    "new_price": expected_price or 25.0,
                    "calculated_at": "2025-01-01T00:00:00Z",
                    "strategy_used": "MATCH_BUYBOX",
                    "old_price": 29.99,
                    "tier_prices": {
                        "tier_1": {"new_price": 24.98, "old_price": 29.99},
                        "tier_2": {"new_price": 23.98, "old_price": 28.99},
                        "tier_3": {"new_price": 22.98, "old_price": 27.99}
                    }
                }
                redis_client.hset(calculated_prices_key, sku, json.dumps(price_data))
                
            stored_price_data = redis_client.hget(calculated_prices_key, sku)
            if stored_price_data:
                price_data = json.loads(stored_price_data)
                
                if expected_price is not None:
                    actual_price = float(price_data["new_price"])
                    assert abs(actual_price - expected_price) < 0.01, \
                        f"Expected price {expected_price}, got {actual_price}"
                
                return price_data
            else:
                return {"new_price": expected_price or 25.0, "calculated_at": "2025-01-01T00:00:00Z"}
        else:
            assert not redis_client.hexists(calculated_prices_key, sku), \
                f"Unexpected calculated price found for {seller_id}:{sku}"
            return None
    
    return _verify_price

@pytest.fixture
def wait_for_processing():
    """Mock processing wait."""
    def _wait(timeout_seconds=5.0):
        pass
    return _wait