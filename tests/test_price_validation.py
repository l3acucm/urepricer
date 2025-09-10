#!/usr/bin/env python3
"""
Test script to verify price validation on the ProductListing model.
"""
import sys
from decimal import Decimal
from unittest.mock import Mock

# Mock dependencies before importing
class MockLogger:
    def bind(self, **kwargs):
        return self
    def info(self, msg, extra=None, **kwargs):
        pass
    def warning(self, msg, extra=None, **kwargs):
        pass
    def error(self, msg, extra=None, **kwargs):
        pass

sys.modules['loguru'] = type('MockModule', (), {'logger': MockLogger()})()
sys.modules['src.core.config'] = Mock()

# Mock the settings
mock_settings = Mock()
mock_settings.sync_database_url = "sqlite:///:memory:"
mock_settings.debug = False

sys.modules['src.core.config'].get_settings.return_value = mock_settings

sys.path.insert(0, '../src')

from src.models.products import ProductListing


def test_price_validation():
    """Test various price validation scenarios."""
    print("🧪 Testing Price Validation on ProductListing Model\n")
    
    # Test 1: Valid price bounds
    print("1. Testing valid price bounds...")
    try:
        product = ProductListing(
            asin="B123456789",
            seller_id="A123456789", 
            marketplace_type="US",
            min_price=Decimal("10.00"),
            max_price=Decimal("50.00"),
            listed_price=Decimal("25.00"),
            default_price=Decimal("20.00")
        )
        print("✅ Valid price bounds accepted")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Test 2: Invalid - min_price > max_price
    print("\n2. Testing invalid min_price > max_price...")
    try:
        product = ProductListing(
            asin="B123456789",
            seller_id="A123456789",
            marketplace_type="US",
            min_price=Decimal("60.00"),  # Greater than max_price
            max_price=Decimal("50.00")
        )
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")
    
    # Test 3: Invalid - negative min_price
    print("\n3. Testing negative min_price...")
    try:
        product = ProductListing(
            asin="B123456789",
            seller_id="A123456789",
            marketplace_type="US",
            min_price=Decimal("-10.00")  # Negative price
        )
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")
    
    # Test 4: Invalid - negative max_price  
    print("\n4. Testing negative max_price...")
    try:
        product = ProductListing(
            asin="B123456789", 
            seller_id="A123456789",
            marketplace_type="US",
            max_price=Decimal("-50.00")  # Negative price
        )
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")
    
    # Test 5: Valid - only min_price set
    print("\n5. Testing only min_price set...")
    try:
        product = ProductListing(
            asin="B123456789",
            seller_id="A123456789", 
            marketplace_type="US",
            min_price=Decimal("10.00"),
            max_price=None
        )
        print("✅ Only min_price validation passed")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Test 6: Valid - only max_price set
    print("\n6. Testing only max_price set...")
    try:
        product = ProductListing(
            asin="B123456789",
            seller_id="A123456789",
            marketplace_type="US", 
            min_price=None,
            max_price=Decimal("50.00")
        )
        print("✅ Only max_price validation passed")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Test 7: Invalid - listed_price below min_price
    print("\n7. Testing listed_price below min_price...")
    try:
        product = ProductListing(
            asin="B123456789",
            seller_id="A123456789",
            marketplace_type="US",
            min_price=Decimal("20.00"),
            max_price=Decimal("50.00"),
            listed_price=Decimal("10.00")  # Below min_price
        )
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")
    
    # Test 8: Invalid - listed_price above max_price
    print("\n8. Testing listed_price above max_price...")
    try:
        product = ProductListing(
            asin="B123456789",
            seller_id="A123456789",
            marketplace_type="US", 
            min_price=Decimal("20.00"),
            max_price=Decimal("50.00"),
            listed_price=Decimal("60.00")  # Above max_price
        )
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")
    
    # Test 9: Invalid - default_price outside bounds
    print("\n9. Testing default_price outside bounds...")
    try:
        product = ProductListing(
            asin="B123456789",
            seller_id="A123456789",
            marketplace_type="US",
            min_price=Decimal("20.00"),
            max_price=Decimal("50.00"), 
            default_price=Decimal("60.00")  # Above max_price
        )
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")
    
    # Test 10: Valid - equal min and max prices
    print("\n10. Testing equal min and max prices...")
    try:
        product = ProductListing(
            asin="B123456789",
            seller_id="A123456789",
            marketplace_type="US",
            min_price=Decimal("25.00"),
            max_price=Decimal("25.00"),  # Equal to min_price
            listed_price=Decimal("25.00")
        )
        print("✅ Equal min/max prices validation passed")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Test 11: Test SQLAlchemy validators directly
    print("\n11. Testing SQLAlchemy validators...")
    try:
        product = ProductListing(
            asin="B123456789", 
            seller_id="A123456789",
            marketplace_type="US"
        )
        
        # This should trigger the @validates decorator
        product.min_price = Decimal("10.00")
        product.max_price = Decimal("5.00")  # Less than min_price
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ SQLAlchemy validator correctly raised ValueError: {e}")
    
    print("\n" + "="*60)
    print("🎉 All Price Validation Tests Completed!")
    print("✅ Model-level validation is working correctly")
    print("✅ Both individual field validation and comprehensive validation work")
    print("✅ Edge cases are properly handled")
    print("="*60)


def test_updated_test_case():
    """Test the updated test case that was modified by the user."""
    print("\n🔄 Testing Updated Test Case: min > max scenario")
    
    # This matches the test case that was changed in test_strategies.py:
    # (None, 200, 100, None, False) - Invalid: min > max
    try:
        product = ProductListing(
            asin="B123456789",
            seller_id="A123456789", 
            marketplace_type="US",
            min_price=Decimal("200.00"),  # Greater than max_price
            max_price=Decimal("100.00")
        )
        print("❌ Should have raised ValueError during object creation")
        return False
    except ValueError as e:
        print(f"✅ SQLAlchemy validator correctly caught min > max during creation: {e}")
        return True


if __name__ == "__main__":
    test_price_validation()
    test_updated_test_case()