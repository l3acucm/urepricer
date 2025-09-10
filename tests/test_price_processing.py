"""
Clean tests for NewPriceProcessor edge cases and price validation logic.
Tests price processing rules with direct values and simple mocks.
"""
import pytest
import unittest.mock
from unittest.mock import Mock

from src.strategies.new_price_processor import NewPriceProcessor, SkipProductRepricing


class TestNewPriceProcessor:
    """Test NewPriceProcessor price validation and rule application."""

    def create_mock_product(self, min_price=None, max_price=None, default_price=None):
        """Helper to create a mock product with pricing attributes."""
        product = Mock()
        product.asin = "B01234567890"
        product.min_price = min_price
        product.max_price = max_price
        product.default_price = default_price
        
        # Mock strategy with default rules
        strategy = Mock()
        strategy.min_price_rule = "JUMP_TO_MIN"
        strategy.max_price_rule = "JUMP_TO_MAX"
        product.strategy = strategy
        
        return product

    @pytest.mark.parametrize("new_price,expected_exception", [
        (None, True),     # None price
        (0, True),        # Zero price
        (-10, True),      # Negative price
        (-0.01, True),    # Negative small price
        (0.01, False),    # Valid small price
        (100, False),     # Valid price
    ])
    def test_process_price_invalid_prices(self, new_price, expected_exception):
        """Test process_price with invalid price values."""
        product = self.create_mock_product()
        processor = NewPriceProcessor(product)
        
        if expected_exception:
            with pytest.raises(SkipProductRepricing, match="is None or Less than zero"):
                processor.process_price(new_price, "A1234567890123", "B01234567890")
        else:
            result = processor.process_price(new_price, "A1234567890123", "B01234567890")
            assert result == new_price

    @pytest.mark.parametrize("new_price,min_price,max_price,should_trigger_rule", [
        (150, 50, 100, "max"),    # Above max price
        (25, 50, 100, "min"),     # Below min price
        (75, 50, 100, None),      # Within range
        (100, 50, 100, None),     # At max boundary
        (50, 50, 100, None),      # At min boundary
        (200, None, 100, "max"),  # No min price, above max
        (25, 50, None, "min"),    # No max price, below min
        (75, None, None, None),   # No price limits
    ])
    def test_process_price_range_checks(self, new_price, min_price, max_price, should_trigger_rule):
        """Test price range checking and rule triggering."""
        product = self.create_mock_product(min_price=min_price, max_price=max_price)
        processor = NewPriceProcessor(product)
        
        if should_trigger_rule == "max":
            with unittest.mock.patch.object(processor, '_apply_price_rule', return_value=max_price) as mock_rule:
                result = processor.process_price(new_price, "SELLER123", "B01234567890")
                mock_rule.assert_called_once_with('max_price_rule', "SELLER123", "B01234567890")
                assert result == max_price
                
        elif should_trigger_rule == "min":
            with unittest.mock.patch.object(processor, '_apply_price_rule', return_value=min_price) as mock_rule:
                result = processor.process_price(new_price, "SELLER123", "B01234567890")
                mock_rule.assert_called_once_with('min_price_rule', "SELLER123", "B01234567890")
                assert result == min_price
                
        else:
            result = processor.process_price(new_price, "SELLER123", "B01234567890")
            assert result == new_price

    @pytest.mark.parametrize("rule_name,method_name", [
        ("JUMP_TO_AVG", "_jump_to_avg"),
        ("JUMP_TO_MIN", "_jump_to_min"),
        ("JUMP_TO_MAX", "_jump_to_max"),
        ("MATCH_COMPETITOR", "_match_competitor"),
        ("DO_NOTHING", "_do_nothing"),
        ("DEFAULT_PRICE", "_default_price"),
    ])
    def test_apply_price_rule_method_mapping(self, rule_name, method_name):
        """Test that price rules map to correct methods."""
        product = self.create_mock_product()
        product.strategy.min_price_rule = rule_name
        processor = NewPriceProcessor(product)
        
        with unittest.mock.patch.object(processor, method_name, return_value=50.0) as mock_method:
            if rule_name == "DEFAULT_PRICE":
                result = processor._apply_price_rule('min_price_rule', "SELLER123", "B01234567890")
                mock_method.assert_called_once_with("SELLER123", "B01234567890")
            else:
                result = processor._apply_price_rule('min_price_rule', "SELLER123", "B01234567890")
                mock_method.assert_called_once_with()
            assert result == 50.0

    def test_apply_price_rule_invalid_rule(self):
        """Test _apply_price_rule with invalid/undefined rule."""
        product = self.create_mock_product()
        product.strategy.min_price_rule = "INVALID_RULE"
        processor = NewPriceProcessor(product)
        
        with pytest.raises(SkipProductRepricing, match="Method '_invalid_rule' is not defined"):
            processor._apply_price_rule('min_price_rule', "SELLER123", "B01234567890")

    def test_jump_to_avg_success(self):
        """Test _jump_to_avg with valid min and max prices."""
        product = self.create_mock_product(min_price=50, max_price=100)
        processor = NewPriceProcessor(product)
        
        result = processor._jump_to_avg()
        assert result == 75.0

    @pytest.mark.parametrize("min_price,max_price,missing_price", [
        (None, 100, "min"),
        (50, None, "max"),
        (None, None, "max"),  # When both are None, error mentions max first
    ])
    def test_jump_to_avg_missing_prices(self, min_price, max_price, missing_price):
        """Test _jump_to_avg with missing min or max prices."""
        product = self.create_mock_product(min_price=min_price, max_price=max_price)
        processor = NewPriceProcessor(product)
        
        with pytest.raises(SkipProductRepricing, match=f"but {missing_price} price is missing"):
            processor._jump_to_avg()

    def test_jump_to_min_success(self):
        """Test _jump_to_min with valid min price."""
        product = self.create_mock_product(min_price=25.99)
        processor = NewPriceProcessor(product)
        
        result = processor._jump_to_min()
        assert result == 25.99

    def test_jump_to_min_missing_price(self):
        """Test _jump_to_min with missing min price."""
        product = self.create_mock_product(min_price=None)
        processor = NewPriceProcessor(product)
        
        with pytest.raises(SkipProductRepricing, match="min price is missing"):
            processor._jump_to_min()

    def test_jump_to_max_success(self):
        """Test _jump_to_max with valid max price."""
        product = self.create_mock_product(max_price=199.99)
        processor = NewPriceProcessor(product)
        
        result = processor._jump_to_max()
        assert result == 199.99

    def test_jump_to_max_missing_price(self):
        """Test _jump_to_max with missing max price."""
        product = self.create_mock_product(max_price=None)
        processor = NewPriceProcessor(product)
        
        with pytest.raises(SkipProductRepricing, match="max price is missing"):
            processor._jump_to_max()

    def test_match_competitor_success(self):
        """Test _match_competitor with valid competitor price."""
        product = self.create_mock_product()
        product.competitor_price = 89.99
        processor = NewPriceProcessor(product)
        
        result = processor._match_competitor()
        assert result == 89.99

    def test_match_competitor_missing_price(self):
        """Test _match_competitor with missing competitor price."""
        product = self.create_mock_product()
        product.competitor_price = None
        processor = NewPriceProcessor(product)
        
        with pytest.raises(SkipProductRepricing, match="competitor price is missing"):
            processor._match_competitor()

    def test_do_nothing_always_raises(self):
        """Test _do_nothing always raises SkipProductRepricing."""
        product = self.create_mock_product()
        processor = NewPriceProcessor(product)
        
        with pytest.raises(SkipProductRepricing, match="Rule is set to do_nothing"):
            processor._do_nothing()

    @pytest.mark.parametrize("default_price,should_raise", [
        (50.0, False),      # Valid default price
        (None, True),       # No default price
        (0, True),          # Zero default price
        (-10, True),        # Negative default price
    ])
    def test_default_price_validation(self, default_price, should_raise):
        """Test _default_price with various default price values."""
        product = self.create_mock_product(default_price=default_price)
        processor = NewPriceProcessor(product)
        
        if should_raise:
            with pytest.raises(SkipProductRepricing, match="default_price is missing"):
                processor._default_price("SELLER123", "B01234567890")
        else:
            result = processor._default_price("SELLER123", "B01234567890")
            assert result == default_price

    def test_default_price_in_range_check_not_implemented(self):
        """Test _default_price with default price range check (not implemented)."""
        product = self.create_mock_product(default_price=100.0)
        processor = NewPriceProcessor(product)
        
        # Since check_default_price_in_range is not implemented,
        # it should return the default price
        result = processor._default_price("SELLER123", "B01234567890")
        assert result == 100.0

    def test_complex_price_processing_workflow(self):
        """Test complete price processing workflow with rule application."""
        product = self.create_mock_product(min_price=50, max_price=150, default_price=75)
        product.strategy.max_price_rule = "JUMP_TO_AVG"
        processor = NewPriceProcessor(product)
        
        # Test price above max triggers max rule
        result = processor.process_price(200, "SELLER123", "B01234567890")
        assert result == 100.0  # Average of 50 and 150

    def test_decimal_price_precision(self):
        """Test price processing maintains proper decimal precision.""" 
        product = self.create_mock_product(min_price=33.33, max_price=66.67)
        processor = NewPriceProcessor(product)
        
        result = processor._jump_to_avg()
        assert result == 50.0  # Should handle decimal precision correctly

    @pytest.mark.parametrize("price,min_p,max_p,expected", [
        (25.99, 30.0, 80.0, 30.0),    # Below min, jump to min
        (85.99, 30.0, 80.0, 80.0),    # Above max, jump to max
        (55.50, 30.0, 80.0, 55.50),   # Within range, no change
    ])
    def test_price_processing_integration(self, price, min_p, max_p, expected):
        """Integration test for full price processing logic."""
        product = self.create_mock_product(min_price=min_p, max_price=max_p)
        product.strategy.min_price_rule = "JUMP_TO_MIN"
        product.strategy.max_price_rule = "JUMP_TO_MAX"
        processor = NewPriceProcessor(product)
        
        result = processor.process_price(price, "SELLER123", "B01234567890")
        assert result == expected