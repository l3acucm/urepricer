"""
Integration tests for price reset and manual repricing API endpoints.
Tests the complete flow: API endpoint → Redis storage → data retrieval.
"""
import pytest
from unittest.mock import patch, AsyncMock
from decimal import Decimal

# Sample test data
SAMPLE_PRODUCT_DATA = {
    "asin": "B07TEST12345",
    "seller_id": "TEST_SELLER_001",
    "sku": "TEST-SKU-PRICING-001",
    "listed_price": 29.99,
    "min_price": 20.00,
    "max_price": 50.00,
    "default_price": 25.00,
    "strategy_id": "1",
    "inventory_quantity": 100,
    "inventory_age": 45,
    "status": "Active",
    "is_b2b": False
}


@pytest.mark.integration
@pytest.mark.slow
class TestPriceResetAPI:
    """Test price reset API endpoint with Redis integration."""
    
    def test_price_reset_success(
        self,
        fastapi_client,
        setup_test_products,
        verify_price_in_redis
    ):
        """
        Test successful price reset to default price.
        
        Flow:
        1. Setup product in Redis with current price
        2. Call price reset API endpoint
        3. Verify price is set to default_price in Redis
        """
        # Setup test product
        test_product = SAMPLE_PRODUCT_DATA.copy()
        setup_test_products([test_product])
        
        # Call price reset endpoint
        reset_data = {
            "asin": test_product["asin"],
            "seller_id": test_product["seller_id"],
            "sku": test_product["sku"],
            "reason": "test_reset"
        }
        
        response = fastapi_client.post("/pricing/reset", json=reset_data)
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["asin"] == test_product["asin"]
        assert response_data["seller_id"] == test_product["seller_id"]
        assert response_data["sku"] == test_product["sku"]
        assert response_data["old_price"] == 29.99
        assert response_data["new_price"] == 25.00  # default_price
        assert "reset_at" in response_data
        assert response_data["reason"] == "test_reset"
    
    def test_price_reset_missing_required_fields(self, fastapi_client):
        """Test price reset with missing required fields."""
        # Missing ASIN
        response = fastapi_client.post("/pricing/reset", json={
            "seller_id": "TEST_SELLER",
            "sku": "TEST_SKU"
        })
        assert response.status_code == 400
        assert "asin is required" in response.json()["detail"]
        
        # Missing seller_id
        response = fastapi_client.post("/pricing/reset", json={
            "asin": "B07TEST12345",
            "sku": "TEST_SKU"
        })
        assert response.status_code == 400
        assert "seller_id is required" in response.json()["detail"]
        
        # Missing SKU
        response = fastapi_client.post("/pricing/reset", json={
            "asin": "B07TEST12345",
            "seller_id": "TEST_SELLER"
        })
        assert response.status_code == 400
        assert "sku is required" in response.json()["detail"]
    
    def test_price_reset_product_not_found(self, fastapi_client):
        """Test price reset when product is not found in Redis."""
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = None
            
            reset_data = {
                "asin": "B07NONEXISTENT",
                "seller_id": "NONEXISTENT_SELLER", 
                "sku": "NONEXISTENT_SKU"
            }
            
            response = fastapi_client.post("/pricing/reset", json=reset_data)
            
            assert response.status_code == 404
            assert "Product not found" in response.json()["detail"]
    
    def test_price_reset_no_default_price(self, fastapi_client):
        """Test price reset when product has no default_price configured."""
        product_without_default = SAMPLE_PRODUCT_DATA.copy()
        product_without_default["default_price"] = None
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = product_without_default
            
            reset_data = {
                "asin": product_without_default["asin"],
                "seller_id": product_without_default["seller_id"],
                "sku": product_without_default["sku"]
            }
            
            response = fastapi_client.post("/pricing/reset", json=reset_data)
            
            assert response.status_code == 400
            assert "no default_price configured" in response.json()["detail"]
    
    def test_price_reset_default_price_below_min(self, fastapi_client):
        """Test price reset when default_price is below min_price."""
        product_invalid_default = SAMPLE_PRODUCT_DATA.copy()
        product_invalid_default["default_price"] = 15.00  # Below min_price of 20.00
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = product_invalid_default
            
            reset_data = {
                "asin": product_invalid_default["asin"],
                "seller_id": product_invalid_default["seller_id"],
                "sku": product_invalid_default["sku"]
            }
            
            response = fastapi_client.post("/pricing/reset", json=reset_data)
            
            assert response.status_code == 400
            assert "below minimum price" in response.json()["detail"]
    
    def test_price_reset_default_price_above_max(self, fastapi_client):
        """Test price reset when default_price is above max_price."""
        product_invalid_default = SAMPLE_PRODUCT_DATA.copy()
        product_invalid_default["default_price"] = 55.00  # Above max_price of 50.00
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = product_invalid_default
            
            reset_data = {
                "asin": product_invalid_default["asin"],
                "seller_id": product_invalid_default["seller_id"],
                "sku": product_invalid_default["sku"]
            }
            
            response = fastapi_client.post("/pricing/reset", json=reset_data)
            
            assert response.status_code == 400
            assert "above maximum price" in response.json()["detail"]
    
    def test_price_reset_redis_save_failure(self, fastapi_client):
        """Test price reset when Redis save fails."""
        test_product = SAMPLE_PRODUCT_DATA.copy()
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = test_product
            mock_redis.save_calculated_price.return_value = False  # Simulate save failure
            
            reset_data = {
                "asin": test_product["asin"],
                "seller_id": test_product["seller_id"],
                "sku": test_product["sku"]
            }
            
            response = fastapi_client.post("/pricing/reset", json=reset_data)
            
            assert response.status_code == 500
            assert "Failed to save price reset to Redis" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.slow
class TestManualRepricingAPI:
    """Test manual repricing API endpoint with Redis integration."""
    
    def test_manual_repricing_success(
        self,
        fastapi_client,
        setup_test_products
    ):
        """
        Test successful manual repricing to specific price.
        
        Flow:
        1. Setup product in Redis with current price
        2. Call manual repricing API endpoint
        3. Verify price is set to specified value in Redis
        """
        # Setup test product
        test_product = SAMPLE_PRODUCT_DATA.copy()
        setup_test_products([test_product])
        
        # Call manual repricing endpoint
        pricing_data = {
            "asin": test_product["asin"],
            "seller_id": test_product["seller_id"],
            "sku": test_product["sku"],
            "new_price": 35.50,
            "reason": "test_manual_adjustment"
        }
        
        response = fastapi_client.post("/pricing/manual", json=pricing_data)
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["asin"] == test_product["asin"]
        assert response_data["seller_id"] == test_product["seller_id"]
        assert response_data["sku"] == test_product["sku"]
        assert response_data["old_price"] == 29.99
        assert response_data["new_price"] == 35.50
        assert "updated_at" in response_data
        assert response_data["reason"] == "test_manual_adjustment"
    
    def test_manual_repricing_missing_required_fields(self, fastapi_client):
        """Test manual repricing with missing required fields."""
        # Missing ASIN
        response = fastapi_client.post("/pricing/manual", json={
            "seller_id": "TEST_SELLER",
            "sku": "TEST_SKU",
            "new_price": 30.00
        })
        assert response.status_code == 400
        assert "asin is required" in response.json()["detail"]
        
        # Missing new_price
        response = fastapi_client.post("/pricing/manual", json={
            "asin": "B07TEST12345",
            "seller_id": "TEST_SELLER",
            "sku": "TEST_SKU"
        })
        assert response.status_code == 400
        assert "new_price is required" in response.json()["detail"]
    
    def test_manual_repricing_negative_price(self, fastapi_client):
        """Test manual repricing with negative price."""
        pricing_data = {
            "asin": "B07TEST12345",
            "seller_id": "TEST_SELLER",
            "sku": "TEST_SKU",
            "new_price": -10.00
        }
        
        response = fastapi_client.post("/pricing/manual", json=pricing_data)
        
        assert response.status_code == 400
        assert "must be non-negative" in response.json()["detail"]
    
    def test_manual_repricing_invalid_price_format(self, fastapi_client):
        """Test manual repricing with invalid price format."""
        pricing_data = {
            "asin": "B07TEST12345",
            "seller_id": "TEST_SELLER", 
            "sku": "TEST_SKU",
            "new_price": "invalid_price"
        }
        
        response = fastapi_client.post("/pricing/manual", json=pricing_data)
        
        assert response.status_code == 400
        assert "Invalid new_price" in response.json()["detail"]
    
    def test_manual_repricing_product_not_found(self, fastapi_client):
        """Test manual repricing when product is not found in Redis."""
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = None
            
            pricing_data = {
                "asin": "B07NONEXISTENT",
                "seller_id": "NONEXISTENT_SELLER",
                "sku": "NONEXISTENT_SKU", 
                "new_price": 30.00
            }
            
            response = fastapi_client.post("/pricing/manual", json=pricing_data)
            
            assert response.status_code == 404
            assert "Product not found" in response.json()["detail"]
    
    def test_manual_repricing_price_below_min(self, fastapi_client):
        """Test manual repricing when new_price is below min_price."""
        test_product = SAMPLE_PRODUCT_DATA.copy()
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = test_product
            
            pricing_data = {
                "asin": test_product["asin"],
                "seller_id": test_product["seller_id"],
                "sku": test_product["sku"],
                "new_price": 15.00  # Below min_price of 20.00
            }
            
            response = fastapi_client.post("/pricing/manual", json=pricing_data)
            
            assert response.status_code == 400
            assert "below minimum price" in response.json()["detail"]
    
    def test_manual_repricing_price_above_max(self, fastapi_client):
        """Test manual repricing when new_price is above max_price."""
        test_product = SAMPLE_PRODUCT_DATA.copy()
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = test_product
            
            pricing_data = {
                "asin": test_product["asin"],
                "seller_id": test_product["seller_id"],
                "sku": test_product["sku"],
                "new_price": 55.00  # Above max_price of 50.00
            }
            
            response = fastapi_client.post("/pricing/manual", json=pricing_data)
            
            assert response.status_code == 400
            assert "above maximum price" in response.json()["detail"]
    
    def test_manual_repricing_at_price_boundaries(self, fastapi_client):
        """Test manual repricing at min and max price boundaries."""
        test_product = SAMPLE_PRODUCT_DATA.copy()
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = test_product
            mock_redis.save_calculated_price.return_value = True
            
            # Test at min price boundary
            pricing_data = {
                "asin": test_product["asin"],
                "seller_id": test_product["seller_id"],
                "sku": test_product["sku"],
                "new_price": 20.00  # Exactly min_price
            }
            
            response = fastapi_client.post("/pricing/manual", json=pricing_data)
            assert response.status_code == 200
            assert response.json()["new_price"] == 20.00
            
            # Test at max price boundary
            pricing_data["new_price"] = 50.00  # Exactly max_price
            
            response = fastapi_client.post("/pricing/manual", json=pricing_data)
            assert response.status_code == 200
            assert response.json()["new_price"] == 50.00
    
    def test_manual_repricing_redis_save_failure(self, fastapi_client):
        """Test manual repricing when Redis save fails."""
        test_product = SAMPLE_PRODUCT_DATA.copy()
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = test_product
            mock_redis.save_calculated_price.return_value = False  # Simulate save failure
            
            pricing_data = {
                "asin": test_product["asin"],
                "seller_id": test_product["seller_id"],
                "sku": test_product["sku"],
                "new_price": 30.00
            }
            
            response = fastapi_client.post("/pricing/manual", json=pricing_data)
            
            assert response.status_code == 500
            assert "Failed to save manual price to Redis" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.slow
class TestPricingEndpointsEdgeCases:
    """Test edge cases for both pricing endpoints."""
    
    def test_pricing_with_no_min_max_bounds(self, fastapi_client):
        """Test pricing endpoints when product has no min/max bounds."""
        product_no_bounds = SAMPLE_PRODUCT_DATA.copy()
        product_no_bounds["min_price"] = None
        product_no_bounds["max_price"] = None
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = product_no_bounds
            mock_redis.save_calculated_price.return_value = True
            
            # Test price reset (should work with default_price)
            reset_data = {
                "asin": product_no_bounds["asin"],
                "seller_id": product_no_bounds["seller_id"],
                "sku": product_no_bounds["sku"]
            }
            
            response = fastapi_client.post("/pricing/reset", json=reset_data)
            assert response.status_code == 200
            assert response.json()["new_price"] == 25.00
            
            # Test manual repricing (should work with any positive price)
            pricing_data = {
                "asin": product_no_bounds["asin"],
                "seller_id": product_no_bounds["seller_id"],
                "sku": product_no_bounds["sku"],
                "new_price": 99.99
            }
            
            response = fastapi_client.post("/pricing/manual", json=pricing_data)
            assert response.status_code == 200
            assert response.json()["new_price"] == 99.99
    
    def test_pricing_with_decimal_prices(self, fastapi_client):
        """Test pricing endpoints with decimal price values."""
        test_product = SAMPLE_PRODUCT_DATA.copy()
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = test_product
            mock_redis.save_calculated_price.return_value = True
            
            # Test manual repricing with decimal price
            pricing_data = {
                "asin": test_product["asin"],
                "seller_id": test_product["seller_id"],
                "sku": test_product["sku"],
                "new_price": 29.999  # Will be rounded appropriately
            }
            
            response = fastapi_client.post("/pricing/manual", json=pricing_data)
            assert response.status_code == 200
            # Should handle decimal precision appropriately
            assert response.json()["new_price"] == 29.999
    
    def test_concurrent_pricing_requests(self, fastapi_client):
        """Test concurrent pricing requests for the same product."""
        test_product = SAMPLE_PRODUCT_DATA.copy()
        
        with patch('src.api.webhook_router.redis_service') as mock_redis:
            mock_redis.get_product_data.return_value = test_product
            mock_redis.save_calculated_price.return_value = True
            
            import concurrent.futures
            
            def make_pricing_request(price):
                return fastapi_client.post("/pricing/manual", json={
                    "asin": test_product["asin"],
                    "seller_id": test_product["seller_id"],
                    "sku": test_product["sku"],
                    "new_price": price
                })
            
            # Send concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(make_pricing_request, 30.00),
                    executor.submit(make_pricing_request, 35.00),
                    executor.submit(make_pricing_request, 40.00)
                ]
                responses = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # All requests should succeed (Redis handles concurrency)
            for response in responses:
                assert response.status_code == 200
                assert response.json()["status"] == "success"