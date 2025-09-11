"""Test price bounds validation in strategies."""

import pytest
import unittest
from unittest.mock import Mock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.strategies import ChaseBuyBox, MaximiseProfit, OnlySeller, PriceBoundsError


class TestPriceBoundsValidation:
    """Test that strategies properly validate price bounds."""
    
    def create_mock_product(
        self,
        min_price: float = 10.0,
        max_price: float = 50.0,
        listed_price: float = 25.0,
        competitor_price: float = 30.0,
        default_price: float = 20.0,
        is_b2b: bool = False
    ):
        """Create a mock product for testing."""
        product = Mock()
        product.min_price = min_price
        product.max_price = max_price
        product.listed_price = listed_price
        product.competitor_price = competitor_price
        product.default_price = default_price
        product.is_b2b = is_b2b
        product.asin = "B07TEST123"
        product.seller_id = "TEST_SELLER"
        product.account = Mock()
        product.account.seller_id = "TEST_SELLER"
        product.tiers = {}
        
        # Mock strategy
        product.strategy = Mock()
        product.strategy.beat_by = -0.50  # Undercut by 50 cents
        product.strategy_id = "1"
        
        return product
    
    def test_chase_buybox_price_too_low_raises_exception(self):
        """Test ChaseBuyBox raises exception when calculated price is below min."""
        # Setup: competitor price is 12, beat_by is -0.50, so calculated = 11.50
        # Min price is 15, so this should fail
        product = self.create_mock_product(
            min_price=15.0,
            max_price=50.0,
            competitor_price=12.0
        )
        
        strategy = ChaseBuyBox(product)
        
        with pytest.raises(PriceBoundsError) as exc_info:
            strategy.apply()
        
        error = exc_info.value
        assert error.calculated_price == 11.50
        assert error.min_price == 15.0
        assert error.max_price == 50.0
        assert "below minimum price" in str(error)
    
    def test_chase_buybox_price_too_high_raises_exception(self):
        """Test ChaseBuyBox raises exception when calculated price is above max."""
        # Setup: We're losing at 55.0, competitor price is 50, beat_by is -0.50, so calculated = 49.50
        # Max price is 45, so this should fail
        product = self.create_mock_product(
            min_price=10.0,
            max_price=45.0,
            listed_price=55.0,      # We're losing, so need to compete
            competitor_price=50.0
        )
        
        strategy = ChaseBuyBox(product)
        
        with pytest.raises(PriceBoundsError) as exc_info:
            strategy.apply()
        
        error = exc_info.value
        assert error.calculated_price == 49.50
        assert error.min_price == 10.0
        assert error.max_price == 45.0
        assert "exceeds maximum price" in str(error)
    
    def test_maximise_profit_price_too_high_raises_exception(self):
        """Test MaximiseProfit raises exception when competitor price exceeds max."""
        # Setup: competitor price is 60, max price is 50
        product = self.create_mock_product(
            min_price=10.0,
            max_price=50.0,
            listed_price=25.0,
            competitor_price=60.0  # Above max price
        )
        
        strategy = MaximiseProfit(product)
        
        with pytest.raises(PriceBoundsError) as exc_info:
            strategy.apply()
        
        error = exc_info.value
        assert error.calculated_price == 60.0
        assert error.max_price == 50.0
    
    def test_only_seller_default_price_too_low_raises_exception(self):
        """Test OnlySeller raises exception when default price is below min."""
        product = self.create_mock_product(
            min_price=15.0,
            max_price=50.0,
            default_price=10.0  # Below min price
        )
        
        strategy = OnlySeller(product)
        
        with pytest.raises(PriceBoundsError) as exc_info:
            strategy.apply()
        
        error = exc_info.value
        assert error.calculated_price == 10.0
        assert error.min_price == 15.0
    
    def test_only_seller_mean_price_too_high_raises_exception(self):
        """Test OnlySeller raises exception when mean price exceeds max."""
        # Mean of 45 and 55 is 50, max price is 40
        product = self.create_mock_product(
            min_price=45.0,
            max_price=40.0,  # This creates an invalid range but tests the validation
            default_price=None  # Force mean calculation
        )
        
        strategy = OnlySeller(product)
        
        # This should raise an exception because mean would be invalid
        with pytest.raises(PriceBoundsError):
            strategy.apply()
    
    def test_price_bounds_validation_skipped_when_bounds_missing(self):
        """Test that validation is skipped when min/max bounds are None."""
        product = self.create_mock_product(
            min_price=None,  # No bounds set
            max_price=None,
            listed_price=105.0,     # We're losing, so need to compete
            competitor_price=100.0  # Any price should be accepted
        )
        
        # Mock NewPriceProcessor to avoid actual processing
        with unittest.mock.patch('src.strategies.base_strategy.NewPriceProcessor') as mock_processor:
            mock_processor.return_value.process_price.return_value = 99.50
            
            strategy = ChaseBuyBox(product)
            strategy.apply()  # Should not raise exception
            
            assert product.updated_price == 99.50
    
    def test_price_bounds_validation_with_valid_price(self):
        """Test that valid prices pass bounds validation."""
        product = self.create_mock_product(
            min_price=10.0,
            max_price=50.0,
            listed_price=35.0,      # We're losing, so need to compete
            competitor_price=30.0   # Results in 29.50 after beat_by
        )
        
        # Mock NewPriceProcessor
        with unittest.mock.patch('src.strategies.base_strategy.NewPriceProcessor') as mock_processor:
            mock_processor.return_value.process_price.return_value = 29.50
            
            strategy = ChaseBuyBox(product)
            strategy.apply()  # Should not raise exception
            
            assert product.updated_price == 29.50
    
    def test_b2b_tier_price_bounds_validation(self):
        """Test that B2B tier pricing also validates bounds."""
        product = self.create_mock_product(is_b2b=True)
        
        # Add a tier with its own bounds
        tier = Mock()
        tier.min_price = 20.0
        tier.max_price = 40.0
        tier.competitor_price = 15.0  # Results in 14.50, below tier min
        product.tiers = {"5": tier}
        
        strategy = ChaseBuyBox(product)
        
        # Should not raise exception for main product, but tier should fail
        with unittest.mock.patch('src.strategies.base_strategy.NewPriceProcessor') as mock_processor:
            mock_processor.return_value.process_price.return_value = 29.50  # Valid for main product
            
            strategy.apply()
            
            # Main product should succeed
            assert product.updated_price == 29.50
            
            # Tier should fail and have None price
            assert tier.updated_price is None
    
    @pytest.mark.parametrize("calculated_price,min_price,max_price,should_raise", [
        (15.0, 10.0, 20.0, False),  # Valid price
        (9.0, 10.0, 20.0, True),    # Below min
        (21.0, 10.0, 20.0, True),   # Above max
        (10.0, 10.0, 20.0, False),  # At min boundary
        (20.0, 10.0, 20.0, False),  # At max boundary
        (15.0, 20.0, 10.0, True),   # Min > Max
    ])
    def test_price_bounds_edge_cases(self, calculated_price, min_price, max_price, should_raise):
        """Test edge cases for price bounds validation."""
        from src.strategies.base_strategy import BaseStrategy
        
        # Create a concrete strategy instance for testing
        product = self.create_mock_product(min_price=min_price, max_price=max_price)
        strategy = ChaseBuyBox(product)
        
        if should_raise:
            with pytest.raises(PriceBoundsError):
                strategy.validate_price_bounds(calculated_price)
        else:
            # Should not raise exception
            result = strategy.validate_price_bounds(calculated_price)
            assert result == calculated_price