import unittest
from unittest.mock import Mock

from models.models import Strategy
from exceptions import SkipProductRepricing
from strategies.chase_buybox import NewPriceProcessor


class TestNewPriceProcessor(unittest.TestCase):

    def setUp(self):
        self.product_mock = Mock()
        self.product_mock.min_price = None
        self.product_mock.max_price = None
        self.product_mock.default_price = None
        self.product_mock.competitor_price = None
        self.product_mock.strategy = Strategy()

    def test_process_price_below_min(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.min_price = 10
        self.product_mock.strategy.min_price_rule = "jump_to_min"

        new_price = processor.process_price(5)

        self.assertEqual(new_price, 10)

    def test_process_price_above_max(self):
        processor = NewPriceProcessor(self.product_mock)

        self.product_mock.max_price = 100
        self.product_mock.strategy.max_price_rule = "jump_to_max"

        new_price = processor.process_price(150)

        self.assertEqual(new_price, 100)

    def test_process_price_match_competitor(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.competitor_price = 90
        self.product_mock.min_price = 100
        self.product_mock.strategy.min_price_rule = "match_competitor"

        new_price = processor.process_price(80)

        self.assertEqual(new_price, 90)

    def test_process_price_default_price(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.default_price = 50
        self.product_mock.min_price = 70
        self.product_mock.strategy.min_price_rule = "default_price"

        new_price = processor.process_price(60)

        self.assertEqual(new_price, 50)

    def test_process_price_do_nothing(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.strategy.min_price_rule = "do_nothing"
        self.product_mock.min_price = 110

        with self.assertRaises(SkipProductRepricing):
            processor.process_price(100)

    def test_process_price_below_min_edge_case(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.min_price = 10
        self.product_mock.strategy.min_price_rule = "jump_to_min"

        new_price = processor.process_price(9)

        self.assertEqual(new_price, 10)

    def test_process_price_above_max_edge_case(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.max_price = 100
        self.product_mock.strategy.max_price_rule = "jump_to_max"

        new_price = processor.process_price(101)

        self.assertEqual(new_price, 100)

    def test_process_no_rule_defined_with_min_value(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.min_price = 100
        new_price = processor.process_price(101)
        self.assertEqual(new_price, 101)

    def test_process_price_rules_defined_without_min(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.strategy.min_price_rule = "jump_to_min"
        new_price = processor.process_price(101)
        self.assertEqual(new_price, 101)

    def test_process_price_rules_for_both_min_max_defined(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.strategy.min_price_rule = "jump_to_min"
        self.product_mock.strategy.min_price_rule = "jump_to_max"
        new_price = processor.process_price(101)
        self.assertEqual(new_price, 101)

    def test_process_no_rule_defined(self):
        processor = NewPriceProcessor(self.product_mock)
        new_price = processor.process_price(101)
        self.assertEqual(new_price, 101)

    def test_process_price_unknown_rule(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.min_price = 10
        self.product_mock.strategy.min_price_rule = "_unknown_rule"

        with self.assertRaises(SkipProductRepricing):
            processor.process_price(5)

    def test_process_price_invalid_default_price(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.min_price = 70
        self.product_mock.strategy.min_price_rule = "default_price"

        with self.assertRaises(SkipProductRepricing):
            processor.process_price(60)

    def test_process_price_negative_default_price(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.default_price = -50
        self.product_mock.min_price = 70
        self.product_mock.strategy.min_price_rule = "default_price"

        with self.assertRaises(SkipProductRepricing):
            processor.process_price(60)

    def test_process_price_within_min_max_range(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.min_price = 50
        self.product_mock.max_price = 100
        self.product_mock.strategy.min_price_rule = "jump_to_min"
        self.product_mock.strategy.max_price_rule = "jump_to_max"

        new_price = processor.process_price(75)

        self.assertEqual(new_price, 75)

    def test_process_price_below_min_with_negative_price(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.min_price = -10
        self.product_mock.strategy.min_price_rule = "jump_to_min"

        with self.assertRaises(SkipProductRepricing):
            processor.process_price(-10)

    def test_process_price_above_max_with_no_min_price(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.max_price = 1000
        self.product_mock.strategy.max_price_rule = "jump_to_min"

        with self.assertRaises(SkipProductRepricing):
            processor.process_price(1500)

    def test_process_match_competitor_with_no_competitor_price(self):
        processor = NewPriceProcessor(self.product_mock)
        self.product_mock.max_price = 1000
        self.product_mock.strategy.max_price_rule = "match_competitor"

        with self.assertRaises(SkipProductRepricing):
            processor.process_price(1001)


if __name__ == "__main__":
    unittest.main()
