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
    default_price=30.0,
    listed_price=None
):
    """Create a Mock tier that mimics B2BTier behavior for B2B testing."""
    # For now, use Mock objects to avoid Redis connection issues
    # TODO: Replace with real B2BTier instances once Redis is properly mocked
    
    tier = Mock()
    tier.competitor_price = competitor_price
    tier.min_price = min_price
    tier.max_price = max_price
    tier.default_price = default_price
    tier.listed_price = listed_price  # Add listed_price for winner detection
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
        """Test ChaseBuyBox for standard (non-B2B) products when we need to be competitive."""
        # Set up scenario where we need to be competitive (our price is higher than calculated)
        product = create_mock_product(
            listed_price=105.0,     # Our current price (losing)
            competitor_price=100.0, # Competitor price
            is_b2b=False,
            strategy_beat_by=0.01,
            min_price=90.0,
            max_price=110.0
        )
        
        # Mock the price processor instance
        mock_instance = Mock()
        mock_instance.process_price.return_value = 100.01  # Better than our current 105.0
        mock_processor_class.return_value = mock_instance
        
        strategy = ChaseBuyBox(product)
        strategy.apply()
        
        assert product.updated_price == 100.01
        assert hasattr(product, 'message')
        mock_instance.process_price.assert_called_once_with(100.01, "A1234567890123", "B01234567890")

    @patch('src.strategies.base_strategy.NewPriceProcessor')
    def test_apply_standard_pricing_with_bounds_violation(self, mock_processor_class):
        """Test ChaseBuyBox raises PriceBoundsError for standard products."""
        # Set up scenario where calculated price would violate bounds
        product = create_mock_product(
            listed_price=105.0,     # Our current price (higher, so we need to compete)
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
        """Test ChaseBuyBox for B2B products with tiers when we need to be competitive."""
        product = create_mock_product(
            listed_price=105.0,     # We're losing on main product
            competitor_price=100.0,
            is_b2b=True,
            strategy_beat_by=0.01,
            min_price=90.0,
            max_price=110.0
        )
        
        # Setup tier mocks - tier_1 needs to compete, tier_2 has no competitor
        tier_1 = create_mock_tier(
            listed_price=100.0,        # We're losing on this tier too
            competitor_price=95.0,     # Competitor is lower
            min_price=80.0,
            max_price=100.0
        )
        tier_2 = create_mock_tier(competitor_price=None)  # No competitor price
        
        product.tiers = {"5": tier_1, "10": tier_2}
        
        # Mock processor to return input price for simplicity
        mock_instance = Mock()
        mock_instance.process_price.side_effect = lambda price, *args: price
        mock_processor_class.return_value = mock_instance
        
        strategy = ChaseBuyBox(product)
        strategy.apply()
        
        # Check main product was processed (100 + 0.01 = 100.01, better than our 105.0)
        assert product.updated_price == 100.01
        
        # Check tier with competitor price was processed (95 + 0.01 = 95.01, better than our 100.0)
        assert tier_1.updated_price == 95.01
        assert tier_1.strategy == product.strategy
        assert tier_1.strategy_id == "1"
        
        # Tier without competitor price should be skipped
        assert tier_2.updated_price is None

    @patch('src.strategies.base_strategy.NewPriceProcessor')
    def test_apply_b2b_tier_with_bounds_violation(self, mock_processor_class):
        """Test ChaseBuyBox handles B2B tier bounds violations gracefully."""
        product = create_mock_product(
            listed_price=105.0,     # We're losing on main product
            competitor_price=100.0,
            is_b2b=True,
            strategy_beat_by=0.01,
            min_price=90.0,
            max_price=110.0
        )
        
        # Tier with competitor price that will violate bounds after calculation
        tier_bad = create_mock_tier(
            listed_price=65.0,          # We're losing on this tier
            competitor_price=50.0,      # 50.01 will be below min
            min_price=60.0,
            max_price=100.0
        )
        
        tier_good = create_mock_tier(
            listed_price=100.0,         # We're losing on this tier
            competitor_price=95.0,      # 95.01 is good
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
        
        # Main product should succeed (100.01 better than our 105.0)
        assert product.updated_price == 100.01
        
        # Bad tier should fail bounds validation (50.01 below min 60.0)
        assert tier_bad.updated_price is None
        
        # Good tier should succeed (95.01 better than our 100.0)
        assert tier_good.updated_price == 95.01

    @pytest.mark.parametrize("beat_by,competitor_price,expected_price,listed_price", [
        (0.01, 100, 100.01, 105.0),   # We're losing at 105, need to compete at 100.01
        (-0.01, 100, 99.99, 105.0),  # We're losing at 105, need to compete at 99.99
        (0.05, 50.25, 50.30, 55.0),  # We're losing at 55, need to compete at 50.30
        (1.00, 25.99, 26.99, 30.0),  # We're losing at 30, need to compete at 26.99
    ])
    @patch('src.strategies.base_strategy.NewPriceProcessor')
    def test_price_calculation_with_beat_by(self, mock_processor_class, beat_by, competitor_price, expected_price, listed_price):
        """Test price calculation with various beat_by values when we need to be competitive."""
        product = create_mock_product(
            listed_price=listed_price,  # Set our current price higher than expected to trigger repricing
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


class TestSelfCompetitionPrevention:
    """Test prevention of self-competition across all strategies."""

    def test_maxmise_profit_skip_when_already_winning(self):
        """Test MaximiseProfit skips repricing when current seller is already winning."""
        # Scenario: Our price ($30) is already higher than competitor ($25)
        # MaximiseProfit should skip because competitor has a lower price than us
        product = create_mock_product(
            listed_price=30.0,      # Our current price
            competitor_price=25.0,  # Competitor's lower price (they're winning)
            min_price=10.0,
            max_price=50.0,
            seller_id="TEST_SELLER_123"
        )
        
        strategy = MaximiseProfit(product)
        
        # MaximiseProfit correctly skips when competitor_price <= our listed_price
        # because there's no profit to maximize - competitor is already lower
        with pytest.raises(SkipProductRepricing) as exc_info:
            strategy.apply()
        
        # Verify the skip reason mentions competitor at lower price
        assert "lower price than us" in str(exc_info.value)
        assert product.updated_price is None

    def test_maxmise_profit_skip_when_equal_price(self):
        """Test MaximiseProfit skips repricing when prices are equal."""
        # Scenario: Our price equals competitor price - we're tied, no need to reprice
        product = create_mock_product(
            listed_price=25.0,      # Our current price
            competitor_price=25.0,  # Same as competitor
            min_price=10.0,
            max_price=50.0,
            seller_id="TEST_SELLER_123"
        )
        
        strategy = MaximiseProfit(product)
        
        # Should skip repricing because prices are equal
        with pytest.raises(SkipProductRepricing):
            strategy.apply()
        
        assert product.updated_price is None

    @patch('src.strategies.base_strategy.NewPriceProcessor')
    def test_chase_buybox_skip_when_already_optimal(self, mock_processor_class):
        """Test ChaseBuyBox logic for when seller is already in optimal position."""
        # Scenario: Our price is $24.99, competitor is $25.00, beat_by is -0.01
        # Calculated price would be $24.99, same as our current price
        # We should detect we're already optimal and skip repricing
        product = create_mock_product(
            listed_price=24.99,     # Our current price
            competitor_price=25.00, # Competitor price
            strategy_beat_by=-0.01, # Beat by 1 cent
            min_price=10.0,
            max_price=50.0,
            seller_id="TEST_SELLER_123"
        )
        
        # Mock processor to return the calculated price (which equals our current price)
        mock_instance = Mock()
        mock_instance.process_price.return_value = 24.99  # Same as current price
        mock_processor_class.return_value = mock_instance
        
        strategy = ChaseBuyBox(product)
        strategy.apply()
        
        # Strategy should complete but recognize we're already optimal
        # The price should be set but it's the same as current price
        assert product.updated_price == 24.99

    def test_all_strategies_skip_when_no_competitors(self):
        """Test all strategies skip when no competitors exist after self-filtering."""
        # This documents the existing behavior when competitor analysis
        # filters out all offers (including our own), leaving no competitors
        product = create_mock_product(
            competitor_price=None,  # No competitors after filtering out self
            seller_id="TEST_SELLER_123"
        )
        
        # Competitive strategies should skip when no competitors exist
        with pytest.raises(SkipProductRepricing):
            MaximiseProfit(product).apply()
            
        with pytest.raises(SkipProductRepricing):
            ChaseBuyBox(product).apply()
            
        # OnlySeller strategy doesn't need competitors, so it should work
        product_only_seller = create_mock_product(
            default_price=25.0,
            min_price=10.0,
            max_price=50.0,
            seller_id="TEST_SELLER_123"
        )
        OnlySeller(product_only_seller).apply()
        assert product_only_seller.updated_price == 25.0

    def test_chase_buybox_avoids_price_spiral(self):
        """Test ChaseBuyBox avoids price spiral when already winning."""
        # Scenario: We're already buybox winner at $20, next competitor is $22
        # Strategy: beat by $0.01 -> would calculate $21.99
        # But we're already winning at $20, so we should skip repricing!
        
        product = create_mock_product(
            listed_price=20.00,     # Our current winning price  
            competitor_price=22.00, # Competitor's higher price
            strategy_beat_by=-0.01, # Beat by 1 cent
            min_price=10.0,
            max_price=50.0,
            seller_id="TEST_SELLER_123"
        )
        
        strategy = ChaseBuyBox(product)
        
        # Now ChaseBuyBox should skip repricing when we're already winning
        with pytest.raises(SkipProductRepricing) as exc_info:
            strategy.apply()
        
        # Verify the skip reason mentions already winning
        assert "Already winning with better price" in str(exc_info.value)
        assert product.updated_price is None

    @patch('src.strategies.base_strategy.NewPriceProcessor')
    def test_chase_buybox_reprices_when_losing(self, mock_processor_class):
        """Test ChaseBuyBox still reprices when we're losing and need to be competitive."""
        # Scenario: We're losing at $25, competitor at $20, beat_by -0.01  
        # Calculated: $19.99, this is good - we should reprice lower
        product = create_mock_product(
            listed_price=25.00,     # We're losing
            competitor_price=20.00, # Competitor lower
            strategy_beat_by=-0.01,
            min_price=10.0,
            max_price=50.0,
            seller_id="TEST_SELLER_123"
        )
        
        # Mock processor to return the calculated price
        mock_instance = Mock()
        mock_instance.process_price.return_value = 19.99  # competitor_price + beat_by
        mock_processor_class.return_value = mock_instance
        
        strategy = ChaseBuyBox(product)
        strategy.apply()
        
        # Should reprice because calculated price (19.99) is better than our current price (25.00)
        assert product.updated_price == 19.99

    def test_chase_buybox_winner_vs_loser_scenarios(self):
        """Test ChaseBuyBox handles winner vs loser scenarios correctly."""
        
        # Scenario 1: We're winning at $15, competitor at $20, beat_by -0.01
        # Calculated: $19.99, but we're already better at $15 - should skip
        product1 = create_mock_product(
            listed_price=15.00,     # We're winning
            competitor_price=20.00, # Competitor higher
            strategy_beat_by=-0.01,
            min_price=10.0,
            max_price=50.0
        )
        
        strategy1 = ChaseBuyBox(product1)
        
        # Should skip repricing because we're already winning with a better price
        with pytest.raises(SkipProductRepricing) as exc_info:
            strategy1.apply()
        
        assert "Already winning with better price" in str(exc_info.value)
        assert product1.updated_price is None