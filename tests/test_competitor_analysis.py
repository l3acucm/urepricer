"""
Clean tests for SetCompetitorInfo competitor analysis functionality.
Tests competitor pricing logic with direct values and simple mocks.
"""
import pytest
import unittest.mock
from unittest.mock import Mock

from src.tasks.set_competitor_info import SetCompetitorInfo, SkipProductRepricing


class TestSetCompetitorInfo:
    """Test SetCompetitorInfo competitor analysis functionality."""

    def create_mock_product(self, seller_id="A1234567890123", is_b2b=False, compete_with="LOWEST_PRICE"):
        """Helper to create a mock product with common attributes."""
        product = Mock()
        product.asin = "B01234567890"
        product.is_b2b = is_b2b
        product.mapped_item_condition = "new"
        
        # Account mock
        account = Mock()
        account.seller_id = seller_id
        product.account = account
        
        # Strategy mock
        strategy = Mock()
        strategy.compete_with = compete_with
        product.strategy = strategy
        
        # Initialize pricing attributes
        product.competitor_price = None
        product.no_of_offers = 0
        product.is_seller_buybox_winner = False
        
        # Tiers for B2B products
        product.tiers = {}
        
        return product

    def test_set_number_of_offers(self):
        """Test setting number of offers from payload."""
        product = self.create_mock_product()
        payload = {"Summary.TotalOfferCount": 5}
        
        competitor_info = SetCompetitorInfo(product, payload)
        competitor_info._set_number_of_offers()
        
        assert product.no_of_offers == 5

    def test_apply_single_offer_no_competitor_analysis(self):
        """Test that no competitor analysis is done when only 1 offer exists."""
        product = self.create_mock_product()
        payload = {"Summary.TotalOfferCount": 1}
        
        competitor_info = SetCompetitorInfo(product, payload)
        result = competitor_info.apply()
        
        assert result.no_of_offers == 1
        assert result.competitor_price is None

    @pytest.mark.parametrize("compete_with,expected_method", [
        ("LOWEST_FBA_PRICE", "_set_fba_lowest_price"),
        ("LOWEST_PRICE", "_set_min_price"), 
        ("MATCH_BUYBOX", "_set_buybox_price"),
    ])
    def test_competitors_info_routing(self, compete_with, expected_method):
        """Test that competitor info routing calls correct method."""
        product = self.create_mock_product(compete_with=compete_with)
        payload = {"Summary.TotalOfferCount": 3}
        
        competitor_info = SetCompetitorInfo(product, payload)
        
        # Mock the specific method to verify it's called
        with unittest.mock.patch.object(competitor_info, expected_method) as mock_method:
            competitor_info.apply()
            mock_method.assert_called_once()

    def test_set_fba_lowest_price_success(self):
        """Test setting FBA lowest price successfully."""
        product = self.create_mock_product()
        
        offers = [
            {
                "SubCondition": "New",
                "IsFulfilledByAmazon": True,
                "ListingPrice.Amount": 25.99,
                "SellerId": "ANOTHERSELLERID"
            },
            {
                "SubCondition": "New", 
                "IsFulfilledByAmazon": True,
                "ListingPrice.Amount": 24.99,
                "SellerId": "DIFFERENTSELLERID"
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 3,
            "Offers": offers
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        competitor_info.apply()
        
        assert product.competitor_price == 24.99  # Lowest FBA price

    def test_set_fba_lowest_price_skip_own_offer(self):
        """Test FBA lowest price skips seller's own offer."""
        product = self.create_mock_product(seller_id="A1234567890123")
        
        offers = [
            {
                "SubCondition": "New",
                "IsFulfilledByAmazon": True,
                "ListingPrice.Amount": 20.99,
                "SellerId": "A1234567890123"  # Our seller ID
            },
            {
                "SubCondition": "New",
                "IsFulfilledByAmazon": True, 
                "ListingPrice.Amount": 25.99,
                "SellerId": "ANOTHERSELLERID"
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 3,
            "Offers": offers
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        competitor_info.apply()
        
        assert product.competitor_price == 25.99  # Skip our own offer

    def test_set_fba_lowest_price_only_own_offer_raises_exception(self):
        """Test FBA lowest price raises exception when only our offer exists."""
        product = self.create_mock_product(seller_id="A1234567890123")
        
        offers = [
            {
                "SubCondition": "New",
                "IsFulfilledByAmazon": True,
                "ListingPrice.Amount": 20.99,
                "SellerId": "A1234567890123"  # Only our offer
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 2,
            "Offers": offers
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        
        with pytest.raises(SkipProductRepricing, match="This seller has the only"):
            competitor_info.apply()

    def test_set_min_price_success(self):
        """Test setting minimum price from all offers."""
        product = self.create_mock_product(compete_with="LOWEST_PRICE")
        
        offers = [
            {
                "SubCondition": "New",
                "ListingPrice.Amount": 25.99,
                "SellerId": "SELLERID1"
            },
            {
                "SubCondition": "New",
                "ListingPrice.Amount": 20.99,  # Lowest
                "SellerId": "SELLERID2"
            },
            {
                "SubCondition": "New",
                "ListingPrice.Amount": 30.99,
                "SellerId": "SELLERID3"
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 4,
            "Offers": offers
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        competitor_info.apply()
        
        assert product.competitor_price == 20.99

    def test_set_buybox_price_success(self):
        """Test setting buybox winner price."""
        product = self.create_mock_product(compete_with="MATCH_BUYBOX")
        
        offers = [
            {
                "IsBuyBoxWinner": False,
                "ListingPrice.Amount": 25.99,
                "SellerId": "SELLERID1"
            },
            {
                "IsBuyBoxWinner": True,  # Buybox winner
                "ListingPrice.Amount": 22.99,
                "SellerId": "SELLERID2"
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 3,
            "Offers": offers
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        competitor_info.apply()
        
        assert product.competitor_price == 22.99

    def test_set_buybox_price_seller_is_winner(self):
        """Test buybox price when seller is the winner."""
        product = self.create_mock_product(seller_id="A1234567890123", compete_with="MATCH_BUYBOX")
        
        offers = [
            {
                "IsBuyBoxWinner": True,
                "ListingPrice.Amount": 22.99,
                "SellerId": "A1234567890123"  # We are the buybox winner
            },
            {
                "IsBuyBoxWinner": False,
                "ListingPrice.Amount": 25.99,
                "SellerId": "SELLERID2"
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 3,
            "Offers": offers
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        competitor_info.apply()
        
        assert product.is_seller_buybox_winner is True
        assert product.competitor_price == 25.99  # Use second offer

    def test_set_buybox_price_no_buybox_winner(self):
        """Test buybox price when no buybox winner exists."""
        product = self.create_mock_product(compete_with="MATCH_BUYBOX")
        
        offers = [
            {
                "IsBuyBoxWinner": False,
                "ListingPrice.Amount": 25.99,
                "SellerId": "SELLERID1"
            },
            {
                "IsBuyBoxWinner": False,
                "ListingPrice.Amount": 22.99,
                "SellerId": "SELLERID2"
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 3,
            "Offers": offers
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        
        with pytest.raises(SkipProductRepricing, match="Buybox is suppressed"):
            competitor_info.apply()

    def test_b2b_pricing_standard_offer(self):
        """Test B2B pricing for standard offer."""
        product = self.create_mock_product(is_b2b=True, compete_with="MATCH_BUYBOX")
        
        summaries = [
            {
                "condition": "new",
                "offerType": "B2C",
                "quantityTier": 1,
                "ListingPrice.Amount": 25.99,
                "sellerId": "ANOTHERSELLERID"
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 2,
            "Summary.BuyBoxPrices": summaries
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        competitor_info.apply()
        
        assert product.competitor_price == 25.99

    def test_b2b_pricing_with_tiers(self):
        """Test B2B pricing with quantity tiers."""
        product = self.create_mock_product(is_b2b=True, compete_with="LOWEST_PRICE")
        
        # Create mock tiers
        tier_5 = Mock()
        tier_5.competitor_price = None
        tier_10 = Mock() 
        tier_10.competitor_price = None
        
        product.tiers = {"5": tier_5, "10": tier_10}
        
        summaries = [
            {
                "condition": "new",
                "offerType": "B2B",  # This will trigger the else clause
                "quantityTier": 5,
                "ListingPrice.Amount": 20.99,
                "sellerId": "ANOTHERSELLERID"
            },
            {
                "condition": "new", 
                "quantityTier": 10,
                "ListingPrice.Amount": 18.99,
                "sellerId": "ANOTHERSELLERID"
            },
            {
                "condition": "new",
                "quantityTier": 15,  # No matching tier
                "ListingPrice.Amount": 15.99,
                "sellerId": "ANOTHERSELLERID"
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 4,
            "Summary.LowestPrices": summaries
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        competitor_info.apply()
        
        assert tier_5.competitor_price == 20.99
        assert tier_10.competitor_price == 18.99

    @pytest.mark.parametrize("condition_input,mapped_condition", [
        ("new", "new"),
        ("NEW", "new"), 
        ("used", "used"),
        ("USED", "used"),
    ])
    def test_condition_filtering(self, condition_input, mapped_condition):
        """Test that condition filtering works with case variations."""
        product = self.create_mock_product(compete_with="LOWEST_PRICE")
        product.mapped_item_condition = mapped_condition
        
        offers = [
            {
                "SubCondition": condition_input,
                "ListingPrice.Amount": 25.99,
                "SellerId": "SELLERID1"
            },
            {
                "SubCondition": "Different",  # Should be filtered out
                "ListingPrice.Amount": 15.99,
                "SellerId": "SELLERID2"
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 3,
            "Offers": offers
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        competitor_info.apply()
        
        assert product.competitor_price == 25.99  # Only matching condition

    def test_no_matching_offers_raises_exception(self):
        """Test that exception is raised when no matching offers found."""
        product = self.create_mock_product(compete_with="LOWEST_FBA_PRICE")
        
        offers = [
            {
                "SubCondition": "Used",  # Different condition
                "IsFulfilledByAmazon": True,
                "ListingPrice.Amount": 25.99,
                "SellerId": "SELLERID1"
            }
        ]
        
        payload = {
            "Summary.TotalOfferCount": 2,
            "Offers": offers
        }
        
        competitor_info = SetCompetitorInfo(product, payload)
        
        with pytest.raises(SkipProductRepricing, match="Competitor not found"):
            competitor_info.apply()