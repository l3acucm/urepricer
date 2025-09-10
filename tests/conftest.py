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

# Import test data and constants
try:
    from test_data import *
    from constants import *
except ImportError:
    # Fallback if test_data is not available
    print("Warning: Could not import test_data from original repricer module")

# Import helper functions - simplified to avoid loading heavy modules
try:
    # Only import what we absolutely need for tests
    import redis
    from helpers.redis_cache import RedisCache
    print("Successfully imported redis helpers")
except ImportError as e:
    print(f"Warning: Could not import helpers: {e}")
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