import unittest
from unittest.mock import Mock
from exceptions import SkipProductRepricing

from models.models import Product
from strategies.only_seller import OnlySeller


class TestOnlySeller(unittest.TestCase):

    def setUp(self):
        self.product_mock = Mock(spec=Product)

        # Initialize tiers with default values
        self.product_mock.tiers = None

    def test_apply_with_default_price(self):
        # Test case 1: Product has a default price
        self.product_mock.default_price = 150

        strategy = OnlySeller(self.product_mock)
        strategy.apply()

        # Assert that product.updated_price is updated to default_price
        self.assertEqual(self.product_mock.updated_price, 150)

    def test_apply_without_default_price(self):
        # Test case 2: Product does not have a default price
        self.product_mock.default_price = None
        self.product_mock.min_price = 100
        self.product_mock.max_price = 200

        strategy = OnlySeller(self.product_mock)
        strategy.apply()

        # Calculate the expected updated price as the mean of min_price and max_price
        expected_updated_price = (self.product_mock.min_price + self.product_mock.max_price) / 2

        # Assert that product.updated_price is updated to the calculated mean
        self.assertEqual(self.product_mock.updated_price, expected_updated_price)

    def test_apply_with_default_price_and_valid_min_max_prices(self):
        # Test case 3: Product has a default price, and valid min_price and max_price
        self.product_mock.default_price = 150
        self.product_mock.min_price = 100
        self.product_mock.max_price = 200

        strategy = OnlySeller(self.product_mock)
        strategy.apply()

        # Assert that product.updated_price is updated to default_price
        self.assertEqual(self.product_mock.updated_price, 150)

    def test_apply_with_default_price_and_invalid_min_max_prices(self):
        # Test case 4: Product has a default price, but invalid min_price and max_price
        self.product_mock.default_price = None
        self.product_mock.min_price = 200  # Invalid: min_price or max_price
        self.product_mock.max_price = None

        strategy = OnlySeller(self.product_mock)

        # Assert that an exception is raised when applying the strategy
        with self.assertRaises(SkipProductRepricing):
            strategy.apply()

    def test_apply_without_default_price_and_invalid_min_max_prices(self):
        # Test case 5: Product does not have a default price, and has invalid min_price and max_price
        self.product_mock.default_price = None
        self.product_mock.min_price = None  # Invalid: min_price or max_price
        self.product_mock.max_price = 100

        strategy = OnlySeller(self.product_mock)

        # Assert that an exception is raised when applying the strategy
        with self.assertRaises(SkipProductRepricing):
            strategy.apply()


if __name__ == '__main__':
    unittest.main()
