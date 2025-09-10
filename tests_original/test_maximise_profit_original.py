import unittest
from unittest.mock import Mock
from exceptions import SkipProductRepricing

from models.models import Product
from strategies.maxmise_profit import MaximiseProfit


class TestMaximiseProfit(unittest.TestCase):

    def setUp(self):
        self.product_mock = Mock(spec=Product)

        # set default values
        self.product_mock.updated_price = None

    def test_apply_lower_competitor_price(self):
        # Test case 1: Competitor price is lower than the listed price
        self.product_mock.listed_price = 120
        self.product_mock.competitor_price = 100

        maximizer = MaximiseProfit(self.product_mock)

        # Assert that SkipProductRepricing exception is raised
        with self.assertRaises(SkipProductRepricing):
            maximizer.apply()

        # Ensure that product.updated_price is not set
        self.assertIsNone(self.product_mock.updated_price)

    def test_apply_equal_competitor_price(self):
        # Test case 2: Competitor price is equal to the listed price
        self.product_mock.listed_price = 100
        self.product_mock.competitor_price = 100

        maximizer = MaximiseProfit(self.product_mock)

        # Assert that SkipProductRepricing exception is raised
        with self.assertRaises(SkipProductRepricing):
            maximizer.apply()

        # Ensure that product.updated_price is not set
        self.assertIsNone(self.product_mock.updated_price)

    def test_apply_higher_competitor_price(self):
        # Test case 3: Competitor price is higher than the listed price
        self.product_mock.listed_price = 120
        self.product_mock.competitor_price = 150

        maximizer = MaximiseProfit(self.product_mock)

        # Apply the strategy
        maximizer.apply()

        # Assert that product.updated_price is updated to competitor_price
        self.assertEqual(self.product_mock.updated_price, 150)

    # Test case 4: Additional test case for negative prices
    def test_apply_negative_prices(self):
        self.product_mock.listed_price = 80
        self.product_mock.competitor_price = -90

        maximizer = MaximiseProfit(self.product_mock)

        # Assert that SkipProductRepricing exception is raised
        with self.assertRaises(SkipProductRepricing):
            maximizer.apply()

        # Ensure that product.updated_price is not set
        self.assertIsNone(self.product_mock.updated_price)

    # Test case 5: Additional test case for zero prices
    def test_apply_zero_prices(self):
        self.product_mock.listed_price = 0
        self.product_mock.competitor_price = 0

        maximizer = MaximiseProfit(self.product_mock)

        # Assert that SkipProductRepricing exception is raised
        with self.assertRaises(SkipProductRepricing):
            maximizer.apply()

        # Ensure that product.updated_price is not set
        self.assertIsNone(self.product_mock.updated_price)

    # Test case 6: Additional test case for lower bound prices
    def test_apply_lower_bound_prices(self):
        self.product_mock.listed_price = 100
        self.product_mock.competitor_price = 0

        maximizer = MaximiseProfit(self.product_mock)

        # Assert that SkipProductRepricing exception is raised
        with self.assertRaises(SkipProductRepricing):
            maximizer.apply()

        # Ensure that product.updated_price is not set
        self.assertIsNone(self.product_mock.updated_price)

    # Test case 7: Additional test case for negative competitor price
    def test_apply_negative_competitor_price(self):
        self.product_mock.listed_price = 120
        self.product_mock.competitor_price = -100

        maximizer = MaximiseProfit(self.product_mock)

        # Assert that SkipProductRepricing exception is raised
        with self.assertRaises(SkipProductRepricing):
            maximizer.apply()

        # Ensure that product.updated_price is not set
        self.assertIsNone(self.product_mock.updated_price)

    # Test case 8: Additional test case for lower bound boundary values
    def test_apply_boundary_lower_bound(self):
        self.product_mock.listed_price = 1
        self.product_mock.competitor_price = 1

        maximizer = MaximiseProfit(self.product_mock)

        # Assert that SkipProductRepricing exception is raised
        with self.assertRaises(SkipProductRepricing):
            maximizer.apply()

        # Ensure that product.updated_price is not set
        self.assertIsNone(self.product_mock.updated_price)

    # Test case 9: Additional test case for upper bound boundary values
    def test_apply_boundary_upper_bound(self):
        self.product_mock.listed_price = 10**9
        self.product_mock.competitor_price = 10**9

        maximizer = MaximiseProfit(self.product_mock)

        # Assert that SkipProductRepricing exception is raised
        with self.assertRaises(SkipProductRepricing):
            maximizer.apply()

        # Ensure that product.updated_price is not set
        self.assertIsNone(self.product_mock.updated_price)

    # Test case 10: Additional test case for a large difference
    def test_apply_large_difference(self):
        self.product_mock.listed_price = 1
        self.product_mock.competitor_price = 10**9

        maximizer = MaximiseProfit(self.product_mock)
        maximizer.apply()

        # Assert that product.updated_price is updated to competitor_price
        self.assertEqual(self.product_mock.updated_price, 10**9)

    # Test case 11: Additional test case for extremely large prices
    def test_apply_extremely_large_prices(self):
        self.product_mock.listed_price = 10**15 + 1
        self.product_mock.competitor_price = 10**15

        maximizer = MaximiseProfit(self.product_mock)

        # Assert that SkipProductRepricing exception is raised
        with self.assertRaises(SkipProductRepricing):
            maximizer.apply()

        # Ensure that product.updated_price is not set
        self.assertIsNone(self.product_mock.updated_price)


if __name__ == '__main__':
    unittest.main()
