"""Better fixture design for pricing tests."""

import pytest
from decimal import Decimal
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ProductData:
    """Structured product data instead of raw dictionaries."""
    asin: str
    seller_id: str  
    sku: str
    min_price: Decimal
    max_price: Decimal
    listed_price: Decimal
    strategy_id: int
    fulfillment_type: str = "AMAZON"
    item_condition: str = "new"

@dataclass
class PricingScenario:
    """Test scenario with expected outcomes."""
    name: str
    product: ProductData
    competitor_price: Decimal
    strategy: Dict[str, Any]
    expected_price: Decimal
    should_succeed: bool = True
    expected_exception: Optional[type] = None

# Factory for creating test data
class TestDataFactory:
    """Factory for creating consistent test data."""
    
    @staticmethod
    def create_standard_product(**overrides) -> ProductData:
        defaults = {
            "asin": "B00ZVGB1KO",
            "seller_id": "A3FYUV88HJ6LTP", 
            "sku": "ZXAK012H21",
            "min_price": Decimal("5.12"),
            "max_price": Decimal("22.00"),
            "listed_price": Decimal("40.00"),
            "strategy_id": 1
        }
        defaults.update(overrides)
        return ProductData(**defaults)
    
    @staticmethod
    def create_pricing_scenarios() -> list[PricingScenario]:
        """Create comprehensive test scenarios."""
        return [
            PricingScenario(
                name="jump_to_min_when_competitor_high",
                product=TestDataFactory.create_standard_product(min_price=Decimal("22.00")),
                competitor_price=Decimal("29.50"),
                strategy={"rule": "jump_to_min", "beat_by": Decimal("0.1")},
                expected_price=Decimal("22.00")
            ),
            PricingScenario(
                name="match_competitor_when_in_range",
                product=TestDataFactory.create_standard_product(min_price=Decimal("25.00"), max_price=Decimal("35.00")),
                competitor_price=Decimal("30.76"),
                strategy={"rule": "match_competitor"},
                expected_price=Decimal("30.76")
            ),
            PricingScenario(
                name="exception_when_competitor_below_viable",
                product=TestDataFactory.create_standard_product(min_price=Decimal("25.00")),
                competitor_price=Decimal("17.00"),
                strategy={"rule": "jump_to_min"},
                expected_price=None,
                should_succeed=False,
                expected_exception=SkipProductRepricing
            )
        ]

# Better fixtures
@pytest.fixture
def standard_product():
    """Standard product for basic testing."""
    return TestDataFactory.create_standard_product()

@pytest.fixture
def pricing_scenarios():
    """All pricing test scenarios."""
    return TestDataFactory.create_pricing_scenarios()

@pytest.fixture
def mock_pricing_service():
    """Properly configured mock service."""
    with patch('src.services.PricingService') as mock:
        # Configure realistic behavior
        instance = mock.return_value
        instance.calculate_price.side_effect = lambda product, competitor, strategy: (
            PricingResult(competitor, min(competitor, product.max_price))
        )
        yield instance