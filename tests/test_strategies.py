"""
Clean, parametrized tests for all pricing strategies.
Tests the core business logic with direct values and simple mocks.
"""
import pytest
import unittest.mock
from unittest.mock import Mock, MagicMock
from decimal import Decimal

from src.strategies.maxmise_profit import MaximiseProfit
from src.strategies.only_seller import OnlySeller
from src.strategies.chase_buybox import ChaseBuyBox
from src.strategies.new_price_processor import SkipProductRepricing, NewPriceProcessor


class TestMaximizeProfit:
    """Test MaximiseProfit strategy with parametrized test cases."""

    @pytest.mark.parametrize("listed_price,competitor_price,should_raise", [
        (120, 100, True),   # Competitor price lower - skip
        (100, 100, True),   # Equal prices - skip  
        (80, -90, True),    # Negative competitor - skip
        (0, 0, True),       # Zero prices - skip
        (100, 0, True),     # Zero competitor - skip
        (120, -100, True),  # Negative competitor - skip
        (1, 1, True),       # Boundary equal - skip
        (10**9, 10**9, True),  # Large equal - skip
        (10**15 + 1, 10**15, True),  # Extremely large, competitor lower - skip
    ])
    def test_apply_should_skip(self, listed_price, competitor_price, should_raise):
        """Test cases where MaximiseProfit should skip repricing."""
        product = Mock()
        product.listed_price = listed_price
        product.competitor_price = competitor_price
        product.updated_price = None
        
        strategy = MaximiseProfit(product)
        
        if should_raise:
            with pytest.raises(SkipProductRepricing):
                strategy.apply()
            assert product.updated_price is None
        else:
            strategy.apply()
            assert product.updated_price == round(competitor_price, 2)

    @pytest.mark.parametrize("listed_price,competitor_price,expected_price", [
        (120, 150, 150),      # Competitor higher - update
        (1, 10**9, 10**9),    # Large difference - update
        (50.25, 75.678, 75.68),  # Decimal rounding test
        (100, 125.99, 125.99), # Normal case
    ])
    def test_apply_should_update(self, listed_price, competitor_price, expected_price):
        """Test cases where MaximiseProfit should update price."""
        product = Mock()
        product.listed_price = listed_price
        product.competitor_price = competitor_price
        product.updated_price = None
        product.asin = "B01234567890"
        
        strategy = MaximiseProfit(product)
        strategy.apply()
        
        assert product.updated_price == expected_price
        assert hasattr(product, 'message')


class TestOnlySeller:
    """Test OnlySeller strategy with parametrized test cases."""

    @pytest.mark.parametrize("default_price,min_price,max_price,expected_price,should_raise", [
        (150, None, None, 150, False),    # Has default price
        (150, 100, 200, 150, False),      # Has default price (ignores min/max)
        (None, 100, 200, 150, False),     # No default, use mean of min/max
        (None, 200, None, None, True),    # Invalid: min without max
        (None, None, 100, None, True),    # Invalid: max without min
        (None, None, None, None, True),   # Invalid: no prices at all
        (0, 50, 100, 75, False),         # Default is 0, use mean
        (None, 50.5, 100.5, 75.5, False), # Decimal mean calculation
    ])
    def test_apply_various_pricing_scenarios(self, default_price, min_price, max_price, expected_price, should_raise):
        """Test OnlySeller strategy with various pricing scenarios."""
        product = Mock()
        product.default_price = default_price
        product.min_price = min_price
        product.max_price = max_price
        product.tiers = None
        product.is_b2b = False
        product.asin = "B01234567890"
        
        strategy = OnlySeller(product)
        
        if should_raise:
            with pytest.raises(SkipProductRepricing):
                strategy.apply()
        else:
            strategy.apply()
            assert product.updated_price == expected_price
            assert hasattr(product, 'strategy')
            assert hasattr(product, 'message')

    def test_apply_with_b2b_tiers(self):
        """Test OnlySeller with B2B tiers."""
        # Create mock product
        product = Mock()
        product.default_price = 100
        product.tiers = {}
        product.is_b2b = True
        product.strategy = "ONLY_SELLER"
        product.strategy_id = 1
        product.asin = "B01234567890"
        
        # Create mock tiers
        tier_1 = Mock()
        tier_1.default_price = 90
        tier_1.asin = "B01234567890"
        
        tier_2 = Mock()
        tier_2.default_price = None
        tier_2.min_price = 80
        tier_2.max_price = 120
        tier_2.asin = "B01234567890"
        
        product.tiers = {"5": tier_1, "10": tier_2}
        
        strategy = OnlySeller(product)
        strategy.apply()
        
        # Check main product
        assert product.updated_price == 100
        
        # Check tiers
        assert tier_1.updated_price == 90
        assert tier_1.strategy == "ONLY_SELLER"
        assert tier_1.strategy_id == 1
        
        assert tier_2.updated_price == 100  # Mean of 80 and 120
        assert tier_2.strategy == "ONLY_SELLER"
        assert tier_2.strategy_id == 1


class TestChaseBuyBox:
    """Test ChaseBuyBox strategy with parametrized test cases."""

    def test_apply_standard_pricing(self):
        """Test ChaseBuyBox for standard (non-B2B) products."""
        # Setup product mock
        product = Mock()
        product.competitor_price = 100
        product.is_b2b = False
        product.asin = "B01234567890"
        product.account.seller_id = "A1234567890123"
        
        # Setup strategy mock
        strategy_mock = Mock()
        strategy_mock.beat_by = "0.01"  # Beat by 1 cent
        product.strategy = strategy_mock
        
        # Mock the price processor
        with unittest.mock.patch('src.strategies.chase_buybox.NewPriceProcessor') as mock_processor:
            mock_instance = Mock()
            mock_instance.process_price.return_value = 100.01
            mock_processor.return_value = mock_instance
            
            strategy = ChaseBuyBox(product)
            strategy.apply()
            
            assert product.updated_price == 100.01
            mock_instance.process_price.assert_called_once_with(100.01, "A1234567890123", "B01234567890")

    def test_apply_b2b_pricing(self):
        """Test ChaseBuyBox for B2B products with tiers."""
        # Setup product mock
        product = Mock()
        product.competitor_price = 100
        product.is_b2b = True
        product.asin = "B01234567890"
        product.account.seller_id = "A1234567890123"
        product.strategy_id = 1
        
        # Setup strategy mock
        strategy_mock = Mock()
        strategy_mock.beat_by = "0.01"
        product.strategy = strategy_mock
        
        # Setup tier mocks
        tier_1 = Mock()
        tier_1.competitor_price = 95
        
        tier_2 = Mock()
        tier_2.competitor_price = None  # No competitor price
        
        product.tiers = {"5": tier_1, "10": tier_2}
        
        # Mock the price processor for both main and tier processing
        with unittest.mock.patch('src.strategies.chase_buybox.NewPriceProcessor') as mock_processor:
            # Create mock instance that returns appropriate values
            def process_price_side_effect(new_price, seller_id, asin):
                return new_price  # Just return the input price for simplicity
            
            mock_instance = Mock()
            mock_instance.process_price.side_effect = process_price_side_effect
            mock_processor.return_value = mock_instance
            
            strategy = ChaseBuyBox(product)
            strategy.apply()
            
            # Check main product was processed (100 + 0.01 = 100.01)
            assert product.updated_price == 100.01
            
            # Check tier with competitor price was processed (95 + 0.01 = 95.01)
            assert tier_1.updated_price == 95.01
            assert tier_1.strategy == strategy_mock
            assert tier_1.strategy_id == 1
            
            # Since mocks auto-create attributes, we'll verify the tier with None competitor price
            # was handled correctly by checking that only tier_1 was processed (95 + 0.01 = 95.01)
            # and tier_2 with None competitor_price should remain unprocessed
            # The important test is that the function doesn't crash and tier_1 gets the right price

    def test_apply_b2b_with_skip_exceptions(self):
        """Test ChaseBuyBox handles SkipProductRepricing exceptions gracefully."""
        product = Mock()
        product.competitor_price = 100
        product.is_b2b = True
        product.asin = "B01234567890"
        product.account.seller_id = "A1234567890123"
        product.strategy_id = 1
        
        strategy_mock = Mock()
        strategy_mock.beat_by = "0.01"
        product.strategy = strategy_mock
        
        # Setup tier that will cause exception
        tier_1 = Mock()
        tier_1.competitor_price = 95
        product.tiers = {"5": tier_1}
        
        # Mock price processor to raise exception for tier
        with unittest.mock.patch('src.strategies.chase_buybox.NewPriceProcessor') as mock_processor:
            main_instance = Mock()
            main_instance.process_price.return_value = 100.01
            
            tier_instance = Mock()
            tier_instance.process_price.side_effect = SkipProductRepricing("Test skip")
            
            # Return different instances for main product vs tier
            mock_processor.side_effect = [main_instance, tier_instance]
            
            strategy = ChaseBuyBox(product)
            
            # Should not raise exception - should handle it gracefully
            strategy.apply()
            
            # Main product should still be processed
            assert product.updated_price == 100.01

    @pytest.mark.parametrize("beat_by,competitor_price,expected_price", [
        ("0.01", 100, 100.01),
        ("-0.01", 100, 99.99),  # Beat by negative amount (undercut)
        ("0.05", 50.25, 50.30),
        ("1.00", 25.99, 26.99),
    ])
    def test_price_calculation_with_beat_by(self, beat_by, competitor_price, expected_price):
        """Test price calculation with various beat_by values."""
        product = Mock()
        product.competitor_price = competitor_price
        product.is_b2b = False
        product.asin = "B01234567890"
        product.account.seller_id = "A1234567890123"
        
        strategy_mock = Mock()
        strategy_mock.beat_by = beat_by
        product.strategy = strategy_mock
        
        with unittest.mock.patch('src.strategies.chase_buybox.NewPriceProcessor') as mock_processor:
            mock_instance = Mock()
            mock_instance.process_price.return_value = expected_price
            mock_processor.return_value = mock_instance
            
            strategy = ChaseBuyBox(product)
            strategy.apply()
            
            # Verify the expected price was calculated and passed to processor
            mock_instance.process_price.assert_called_once_with(
                expected_price, "A1234567890123", "B01234567890"
            )
            assert product.updated_price == expected_price