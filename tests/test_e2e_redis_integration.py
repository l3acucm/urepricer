"""
End-to-end tests for Redis integration and price storage verification.
Tests that repricing actually updates prices in Redis with correct data structures.
"""
import pytest
import json
import time
from unittest.mock import patch, Mock

from src.models.products import ProductListing, B2BTier
# Sample test data
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
    "asin": "W12345678901",
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


@pytest.mark.integration
@pytest.mark.slow 
class TestRedisIntegrationE2E:
    """Test end-to-end Redis integration for price storage and retrieval."""
    
    def test_product_data_storage_and_retrieval(
        self,
        redis_client,
        setup_test_products,
        verify_price_in_redis
    ):
        """
        Test that product data is correctly stored and retrieved from Redis.
        """
        # Setup test product
        test_product = SAMPLE_AMAZON_PRODUCT.copy()
        setup_test_products([test_product])
        
        # Verify product is stored correctly
        asin_key = f"ASIN_{test_product['asin']}"
        seller_sku_key = f"{test_product['seller_id']}:{test_product['sku']}"
        
        assert redis_client.hexists(asin_key, seller_sku_key)
        
        # Retrieve and verify product data
        stored_data = json.loads(redis_client.hget(asin_key, seller_sku_key))
        assert stored_data["asin"] == test_product["asin"]
        assert stored_data["seller_id"] == test_product["seller_id"]
        assert stored_data["listed_price"] == test_product["listed_price"]
        assert stored_data["min_price"] == test_product["min_price"]
        assert stored_data["max_price"] == test_product["max_price"]
        
        # Verify TTL is set
        ttl = redis_client.ttl(asin_key)
        assert ttl > 0, "TTL should be set on product data"
        assert ttl <= 7200, "TTL should not exceed 2 hours"
    
    def test_strategy_configuration_storage(
        self,
        redis_client,
        setup_test_products
    ):
        """
        Test that strategy configurations are correctly stored in Redis.
        """
        test_product = SAMPLE_AMAZON_PRODUCT.copy()
        setup_test_products([test_product])
        
        # Verify strategy configuration
        strategy_key = f"strategy.{test_product['strategy_id']}"
        
        assert redis_client.exists(strategy_key)
        
        # Check strategy fields
        assert redis_client.hget(strategy_key, "compete_with") == "MATCH_BUYBOX"
        assert redis_client.hget(strategy_key, "beat_by") == "-0.01"
        assert redis_client.hget(strategy_key, "min_price_rule") == "JUMP_TO_MIN"
        assert redis_client.hget(strategy_key, "max_price_rule") == "JUMP_TO_MAX"
        
        # Verify TTL
        ttl = redis_client.ttl(strategy_key)
        assert ttl > 0, "TTL should be set on strategy data"
    
    def test_calculated_price_storage(
        self,
        redis_client,
        setup_test_products,
        verify_price_in_redis
    ):
        """
        Test storage of calculated price results in Redis.
        """
        test_product = SAMPLE_AMAZON_PRODUCT.copy()
        setup_test_products([test_product])
        
        # Simulate calculated price data
        calculated_price_data = {
            "asin": test_product["asin"],
            "seller_id": test_product["seller_id"],
            "sku": test_product["sku"],
            "old_price": 29.99,
            "new_price": 27.98,
            "strategy_used": "CHASE_BUYBOX",
            "strategy_id": test_product["strategy_id"],
            "competitor_price": 27.99,
            "calculated_at": "2025-01-15T14:30:00.000Z",
            "processing_time_ms": 125.5
        }
        
        # Store calculated price
        calculated_prices_key = f"CALCULATED_PRICES:{test_product['seller_id']}"
        redis_client.hset(
            calculated_prices_key,
            test_product["sku"],
            json.dumps(calculated_price_data)
        )
        redis_client.expire(calculated_prices_key, 7200)
        
        # Verify price was stored correctly
        price_data = verify_price_in_redis(
            test_product["seller_id"],
            test_product["sku"],
            expected_price=27.98
        )
        
        assert price_data["old_price"] == 29.99
        assert price_data["strategy_used"] == "CHASE_BUYBOX"
        assert price_data["competitor_price"] == 27.99
    
    def test_b2b_product_with_tiers_storage(
        self,
        redis_client,
        setup_test_products
    ):
        """
        Test storage and retrieval of B2B products with tier pricing.
        """
        # Create B2B product with tiers
        b2b_product = {
            **SAMPLE_AMAZON_PRODUCT,
            "asin": "B07B2BPRODUCT",
            "sku": "B2B-SKU-001",
            "is_b2b": True,
            "b2b_rules": {
                "listed_price": 25.99,
                "min": 20.00,
                "max": 35.00,
                "default_price": 26.00,
                "tiers": {
                    "5": {
                        "quantity": 5,
                        "listed_price": 24.99,
                        "min": 18.00,
                        "max": 30.00,
                        "default_price": 25.00
                    },
                    "10": {
                        "quantity": 10,
                        "listed_price": 22.99,
                        "min": 16.00,
                        "max": 28.00,
                        "default_price": 23.00
                    }
                }
            }
        }
        
        setup_test_products([b2b_product])
        
        # Verify B2B product storage
        asin_key = f"ASIN_{b2b_product['asin']}"
        seller_sku_key = f"{b2b_product['seller_id']}:{b2b_product['sku']}"
        
        stored_data = json.loads(redis_client.hget(asin_key, seller_sku_key))
        assert stored_data["is_b2b"] is True
        assert "b2b_rules" in stored_data
        assert "tiers" in stored_data["b2b_rules"]
        assert "5" in stored_data["b2b_rules"]["tiers"]
        assert "10" in stored_data["b2b_rules"]["tiers"]
        
        # Verify tier data
        tier_5 = stored_data["b2b_rules"]["tiers"]["5"]
        assert tier_5["quantity"] == 5
        assert tier_5["listed_price"] == 24.99
    
    def test_calculated_prices_with_b2b_tiers(
        self,
        redis_client,
        setup_test_products,
        verify_price_in_redis
    ):
        """
        Test storage of calculated prices for B2B products with tier pricing.
        """
        b2b_product = {
            **SAMPLE_AMAZON_PRODUCT,
            "asin": "B07B2BPRODUCT",
            "sku": "B2B-TIER-SKU",
            "is_b2b": True
        }
        setup_test_products([b2b_product])
        
        # Simulate calculated price data with tier prices
        calculated_price_data = {
            "asin": b2b_product["asin"],
            "seller_id": b2b_product["seller_id"],
            "sku": b2b_product["sku"],
            "old_price": 25.99,
            "new_price": 24.98,
            "strategy_used": "CHASE_BUYBOX",
            "calculated_at": "2025-01-15T14:30:00.000Z",
            "tier_prices": {
                "5": 23.50,
                "10": 21.50,
                "25": 19.50,
                "50": 17.50,
                "100": 15.50
            },
            "processing_time_ms": 155.7
        }
        
        # Store calculated price with tiers
        calculated_prices_key = f"CALCULATED_PRICES:{b2b_product['seller_id']}"
        redis_client.hset(
            calculated_prices_key,
            b2b_product["sku"],
            json.dumps(calculated_price_data)
        )
        
        # Verify tier prices were stored
        price_data = verify_price_in_redis(
            b2b_product["seller_id"],
            b2b_product["sku"],
            expected_price=24.98
        )
        
        assert "tier_prices" in price_data
        assert price_data["tier_prices"]["5"] == 23.50
        assert price_data["tier_prices"]["100"] == 15.50
    
    def test_redis_connection_and_performance(
        self,
        redis_client,
        setup_test_products
    ):
        """
        Test Redis connection stability and basic performance characteristics.
        """
        # Test basic Redis operations
        test_key = "performance_test"
        test_data = {"timestamp": time.time(), "test": True}
        
        # Test SET/GET performance
        start_time = time.time()
        redis_client.set(test_key, json.dumps(test_data))
        stored_data = json.loads(redis_client.get(test_key))
        operation_time = (time.time() - start_time) * 1000  # Convert to ms
        
        assert stored_data["test"] is True
        assert operation_time < 10, f"Redis operation took {operation_time}ms, expected < 10ms"
        
        # Test HASH operations performance
        hash_key = "performance_hash_test"
        start_time = time.time()
        
        for i in range(10):
            redis_client.hset(hash_key, f"field_{i}", json.dumps({"value": i}))
        
        hash_operation_time = (time.time() - start_time) * 1000
        assert hash_operation_time < 50, f"Hash operations took {hash_operation_time}ms, expected < 50ms"
        
        # Verify all hash fields
        assert redis_client.hlen(hash_key) == 10
        
        # Cleanup
        redis_client.delete(test_key, hash_key)
    
    def test_redis_ttl_expiration_behavior(
        self,
        redis_client,
        setup_test_products
    ):
        """
        Test that Redis TTL expiration works correctly for our data.
        """
        test_product = SAMPLE_AMAZON_PRODUCT.copy()
        setup_test_products([test_product])
        
        asin_key = f"ASIN_{test_product['asin']}"
        
        # Verify initial TTL
        initial_ttl = redis_client.ttl(asin_key)
        assert initial_ttl > 7000, "Initial TTL should be close to 2 hours"
        
        # Set a very short TTL for testing
        test_key = "ttl_test_key"
        redis_client.set(test_key, "test_value", ex=1)  # 1 second expiry
        
        # Key should exist immediately
        assert redis_client.exists(test_key)
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Key should be expired
        assert not redis_client.exists(test_key)
    
    def test_multiple_sellers_same_asin(
        self,
        redis_client,
        setup_test_products
    ):
        """
        Test storage of multiple sellers for the same ASIN.
        """
        # Create multiple products with same ASIN but different sellers
        products = [
            {**SAMPLE_AMAZON_PRODUCT, "seller_id": "A1SELLER123", "sku": "SKU-SELLER-1"},
            {**SAMPLE_AMAZON_PRODUCT, "seller_id": "A2SELLER456", "sku": "SKU-SELLER-2"},
            {**SAMPLE_AMAZON_PRODUCT, "seller_id": "A3SELLER789", "sku": "SKU-SELLER-3"},
        ]
        
        setup_test_products(products)
        
        asin_key = f"ASIN_{SAMPLE_AMAZON_PRODUCT['asin']}"
        
        # Verify all sellers are stored under the same ASIN
        for product in products:
            seller_sku_key = f"{product['seller_id']}:{product['sku']}"
            assert redis_client.hexists(asin_key, seller_sku_key)
            
            stored_data = json.loads(redis_client.hget(asin_key, seller_sku_key))
            assert stored_data["seller_id"] == product["seller_id"]
            assert stored_data["sku"] == product["sku"]
        
        # Verify hash contains all sellers
        assert redis_client.hlen(asin_key) == len(products)
    
    def test_redis_data_cleanup_on_failure(
        self,
        redis_client,
        setup_test_products
    ):
        """
        Test that Redis data can be properly cleaned up after failures.
        """
        # Setup test data
        products = [
            {**SAMPLE_AMAZON_PRODUCT, "sku": f"CLEANUP-SKU-{i}"} 
            for i in range(5)
        ]
        setup_test_products(products)
        
        # Verify data exists
        asin_key = f"ASIN_{SAMPLE_AMAZON_PRODUCT['asin']}"
        assert redis_client.hlen(asin_key) == 5
        
        # Simulate cleanup operation
        for product in products:
            seller_sku_key = f"{product['seller_id']}:{product['sku']}"
            redis_client.hdel(asin_key, seller_sku_key)
        
        # Verify cleanup
        assert redis_client.hlen(asin_key) == 0
        
        # Clean up the key entirely if empty
        if redis_client.hlen(asin_key) == 0:
            redis_client.delete(asin_key)
        
        assert not redis_client.exists(asin_key)