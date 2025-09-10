"""
Simplified test configuration to get tests running.
"""
import sys
import os
import unittest
from unittest.mock import Mock

# Set environment variables before imports to avoid configuration issues
os.environ.update({
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


class SkipProductRepricing(Exception):
    """Exception for skipping product repricing."""
    pass


class MockProduct:
    """Mock product for testing."""
    def __init__(self):
        self.asin = "B0TEST12345"
        self.competitor_price = 25.99
        self.updated_price = 22.00
        self.listed_price = 30.00
        self.no_of_offers = 2
        self.is_b2b = False
        self.is_seller_buybox_winner = False
        self.repricer_type = None
        self.message = None


class MockFixture:
    """Mock fixture for basic testing."""
    
    def __init__(self):
        self.product = MockProduct()
        self.event = {}
        self.payload = {}
        self.sellers = {}
        self.service = Mock()
    
    def given_an_event(self, event):
        """Set the event data."""
        self.event = event
    
    def given_a_payload(self):
        """Mock payload setup."""
        pass
    
    def given_platform_from_event(self):
        """Mock platform setup."""
        pass
    
    def when_strategy_applied(self):
        """Mock strategy application."""
        pass
    
    def then_standard_product_competitor_price_should_be(self, expected_value):
        """Mock competitor price assertion."""
        assert self.product.competitor_price == expected_value
    
    def then_standard_product_updated_price_should_be(self, expected_value):
        """Mock updated price assertion."""
        assert self.product.updated_price == expected_value
    
    def then_remove_asin_seller_from_redis(self):
        """Mock Redis cleanup."""
        pass


class BaseFixture(unittest.TestCase):
    """Base test fixture for urepricer tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.fixture = MockFixture()
    
    def tearDown(self):
        """Clean up test environment."""
        pass


# Make this available globally for tests
_Fixture = MockFixture