#!/usr/bin/env python3
"""
Fixed strategy tests that validate the new BaseStrategy architecture.
This version mocks dependencies and focuses on testing the key functionality.
"""

import sys
import os
from unittest.mock import Mock

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

sys.modules['loguru'] = type('MockModule', (), {'logger': MockLogger()})()

# Add src to path
sys.path.insert(0, '../src')

# Import strategy modules
from strategies import ChaseBuyBox, MaximiseProfit, OnlySeller, PriceBoundsError
from strategies.base_strategy import BaseStrategy
from strategies.new_price_processor import SkipProductRepricing


def create_mock_product(
    listed_price=25.0,
    competitor_price=30.0,
    min_price=10.0,
    max_price=50.0,
    default_price=20.0,
    is_b2b=False,
    strategy_beat_by=0.01
):
    """Create a mock product with all necessary attributes."""
    # Create a regular Mock but set specific attributes explicitly
    product = Mock()
    
    # Core pricing attributes - set explicitly to avoid Mock comparison issues
    product.listed_price = listed_price
    product.competitor_price = competitor_price
    # Handle None values explicitly
    if min_price is not None:
        product.min_price = min_price
    else:
        product.min_price = None
    if max_price is not None:
        product.max_price = max_price  
    else:
        product.max_price = None
    product.default_price = default_price
    product.is_b2b = is_b2b
    
    # Product identification
    product.asin = "B01234567890"
    product.seller_id = "A1234567890123"
    
    # Account mock for backward compatibility
    product.account = Mock()
    product.account.seller_id = "A1234567890123"
    
    # Strategy mock
    product.strategy = Mock()
    product.strategy.beat_by = strategy_beat_by
    product.strategy_id = "1"
    
    # B2B attributes
    product.tiers = {}
    
    # Result attributes
    product.updated_price = None
    product.message = ""
    
    return product


def test_inheritance():
    """Test that all strategies inherit from BaseStrategy."""
    print("🧪 Testing Strategy Inheritance...")
    
    assert issubclass(ChaseBuyBox, BaseStrategy), "ChaseBuyBox should inherit from BaseStrategy"
    assert issubclass(MaximiseProfit, BaseStrategy), "MaximiseProfit should inherit from BaseStrategy"  
    assert issubclass(OnlySeller, BaseStrategy), "OnlySeller should inherit from BaseStrategy"
    
    print("✅ All strategies inherit from BaseStrategy correctly")


def test_maximize_profit_bounds_validation():
    """Test MaximiseProfit price bounds validation."""
    print("\n🧪 Testing MaximiseProfit Price Bounds...")
    
    # Test valid price
    product = create_mock_product(
        listed_price=25.0,
        competitor_price=30.0,  # Within bounds
        min_price=10.0,
        max_price=50.0
    )
    
    strategy = MaximiseProfit(product)
    strategy.apply()
    assert product.updated_price == 30.0, f"Expected 30.0, got {product.updated_price}"
    print("✅ Valid price accepted")
    
    # Test bounds violation
    product = create_mock_product(
        listed_price=25.0,
        competitor_price=60.0,  # Above max
        min_price=10.0,
        max_price=50.0
    )
    
    strategy = MaximiseProfit(product)
    try:
        strategy.apply()
        assert False, "Should have raised PriceBoundsError"
    except PriceBoundsError as e:
        assert e.calculated_price == 60.0
        assert e.max_price == 50.0
        assert product.updated_price is None
        print("✅ PriceBoundsError raised correctly for price above max")
    
    # Test skip when competitor price is lower
    product = create_mock_product(
        listed_price=30.0,
        competitor_price=25.0,  # Lower than listed price
        min_price=10.0,
        max_price=50.0
    )
    
    strategy = MaximiseProfit(product)
    try:
        strategy.apply()
        assert False, "Should have raised SkipProductRepricing"
    except SkipProductRepricing:
        print("✅ SkipProductRepricing raised correctly when competitor price is lower")


def test_only_seller_bounds_validation():
    """Test OnlySeller price bounds validation."""
    print("\n🧪 Testing OnlySeller Price Bounds...")
    
    # Test valid default price
    product = create_mock_product(
        default_price=30.0,  # Within bounds
        min_price=20.0,
        max_price=40.0
    )
    
    strategy = OnlySeller(product)
    strategy.apply()
    assert product.updated_price == 30.0, f"Expected 30.0, got {product.updated_price}"
    print("✅ Valid default price accepted")
    
    # Test bounds violation with default price
    product = create_mock_product(
        default_price=60.0,  # Above max
        min_price=20.0,
        max_price=40.0
    )
    
    strategy = OnlySeller(product)
    try:
        strategy.apply()
        assert False, "Should have raised PriceBoundsError"
    except PriceBoundsError as e:
        assert e.calculated_price == 60.0
        assert e.max_price == 40.0
        print("✅ PriceBoundsError raised correctly for default price above max")
    
    # Test mean price calculation
    product = create_mock_product(
        default_price=None,  # Force mean calculation
        min_price=20.0,
        max_price=40.0
    )
    
    strategy = OnlySeller(product)
    strategy.apply()
    assert product.updated_price == 30.0, f"Expected 30.0 (mean of 20 and 40), got {product.updated_price}"
    print("✅ Mean price calculation works correctly")


def test_chase_buybox_bounds_validation():
    """Test ChaseBuyBox price bounds validation."""
    print("\n🧪 Testing ChaseBuyBox Price Bounds...")
    
    # Get the correct import function regardless of __builtins__ type
    if isinstance(__builtins__, dict):
        original_import = __builtins__['__import__']
    else:
        original_import = __builtins__.__import__
    
    def mock_import(name, *args, **kwargs):
        if name == 'src.strategies.new_price_processor':
            mock_module = Mock()
            mock_processor_class = Mock()
            mock_processor_instance = Mock()
            mock_processor_instance.process_price.side_effect = lambda price, *args: price
            mock_processor_class.return_value = mock_processor_instance
            mock_module.NewPriceProcessor = mock_processor_class
            return mock_module
        return original_import(name, *args, **kwargs)
    
    # Set the import function correctly
    if isinstance(__builtins__, dict):
        __builtins__['__import__'] = mock_import
    else:
        __builtins__.__import__ = mock_import
    
    try:
        # Test valid price where we need to be competitive (our price is higher)
        product = create_mock_product(
            listed_price=35.0,      # Our current price (losing)
            competitor_price=30.0,  # Competitor price
            strategy_beat_by=0.01,
            min_price=20.0,
            max_price=40.0,
            is_b2b=False
        )
        
        strategy = ChaseBuyBox(product)
        strategy.apply()
        expected_price = 30.01  # 30.0 + 0.01
        assert product.updated_price == expected_price, f"Expected {expected_price}, got {product.updated_price}"
        print("✅ Valid calculated price accepted when we need to be competitive")
        
        # Test bounds violation where we're losing but calculation exceeds bounds
        product = create_mock_product(
            listed_price=50.0,      # Our current price (losing)
            competitor_price=45.0,  # 45.01 will exceed max
            strategy_beat_by=0.01,
            min_price=20.0,
            max_price=45.0,
            is_b2b=False
        )
        
        strategy = ChaseBuyBox(product)
        try:
            strategy.apply()
            assert False, "Should have raised PriceBoundsError"
        except PriceBoundsError as e:
            assert e.calculated_price == 45.01
            assert e.max_price == 45.0
            print("✅ PriceBoundsError raised correctly for calculated price above max")
        
    finally:
        # Restore the import function correctly
        if isinstance(__builtins__, dict):
            __builtins__['__import__'] = original_import
        else:
            __builtins__.__import__ = original_import


def test_no_bounds_skipping():
    """Test that validation is skipped when bounds are not set."""
    print("\n🧪 Testing Bounds Validation Skipping...")
    
    # Test with no bounds set - need to be explicit about None
    product = Mock()
    product.listed_price = 25.0
    product.competitor_price = 1000.0  # Very high price
    product.min_price = None  # No bounds
    product.max_price = None
    product.default_price = 20.0
    product.is_b2b = False
    product.asin = "B01234567890"
    product.seller_id = "A1234567890123"
    product.account = Mock()
    product.account.seller_id = "A1234567890123"
    product.strategy = Mock()
    product.strategy.beat_by = 0.01
    product.strategy_id = "1"
    product.tiers = {}
    product.updated_price = None
    product.message = ""
    
    strategy = MaximiseProfit(product)
    strategy.apply()
    assert product.updated_price == 1000.0, f"Expected 1000.0, got {product.updated_price}"
    print("✅ Validation correctly skipped when bounds are None")


def test_base_strategy_methods():
    """Test BaseStrategy common methods."""
    print("\n🧪 Testing BaseStrategy Common Methods...")
    
    product = create_mock_product()
    strategy = ChaseBuyBox(product)
    
    # Test price rounding
    rounded = strategy.round_price(30.999)
    assert rounded == 31.0, f"Expected 31.0, got {rounded}"
    print("✅ Price rounding works correctly")
    
    # Test competitive price calculation
    comp_price = strategy.calculate_competitive_price(30.0, 0.01)
    assert comp_price == 30.01, f"Expected 30.01, got {comp_price}"
    print("✅ Competitive price calculation works correctly")
    
    # Test mean price calculation
    product.min_price = 20.0
    product.max_price = 40.0
    mean_price = strategy.calculate_mean_price(product)
    assert mean_price == 30.0, f"Expected 30.0, got {mean_price}"
    print("✅ Mean price calculation works correctly")


def run_all_tests():
    """Run all strategy tests."""
    print("🚀 Running Strategy Tests with Price Bounds Validation\n")
    
    try:
        test_inheritance()
        test_maximize_profit_bounds_validation()
        test_only_seller_bounds_validation() 
        test_chase_buybox_bounds_validation()
        test_no_bounds_skipping()
        test_base_strategy_methods()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("✅ Strategy inheritance working correctly")
        print("✅ Price bounds validation implemented")
        print("✅ PriceBoundsError exception handling works")
        print("✅ Common functionality in BaseStrategy works")
        print("✅ Bounds validation skipping works")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)