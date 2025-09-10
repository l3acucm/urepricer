"""
Clean, parametrized tests for all pricing strategies.
Tests the core business logic with direct values and simple mocks.
Updated for new BaseStrategy architecture with price bounds validation.
"""
import pytest
from unittest.mock import Mock, patch
from src.strategies.maxmise_profit import MaximiseProfit
from src.strategies.only_seller import OnlySeller
from src.strategies.chase_buybox import ChaseBuyBox
from src.strategies.base_strategy import PriceBoundsError
from src.strategies.new_price_processor import SkipProductRepricing


def create_mock_product(
    listed_price=25.0,
    competitor_price=30.0,
    min_price=10.0,
    max_price=50.0,
    default_price=20.0,
    is_b2b=False,
    asin="B01234567890",
    seller_id="A1234567890123",
    strategy_beat_by=0.01
):
    """Create a Mock product that mimics ProductListing behavior for strategy testing."""
    # For now, use Mock objects to avoid Redis connection issues
    # TODO: Replace with real ProductListing instances once Redis is properly mocked
    
    product = Mock()
    
    # Core pricing attributes
    product.listed_price = listed_price
    product.competitor_price = competitor_price
    product.min_price = min_price
    product.max_price = max_price
    product.default_price = default_price
    product.is_b2b = is_b2b
    
    # Product identification
    product.asin = asin
    product.seller_id = seller_id
    
    # Account mock for backward compatibility
    product.account = Mock()
    product.account.seller_id = seller_id
    
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


def create_mock_tier(
    competitor_price=95.0,
    min_price=20.0,
    max_price=40.0,
    default_price=30.0
):
    """Create a Mock tier that mimics B2BTier behavior for B2B testing."""
    # For now, use Mock objects to avoid Redis connection issues
    # TODO: Replace with real B2BTier instances once Redis is properly mocked
    
    tier = Mock()
    tier.competitor_price = competitor_price
    tier.min_price = min_price
    tier.max_price = max_price
    tier.default_price = default_price
    tier.updated_price = None
    tier.strategy = None
    tier.strategy_id = None
    tier.message = ""
    return tier


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
        product = create_mock_product(
            listed_price=listed_price,
            competitor_price=competitor_price,
            min_price=1.0,  # Valid bounds
            max_price=10**10  # Very high max to avoid bounds issues
        )
        
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
        (1, 1000, 1000),     # Large difference - update
        (50.25, 75.678, 75.68),  # Decimal rounding test
        (100, 125.99, 125.99), # Normal case
    ])
    def test_apply_should_update(self, listed_price, competitor_price, expected_price):
        """Test cases where MaximiseProfit should update price."""
        product = create_mock_product(
            listed_price=listed_price,
            competitor_price=competitor_price,
            min_price=1.0,  # Valid bounds
            max_price=10000.0  # High max to avoid bounds issues
        )
        
        strategy = MaximiseProfit(product)
        strategy.apply()
        
        assert product.updated_price == expected_price
        assert hasattr(product, 'message')
        assert hasattr(product, 'strategy')
        assert product.strategy_id == "1"

    def test_apply_price_bounds_violation(self):
        """Test MaximiseProfit raises PriceBoundsError when competitor price exceeds bounds."""
        product = create_mock_product(
            listed_price=25.0,
            competitor_price=60.0,  # Above max price
            min_price=10.0,
            max_price=50.0
        )
        
        strategy = MaximiseProfit(product)
        
        with pytest.raises(PriceBoundsError) as exc_info:
            strategy.apply()
        
        error = exc_info.value
        assert error.calculated_price == 60.0
        assert error.min_price == 10.0
        assert error.max_price == 50.0
        assert "exceeds maximum price" in str(error)
        assert product.updated_price is None

    def test_apply_with_no_bounds(self):
        """Test MaximiseProfit works when no bounds are set."""
        product = create_mock_product(
            listed_price=25.0,
            competitor_price=100.0,
            min_price=None,  # No bounds
            max_price=None
        )
        
        strategy = MaximiseProfit(product)
        strategy.apply()
        
        assert product.updated_price == 100.0


class TestOnlySeller:
    """Test OnlySeller strategy with parametrized test cases."""

    @pytest.mark.parametrize("default_price,min_price,max_price,expected_price,should_raise", [
        (150, None, None, 150, False),    # Has default price, no bounds validation
        (150, 100, 200, 150, False),      # Has default price within bounds
        (None, 100, 200, 150, False),     # No default, use mean of min/max
        (None, 200, None, None, True),    # Invalid: min without max
        (None, 200, 100, None, True),      # Invalid: min > max, mean(150) < min(200)
        (None, None, 100, None, True),    # Invalid: max without min
        (None, None, None, None, True),   # Invalid: no prices at all
        (0, 50, 100, 0, True),           # Default is 0, but below min_price - should raise
        (None, 50.5, 100.5, 75.5, False), # Decimal mean calculation
    ])
    def test_apply_various_pricing_scenarios(self, default_price, min_price, max_price, expected_price, should_raise):
        """Test OnlySeller strategy with various pricing scenarios."""
        product = create_mock_product(
            default_price=default_price,
            min_price=min_price,
            max_price=max_price,
            is_b2b=False
        )
        product.tiers = {}  # Ensure no tiers
        
        strategy = OnlySeller(product)
        
        if should_raise:
            with pytest.raises((SkipProductRepricing, PriceBoundsError)):
                strategy.apply()
            assert product.updated_price is None
        else:
            strategy.apply()
            assert product.updated_price == expected_price
            assert hasattr(product, 'strategy')
            assert hasattr(product, 'message')

    def test_apply_default_price_outside_bounds(self):
        """Test OnlySeller raises PriceBoundsError when default price is outside bounds."""
        product = create_mock_product(
            default_price=5.0,  # Below min price
            min_price=10.0,
            max_price=50.0,
            is_b2b=False
        )
        
        strategy = OnlySeller(product)
        
        with pytest.raises(PriceBoundsError) as exc_info:
            strategy.apply()
        
        error = exc_info.value
        assert error.calculated_price == 5.0
        assert error.min_price == 10.0
        assert error.max_price == 50.0
        assert product.updated_price is None

    def test_apply_mean_price_outside_bounds(self):
        """Test OnlySeller raises PriceBoundsError when calculated mean price is outside bounds."""
        product = create_mock_product(
            default_price=None,  # Force mean calculation
            min_price=45.0,  # Mean will be 42.5, below min
            max_price=40.0,
            is_b2b=False
        )
        
        strategy = OnlySeller(product)
        
        with pytest.raises(PriceBoundsError):
            strategy.apply()
        
        assert product.updated_price is None

    def test_apply_with_b2b_tiers(self):
        """Test OnlySeller with B2B tiers."""
        product = create_mock_product(
            default_price=100,
            min_price=50,
            max_price=200,
            is_b2b=True
        )
        
        # Create mock tiers
        tier_1 = create_mock_tier(
            default_price=90,
            min_price=70,
            max_price=150
        )
        
        tier_2 = create_mock_tier(
            default_price=None,  # Will use mean of 80 and 120 = 100
            min_price=80,
            max_price=120
        )
        
        product.tiers = {"5": tier_1, "10": tier_2}
        
        strategy = OnlySeller(product)
        strategy.apply()
        
        # Check main product
        assert product.updated_price == 100
        assert product.strategy == product.strategy  # Strategy set by mock
        assert product.strategy_id == "1"
        
        # Check tiers
        assert tier_1.updated_price == 90
        assert tier_1.strategy == product.strategy
        assert tier_1.strategy_id == "1"
        
        assert tier_2.updated_price == 100  # Mean of 80 and 120
        assert tier_2.strategy == product.strategy
        assert tier_2.strategy_id == "1"

    def test_apply_b2b_tier_with_bounds_violation(self):
        """Test OnlySeller handles B2B tier bounds violations gracefully."""
        product = create_mock_product(
            default_price=100,
            min_price=50,
            max_price=200,
            is_b2b=True
        )
        
        # Create tier with default price outside its bounds
        tier_with_bad_price = create_mock_tier(
            default_price=10.0,  # Below tier min
            min_price=20.0,
            max_price=40.0
        )
        
        # Create valid tier
        tier_valid = create_mock_tier(
            default_price=30.0,
            min_price=20.0,
            max_price=40.0
        )
        
        product.tiers = {"bad": tier_with_bad_price, "good": tier_valid}
        
        strategy = OnlySeller(product)
        strategy.apply()  # Should not raise exception
        
        # Main product should succeed
        assert product.updated_price == 100
        
        # Bad tier should fail
        assert tier_with_bad_price.updated_price is None
        
        # Good tier should succeed
        assert tier_valid.updated_price == 30.0


class TestChaseBuyBox:
    """Test ChaseBuyBox strategy with parametrized test cases."""

    @patch('src.strategies.base_strategy.NewPriceProcessor')
    def test_apply_standard_pricing(self, mock_processor_class):
        """Test ChaseBuyBox for standard (non-B2B) products."""
        product = create_mock_product(
            competitor_price=100.0,
            is_b2b=False,
            strategy_beat_by=0.01,
            min_price=90.0,
            max_price=110.0
        )
        
        # Mock the price processor instance
        mock_instance = Mock()
        mock_instance.process_price.return_value = 100.01
        mock_processor_class.return_value = mock_instance
        
        strategy = ChaseBuyBox(product)
        strategy.apply()
        
        assert product.updated_price == 100.01
        assert hasattr(product, 'message')
        mock_instance.process_price.assert_called_once_with(100.01, "A1234567890123", "B01234567890")

    @patch('src.strategies.base_strategy.NewPriceProcessor')
    def test_apply_standard_pricing_with_bounds_violation(self, mock_processor_class):
        """Test ChaseBuyBox raises PriceBoundsError for standard products."""
        product = create_mock_product(
            competitor_price=100.0,
            is_b2b=False,
            strategy_beat_by=0.01,
            min_price=90.0,
            max_price=95.0  # 100.01 will exceed this
        )
        
        strategy = ChaseBuyBox(product)
        
        with pytest.raises(PriceBoundsError) as exc_info:
            strategy.apply()
        
        error = exc_info.value
        assert error.calculated_price == 100.01
        assert error.max_price == 95.0
        assert product.updated_price is None

    @patch('src.strategies.base_strategy.NewPriceProcessor')
    def test_apply_b2b_pricing(self, mock_processor_class):
        """Test ChaseBuyBox for B2B products with tiers."""
        product = create_mock_product(
            competitor_price=100.0,
            is_b2b=True,
            strategy_beat_by=0.01,
            min_price=90.0,
            max_price=110.0
        )
        
        # Setup tier mocks
        tier_1 = create_mock_tier(competitor_price=95.0, min_price=80.0, max_price=100.0)
        tier_2 = create_mock_tier(competitor_price=None)  # No competitor price
        
        product.tiers = {"5": tier_1, "10": tier_2}
        
        # Mock processor to return input price for simplicity
        mock_instance = Mock()
        mock_instance.process_price.side_effect = lambda price, *args: price
        mock_processor_class.return_value = mock_instance
        
        strategy = ChaseBuyBox(product)
        strategy.apply()
        
        # Check main product was processed (100 + 0.01 = 100.01)
        assert product.updated_price == 100.01
        
        # Check tier with competitor price was processed (95 + 0.01 = 95.01)
        assert tier_1.updated_price == 95.01
        assert tier_1.strategy == product.strategy
        assert tier_1.strategy_id == "1"
        
        # Tier without competitor price should be skipped
        assert tier_2.updated_price is None

    @patch('src.strategies.base_strategy.NewPriceProcessor')
    def test_apply_b2b_tier_with_bounds_violation(self, mock_processor_class):
        """Test ChaseBuyBox handles B2B tier bounds violations gracefully."""
        product = create_mock_product(
            competitor_price=100.0,
            is_b2b=True,
            strategy_beat_by=0.01,
            min_price=90.0,
            max_price=110.0
        )
        
        # Tier with competitor price that will violate bounds after calculation
        tier_bad = create_mock_tier(
            competitor_price=50.0,  # 50.01 will be below min
            min_price=60.0,
            max_price=100.0
        )
        
        tier_good = create_mock_tier(
            competitor_price=95.0,
            min_price=80.0,
            max_price=100.0
        )
        
        product.tiers = {"bad": tier_bad, "good": tier_good}
        
        # Mock processor
        mock_instance = Mock()
        mock_instance.process_price.side_effect = lambda price, *args: price
        mock_processor_class.return_value = mock_instance
        
        strategy = ChaseBuyBox(product)
        strategy.apply()
        
        # Main product should succeed
        assert product.updated_price == 100.01
        
        # Bad tier should fail bounds validation
        assert tier_bad.updated_price is None
        
        # Good tier should succeed
        assert tier_good.updated_price == 95.01

    @pytest.mark.parametrize("beat_by,competitor_price,expected_price", [
        (0.01, 100, 100.01),
        (-0.01, 100, 99.99),  # Beat by negative amount (undercut)
        (0.05, 50.25, 50.30),
        (1.00, 25.99, 26.99),
    ])
    @patch('src.strategies.base_strategy.NewPriceProcessor')
    def test_price_calculation_with_beat_by(self, mock_processor_class, beat_by, competitor_price, expected_price):
        """Test price calculation with various beat_by values."""
        product = create_mock_product(
            competitor_price=competitor_price,
            is_b2b=False,
            strategy_beat_by=beat_by,
            min_price=0.0,    # Wide bounds to avoid validation issues
            max_price=1000.0
        )
        
        # Mock processor to return the calculated price
        mock_instance = Mock()
        mock_instance.process_price.return_value = expected_price
        mock_processor_class.return_value = mock_instance
        
        strategy = ChaseBuyBox(product)
        strategy.apply()
        
        # Verify the expected price was calculated and passed to processor
        mock_instance.process_price.assert_called_once_with(
            expected_price, "A1234567890123", "B01234567890"
        )
        assert product.updated_price == expected_price

    def test_apply_no_competitor_price(self):
        """Test ChaseBuyBox raises SkipProductRepricing when no competitor price."""
        product = create_mock_product(
            competitor_price=None,
            is_b2b=False
        )
        
        strategy = ChaseBuyBox(product)
        
        with pytest.raises(SkipProductRepricing):
            strategy.apply()
        
        assert product.updated_price is None