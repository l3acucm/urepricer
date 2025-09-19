"""Tests for price reset and resume functionality with mocked time."""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.utils.reset_utils import (
    is_in_reset_window,
    extract_user_info_from_seller_id,
    should_skip_repricing_async,
    should_skip_repricing_sync
)
from src.tasks.price_reset import (
    get_reset_rules_for_user,
    reset_product_to_default,
    process_hourly_reset
)


class TestResetWindowLogic:
    """Test the reset window time logic."""
    
    def test_no_reset_window_when_times_equal(self):
        """Test that no reset window exists when reset_hour == resume_hour."""
        assert not is_in_reset_window(current_hour=10, reset_hour=8, resume_hour=8)
        assert not is_in_reset_window(current_hour=8, reset_hour=8, resume_hour=8)
        assert not is_in_reset_window(current_hour=0, reset_hour=8, resume_hour=8)
    
    def test_normal_reset_window(self):
        """Test normal reset window (reset < resume, no cross-midnight)."""
        # Reset at 1, resume at 23 -> skip hours 1-23
        assert not is_in_reset_window(current_hour=0, reset_hour=1, resume_hour=23)  # Allow
        assert is_in_reset_window(current_hour=1, reset_hour=1, resume_hour=23)     # Skip
        assert is_in_reset_window(current_hour=12, reset_hour=1, resume_hour=23)    # Skip
        assert is_in_reset_window(current_hour=23, reset_hour=1, resume_hour=23)    # Skip
    
    def test_cross_midnight_reset_window(self):
        """Test cross-midnight reset window (reset > resume)."""
        # Reset at 23, resume at 3 -> skip hours 23, 0, 1, 2, 3
        assert is_in_reset_window(current_hour=23, reset_hour=23, resume_hour=3)    # Skip
        assert is_in_reset_window(current_hour=0, reset_hour=23, resume_hour=3)     # Skip
        assert is_in_reset_window(current_hour=1, reset_hour=23, resume_hour=3)     # Skip
        assert is_in_reset_window(current_hour=2, reset_hour=23, resume_hour=3)     # Skip
        assert is_in_reset_window(current_hour=3, reset_hour=23, resume_hour=3)     # Skip
        assert not is_in_reset_window(current_hour=4, reset_hour=23, resume_hour=3) # Allow
        assert not is_in_reset_window(current_hour=12, reset_hour=23, resume_hour=3)# Allow
        assert not is_in_reset_window(current_hour=22, reset_hour=23, resume_hour=3)# Allow
    
    def test_edge_cases(self):
        """Test edge cases for reset window logic."""
        # Reset at 0, resume at 1 -> skip hours 0, 1
        assert is_in_reset_window(current_hour=0, reset_hour=0, resume_hour=1)
        assert is_in_reset_window(current_hour=1, reset_hour=0, resume_hour=1)
        assert not is_in_reset_window(current_hour=2, reset_hour=0, resume_hour=1)
        
        # Reset at 22, resume at 0 -> skip hours 22, 23, 0
        assert not is_in_reset_window(current_hour=21, reset_hour=22, resume_hour=0)
        assert is_in_reset_window(current_hour=22, reset_hour=22, resume_hour=0)
        assert is_in_reset_window(current_hour=23, reset_hour=22, resume_hour=0)
        assert is_in_reset_window(current_hour=0, reset_hour=22, resume_hour=0)
        assert not is_in_reset_window(current_hour=1, reset_hour=22, resume_hour=0)


class TestSellerIdExtraction:
    """Test seller ID to user info extraction."""
    
    def test_uk_seller_extraction(self):
        """Test UK seller ID extraction."""
        user_id, market = extract_user_info_from_seller_id("UK_SELLER_123")
        assert user_id == 123
        assert market == "uk"
        
        user_id, market = extract_user_info_from_seller_id("UK_SELLER_9999")
        assert user_id == 9999
        assert market == "uk"
    
    def test_us_seller_extraction(self):
        """Test US seller ID extraction."""
        user_id, market = extract_user_info_from_seller_id("US_SELLER_456")
        assert user_id == 456
        assert market == "us"
        
        user_id, market = extract_user_info_from_seller_id("US_SELLER_1")
        assert user_id == 1
        assert market == "us"
    
    def test_amazon_seller_detection(self):
        """Test Amazon seller ID detection."""
        user_id, market = extract_user_info_from_seller_id("A1234567890123")
        assert user_id is None
        assert market == "amazon"
        
        user_id, market = extract_user_info_from_seller_id("ABCDEFGHIJ1234")
        assert user_id is None
        assert market == "amazon"
    
    def test_invalid_seller_ids(self):
        """Test invalid seller ID handling."""
        user_id, market = extract_user_info_from_seller_id("UK_SELLER_abc")
        assert user_id is None
        assert market == "unknown"
        
        user_id, market = extract_user_info_from_seller_id("INVALID")
        assert user_id is None
        assert market == "unknown"
        
        user_id, market = extract_user_info_from_seller_id("")
        assert user_id is None
        assert market == "unknown"


class TestResetRulesRetrieval:
    """Test reset rules retrieval from Redis."""
    
    @pytest.mark.asyncio
    async def test_get_reset_rules_specific_market(self):
        """Test getting reset rules for specific market."""
        # Mock Redis service and client
        mock_redis_service = Mock()
        mock_redis_client = AsyncMock()
        mock_redis_service.get_connection.return_value = mock_redis_client
        
        # Mock data for UK market
        mock_redis_client.hgetall.return_value = {
            "price_reset_enabled": "true",
            "price_reset_time": "01",
            "price_resume_time": "23",
            "product_condition": "ALL",
            "market": "uk"
        }
        
        rules = await get_reset_rules_for_user(mock_redis_service, 123, "uk")
        
        assert rules is not None
        assert rules["price_reset_enabled"] is True
        assert rules["price_reset_time"] == 1
        assert rules["price_resume_time"] == 23
        assert rules["market"] == "uk"
        
        # Verify Redis was called with correct key
        mock_redis_client.hgetall.assert_called_with("reset_rules.123:uk")
    
    @pytest.mark.asyncio
    async def test_get_reset_rules_fallback_to_all(self):
        """Test fallback to 'all' market when specific market not found."""
        mock_redis_service = Mock()
        mock_redis_client = AsyncMock()
        mock_redis_service.get_connection.return_value = mock_redis_client
        
        # First call (specific market) returns empty, second call (all) returns data
        mock_redis_client.hgetall.side_effect = [
            {},  # No data for specific market
            {    # Data for 'all' market
                "price_reset_enabled": "false",
                "price_reset_time": "02",
                "price_resume_time": "08",
                "product_condition": "ALL",
                "market": "all"
            }
        ]
        
        rules = await get_reset_rules_for_user(mock_redis_service, 456, "us")
        
        assert rules is not None
        assert rules["price_reset_enabled"] is False
        assert rules["price_reset_time"] == 2
        assert rules["price_resume_time"] == 8
        assert rules["market"] == "all"
        
        # Verify both Redis calls were made
        assert mock_redis_client.hgetall.call_count == 2
        mock_redis_client.hgetall.assert_any_call("reset_rules.456:us")
        mock_redis_client.hgetall.assert_any_call("reset_rules.456:all")
    
    @pytest.mark.asyncio
    async def test_get_reset_rules_not_found(self):
        """Test when no reset rules are found."""
        mock_redis_service = Mock()
        mock_redis_client = AsyncMock()
        mock_redis_service.get_connection.return_value = mock_redis_client
        
        # Both calls return empty
        mock_redis_client.hgetall.return_value = {}
        
        rules = await get_reset_rules_for_user(mock_redis_service, 999, "uk")
        
        assert rules is None


class TestRepricingSkipLogic:
    """Test the main repricing skip logic."""
    
    @pytest.mark.asyncio
    async def test_should_skip_repricing_in_window(self):
        """Test skipping repricing when in reset window."""
        with patch('src.utils.reset_utils.RedisService') as mock_redis_class, \
             patch('src.utils.reset_utils.get_reset_rules_for_user') as mock_get_rules:
            
            mock_get_rules.return_value = {
                "price_reset_enabled": True,
                "price_reset_time": 23,
                "price_resume_time": 3,
                "product_condition": "ALL",
                "market": "uk"
            }
            
            # Test different hours in the reset window
            test_time_23 = datetime(2025, 1, 1, 23, 30, tzinfo=UTC)  # Should skip
            test_time_01 = datetime(2025, 1, 1, 1, 15, tzinfo=UTC)   # Should skip
            test_time_12 = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)   # Should not skip
            
            assert await should_skip_repricing_async("UK_SELLER_123", test_time_23) is True
            assert await should_skip_repricing_async("UK_SELLER_123", test_time_01) is True
            assert await should_skip_repricing_async("UK_SELLER_123", test_time_12) is False
    
    @pytest.mark.asyncio
    async def test_should_skip_repricing_disabled(self):
        """Test not skipping when reset is disabled."""
        with patch('src.utils.reset_utils.RedisService') as mock_redis_class, \
             patch('src.utils.reset_utils.get_reset_rules_for_user') as mock_get_rules:
            
            mock_get_rules.return_value = {
                "price_reset_enabled": False,  # Disabled
                "price_reset_time": 1,
                "price_resume_time": 23,
                "product_condition": "ALL",
                "market": "uk"
            }
            
            test_time = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
            
            assert await should_skip_repricing_async("UK_SELLER_123", test_time) is False
    
    @pytest.mark.asyncio
    async def test_should_skip_repricing_no_rules(self):
        """Test not skipping when no rules found."""
        with patch('src.utils.reset_utils.RedisService') as mock_redis_class, \
             patch('src.utils.reset_utils.get_reset_rules_for_user') as mock_get_rules:
            
            mock_get_rules.return_value = None  # No rules found
            
            test_time = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
            
            assert await should_skip_repricing_async("UK_SELLER_999", test_time) is False
    
    @pytest.mark.asyncio
    async def test_should_skip_repricing_amazon_seller(self):
        """Test not applying reset rules to Amazon sellers."""
        test_time = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
        
        # Amazon seller IDs should not have reset rules applied
        assert await should_skip_repricing_async("A1234567890123", test_time) is False
    
    def test_should_skip_repricing_sync_wrapper(self):
        """Test the synchronous wrapper function."""
        with patch('src.utils.reset_utils.should_skip_repricing_async') as mock_async:
            mock_async.return_value = True
            
            test_time = datetime(2025, 1, 1, 1, 0, tzinfo=UTC)
            result = should_skip_repricing_sync("UK_SELLER_123", test_time)
            
            assert result is True
            mock_async.assert_called_once_with("UK_SELLER_123", test_time)


class TestPriceResetTask:
    """Test the price reset task functionality."""
    
    @pytest.mark.asyncio
    async def test_reset_product_to_default_success(self):
        """Test successful price reset to default."""
        mock_redis_service = Mock()
        
        # Mock product data
        mock_redis_service.get_product_data.return_value = {
            "listed_price": 29.99,
            "default_price": 25.00,
            "min_price": 20.00,
            "max_price": 50.00
        }
        
        mock_redis_service.save_calculated_price.return_value = True
        
        result = await reset_product_to_default(
            mock_redis_service,
            "B123456789", 
            "UK_SELLER_123", 
            "SKU-123",
            "test_reset"
        )
        
        assert result is True
        mock_redis_service.get_product_data.assert_called_once_with("B123456789", "UK_SELLER_123", "SKU-123")
        mock_redis_service.save_calculated_price.assert_called_once()
        
        # Check the price data passed to save_calculated_price
        call_args = mock_redis_service.save_calculated_price.call_args
        price_data = call_args[0][3]  # Fourth argument is the price_data dict
        
        assert price_data["old_price"] == 29.99
        assert price_data["new_price"] == 25.00
        assert price_data["strategy_used"] == "PRICE_RESET"
        assert price_data["reason"] == "test_reset"
    
    @pytest.mark.asyncio
    async def test_reset_product_already_at_default(self):
        """Test reset when product is already at default price."""
        mock_redis_service = Mock()
        
        # Product already at default price
        mock_redis_service.get_product_data.return_value = {
            "listed_price": 25.00,
            "default_price": 25.00,
            "min_price": 20.00,
            "max_price": 50.00
        }
        
        result = await reset_product_to_default(
            mock_redis_service,
            "B123456789",
            "UK_SELLER_123",
            "SKU-123"
        )
        
        assert result is True
        # Should not call save_calculated_price since price is already correct
        mock_redis_service.save_calculated_price.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_reset_product_not_found(self):
        """Test reset when product is not found."""
        mock_redis_service = Mock()
        mock_redis_service.get_product_data.return_value = None
        
        result = await reset_product_to_default(
            mock_redis_service,
            "B999999999",
            "UK_SELLER_999",
            "SKU-999"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_reset_product_no_default_price(self):
        """Test reset when product has no default price."""
        mock_redis_service = Mock()
        mock_redis_service.get_product_data.return_value = {
            "listed_price": 29.99,
            "default_price": None,  # No default price
            "min_price": 20.00,
            "max_price": 50.00
        }
        
        result = await reset_product_to_default(
            mock_redis_service,
            "B123456789",
            "UK_SELLER_123",
            "SKU-123"
        )
        
        assert result is False


class TestHourlyResetProcessing:
    """Test the complete hourly reset processing logic."""
    
    @pytest.mark.asyncio
    async def test_process_hourly_reset_reset_hour(self):
        """Test processing during the reset hour."""
        with patch('src.tasks.price_reset.datetime') as mock_datetime, \
             patch('src.tasks.price_reset.RedisService') as mock_redis_class, \
             patch('src.tasks.price_reset.get_reset_rules_for_user') as mock_get_rules, \
             patch('src.tasks.price_reset.reset_product_to_default') as mock_reset:
            
            # Mock current time to be hour 1 (reset time)
            mock_now = datetime(2025, 1, 1, 1, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            
            # Mock Redis service
            mock_redis_service = Mock()
            mock_redis_client = AsyncMock()
            mock_redis_service.get_connection.return_value = mock_redis_client
            mock_redis_class.return_value = mock_redis_service
            
            # Mock ASIN keys
            mock_redis_client.keys.return_value = ["ASIN_B123456789"]
            mock_redis_client.hgetall.return_value = {
                "UK_SELLER_123:SKU-123": '{"listed_price": 29.99, "default_price": 25.00}'
            }
            
            # Mock reset rules - enabled with reset at hour 1
            mock_get_rules.return_value = {
                "price_reset_enabled": True,
                "price_reset_time": 1,
                "price_resume_time": 23,
                "product_condition": "ALL",
                "market": "uk"
            }
            
            # Mock successful reset
            mock_reset.return_value = True
            
            result = await process_hourly_reset()
            
            assert result["reset_count"] == 1
            assert result["skip_count"] == 0
            assert result["error_count"] == 0
            assert result["hour"] == 1
            
            # Verify reset was called
            mock_reset.assert_called_once_with(
                mock_redis_service,
                "B123456789",
                "UK_SELLER_123", 
                "SKU-123",
                "hourly_reset_01:00"
            )
    
    @pytest.mark.asyncio 
    async def test_process_hourly_reset_skip_hour(self):
        """Test processing during a skip hour (not reset hour)."""
        with patch('src.tasks.price_reset.datetime') as mock_datetime, \
             patch('src.tasks.price_reset.RedisService') as mock_redis_class, \
             patch('src.tasks.price_reset.get_reset_rules_for_user') as mock_get_rules, \
             patch('src.tasks.price_reset.reset_product_to_default') as mock_reset:
            
            # Mock current time to be hour 12 (between reset window)
            mock_now = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            
            # Mock Redis service
            mock_redis_service = Mock()
            mock_redis_client = AsyncMock()
            mock_redis_service.get_connection.return_value = mock_redis_client
            mock_redis_class.return_value = mock_redis_service
            
            # Mock ASIN keys
            mock_redis_client.keys.return_value = ["ASIN_B123456789"]
            mock_redis_client.hgetall.return_value = {
                "UK_SELLER_123:SKU-123": '{"listed_price": 29.99, "default_price": 25.00}'
            }
            
            # Mock reset rules - reset at 1, resume at 23 (so hour 12 should be skipped)
            mock_get_rules.return_value = {
                "price_reset_enabled": True,
                "price_reset_time": 1,
                "price_resume_time": 23,
                "product_condition": "ALL",
                "market": "uk"
            }
            
            result = await process_hourly_reset()
            
            assert result["reset_count"] == 0
            assert result["skip_count"] == 1  # One product was in skip window
            assert result["error_count"] == 0
            assert result["hour"] == 12
            
            # Verify reset was NOT called
            mock_reset.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])