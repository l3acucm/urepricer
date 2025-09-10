import sys, os, json, unittest, redis

project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from test_data import *
from constants import *
from models.models import Account
from helpers.data_to_redis import SetData
from helpers.redis_cache import RedisCache
from exceptions import SkipProductRepricing
from helpers.preprocess import MessageProcessor
from services.apply_strategy_service import ApplyStrategyService
from helpers.utils import CustomJSON, check_missing_values_in_message

redis_client = RedisCache()


class Fixture(unittest.TestCase):
    pass


class TestStrategies(unittest.TestCase):
    def setUp(self):
        self.fixture = self._Fixture()

    def test_amazon_price_update(self):
        """
        This test case is designed to update the price of the product
        """
        self.fixture.given_an_event(SPP_API)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(29.5)
        self.fixture.then_standard_product_updated_price_should_be(22)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_amazon_price_update(self):
        """
        This test case is designed to update the price of the product
        """
        self.fixture.given_an_event(B2B_SPP_API)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(15.47)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_positive_min_rule_applied(self):
        """
        This test case(01) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------
        the expected value for the competitor is : 22.97
        the expected value for the product is: 22.00

        """
        self.fixture.given_an_event(Compete_With_Lowest_Price_Jump_to_Min_positive_T01)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(29.7)
        self.fixture.then_standard_product_updated_price_should_be(22)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_negative_min_rule_applied(self):
        """
        This test case(02) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 31

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Min_negative_rule_applied_T02)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(31)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_default_value_min_rule_applied(self):
        """
        This test case(03) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : 0
        ---------------------

      the expected value for the competitor is : 15.71
      the expected value for the product is: 16

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Min_default_value_rule_applied_T03)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.71)
        self.fixture.then_standard_product_updated_price_should_be(16)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_default_value_min_rule_applied_min_not_exist(self):
        """
        This test case(04) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : 0
        ---------------------

      the expected value for the competitor is : 20.91
      the expected value for the product is: 20.81

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Min_default_value_rule_applied_min_price_not_exist_T04)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.81)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_value_default_value_min_rule_applied(self):
        """
        This test case(05) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
     
        ---------------------

        the expected value for the competitor is : 29
        the expected value for the product is: 31

        """
        self.fixture.given_an_event(Lowest_Price_rule_default_value_beat_by_default_value_rule_applied_min_price_T05)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(29)
        self.fixture.then_standard_product_updated_price_should_be(31)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_max_positive_min_rule_applied(self):
        """
        This test case(06) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 50

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Max_positive_rule_applied_T06)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(50)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_max_negative_min_rule_applied(self):
        """
        This test case(07) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 12
        the expected value for the product is: 15

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Max_negative_rule_applied_T07)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(12)
        self.fixture.then_standard_product_updated_price_should_be(15)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_max_default_value_min_rule_applied(self):
        """
        This test case(08) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : 0
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 25

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Max_default_value_rule_applied_T08)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(25)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_max_default_value_rule_applied_max_price_not_exist(self):
        """
        This test case(09) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : 0
        ---------------------

        the expected exception value should be: Rule is set to jump_to_max, but max price is missing...

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Max_default_value_rule_applied_max_price_not_exist_T09)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to jump_to_max, but max price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_match_competitor_positive_min_rule_applied(self):
        """
        This test case(10) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.76

        """
        self.fixture.given_an_event(Lowest_Price_match_competitor_positive_rule_applied_T10)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_match_competitor_negative_min_rule_applied(self):
        """
        This test case(11) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 7
        the expected value for the product is: 7

        """
        self.fixture.given_an_event(Lowest_Price_match_competitor_negative_rule_applied_T11)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(7)
        self.fixture.then_standard_product_updated_price_should_be(7)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_match_competitor_default_value_min_rule_applied(self):
        """
        This test case(12) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : 0
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 20.91

        """
        self.fixture.given_an_event(Lowest_Price_match_competitor_default_value_rule_applied_T12)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.91)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_match_competitor_default_value_min_rule_applied_competitor_not_exist(self):
        """
        This test case(13) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : 0
        ---------------------

        the expected value for the competitor is : None
        the expected value for the product is: 35

        """
        self.fixture.given_an_event(Lowest_Price_match_competitor_default_value_competitor_not_exist_rule_applied_T13)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(None)
        self.fixture.then_standard_product_updated_price_should_be(35)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_positive_min_rule_applied(self):
        """
        This test case(14) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 45

        """
        self.fixture.given_an_event(Lowest_Price_default_price_positive_rule_applied_T14)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(45)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_negative_min_rule_applied(self):
        """
        This test case(15) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 45

        """
        self.fixture.given_an_event(Lowest_Price_default_price_negative_rule_applied_T15)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(45)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_default_min_rule_applied(self):
        """
        This test case(16) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DEFAULT_PRICE

        ---------------------

        
        the expected value for the competitor is : 20.91
        the expected value for the product is: 46

        """
        self.fixture.given_an_event(Lowest_Price_default_price_default_rule_applied_T16)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(46)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_default_rule_applied_default_value_not_exist(self):
        """
        This test case(17) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

         the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(Lowest_Price_default_price_default_rule_applied_default_value_not_exist_T17)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_default_rule_applied_default_value_negative(self):
        """
        This test case(18) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------


                 the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(Lowest_Price_default_price_default_rule_applied_default_value_negative_T18)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_do_nothing_default_min_rule_applied(self):
        """
        This test case(19) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DO_NOTHING
        BEAT_BY : (+)
        ---------------------

        the expected exception value should be: Rule is set to do_nothing, therefore, skipping repricing...

        """
        self.fixture.given_an_event(Lowest_Price_do_nothing_default_rule_applied_T19)
        self.fixture.given_a_payload()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to do_nothing, therefore, skipping repricing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_default_rule_not_applied(self):
        """
        This test case(20) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE

        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 20.91

        """
        self.fixture.given_an_event(Lowest_Price_default_value_default_value_rule_not_appied_T20)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.91)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_positive_max_rule_applied(self):
        """
        This test case(21) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 10

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Min_positive_rule_applied_max_T21)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(10)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_negative_max_rule_applied(self):
        """
        This test case(22) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 10

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Min_negative_rule_applied_max_T22)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(10)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_default_value_max_rule_applied(self):
        """
        This test case(23) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : 0
        ---------------------

        the expected value for the competitor is : 21
        the expected value for the product is: 10

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Min_default_value_rule_applied_max_T23)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(21)
        self.fixture.then_standard_product_updated_price_should_be(10)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_default_value_max_rule_applied_min_price_not_exist(self):
        """
        This test case(24) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : 0
        ---------------------

        the expected exception value should be: Rule is set to jump_to_min, but min price is missing...

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Min_default_value_rule_applied_Max_min_price_not_exist_T24)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to jump_to_min, but min price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_value_default_value_rule_applied_max_price(self):
        """
        This test case(25) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE

        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 19

        """
        self.fixture.given_an_event(Lowest_Price_default_value_default_value_rule_applied_max_T25)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(19)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_max_positive_max_rule_applied(self):
        """
        This test case(26) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 15

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Max_positive_rule_applied_Max_T26)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(15)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_max_negative_max_rule_applied(self):
        """
        This test case(27) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 19

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Max_negative_rule_applied_Max_T27)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(16)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_max_default_value_rule_not_applied(self):
        """
        This test case(28) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : 0
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 19

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Max_default_rule_not_applied_T28)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(25.91)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_max_default_value_max_rule_applied_price_not_exist(self):
        """
        This test case(29) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 20.91

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Max_default_rule_applied_Max_T29)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.91)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_match_competitor_positive_max_rule_applied(self):
        """
        This test case(30) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 20.91

        """
        self.fixture.given_an_event(Lowest_Price_match_competitor_positive_rule_applied_Max_T30)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.91)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_match_competitor_negative_max_rule_applied(self):
        """
        This test case(31) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 20.91

        """
        self.fixture.given_an_event(Lowest_Price_match_competitor_negative_rule_applied_Max_T31)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.91)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_match_competitor_default_max_rule_applied(self):
        """
        This test case(32) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 20.91

        """
        self.fixture.given_an_event(Lowest_Price_match_competitor_default_rule_applied_Max_T32)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.91)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_match_competitor_default_rule_not_applied(self):
        """
        This test case(33) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : 0
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 20.91

        """
        self.fixture.given_an_event(Lowest_Price_match_competitor_default_rule_not_applied_T33)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.91)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_positive_max_rule_applied(self):
        """
        This test case(34) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 12

        """
        self.fixture.given_an_event(Lowest_Price_default_price_positive_rule_applied_Max_T34)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(12)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_negative_max_rule_applied(self):
        """
        This test case(35) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 20.91
        the expected value for the product is: 15

        """
        self.fixture.given_an_event(Lowest_Price_default_price_negative_rule_applied_Max_T35)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(15)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_default_value_max_rule_applied(self):
        """
        This test case(36) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DEFAULT_PRICE
 
        ---------------------
        the expected value for the competitor is : 20.91
        the expected value for the product is: 20.91

        """
        self.fixture.given_an_event(Lowest_Price_default_price_default_rule_not_applied_Max_T36)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.91)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_default_value_max_rule_applied_default_not_exist(self):
        """
        This test case(37) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DEFAULT_PRICE
  
        ---------------------

        the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(Lowest_Price_default_price_default_rule_applied_Max_T37)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_price_default_value_max_rule_applied_default_is_negative(self):
        """
        This test case(38) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : 0
        ---------------------

        the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(Lowest_Price_default_price_default_rule_applied_Max_default_negative_T38)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_do_nothing_default_value_max_rule_applied(self):
        """
        This test case(39) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : DO_NOTHING

        ---------------------

        the expected exception value should be: Rule is set to do_nothing, therefore, skipping repricing...

        """
        self.fixture.given_an_event(Lowest_Price_do_nothing_default_rule_applied_Max_T39)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to do_nothing, therefore, skipping repricing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_default_value_default_value_competitor_not_found_max_rule(self):
        """
        This test case(40) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        ---------------------

        the expected exception value should be: Min price not found for...

        """
        self.fixture.given_an_event(Lowest_Price_default_price_default_rule_applied_competitor_not_found_T40)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception), f"Min price not found for ASIN: {self.fixture.payload.get('ASIN')}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_min_positive_min_rule_applied(self):
        """
        This test case(41) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15
        the expected value for the product is: 30

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_min_positive_applied_T41)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15)
        self.fixture.then_standard_product_updated_price_should_be(30)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_min_negative_min_rule_applied(self):
        """
        This test case(42) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 10
        the expected value for the product is: 15

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_min_negative_applied_T42)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(10)
        self.fixture.then_standard_product_updated_price_should_be(25)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_min_default_value_min_rule_applied(self):
        """
        This test case(43) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MIN

        ---------------------

        the expected value for the competitor is : 10
        the expected value for the product is: 22

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_min_default_applied_T43)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(9)
        self.fixture.then_standard_product_updated_price_should_be(22)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_min_default_value_min_rule_applied_min_not_exist(self):
        """
        This test case(44) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MIN

        ---------------------

        the expected value for the competitor is : 10
        the expected value for the product is: 22

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_min_default_applied_min_not_exist_T44)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_value_default_value_min_rule_applied(self):
        """
        This test case(45) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
    
        ---------------------

        the expected value for the competitor is : 10
        the expected value for the product is: 42

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_value_default_applied_default_exist_T45)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(11)
        self.fixture.then_standard_product_updated_price_should_be(42)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_max_positive_min_rule_applied(self):
        """
        This test case(46) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 15

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_max_postive_applied_T46)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(15)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_max_negative_min_rule_applied(self):
        """
        This test case(47) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 6
        the expected value for the product is: 15

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_max_negative_applied_T47)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(6)
        self.fixture.then_standard_product_updated_price_should_be(15)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_max_default_value_min_rule_not_applied(self):
        """
        This test case(48) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MAX
  
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.76

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_max_default_not_applied_T48)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_max_default_value_min_rule_applied_max_not_exist(self):
        """
        This test case(49) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MAX
        ---------------------

        the expected exception value should be: Rule is set to jump_to_max, but max price is missing...

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_max_default_value_max_not_exist_T49)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to jump_to_max, but max price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_match_competitor_default_value_min_rule_applied(self):
        """
        This test case(50) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.76

        """
        self.fixture.given_an_event(Lowest_FBA_Price_match_competitor_positive_applied_T50)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_match_competitor_default_value_new_and_old_same(self):
        """
        This test case(51) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        
        the expected exception value should be: New price and old price are same, therefore, skipping repricing...

        """
        self.fixture.given_an_event(Lowest_FBA_Price_match_competitor_negative_applied_T51)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"New price and old price are same, therefore, skipping repricing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_match_competitor_default_value_min_rule_not_applied(self):
        """
        This test case(52) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.66

        """
        self.fixture.given_an_event(Lowest_FBA_Price_match_competitor_default_not_applied_T52)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.66)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_match_competitor_default_value_min_rule_applied_match(self):
        """
        This test case(53) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.76

        """
        self.fixture.given_an_event(Lowest_FBA_Price_match_competitor_default_applied_T53)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_price_positive_min_rule_applied(self):
        """
        This test case(54) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 50

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_positive_applied_T54)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(50)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_price_negative_min_rule_applied(self):
        """
        This test case(55) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 45

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_negative_applied_T55)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(45)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_price_default_value_min_rule_applied(self):
        """
          This test case(56) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 50

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_default_applied_T56)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(50)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_price_default_value_min_rule_applied_default_not_exist(self):
        """
        This test case(57) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_default_applied_not_exist_T57)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_price_default_value_min_rule_applied_default_is_negative(self):
        """
        This test case(58) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_default_applied_exist_but_negative_T58)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_do_nothing_default_value_min_rule_applied(self):
        """
        This test case(59) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DO_NOTHING
     
        ---------------------

        the expected exception value should be: Rule is set to do_nothing, therefore, skipping repricing...

        """
        self.fixture.given_an_event(Lowest_FBA_Price_do_nothing_default_applied_T59)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to do_nothing, therefore, skipping repricing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default__default_value_min_rule_applied(self):
        """
        This test case(60) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
    
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 50

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_default_applied_T60)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(50)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_min_positive_max_rule_applied(self):
        """
        This test case(61) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15
        the expected value for the product is: 10

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_min_positive_applied_MAX_T61)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15)
        self.fixture.then_standard_product_updated_price_should_be(10)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_min_negative_max_rule_applied(self):
        """
        This test case(62) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 10
        the expected value for the product is: 12

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_min_negative_applied_Max_T62)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(10)
        self.fixture.then_standard_product_updated_price_should_be(12)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_min_default_value_max_rule_applied(self):
        """
        This test case(63) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : 0
        ---------------------

        the expected value for the competitor is : 7
        the expected value for the product is: 7

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_min_default_applied_Max_T63)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(7)
        self.fixture.then_standard_product_updated_price_should_be(7)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_min_default_value_max_rule_applied_min_not_exist(self):
        """
        This test case(64) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : 0
        ---------------------

        the expected exception value should be: Rule is set to jump_to_min, but min price is missing...

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_min_default_applied_Max_min_not_exist_T64)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to jump_to_min, but min price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_value_default_value_max_rule_applied(self):
        """
        This test case(65) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
 
        ---------------------

        the expected value for the competitor is : 11
        the expected value for the product is: 7

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_value_default_applied_default_exist_T65)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(11)
        self.fixture.then_standard_product_updated_price_should_be(7)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_max_positive_max_rule_applied(self):
        """
        This test case(66) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 15

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_max_postive_applied_Max_T66)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(15)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_max_negative_max_rule_applied(self):
        """
        This test case(67) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 6
        the expected value for the product is: 15

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_max_negative_applied_Max_T67)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(6)
        self.fixture.then_standard_product_updated_price_should_be(15)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_max_default_value_max_rule_applied(self):
        """
        This test case(68) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : 0
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.76

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_max_default_not_applied_Max_T68)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_jump_to_max_default_value_max_rule_applied_max_not_exist(self):
        """
        This test case(69) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : JUMP_TO_MAX
     
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 30.71

        """
        self.fixture.given_an_event(Lowest_FBA_Price_jump_to_max_default_value_max_not_exist_T69)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_match_competitor_positive_max_rule_applied(self):
        """
        This test case(70) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.76

        """
        self.fixture.given_an_event(Lowest_FBA_Price_match_competitor_positive_applied_T70)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_match_competitor_negative_max_rule_applied(self):
        """
        This test case(71) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.76

        """
        self.fixture.given_an_event(Lowest_FBA_Price_match_competitor_negative_applied_T71)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_match_competitor_default_max_not_rule_applied(self):
        """
        This test case(72) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.76

        """
        self.fixture.given_an_event(Lowest_FBA_Price_match_competitor_default_not_applied_T72)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_match_competitor_default_max_rule_applied(self):
        """
        This test case(73) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.76

        """
        self.fixture.given_an_event(Lowest_FBA_Price_match_competitor_default_applied_Max_T73)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_price_positive_max_rule_applied(self):
        """
        This test case(74) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 20

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_positive_applied_T74)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(20)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_price_negative_max_rule_applied(self):
        """
        This test case(75) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 17

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_negative_applied_T75)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(17)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_price_default_max_rule_applied(self):
        """
        This test case(76) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 30.76

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_default_applied_T76)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(30.76)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_price_default_max_rule_applied_default_not_exist(self):
        """
        This test case(77) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_default_applied_not_exist_T77)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_price_default_max_rule_applied_default_is_negative(self):
        """
        This test case(78) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_default_applied_exist_but_negative_T58)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_do_nothing_default_max_rule_applied(self):
        """
        This test case(79) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        COMPETE RULE : DO_NOTHING
        BEAT_BY : (+)
        ---------------------

        the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_price_default_applied_exist_but_negative_T78)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_fba_price_default_value_default_max_rule_applied(self):
        """
        This test case(80) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
   
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 50

        """
        self.fixture.given_an_event(Lowest_FBA_Price_default_default_applied_T60)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(50)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_min_positive_min_rule_applied(self):
        """
        This test case(81) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.76
        the expected value for the product is: 40

        """

        self.fixture.given_an_event(Match_Buybox_Jump_To_min_positive_applied_T81)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.76)
        self.fixture.then_standard_product_updated_price_should_be(40)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_min_negative_min_rule_applied(self):
        """
        This test case(82) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        -------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 45

        """

        self.fixture.given_an_event(Match_Buybox_Jump_To_min_negative_applied_T82)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(35)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_min_default_value_min_rule_applied(self):
        """
        This test case(83) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MIN
  
        ---------------------

        the expected value for the competitor is : 8
        the expected value for the product is: 40

        """

        self.fixture.given_an_event(Match_Buybox_Jump_To_min_default_applied_T83)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(8)
        self.fixture.then_standard_product_updated_price_should_be(40)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_min_default_value_min_rule_applied_min_not_exist(self):
        """
        This test case(84) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MIN

        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 30.71

        """

        self.fixture.given_an_event(Match_Buybox_Jump_To_min_default_applied_min_not_exist_T84)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_value_default_value_min_rule_applied_(self):
        """
        This test case(85) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MIN
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 40

        """

        self.fixture.given_an_event(Match_Buybox_default_value_default_applied_T85)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(40)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_max_positive_min_rule_applied(self):
        """
        This test case(86) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 18
        the expected value for the product is: 50

        """

        self.fixture.given_an_event(Match_Buybox_Jump_To_min_positive_applied_T86)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(18)
        self.fixture.then_standard_product_updated_price_should_be(50)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_max_negative_min_rule_applied(self):
        """
        This test case(87) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 32

        """

        self.fixture.given_an_event(Match_Buybox_Jump_To_min_negative_applied_T87)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(32)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_max_default_min_rule_applied(self):
        """
        This test case(88) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MAX
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 39

        """

        self.fixture.given_an_event(Match_Buybox_Jump_To_min_default_applied_T88)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(39)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_max_default_min_rule_applied_max_not_exist(self):
        """
        This test case(89) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MAX

        ---------------------

        """

        self.fixture.given_an_event(Match_Buybox_Jump_To_min_default_applied_Max_not_exist_T89)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to jump_to_max, but max price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_match_competitor_positive_min_rule_applied(self):
        """
        This test case(90) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 30.71

        """

        self.fixture.given_an_event(Match_Buybox_Match_competitior_positive_T90)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_match_competitor_negative_min_rule_applied(self):
        """
        This test case(91) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 30.71

        """

        self.fixture.given_an_event(Match_Buybox_Match_competitior_negative_T91)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_match_competitor_default_min_rule_applied(self):
        """
        This test case(92) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : MATCH_COMPETITOR

        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 30.71

        """

        self.fixture.given_an_event(Match_Buybox_Match_competitior_default_T92)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.72)
        self.fixture.then_standard_product_updated_price_should_be(30.72)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_match_competitor_default_min_rule_applie_competitor_not_exist(self):
        """
        This test case(93) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : MATCH_COMPETITOR

        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 30.71

        """

        self.fixture.given_an_event(Match_Buybox_Match_competitior_default_competitor_not_exist_T93)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Buybox is suppressed. Not competitor found for ASIN: {self.fixture.payload.get('ASIN')}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_price_positive_min_rule_applied(self):
        """
        This test case(94) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 44

        """

        self.fixture.given_an_event(Match_BuyBox_default_price_positive_T94)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(44)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_price_negative_min_rule_applied(self):
        """
        This test case(95) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 45

        """

        self.fixture.given_an_event(Match_BuyBox_default_price_negative_T95)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(45)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_price_default_min_rule_applied(self):
        """
        This test case(96) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : DEFAULT_PRICE



        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 46

        """

        self.fixture.given_an_event(Match_BuyBox_default_price_default_T96)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(46)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_price_default_min_rule_applied_default_not_exist(self):
        """
        This test case(97) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : DEFAULT_PRICE
        ---------------------

        
        the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """

        self.fixture.given_an_event(Match_BuyBox_default_price_default_default_not_exist_T97)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_price_default_min_rule_applied_default_is_negative(self):
        """
        This test case(98) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : DEFAULT_PRICE
        ---------------------

        the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """

        self.fixture.given_an_event(Match_BuyBox_default_price_default_default_negative_T98)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_do_nothing_default_min_rule_applied(self):
        """
        This test case(99) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : DEFAULT_PRICE



        ---------------------

        the expected exception value should be: Rule is set to do_nothing, therefore, skipping repricing...

        """
        self.fixture.given_an_event(Match_BuyBox_do_nothing_default_T99)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to do_nothing, therefore, skipping repricing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_value_default_value_min_rule_applied_cmp_not_found(self):
        """
            This test case(100) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : MATCH_BUYBOX




            ---------------------

            the exception value should be raised
        """
        self.fixture.given_an_event(match_buybox_default_value_default_value_min_rule_applied_cmp_not_found_T100)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_min_positive_max_rule_applied(self):
        """
          This test case(101) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX
          COMPETE RULE : JUMP_TO_MIN
          BEAT By : (+)


          ---------------------

          the expected value for the competitor is : 30.71
          the expected value for the product is: 50

        """
        self.fixture.given_an_event(match_buybox_jump_to_min_positive_max_rule_applied_T101)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(50)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_min_negative_max_rule_applied(self):
        """
          This test case(102) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX
          COMPETE RULE : JUMP_TO_MIN
          BEAT By : (-)


          ---------------------

          the expected value for the competitor is : 30.71
          the expected value for the product is: 20

        """
        self.fixture.given_an_event(match_buybox_jump_to_min_negative_max_rule_applied_T102)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(20)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_min_defaut_value_max_rule_applied(self):
        """
          This test case(103) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX
          COMPETE RULE : JUMP_TO_MIN



          ---------------------

          the expected value for the competitor is : 30.71
          the expected value for the product is: 20

        """
        self.fixture.given_an_event(match_buybox_jump_to_min_defaut_value_max_rule_applied_T103)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(20)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_min_defaut_value_max_rule_applied_min_not_exist(self):
        """
          This test case(104) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX
          COMPETE RULE : JUMP_TO_MIN



          the expected exception value should be: Rule is set to jump_to_min, but min price is missing...
          ---------------------



        """
        self.fixture.given_an_event(match_buybox_jump_to_min_defaut_value_max_rule_applied_min_not_exist_T104)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to jump_to_min, but min price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_value_defaut_value_max_rule_applied_(self):
        """
          This test case(105) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX



          ---------------------

          the expected value for the competitor is : 30.71
          the expected value for the product is: 30

        """
        self.fixture.given_an_event(match_buybox_default_value_defaut_value_max_rule_applied_T105)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_max_positive_max_rule_applied(self):
        """
          This test case(106) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX
          COMPETE RULE : JUMP_TO_MAX
          BEAT By : (+)


          ---------------------

          the expected value for the competitor is : 30.71
          the expected value for the product is: 25

        """
        self.fixture.given_an_event(match_buybox_jump_to_max_positive_max_rule_applied_T106)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(25)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_max_negative_max_rule_applied(self):
        """
          This test case(107) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX
          COMPETE RULE : JUMP_TO_MAX
          BEAT By : (-)
          ---------------------

          the expected value for the competitor is : 30.71
          the expected value for the product is: 30

        """
        self.fixture.given_an_event(match_buybox_jump_to_max_negative_max_rule_applied_107)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_max_default_max_rule_applied(self):
        """
          This test case(108) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX
          COMPETE RULE : JUMP_TO_MAX
          ---------------------

          the expected value for the competitor is : 30.71
          the expected value for the product is: 30

        """
        self.fixture.given_an_event(match_buybox_jump_to_max_default_max_rule_applied_T108)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(29)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_jump_to_max_default_max_rule_applied_max_not_exist(self):
        """
          This test case(109) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX
          COMPETE RULE : JUMP_TO_MAX

          ---------------------

          the expected value for the competitor is : 30.71
          the expected value for the product is: 30.71

        """
        self.fixture.given_an_event(match_buybox_jump_to_max_default_max_rule_applied_max_not_exist_T109)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_match_competitor_positive_max_rule_applied(self):
        """
            This test case(110) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : MATCH_BUYBOX
            COMPETE RULE : MATCH_COMPETITOR
            BEAT By : (+)
            ---------------------

            the expected value for the competitor is : 30.71
            the expected value for the product is: 30.71

          """
        self.fixture.given_an_event(match_buybox_match_competitor_positive_max_rule_applied_T110)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_match_competitor_negative_max_rule_applied(self):
        """
          This test case(111) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX
          COMPETE RULE : MATCH_COMPETITOR
          BEAT By : (-)
          ---------------------

          the expected value for the competitor is : 30.71
          the expected value for the product is: 30.71

      """
        self.fixture.given_an_event(match_buybox_match_competitor_negative_max_rule_applied_T111)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_match_competitor_default_value_max_rule_applied(self):
        """
          This test case(111) is designed to update the price of the product for

          TEST VALUES
          -------------------
          COMPETE WITH : MATCH_BUYBOX
          COMPETE RULE : MATCH_COMPETITOR
          ---------------------

          the expected value for the competitor is : 30.71
          the expected value for the product is: 30.71

      """
        self.fixture.given_an_event(match_buybox_match_competitor_default_value_max_rule_applied_T112)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    # def test_T113(self):
    #   """
    #   This test case is designed for payload T113
    #   """
    #   self.fixture.given_an_event(T113)
    #   self.fixture.given_a_payload()
    #   self.fixture.given_platform_from_event()
    #   with self.assertRaises(SkipProductRepricing) as context:
    #     self.fixture.when_strategy_applied()

    def test_match_buybox_default_price_positive_max_rule_applied(self):
        """
            This test case(114) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : MATCH_BUYBOX
            COMPETE RULE : DEFAULT_PRICE
            BEAT By : (+)
            ---------------------

            the expected value for the competitor is : 30.71
            the expected value for the product is: 21

        """
        self.fixture.given_an_event(match_buybox_default_price_positive_max_rule_applied_T114)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(21)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_price_negative_max_rule_applied(self):
        """
            This test case(115) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : MATCH_BUYBOX
            COMPETE RULE : DEFAULT_PRICE
            BEAT By : (-)
            ---------------------

            the expected value for the competitor is : 30.71
            the expected value for the product is: 21

        """
        self.fixture.given_an_event(match_buybox_default_price_negative_max_rule_applied_T115)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(21)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_price_default_value_max_rule_applied(self):
        """
            This test case(116) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : MATCH_BUYBOX
            COMPETE RULE : DEFAULT_PRICE

            ---------------------

            the expected value for the competitor is : 30.71
            the expected value for the product is: 21

        """
        self.fixture.given_an_event(match_buybox_default_price_default_value_max_rule_applied_T116)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(21)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_price_default_value_max_rule_applied_default_not_exist(self):
        """
            This test case(117) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : MATCH_BUYBOX
            COMPETE RULE : DEFAULT_PRICE
            ---------------------

            the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(match_buybox_default_price_default_value_max_rule_applied_default_not_exist_T117)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_default_price_default_value_max_rule_applied_default_is_negative(self):
        """
            This test case(117) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : MATCH_BUYBOX
            COMPETE RULE : DEFAULT_PRICE
            ---------------------

            the expected exception value should be: Rule is set to default_price, but default_price is missing...

        """
        self.fixture.given_an_event(match_buybox_default_price_default_value_max_rule_applied_default_negative_T118)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to default_price, but default_price is missing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_match_buybox_do_nothing_default_value_max_rule_applied_(self):
        """
            This test case(119) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : MATCH_BUYBOX
            COMPETE RULE : DO_NOTHING
            ---------------------

            the expected exception value should be: Rule is set to do_nothing, therefore, skipping repricing...

        """
        self.fixture.given_an_event(match_buybox_do_nothing_default_value_max_rule_applied_T119)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Rule is set to do_nothing, therefore, skipping repricing for ASIN: {self.fixture.product.asin}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_positive_min_rule_not_applied(self):
        """
            This test case(122) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : LOWEST PRICE
            COMPETE RULE : JUMP TO MIN
            BEAT BY : (+)

            Rule not applied
            ---------------------

            the expected value for the competitor is : 20.91
            the expected value for the product is: 21.11

        """
        self.fixture.given_an_event(lowest_price_jump_to_min_positive_min_rule_not_applied_T122)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(21.11)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_negative_min_rule_not_applied(self):
        """
            This test case(123) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : LOWEST PRICE
            COMPETE RULE : JUMP TO MIN
            BEAT BY : (-)

            Rule not applied
            ---------------------

            the expected value for the competitor is : 20.91
            the expected value for the product is: 21.71

        """
        self.fixture.given_an_event(lowest_price_jump_to_min_negative_min_rule_not_applied_T123)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_default_min_rule_not_applied(self):
        """
            This test case(124) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : LOWEST PRICE
            COMPETE RULE : JUMP TO MIN


            Rule not applied
            ---------------------

            the expected value for the competitor is : 20.91
            the expected value for the product is: 21.91

        """
        self.fixture.given_an_event(lowest_price_jump_to_min_default_min_rule_not_applied_T124)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(20.91)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_all_default_values_rule_not_applied(self):
        """
            This test case(125) is designed to update the price of the product for

            TEST VALUES
            -------------------


            Rule not applied
            ---------------------

            the expected value for the competitor is : 30.71
            the expected value for the product is: 30.71

        """
        self.fixture.given_an_event(all_default_values_rule_not_applied_T125)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_all_default_values_rule_applied(self):
        """
            This test case(126) is designed to update the price of the product for

            TEST VALUES
            -------------------


            Rule applied
            ---------------------

            the expected value for the competitor is : 30.71
            the expected value for the product is: 30.71

        """
        self.fixture.given_an_event(all_default_values_rule_applied_T126)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_default_min_rule_applied_chose_next_cmp(self):
        """
            This test case(127) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : LOWEST PRICE
            COMPETE RULE : JUMP TO MIN



            ---------------------

            the expected value for the competitor is : 30.71
            the expected value for the product is: 30.71

        """
        self.fixture.given_an_event(lowest_price_jump_to_min_default_min_rule_applied_chose_next_cmp_T127)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(30.71)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_min_default_min_rule_applied_not_at_min(self):
        """
            This test case(128) is designed to update the price of the product for

            TEST VALUES
            -------------------
            COMPETE WITH : LOWEST PRICE
            COMPETE RULE : JUMP TO MIN



            ---------------------

            the expected value for the competitor is : 20.91
            the expected value for the product is: 21

        """
        self.fixture.given_an_event(lowest_price_jump_to_min_default_min_rule_applied_not_at_min_T128)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.91)
        self.fixture.then_standard_product_updated_price_should_be(21)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_item_condition_match_club(self):
        """
        This test case(129) is designed to update the price of the product for

        TEST VALUES
        -------------------
        ITEM_CONDITION: club
        --------------------- 
        the expected value for the competitor is : 12
        the expected value for the product is: 39

        """

        self.fixture.given_an_event(Lowest_price_verify_item_condition_T129)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(12)
        self.fixture.then_standard_product_updated_price_should_be(39)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_only_seller_set_default_value(self):
        """
        This test case(130) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : None
        the expected value for the product is: 40

        """

        self.fixture.given_an_event(Lowest_price_verify_only_seller_default_T130)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(None)
        self.fixture.then_standard_product_updated_price_should_be(40)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_only_seller_set_mean_value(self):
        """
        This test case(131) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : None
        the expected value for the product is: 40.5

        """

        self.fixture.given_an_event(Lowest_price_verify_only_seller_mean_131)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(None)
        self.fixture.then_standard_product_updated_price_should_be(40.5)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_maximise_profit_set_competitor_price(self):
        """
        This test case(132) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : None
        the expected value for the product is: 17

        """

        self.fixture.given_an_event(Lowest_price_verify_maximise_profit_T132)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17)
        self.fixture.then_standard_product_updated_price_should_be(17)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_maximise_profit_competitor_less_then_listed(self):
        """
        This test case(133) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------
        the expected exception value should be: Competitor price(17) is less than default price 40

        """

        self.fixture.given_an_event(Lowest_price_verify_maximise_profit_T133_raise_exception)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()
        self.fixture.then_remove_asin_seller_from_redis()

    def test_buybox_suppressed_case(self):
        """
        This test case(134) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------
        the expected exception value should be: Buybox is supressed

        """

        self.fixture.given_an_event(Lowest_price_verify_buybox_supressed)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         f"Buybox is suppressed. Not competitor found for ASIN: {self.fixture.payload.get('ASIN')}...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_uk_seller_and_us_market(self):
        """
        This test case(135) is designed to update the price of the product for
        UK SELLER and US MARKETPLACE_ID

        it will raise exception here : Seller marketplace is different than the payload

        """

        self.fixture.given_an_event(uk_seller_us_market_135)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         "Skipping Repricing! (Seller (SELLER_ID: SX135 marketplace is different than the payload)")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_uk_seller_and_uk_market(self):
        """
        This test case(136) is designed to update the price of the product for
        UK SELLER and UK MARKETPLACE_ID

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 21

        """

        self.fixture.given_an_event(uk_seller_and_uk_market_136)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(21)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_us_seller_and_uk_market(self):
        """
        This test case(137) is designed to update the price of the product for
        US SELLER and UK MARKETPLACE_ID

        it will raise exception here : Seller marketplace is different than the payload

        """

        self.fixture.given_an_event(us_seller_uk_market_137)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         "Skipping Repricing! (Seller (SELLER_ID: SX137 marketplace is different than the payload)")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_us_seller_us_market(self):
        """
        This test case(138) is designed to update the price of the product for
        US SELLER and US MARKETPLACE_ID

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        COMPETE RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 30.71
        the expected value for the product is: 21

        """

        self.fixture.given_an_event(us_seller_us_market_138)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.71)
        self.fixture.then_standard_product_updated_price_should_be(21)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_pick_competitor_price_from_fulfillmentChannel_Merchant(self):
        """
        This test case (139), is designed to update the price of the product where
        competitor price should pick from there, where fulfillmentChannel is Merchant.

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------
        the expected value for the competitor is : 66.7
        the expected value for the product is : 35.0
        """
        self.fixture.given_an_sigle_api_event(pick_lowest_price_from_merchant_139)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(66.7)
        self.fixture.then_standard_product_updated_price_should_be(35.0)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_pick_competitor_price_from_compete_with_match_buybox_140(self):
        """
        This test case (140), is designed to update the price of the product where
        competitor price should pick from there Offers when compete_with is match_buybox.

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------
        the expected value for the competitor is : 66.2
        the expected value for the product is : 38.9
        """
        self.fixture.given_an_sigle_api_event(pick_competitor_price_from_compete_with_match_buybox_140)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(66.2)
        self.fixture.then_standard_product_updated_price_should_be(38.9)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_pick_competitor_price_from_compete_with_lowest_price_141(self):
        """
        This test case (141), is designed to update the price of the product where
        competitor price should pick from there Offers when compete_with is lowest_price.
        it will pick minimum listing price from offers.

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------
        the expected value for the competitor is : 35.2
        the expected value for the product is : 34.7
        """
        self.fixture.given_an_sigle_api_event(pick_competitor_price_from_compete_with_lowest_price_141)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(35.2)
        self.fixture.then_standard_product_updated_price_should_be(34.7)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_pick_competitor_price_from_compete_with_lowest_fba_price_142(self):
        """
        This test case (142), is designed to update the price of the product where
        competitor price should pick from there Offers when compete_with is lowest_fba_price.
        it will pick minimum listing price from offers.

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------
        the expected value for the competitor is : 37.4
        the expected value for the product is : 40.12
        """
        self.fixture.given_an_sigle_api_event(pick_competitor_price_from_compete_with_lowest_fba_price_142)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(37.4)
        self.fixture.then_standard_product_updated_price_should_be(40.12)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_min_positive_min_rule_applied(self):
        """
        This test case(150) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 16.12
        the expected values for the tiers are : [15.04,13.75]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_min_positive_applied_T150)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(16.12)
        self.fixture.then_b2b_product_updated_price_should_be([15.04, 13.75])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_min_negative_min_rule_applied(self):
        """
        This test case(151) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.97
        the expected value for the product is : 16.12
        the expected values for the tiers are : [14.84,13.55]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_min_negative_applied_T151)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.97)
        self.fixture.then_standard_product_updated_price_should_be(16.12)
        self.fixture.then_b2b_product_updated_price_should_be([14.84, 13.55])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_min_zero_min_rule_applied(self):
        """
        This test case(152)is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 17.25
        the expected values for the tiers are : [14.94,13.65]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_min_zero_applied_T152)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(17.25)
        self.fixture.then_b2b_product_updated_price_should_be([14.94, 13.65])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_match_competitor_positive_min_rule_applied(self):
        """
        This test case(153) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.97
        the expected value for the product is : 15.97
        the expected values for the tiers are : [15.14,13.85]

        """
        self.fixture.given_an_event(b2b_low_price_match_competitor_positive_applied_T153)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.97)
        self.fixture.then_standard_product_updated_price_should_be(15.97)
        self.fixture.then_b2b_product_updated_price_should_be([15.14, 13.85])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_match_competitor_negative_min_rule_applied(self):
        """
        This test case(154) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.98
        the expected value for the product is : 15.78
        the expected values for the tiers are : [14.74,13.45]

        """
        self.fixture.given_an_event(b2b_low_price_match_competitor_negative_applied_T154)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.98)
        self.fixture.then_standard_product_updated_price_should_be(15.98)
        self.fixture.then_b2b_product_updated_price_should_be([14.74, 13.45])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_match_competitor_zero_min_rule_applied(self):
        """
        This test case(155) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.99
        the expected value for the product is : 15.99
        the expected values for the tiers are : [14.94,13.65]

        """
        self.fixture.given_an_event(b2b_low_price_match_competitor_zero_applied_T155)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.99)
        self.fixture.then_standard_product_updated_price_should_be(15.99)
        self.fixture.then_b2b_product_updated_price_should_be([14.94, 13.65])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_jump_to_min_positive_min_rule_applied(self):
        """
        This test case(156) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.91
        the expected value for the product is : 16.11
        the expected values for the tiers are : [15.14,13.85]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_jump_to_min_positive_applied_T156)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.91)
        self.fixture.then_standard_product_updated_price_should_be(16.11)
        self.fixture.then_b2b_product_updated_price_should_be([15.14, 13.85])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_jump_to_min_negative_min_rule_applied(self):
        """
        This test case(157) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.91
        the expected value for the product is : 17.12
        the expected values for the tiers are : [14.74,13.45]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_jump_to_min_negative_applied_T157)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.91)
        self.fixture.then_standard_product_updated_price_should_be(17.12)
        self.fixture.then_b2b_product_updated_price_should_be([14.74, 13.45])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_jump_to_min_zero_min_rule_applied(self):
        """
        This test case(158) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.91
        the expected value for the product is : 16.12
        the expected values for the tiers are : [14.94,13.65]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_jump_to_min_zero_applied_T158)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.91)
        self.fixture.then_standard_product_updated_price_should_be(16.12)
        self.fixture.then_b2b_product_updated_price_should_be([14.94, 13.65])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_match_competitor_positive_min_rule_applied(self):
        """
        This test case(159) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.91
        the expected value for the product is : 16.12
        the expected values for the tiers are : [14.94,13.65]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_match_competitor_positive_applied_T159)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.66)
        self.fixture.then_standard_product_updated_price_should_be(16.96)
        self.fixture.then_b2b_product_updated_price_should_be([15.24, 13.95])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_match_competitor_negative_min_rule_applied(self):
        """
        This test case(160) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 16.66
        the expected value for the product is : 16.66
        the expected values for the tiers are : [14.64,13.35]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_match_competitor_negative_applied_T160)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.66)
        self.fixture.then_standard_product_updated_price_should_be(16.66)
        self.fixture.then_b2b_product_updated_price_should_be([14.64, 13.35])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_match_competitor_zero_min_rule_applied(self):
        """
        This test case(161) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.44
        the expected value for the product is : 15.44
        the expected values for the tiers are : [14.94,13.65]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_match_competitor_zero_applied_T161)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.44)
        self.fixture.then_standard_product_updated_price_should_be(15.44)
        self.fixture.then_b2b_product_updated_price_should_be([14.94, 13.65])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_min_positive_min_rule_applied(self):
        """
        This test case(162) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.55
        the expected value for the product is : 17.12
        the expected values for the tiers are : [12.0,15.98]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_min_positive_applied_T162)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.55)
        self.fixture.then_standard_product_updated_price_should_be(17.12)
        self.fixture.then_b2b_product_updated_price_should_be([12.0, 15.98])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_min_negative_min_rule_applied(self):
        """
        This test case(163) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 17.99
        the expected value for the product is : 21.21
        the expected values for the tiers are : [14.14,17.17]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_min_negative_applied_T163)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.99)
        self.fixture.then_standard_product_updated_price_should_be(21.21)
        self.fixture.then_b2b_product_updated_price_should_be([14.14, 17.17])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_min_zero_min_rule_applied(self):
        """
        This test case(164) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 18.89
        the expected value for the product is : 22.77
        the expected values for the tiers are : [15.9,18.32]
        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_min_zero_applied_T164)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(18.89)
        self.fixture.then_standard_product_updated_price_should_be(22.77)
        self.fixture.then_b2b_product_updated_price_should_be([15.9, 18.32])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_match_competitor_positive_min_price_applied(self):
        """
        This test case(165) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 19.21
        the expected value for the product is : 19.21
        the expected values for the tiers are : [14.71,16.72]

        """
        self.fixture.given_an_event(b2b_match_buybox_match_competitor_positive_applied_T165)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(19.21)
        self.fixture.then_standard_product_updated_price_should_be(19.21)
        self.fixture.then_b2b_product_updated_price_should_be([14.71, 16.72])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_match_competitor_negative_min_price_applied(self):
        """
        This test case(166) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 20.70
        the expected value for the product is : 20.70
        the expected values for the tiers are : [15.14,17.91]

        """
        self.fixture.given_an_event(b2b_match_buybox_match_competitor_negative_applied_T166)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.70)
        self.fixture.then_standard_product_updated_price_should_be(20.70)
        self.fixture.then_b2b_product_updated_price_should_be([15.14, 17.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_match_competitor_zero_min_price_applied(self):
        """
        This test case(167) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 21.71
        the expected value for the product is : 21.71
        the expected values for the tiers are : [16.15,18.92]

        """
        self.fixture.given_an_event(b2b_match_buybox_match_competitor_zero_applied_T167)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(21.71)
        self.fixture.then_standard_product_updated_price_should_be(21.71)
        self.fixture.then_b2b_product_updated_price_should_be([16.15, 18.92])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_max_positive_max_rule_applied(self):
        """
        This test case(168) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 42.7
        the expected value for the product is : 24
        the expected values for the tiers are : [48.0,40.0]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_max_positive_applied_T168)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(42.7)
        self.fixture.then_standard_product_updated_price_should_be(24)
        self.fixture.then_b2b_product_updated_price_should_be([48.0, 40.0])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_max_negative_max_rule_applied(self):
        """
        This test case(169) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 43.77
        the expected value for the product is : 41.99
        the expected values for the tiers are : [15.62,19.51]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_max_negative_applied_T169)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(43.77)
        self.fixture.then_standard_product_updated_price_should_be(41.99)
        self.fixture.then_b2b_product_updated_price_should_be([15.62, 19.51])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_max_zero_max_rule_applied(self):
        """
        This test case(170) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 37.84
        the expected value for the product is : 36.83
        the expected values for the tiers are : [49.00, 43.00]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_max_zero_applied_T170)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(37.84)
        self.fixture.then_standard_product_updated_price_should_be(36.83)
        self.fixture.then_b2b_product_updated_price_should_be([49.00, 43.00])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_match_competitor_positive_max_rule_applied(self):
        """
        This test case(171) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 23.46
        the expected value for the product is : 23.46
        the expected values for the tiers are : [52.12, 54.14]

        """
        self.fixture.given_an_event(b2b_low_price_match_competitor_positive_applied_T171)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(23.46)
        self.fixture.then_standard_product_updated_price_should_be(23.46)
        self.fixture.then_b2b_product_updated_price_should_be([52.12, 54.14])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_match_competitor_negative_max_rule_applied(self):
        """
        This test case(172) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 24.72
        the expected value for the product is : 24.72
        the expected values for the tiers are : [49.13, 51.11]

        """
        self.fixture.given_an_event(b2b_low_price_match_competitor_negative_applied_T172)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(24.72)
        self.fixture.then_standard_product_updated_price_should_be(24.72)
        self.fixture.then_b2b_product_updated_price_should_be([49.13, 51.11])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_match_competitor_zero_max_rule_applied(self):
        """
        This test case(173) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 26.22
        the expected value for the product is : 26.22
        the expected values for the tiers are : [51.59, 53.75]

        """
        self.fixture.given_an_event(b2b_low_price_match_competitor_negative_applied_T173)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(26.22)
        self.fixture.then_standard_product_updated_price_should_be(26.22)
        self.fixture.then_b2b_product_updated_price_should_be([51.59, 53.75])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_jump_to_max_positive_max_rule_applied(self):
        """
        This test case(174) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 26.61
        the expected value for the product is : 22
        the expected values for the tiers are : [45.0, 42.0]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_jump_to_max_positive_applied_T174)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(26.61)
        self.fixture.then_standard_product_updated_price_should_be(22)
        self.fixture.then_b2b_product_updated_price_should_be([45.0, 42.0])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_jump_to_max_negative_max_rule_applied(self):
        """
        This test case(175) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 28.72
        the expected value for the product is : 24
        the expected values for the tiers are : [47.00, 44.0]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_jump_to_max_negative_applied_T175)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(28.72)
        self.fixture.then_standard_product_updated_price_should_be(24)
        self.fixture.then_b2b_product_updated_price_should_be([47.00, 44.0])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_jump_to_max_zero_max_rule_applied(self):
        """
        This test case(176) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 30.31
        the expected value for the product is : 26.26
        the expected values for the tiers are : [49.5, 46.5]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_jump_to_max_zero_applied_T176)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.31)
        self.fixture.then_standard_product_updated_price_should_be(26.26)
        self.fixture.then_b2b_product_updated_price_should_be([49.5, 46.5])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_match_competitor_positive_max_rule_applied(self):
        """
        This test case(177) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 28.91
        the expected value for the product is : 28.91
        the expected values for the tiers are : [53.90, 48.48]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_match_competitor_positive_applied_T177)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(28.91)
        self.fixture.then_standard_product_updated_price_should_be(28.91)
        self.fixture.then_b2b_product_updated_price_should_be([53.90, 48.48])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_match_competitor_negative_max_rule_applied(self):
        """
        This test case(178) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 30.97
        the expected value for the product is : 30.97
        the expected values for the tiers are : [55.60, 50.50]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_match_competitor_negative_applied_T178)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.97)
        self.fixture.then_standard_product_updated_price_should_be(30.97)
        self.fixture.then_b2b_product_updated_price_should_be([55.60, 50.50])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_match_competitor_zero_max_rule_applied(self):
        """
        This test case(179) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 27.97
        the expected value for the product is : 27.97
        the expected values for the tiers are : [57.55, 54.91]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_match_competitor_zero_applied_T179)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(27.97)
        self.fixture.then_standard_product_updated_price_should_be(27.97)
        self.fixture.then_b2b_product_updated_price_should_be([57.55, 54.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_max_positive_max_rule_applied(self):
        """
        This test case(180) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 26.72
        the expected value for the product is : 22
        the expected values for the tiers are : [45.0, 32.51]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_max_positive_applied_T180)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(26.72)
        self.fixture.then_standard_product_updated_price_should_be(22)
        self.fixture.then_b2b_product_updated_price_should_be([45.0, 32.51])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_max_negative_max_rule_applied(self):
        """
        This test case(181) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 27.44
        the expected value for the product is : 23
        the expected values for the tiers are : [46.0, 33.51]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_max_negative_applied_T181)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(27.44)
        self.fixture.then_standard_product_updated_price_should_be(23)
        self.fixture.then_b2b_product_updated_price_should_be([46.0, 33.51])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_max_zero_max_rule_applied(self):
        """
        This test case(182) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 29.44
        the expected value for the product is : 25.44
        the expected values for the tiers are : [48.51, 35.87]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_max_zero_applied_T182)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(29.44)
        self.fixture.then_standard_product_updated_price_should_be(25.44)
        self.fixture.then_b2b_product_updated_price_should_be([48.51, 35.87])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_match_competitor_positive_max_rule_applied(self):
        """
        This test case(182) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 29.44
        the expected value for the product is : 29.44
        the expected values for the tiers are : [50.11, 39.57]

        """
        self.fixture.given_an_event(b2b_match_buybox_match_competitor_positive_applied_T183)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(29.44)
        self.fixture.then_standard_product_updated_price_should_be(29.44)
        self.fixture.then_b2b_product_updated_price_should_be([50.11, 39.57])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_match_competitor_negative_max_rule_applied(self):
        """
        This test case(184) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 30.55
        the expected value for the product is : 30.55
        the expected values for the tiers are : [51.22, 40.62]

        """
        self.fixture.given_an_event(b2b_match_buybox_match_competitor_negative_applied_T184)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(30.55)
        self.fixture.then_standard_product_updated_price_should_be(30.55)
        self.fixture.then_b2b_product_updated_price_should_be([51.22, 40.62])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_match_competitor_zero_max_rule_applied(self):
        """
        This test case(185) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 31.66
        the expected value for the product is : 31.66
        the expected values for the tiers are : [52.77, 41.75]

        """
        self.fixture.given_an_event(b2b_match_buybox_match_competitor_zero_applied_T185)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(31.66)
        self.fixture.then_standard_product_updated_price_should_be(31.66)
        self.fixture.then_b2b_product_updated_price_should_be([52.77, 41.75])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_default_price_positive_min_rule_applied(self):
        """
        This test case(186) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 20.22
        the expected values for the tiers are : [15.04,13.75]

        """
        self.fixture.given_an_event(b2b_low_price_default_price_positive_applied_T186)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(20.22)
        self.fixture.then_b2b_product_updated_price_should_be([15.04, 13.75])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_default_price_negative_min_rule_applied(self):
        """
        This test case(187) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 18.64
        the expected value for the product is : 21.32
        the expected values for the tiers are : [15.7,13.68]

        """
        self.fixture.given_an_event(b2b_low_price_default_price_negative_applied_T187)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(18.64)
        self.fixture.then_standard_product_updated_price_should_be(21.32)
        self.fixture.then_b2b_product_updated_price_should_be([15.7, 13.68])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_default_price_zero_min_rule_applied(self):
        """
        This test case(188) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 18.71
        the expected value for the product is : 20.32
        the expected values for the tiers are : [15.9,13.88]

        """
        self.fixture.given_an_event(b2b_low_price_default_price_zero_applied_T188)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(18.71)
        self.fixture.then_standard_product_updated_price_should_be(20.32)
        self.fixture.then_b2b_product_updated_price_should_be([15.9, 13.88])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_default_price_positive_min_rule_applied(self):
        """
        This test case(189) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 14.01
        the expected value for the product is : 20.73
        the expected values for the tiers are : [31.74,33.15]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_default_price_positive_applied_T189)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(14.01)
        self.fixture.then_standard_product_updated_price_should_be(20.73)
        self.fixture.then_b2b_product_updated_price_should_be([31.74, 33.15])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_default_price_negative_min_rule_applied(self):
        """
        This test case(190) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 14.01
        the expected value for the product is : 20.73
        the expected values for the tiers are : [19.4,16.41]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_default_price_negative_applied_T190)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(14.01)
        self.fixture.then_standard_product_updated_price_should_be(20.73)
        self.fixture.then_b2b_product_updated_price_should_be([19.4, 16.41])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_FBA_Price_default_price_zero_min_rule_applied(self):
        """
        This test case(191) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 14.01
        the expected value for the product is : None
        the expected values for the tiers are : [19.6,16.61]

        """
        self.fixture.given_an_event(b2b_low_FBA_Price_default_price_zero_applied_T191)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(14.01)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([19.6, 16.61])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_price_positive_min_rule_applied(self):
        """
        This test case(192) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.55
        the expected value for the product is : None
        the expected values for the tiers are : [33.92,30.93]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_price_positive_applied_T192)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.55)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([33.92, 30.93])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_price_negative_min_rule_applied(self):
        """
        This test case(193) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.55
        the expected value for the product is : 20.91
        the expected values for the tiers are : [33.92,30.93]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_price_negative_applied_T193)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.55)
        self.fixture.then_standard_product_updated_price_should_be(20.91)
        self.fixture.then_b2b_product_updated_price_should_be([33.92, 30.93])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_price_zero_min_rule_applied(self):
        """
        This test case(194) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.55
        the expected value for the product is : 18.42
        the expected values for the tiers are : [37.43,27.44]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_price_zero_applied_T194)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.55)
        self.fixture.then_standard_product_updated_price_should_be(18.42)
        self.fixture.then_b2b_product_updated_price_should_be([37.43, 27.43])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_price_do_nothing_positive_max_rule_applied(self):
        """
        This test case(195) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : None
        the expected values for the tiers are : [15.24,19.24]

        """
        self.fixture.given_an_event(b2b_lowest_price_do_nothing_positive_applied_T195)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([15.24, 19.24])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_price_do_nothing_negative_max_rule_applied(self):
        """
        This test case(196) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : None
        the expected values for the tiers are : [14.64,18.64]

        """
        self.fixture.given_an_event(b2b_lowest_price_do_nothing_negative_applied_T196)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([14.64, 18.64])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_price_do_nothing_zero_max_rule_applied(self):
        """
        This test case(197) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : None
        the expected values for the tiers are : [14.94,18.94]

        """
        self.fixture.given_an_event(b2b_lowest_price_do_nothing_zero_applied_T197)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([14.94, 18.94])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_fba_price_do_nothing_positive_max_rule_applied(self):
        """
        This test case(198) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : None
        the expected values for the tiers are : [15.24,19.24]

        """
        self.fixture.given_an_event(b2b_lowest_fba_price_do_nothing_positive_applied_T198)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([15.24, 19.24])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_fba_price_do_nothing_negative_max_rule_applied(self):
        """
        This test case(199) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : None
        the expected values for the tiers are : [14.64,18.64]

        """
        self.fixture.given_an_event(b2b_lowest_fba_price_do_nothing_negative_applied_T199)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([14.64, 18.64])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_fba_price_do_nothing_zero_max_rule_applied(self):
        """
        This test case(200) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : None
        the expected values for the tiers are : [14.94,18.94]

        """
        self.fixture.given_an_event(b2b_lowest_fba_price_do_nothing_zero_applied_T200)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([14.94, 18.94])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_competitor_do_nothing_positive_max_rule_applied(self):
        """
        This test case(201) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.55
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_match_competitor_do_nothing_positive_applied_T201)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.55)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_competitor_do_nothing_negative_max_rule_applied(self):
        """
        This test case(202) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.55
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_match_competitor_do_nothing_negative_applied_T202)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.55)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_competitor_do_nothing_zero_max_rule_applied(self):
        """
        This test case(203) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.99
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_match_competitor_do_nothing_zero_applied_T203)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.99)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_max_positive_min_rule_applied(self):
        """
        This test case(204) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 22
        the expected values for the tiers are : [15.04,13.75]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_max_positive_applied_T204)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(22)
        self.fixture.then_b2b_product_updated_price_should_be([15.04, 13.75])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_max_negative_min_rule_applied(self):
        """
        This test case(205) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 16.02
        the expected value for the product is : 23.22
        the expected values for the tiers are : [14.74,13.45]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_max_negative_applied_T205)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.02)
        self.fixture.then_standard_product_updated_price_should_be(23.22)
        self.fixture.then_b2b_product_updated_price_should_be([14.74, 13.45])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_max_zero_min_rule_applied(self):
        """
        This test case(206) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 16.02
        the expected value for the product is : 23.22
        the expected values for the tiers are : [14.94,13.65]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_max_zero_applied_T206)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.02)
        self.fixture.then_standard_product_updated_price_should_be(23.22)
        self.fixture.then_b2b_product_updated_price_should_be([14.94, 13.65])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_default_positive_min_rule_applied(self):
        """
        This test case(207) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : "DEFAULT_VALUE"
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 16.02
        the expected value for the product is : 16.32
        the expected values for the tiers are : [15.24,13.95]

        """
        self.fixture.given_an_event(b2b_low_price_default_positive_applied_T207)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.02)
        self.fixture.then_standard_product_updated_price_should_be(16.32)
        self.fixture.then_b2b_product_updated_price_should_be([15.24, 13.95])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_default_negative_min_rule_applied(self):
        """
        This test case(208) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : "DEFAULT_VALUE"
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 16.02
        the expected value for the product is : 16.14
        the expected values for the tiers are : [14.64,13.35]

        """
        self.fixture.given_an_event(b2b_low_price_default_negative_applied_T208)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.02)
        self.fixture.then_standard_product_updated_price_should_be(16.14)
        self.fixture.then_b2b_product_updated_price_should_be([14.64, 13.35])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_default_zero_min_rule_applied(self):
        """
        This test case(209) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : "DEFAULT_VALUE"
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 16.02
        the expected value for the product is : 16.14
        the expected values for the tiers are : [14.94,13.65]

        """
        self.fixture.given_an_event(b2b_low_price_default_zero_applied_T209)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.02)
        self.fixture.then_standard_product_updated_price_should_be(16.14)
        self.fixture.then_b2b_product_updated_price_should_be([14.94, 13.65])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_min_positive_max_rule_applied(self):
        """
        This test case(210) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : "JUMP_TO_MIN"
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 25.4
        the expected value for the product is : 16.14
        the expected values for the tiers are : [10.0,14.05]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_min_positive_applied_T210)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(25.4)
        self.fixture.then_standard_product_updated_price_should_be(16.14)
        self.fixture.then_b2b_product_updated_price_should_be([10.0, 14.05])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_min_negative_max_rule_applied(self):
        """
        This test case(211) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : "JUMP_TO_MIN"
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 25.4
        the expected value for the product is : 16.14
        the expected values for the tiers are : [10.0,13.25]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_min_negative_applied_T211)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(25.4)
        self.fixture.then_standard_product_updated_price_should_be(16.14)
        self.fixture.then_b2b_product_updated_price_should_be([10.0, 13.25])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_jump_to_min_zero_max_rule_applied(self):
        """
        This test case(212) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : "JUMP_TO_MIN"
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 25.4
        the expected value for the product is : 16.14
        the expected values for the tiers are : [10.0,13.65]

        """
        self.fixture.given_an_event(b2b_low_price_jump_to_min_zero_applied_T212)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(25.4)
        self.fixture.then_standard_product_updated_price_should_be(16.14)
        self.fixture.then_b2b_product_updated_price_should_be([10.0, 13.65])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_default_value_positive_max_rule_applied(self):
        """
        This test case(213) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 31.94
        the expected value for the product is : 22.22
        the expected values for the tiers are : [22.22,14.15]

        """
        self.fixture.given_an_event(b2b_low_price_default_value_positive_applied_T213)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(31.94)
        self.fixture.then_standard_product_updated_price_should_be(25.71)
        self.fixture.then_b2b_product_updated_price_should_be([50.0, 14.15])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_default_value_negative_max_rule_applied(self):
        """
        This test case(214) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 31.94
        the expected value for the product is : 25.71
        the expected values for the tiers are : [50.0,13.15]

        """
        self.fixture.given_an_event(b2b_low_price_default_value_negative_applied_T214)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(31.94)
        self.fixture.then_standard_product_updated_price_should_be(25.71)
        self.fixture.then_b2b_product_updated_price_should_be([50.0, 13.15])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_price_default_value_zero_max_rule_applied(self):
        """
        This test case(215) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 31.94
        the expected value for the product is : 25.71
        the expected values for the tiers are : [50.0,13.65]

        """
        self.fixture.given_an_event(b2b_low_price_default_value_zero_applied_T215)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(31.94)
        self.fixture.then_standard_product_updated_price_should_be(25.71)
        self.fixture.then_b2b_product_updated_price_should_be([50.0, 13.65])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_jump_to_max_positive_min_rule_applied(self):
        """
        This test case(216) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.2
        the expected value for the product is : 25.71
        the expected values for the tiers are : [50.0,45.0]

        """
        self.fixture.given_an_event(b2b_low_fba_price_jump_to_max_positive_applied_T216)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.2)
        self.fixture.then_standard_product_updated_price_should_be(25.71)
        self.fixture.then_b2b_product_updated_price_should_be([50.0, 45.0])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_jump_to_max_negative_min_rule_applied(self):
        """
        This test case(217) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.2
        the expected value for the product is : 25.71
        the expected values for the tiers are : [50.0,45.0]

        """
        self.fixture.given_an_event(b2b_low_fba_price_jump_to_max_negative_applied_T217)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.2)
        self.fixture.then_standard_product_updated_price_should_be(25.71)
        self.fixture.then_b2b_product_updated_price_should_be([50.0, 45.0])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_jump_to_max_zero_min_rule_applied(self):
        """
        This test case(218) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 16.1
        the expected value for the product is : 25.71
        the expected values for the tiers are : [44.9,41.8]

        """
        self.fixture.given_an_event(b2b_low_fba_price_jump_to_max_zero_applied_T218)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.1)
        self.fixture.then_standard_product_updated_price_should_be(25.71)
        self.fixture.then_b2b_product_updated_price_should_be([44.9, 41.8])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_default_positive_min_rule_applied(self):
        """
        This test case(219) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 16.1
        the expected value for the product is : 16.6
        the expected values for the tiers are : [21.33,16.66]

        """
        self.fixture.given_an_event(b2b_low_fba_price_default_positive_applied_T219)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.1)
        self.fixture.then_standard_product_updated_price_should_be(16.6)
        self.fixture.then_b2b_product_updated_price_should_be([21.33, 16.66])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_default_negative_min_rule_applied(self):
        """
        This test case(220) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 16.1
        the expected value for the product is : 16.14
        the expected values for the tiers are : [21.33,16.66]

        """
        self.fixture.given_an_event(b2b_low_fba_price_default_negative_applied_T220)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.1)
        self.fixture.then_standard_product_updated_price_should_be(16.14)
        self.fixture.then_b2b_product_updated_price_should_be([21.33, 16.66])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_default_zero_min_rule_applied(self):
        """
        This test case(221) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 16.1
        the expected value for the product is : 16.14
        the expected values for the tiers are : [21.33,16.66]

        """
        self.fixture.given_an_event(b2b_low_fba_price_default_zero_applied_T221)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.1)
        self.fixture.then_standard_product_updated_price_should_be(16.14)
        self.fixture.then_b2b_product_updated_price_should_be([21.33, 16.66])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_jump_to_min_positive_max_rule_applied(self):
        """
        This test case(222) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 16.1
        the expected value for the product is : 16.6
        the expected values for the tiers are : [21.33,16.66]

        """
        self.fixture.given_an_event(b2b_low_fba_price_jump_to_min_positive_applied_T222)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.1)
        self.fixture.then_standard_product_updated_price_should_be(16.6)
        self.fixture.then_b2b_product_updated_price_should_be([21.33, 16.66])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_jump_to_min_negative_max_rule_applied(self):
        """
        This test case(223) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 17.3
        the expected value for the product is : 16.8
        the expected values for the tiers are : [21.33,17.15]

        """
        self.fixture.given_an_event(b2b_low_fba_price_jump_to_min_negative_applied_T223)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.3)
        self.fixture.then_standard_product_updated_price_should_be(16.8)
        self.fixture.then_b2b_product_updated_price_should_be([21.33, 17.15])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_jump_to_min_zero_max_rule_applied(self):
        """
        This test case(224) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 17.3
        the expected value for the product is : 17.3
        the expected values for the tiers are : [21.4,17.65]

        """
        self.fixture.given_an_event(b2b_low_fba_price_jump_to_min_zero_applied_T224)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.3)
        self.fixture.then_standard_product_updated_price_should_be(17.3)
        self.fixture.then_b2b_product_updated_price_should_be([21.4, 17.65])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_jump_to_max_positive_max_rule_applied(self):
        """
        This test case(225) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 17.3
        the expected value for the product is : 17.8
        the expected values for the tiers are : [44.9,41.8]

        """
        self.fixture.given_an_event(b2b_low_fba_price_jump_to_max_positive_applied_T225)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.3)
        self.fixture.then_standard_product_updated_price_should_be(17.8)
        self.fixture.then_b2b_product_updated_price_should_be([44.9, 41.8])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_jump_to_max_negative_max_rule_applied(self):
        """
        This test case(226) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 17.3
        the expected value for the product is : 16.9
        the expected values for the tiers are : [44.9,41.8]
        """
        self.fixture.given_an_event(b2b_low_fba_price_jump_to_max_negative_applied_T226)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.3)
        self.fixture.then_standard_product_updated_price_should_be(16.9)
        self.fixture.then_b2b_product_updated_price_should_be([44.9, 41.8])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_low_fba_price_jump_to_max_zero_max_rule_applied(self):
        """
        This test case(227) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 17.3
        the expected value for the product is : 17.3
        the expected values for the tiers are : [44.9,41.8]
        """
        self.fixture.given_an_event(b2b_low_fba_price_jump_to_max_zero_applied_T227)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.3)
        self.fixture.then_standard_product_updated_price_should_be(17.3)
        self.fixture.then_b2b_product_updated_price_should_be([44.9, 41.8])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_max_positive_min_rule_applied(self):
        """
        This test case(228) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 19.2
        the expected value for the product is : 19.5
        the expected values for the tiers are : [46.88,43.7]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_max_positive_applied_T228)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(19.2)
        self.fixture.then_standard_product_updated_price_should_be(19.5)
        self.fixture.then_b2b_product_updated_price_should_be([46.88, 43.7])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_max_negative_min_rule_applied(self):
        """
        This test case(229) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 19.2
        the expected value for the product is : 18.8
        the expected values for the tiers are : [46.88,43.7]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_max_negative_applied_T229)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(19.2)
        self.fixture.then_standard_product_updated_price_should_be(18.8)
        self.fixture.then_b2b_product_updated_price_should_be([46.88, 43.7])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_max_zero_min_rule_applied(self):
        """
        This test case(230) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 19.2
        the expected value for the product is : 19.2
        the expected values for the tiers are : [46.88,43.7]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_max_zero_applied_T230)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(19.2)
        self.fixture.then_standard_product_updated_price_should_be(19.2)
        self.fixture.then_b2b_product_updated_price_should_be([46.88, 43.7])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_positive_min_rule_applied(self):
        """
        This test case(231) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 17.1
        the expected value for the product is : 18.21
        the expected values for the tiers are : [24.91,20.42]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_positive_applied_T231)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.1)
        self.fixture.then_standard_product_updated_price_should_be(18.21)
        self.fixture.then_b2b_product_updated_price_should_be([24.91, 20.42])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_negative_min_rule_applied(self):
        """
        This test case(232) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 17.1
        the expected value for the product is : 18.21
        the expected values for the tiers are : [25.92,21.21]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_negative_applied_T232)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.1)
        self.fixture.then_standard_product_updated_price_should_be(18.21)
        self.fixture.then_b2b_product_updated_price_should_be([25.92, 21.21])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_zero_min_rule_applied(self):
        """
        This test case(233) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 17.1
        the expected value for the product is : 18.21
        the expected values for the tiers are : [27.71,22.34]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_zero_applied_T233)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.1)
        self.fixture.then_standard_product_updated_price_should_be(18.21)
        self.fixture.then_b2b_product_updated_price_should_be([27.71, 22.34])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_min_positive_max_rule_applied(self):
        """
        This test case(234) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 17.1
        the expected value for the product is : 18.21
        the expected values for the tiers are : [27.71,22.34]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_min_positive_applied_T234)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.1)
        self.fixture.then_standard_product_updated_price_should_be(18.21)
        self.fixture.then_b2b_product_updated_price_should_be([27.71, 22.34])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_min_negative_max_rule_applied(self):
        """
        This test case(235) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 17.1
        the expected value for the product is : 18.21
        the expected values for the tiers are : [28.82,29.34]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_min_negative_applied_T235)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.1)
        self.fixture.then_standard_product_updated_price_should_be(18.21)
        self.fixture.then_b2b_product_updated_price_should_be([28.82, 29.34])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_jump_to_min_zero_max_rule_applied(self):
        """
        This test case(236) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 17.1
        the expected value for the product is : 21.21
        the expected values for the tiers are : [29.29,31.34]

        """
        self.fixture.given_an_event(b2b_match_buybox_jump_to_min_zero_applied_T236)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.1)
        self.fixture.then_standard_product_updated_price_should_be(21.21)
        self.fixture.then_b2b_product_updated_price_should_be([29.29, 31.34])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_positive_max_rule_applied(self):
        """
        This test case(237) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 28.28
        the expected value for the product is : 27.72
        the expected values for the tiers are : [47.88,44.72]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_positive_applied_T237)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(28.28)
        self.fixture.then_standard_product_updated_price_should_be(27.72)
        self.fixture.then_b2b_product_updated_price_should_be([47.88, 44.72])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_negative_max_rule_applied(self):
        """
        This test case(238) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 28.28
        the expected value for the product is : 27.72
        the expected values for the tiers are : [47.88,44.72]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_negative_applied_T238)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(28.28)
        self.fixture.then_standard_product_updated_price_should_be(27.72)
        self.fixture.then_b2b_product_updated_price_should_be([47.88, 44.72])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_zero_max_rule_applied(self):
        """
        This test case(239) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 28.28
        the expected value for the product is : 28.28
        the expected values for the tiers are : [48.0,45.91]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_zero_applied_T239)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(28.28)
        self.fixture.then_standard_product_updated_price_should_be(28.28)
        self.fixture.then_b2b_product_updated_price_should_be([48.0, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_min_positive_min_rule_applied(self):
        """
        This test case(240) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 20.2
        the expected value for the product is : 21.21
        the expected values for the tiers are : [29.29,45.91]

        """
        self.fixture.given_an_event(b2b_default_jump_to_min_positive_applied_T240)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.2)
        self.fixture.then_standard_product_updated_price_should_be(21.21)
        self.fixture.then_b2b_product_updated_price_should_be([29.29, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_min_negative_min_rule_applied(self):
        """
        This test case(241) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 20.2
        the expected value for the product is : 21.21
        the expected values for the tiers are : [28.28,45.91]

        """
        self.fixture.given_an_event(b2b_default_jump_to_min_negative_applied_T241)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.2)
        self.fixture.then_standard_product_updated_price_should_be(21.21)
        self.fixture.then_b2b_product_updated_price_should_be([28.28, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_min_zero_min_rule_applied(self):
        """
        This test case(242) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 20.2
        the expected value for the product is : 21.21
        the expected values for the tiers are : [28.28,45.91]

        """
        self.fixture.given_an_event(b2b_default_jump_to_min_zero_applied_T242)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.2)
        self.fixture.then_standard_product_updated_price_should_be(21.21)
        self.fixture.then_b2b_product_updated_price_should_be([28.28, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_match_competitor_positive_min_rule_applied(self):
        """
        This test case(243) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 22.11
        the expected value for the product is : 22.61
        the expected values for the tiers are : [25.61,45.91]

        """
        self.fixture.given_an_event(b2b_default_match_competitor_positive_applied_T243)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.11)
        self.fixture.then_standard_product_updated_price_should_be(22.61)
        self.fixture.then_b2b_product_updated_price_should_be([25.61, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_match_competitor_negative_min_rule_applied(self):
        """
        This test case(244) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 22.11
        the expected value for the product is : 21.61
        the expected values for the tiers are : [25.61,45.91]

        """
        self.fixture.given_an_event(b2b_default_match_competitor_negative_applied_T244)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.11)
        self.fixture.then_standard_product_updated_price_should_be(21.61)
        self.fixture.then_b2b_product_updated_price_should_be([25.61, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_match_competitor_zero_min_rule_applied(self):
        """
        This test case(245) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 22.11
        the expected value for the product is : 22.11
        the expected values for the tiers are : [25.61,45.91]

        """
        self.fixture.given_an_event(b2b_default_match_competitor_zero_applied_T245)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.11)
        self.fixture.then_standard_product_updated_price_should_be(22.11)
        self.fixture.then_b2b_product_updated_price_should_be([25.61, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_max_positive_min_rule_applied(self):
        """
        This test case(246) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 22.11
        the expected value for the product is : 22.41
        the expected values for the tiers are : [48.0,45.91]

        """
        self.fixture.given_an_event(b2b_default_jump_to_max_positive_applied_T246)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.11)
        self.fixture.then_standard_product_updated_price_should_be(22.41)
        self.fixture.then_b2b_product_updated_price_should_be([48.0, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_max_negative_min_rule_applied(self):
        """
        This test case(247) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 22.11
        the expected value for the product is : 21.81
        the expected values for the tiers are : [51.23,45.91]

        """
        self.fixture.given_an_event(b2b_default_jump_to_max_negative_applied_T247)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.11)
        self.fixture.then_standard_product_updated_price_should_be(21.81)
        self.fixture.then_b2b_product_updated_price_should_be([51.23, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_max_zero_min_rule_applied(self):
        """
        This test case(248) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 22.11
        the expected value for the product is : 22.11
        the expected values for the tiers are : [51.23,45.91]

        """
        self.fixture.given_an_event(b2b_default_jump_to_max_zero_applied_T248)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.11)
        self.fixture.then_standard_product_updated_price_should_be(22.11)
        self.fixture.then_b2b_product_updated_price_should_be([51.23, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_default_price_positive_min_rule_applied(self):
        """
        This test case(249) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 22.11
        the expected value for the product is : 22.61
        the expected values for the tiers are : [33.06,45.91]

        """
        self.fixture.given_an_event(b2b_default_default_price_applied_T249)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.11)
        self.fixture.then_standard_product_updated_price_should_be(22.61)
        self.fixture.then_b2b_product_updated_price_should_be([33.06, 45.91])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_default_price_negative_min_rule_applied(self):
        """
        This test case(250) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 16
        the expected values for the tiers are : [14.74, 12.74]

        """
        self.fixture.given_an_event(T250)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(16)
        self.fixture.then_b2b_product_updated_price_should_be([14.74, 12.74])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_default_price_zero_min_rule_applied(self):
        """
        This test case(251) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MIN_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 16.12
        the expected values for the tiers are : [14.94, 12.94]

        """
        self.fixture.given_an_event(T251)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(16.12)
        self.fixture.then_b2b_product_updated_price_should_be([14.94, 12.94])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_do_nothing_positive_min_rule_applied(self):
        """
        This test case(252) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : None
        the expected values for the tiers are : [None, 13.14]

        """
        self.fixture.given_an_event(T252)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, 13.14])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_do_nothing_negative_min_rule_applied(self):
        """
        This test case(253) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : None
        the expected values for the tiers are : [None, 12.74]

        """
        self.fixture.given_an_event(T253)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, 12.74])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_do_nothing_zero_min_rule_applied(self):
        """
        This test case(254) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : None
        the expected values for the tiers are : [None, 12.94]

        """
        self.fixture.given_an_event(T254)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, 12.94])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_default_value_positive_min_rule_applied(self):
        """
        This test case(255) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 16.12
        the expected values for the tiers are : [10.00, 13.14]

        """
        self.fixture.given_an_event(T255)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(16.12)
        self.fixture.then_b2b_product_updated_price_should_be([10.00, 13.14])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_default_value_negative_min_rule_applied(self):
        """
        This test case(256) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 16.12
        the expected values for the tiers are : [10.00, 12.74]

        """
        self.fixture.given_an_event(T256)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(16.12)
        self.fixture.then_b2b_product_updated_price_should_be([10.00, 12.74])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_default_value_zero_min_rule_applied(self):
        """
        This test case(257) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 16.12
        the expected values for the tiers are : [10.00, 12.94]

        """
        self.fixture.given_an_event(T257)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(16.12)
        self.fixture.then_b2b_product_updated_price_should_be([10.00, 12.94])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_min_positive_max_rule_applied(self):
        """
        This test case(258) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MAX_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 16.12
        the expected values for the tiers are : [10.00, 12.94]

        """
        self.fixture.given_an_event(T258)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(16.12)
        self.fixture.then_b2b_product_updated_price_should_be([10.00, 12.94])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_min_negative_max_rule_applied(self):
        """
        This test case(259) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MAX_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 16.12
        the expected values for the tiers are : [10.00, 12.74]

        """
        self.fixture.given_an_event(T259)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(16.12)
        self.fixture.then_b2b_product_updated_price_should_be([10.00, 12.74])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_min_zero_max_rule_applied(self):
        """
        This test case(260) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MAX_PRICE_RULE : JUMP_TO_MIN
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 16.12
        the expected values for the tiers are : [10.00, 12.94]

        """
        self.fixture.given_an_event(T260)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(16.12)
        self.fixture.then_b2b_product_updated_price_should_be([10.00, 12.94])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_match_competitor_positive_max_rule_applied(self):
        """
        This test case(261) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 15.37
        the expected values for the tiers are : [9.00, 13.14]

        """
        self.fixture.given_an_event(T261)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(15.37)
        self.fixture.then_b2b_product_updated_price_should_be([9.00, 13.14])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_match_competitor_negative_max_rule_applied(self):
        """
        This test case(262) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 15.37
        the expected values for the tiers are : [9.00, 12.74]

        """
        self.fixture.given_an_event(T262)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(15.37)
        self.fixture.then_b2b_product_updated_price_should_be([9.00, 12.74])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_match_competitor_zero_max_rule_applied(self):
        """
        This test case(263) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MAX_PRICE_RULE : MATCH_COMPETITOR
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 15.37
        the expected value for the product is : 15.37
        the expected values for the tiers are : [9.00, 12.94]

        """
        self.fixture.given_an_event(T263)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.37)
        self.fixture.then_standard_product_updated_price_should_be(15.37)
        self.fixture.then_b2b_product_updated_price_should_be([9.00, 12.94])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_max_positive_max_rule_applied(self):
        """
        This test case(264) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 23
        the expected value for the product is : 22
        the expected values for the tiers are : [50.00, 45.00]

        """
        self.fixture.given_an_event(T264)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(23)
        self.fixture.then_standard_product_updated_price_should_be(22)
        self.fixture.then_b2b_product_updated_price_should_be([50.00, 45.00])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_max_negative_max_rule_applied(self):
        """
        This test case(265) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 23
        the expected value for the product is : 22
        the expected values for the tiers are : [50.00, 45.00]

        """
        self.fixture.given_an_event(T265)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(23)
        self.fixture.then_standard_product_updated_price_should_be(22)
        self.fixture.then_b2b_product_updated_price_should_be([50.00, 45.00])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_jump_to_max_zero_max_rule_applied(self):
        """
        This test case(266) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT_VALUE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 23
        the expected value for the product is : 22
        the expected values for the tiers are : [50.00, 45.00]

        """
        self.fixture.given_an_event(T266)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(23)
        self.fixture.then_standard_product_updated_price_should_be(22)
        self.fixture.then_b2b_product_updated_price_should_be([50.00, 45.00])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_default_price_positive_max_rule_applied(self):
        """
        This test case(267) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 24.23
        the expected value for the product is : 24.73
        the expected values for the tiers are : [30.3,26.28]

        """
        self.fixture.given_an_event(b2b_default_default_price_positive_applied_T267)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(24.23)
        self.fixture.then_standard_product_updated_price_should_be(24.73)
        self.fixture.then_b2b_product_updated_price_should_be([30.3, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_default_price_negative_max_rule_applied(self):
        """
        This test case(268) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 36.36
        the expected value for the product is : 30.77
        the expected values for the tiers are : [32.78, 38.79]

        """
        self.fixture.given_an_event(b2b_default_default_price_negative_applied_T268)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(36.36)
        self.fixture.then_standard_product_updated_price_should_be(30.77)
        self.fixture.then_b2b_product_updated_price_should_be([32.78, 38.79])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_default_price_zero_max_rule_applied(self):
        """
        This test case(269) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 37.37
        the expected value for the product is : 30.55
        the expected values for the tiers are : [32.56,38.57]

        """
        self.fixture.given_an_event(b2b_default_default_price_zero_applied_T269)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(37.37)
        self.fixture.then_standard_product_updated_price_should_be(30.55)
        self.fixture.then_b2b_product_updated_price_should_be([32.56, 38.57])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_do_nothing_positve_max_rule_applied(self):
        """
        This test case(270) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 37.37
        the expected value for the product is : None
        the expected values for the tiers are : [None,None]

        """
        self.fixture.given_an_event(b2b_default_do_nothing_applied_T270)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(37.37)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_do_nothing_negative_max_rule_applied(self):
        """
        This test case(271) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 38.38
        the expected value for the product is : None
        the expected values for the tiers are : [None,None]

        """
        self.fixture.given_an_event(b2b_default_do_nothing_negative_applied_T271)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(38.38)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_do_nothing_zero_max_rule_applied(self):
        """
        This test case(272) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MAX_PRICE_RULE : DO_NOTHING
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 39.39
        the expected value for the product is : None
        the expected values for the tiers are : [None,None]

        """
        self.fixture.given_an_event(b2b_default_do_nothing_zero_applied_T272)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(39.39)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_min_price_rule_positive_min_rule_applied(self):
        """
        This test case(273) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MIN_PRICE_RULE : DEFAULT
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 22.5
        the expected value for the product is : 25.75
        the expected values for the tiers are : [32.34,35.73]

        """
        self.fixture.given_an_event(b2b_default_min_price_rule_applied_T273)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.5)
        self.fixture.then_standard_product_updated_price_should_be(25.75)
        self.fixture.then_b2b_product_updated_price_should_be([32.34, 35.73])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_min_price_rule_negative_min_rule_applied(self):
        """
        This test case(274) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MIN_PRICE_RULE : DEFAULT
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 22.5
        the expected value for the product is : 25.75
        the expected values for the tiers are : [33.53,35.53]

        """
        self.fixture.given_an_event(b2b_default_min_price_rule_negative_applied_T274)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.5)
        self.fixture.then_standard_product_updated_price_should_be(25.75)
        self.fixture.then_b2b_product_updated_price_should_be([33.53, 35.53])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_default_min_price_rule_zero_min_rule_applied(self):
        """
        This test case(275) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : DEFAULT
        MIN_PRICE_RULE : DEFAULT
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 22.5
        the expected value for the product is : 25.75
        the expected values for the tiers are : [34.44,36.44]

        """
        self.fixture.given_an_event(b2b_default_min_price_rule_zero_applied_T275)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.5)
        self.fixture.then_standard_product_updated_price_should_be(25.75)
        self.fixture.then_b2b_product_updated_price_should_be([34.44, 36.44])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_price_do_nothing_positive_min_rule_applied(self):
        """
        This test case(276) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 19.6
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_lowest_price_do_nothing_positive_applied_T276)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(19.6)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_price_do_nothing_negative_min_rule_applied(self):
        """
        This test case(277) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 20.2
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_lowest_price_do_nothing_negative_applied_T277)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(20.2)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_price_do_nothing_zero_min_rule_applied(self):
        """
        This test case is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 18.7
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_lowest_price_do_nothing_negative_applied_T278)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(18.7)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_fba_price_do_nothing_positive_min_rule_applied(self):
        """
        This test case(279) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 18.7
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_lowest_fba_price_do_nothing_positive_applied_T279)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(18.10)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_fba_price_do_nothing_negative_min_rule_applied(self):
        """
        This test case(281) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 19.01
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_lowest_fba_price_do_nothing_negative_applied_T280)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(19.01)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_fba_price_do_nothing_zero_min_rule_applied(self):
        """
        This test case(281) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 22.22
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_lowest_fba_price_do_nothing_zero_applied_T281)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(22.22)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_do_nothing_positive_min_price_rule_applied(self):
        """
        This test case(282) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 23.11
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_match_buybox_do_nothing_positive_applied_T282)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(23.11)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_do_nothing_negative_min_price_rule_applied(self):
        """
        This test case(283) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 18.18
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_match_buybox_do_nothing_negative_applied_T283)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(18.18)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_do_nothing_zero_min_price_rule_applied(self):
        """
        This test case(284) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DO_NOTHING
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 17.7
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_match_buybox_do_nothing_zero_applied_T284)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.7)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_price_default_price_positive_max_rule_applied(self):
        """
        This test case(285) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 38.81
        the expected value for the product is : 34.77
        the expected values for the tiers are : [44.78, 42.79]

        """
        self.fixture.given_an_event(b2b_lowest_price_default_price_positive_applied_T285)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(38.81)
        self.fixture.then_standard_product_updated_price_should_be(34.77)
        self.fixture.then_b2b_product_updated_price_should_be([44.78, 42.79])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_price_default_price_negative_max_rule_applied(self):
        """
        This test case(286) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICER
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 38.81
        the expected value for the product is : 35.77
        the expected values for the tiers are : [45.76, 44.77]

        """
        self.fixture.given_an_event(b2b_lowest_price_default_price_negative_applied_T286)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(35.35)
        self.fixture.then_standard_product_updated_price_should_be(34.85)
        self.fixture.then_b2b_product_updated_price_should_be([45.76, 44.77])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_price_default_price_zero_max_rule_applied(self):
        """
        This test case(287) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 37.01
        the expected value for the product is : 39.92
        the expected values for the tiers are : [40.93, 39.94]

        """
        self.fixture.given_an_event(b2b_lowest_price_default_price_zero_applied_T287)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(37.01)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([40.93, 39.94])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_fba_price_default_price_positive_max_rule_applied(self):
        """
        This test case(288) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 39.04
        the expected value for the product is : 44.44
        the expected values for the tiers are : [44.45, 44.46]

        """
        self.fixture.given_an_event(b2b_lowest_fba_price_default_price_positive_applied_T288)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(39.04)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([44.45, 44.46])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_fba_price_default_price_negative_max_rule_applied(self):
        """
        This test case(289) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 40.52
        the expected value for the product is : 55.53
        the expected values for the tiers are : [55.54, 55.55]

        """
        self.fixture.given_an_event(b2b_lowest_fba_price_default_price_negative_applied_T289)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(40.52)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([55.54, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_fba_price_default_price_zero_max_rule_applied(self):
        """
        This test case(290) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 39.31
        the expected value for the product is : 33.40
        the expected values for the tiers are : [33.41, 33.42]

        """
        self.fixture.given_an_event(b2b_lowest_fba_price_default_price_zero_applied_T290)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(39.31)
        self.fixture.then_standard_product_updated_price_should_be(33.40)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_price_positive_max_rule_applied(self):
        """
        This test case(291) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 42.92
        the expected value for the product is : 37.38
        the expected values for the tiers are : [47.39, 43.40]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_price_positive_applied_T291)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(42.92)
        self.fixture.then_standard_product_updated_price_should_be(37.38)
        self.fixture.then_b2b_product_updated_price_should_be([47.39, 43.40])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_price_negative_max_rule_applied(self):
        """
        This test case(292) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 42.92
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_price_negative_applied_T292)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(42.92)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_price_zero_max_rule_applied(self):
        """
        This test case(293) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (0)
        ---------------------

        the expected value for the competitor is : 43.73
        the expected value for the product is : 36.09
        the expected values for the tiers are : [36.10, 36.11]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_price_zero_applied_T293)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(43.73)
        self.fixture.then_standard_product_updated_price_should_be(36.09)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_min_price_is_missing(self):
        """
        This test case(294) is designed to update the price of the product for
        when min_price is missing.

        the expected value for the competitor is : 17.3
        the expected value for the product is : 17.8
        the expected values for the tiers are : [46.48, 45.16]

        """
        self.fixture.given_an_event(b2b_min_price_is_missing_T294)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.3)
        self.fixture.then_standard_product_updated_price_should_be(17.8)
        self.fixture.then_b2b_product_updated_price_should_be([46.48, 45.16])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_max_price_is_missing(self):
        """
        This test case(295) is designed to update the price of the product for
        when max_price is missing.

        the expected value for the competitor is : 16.4
        the expected value for the product is : 30.07
        the expected values for the tiers are : [45.07, 42.2]

        """
        self.fixture.given_an_event(b2b_max_price_is_missing_T295)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.4)
        self.fixture.then_standard_product_updated_price_should_be(30.07)
        self.fixture.then_b2b_product_updated_price_should_be([45.07, 42.2])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_listed_price_is_missing(self):
        """
        This test case(296) is designed to update the price of the product for
        when listed_price is missing.

        the expected value for the competitor is : 16.4
        the expected value for the product is : 30.07
        the expected values for the tiers are : [39.7, 40.02]

        """
        self.fixture.given_an_event(b2b_listed_price_is_missing_T296)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.4)
        self.fixture.then_standard_product_updated_price_should_be(30.07)
        self.fixture.then_b2b_product_updated_price_should_be([39.7, 40.02])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_max_price_less_than_min_price(self):
        """
        This test case(297) is designed to update the price of the product for
        when max_price is less than min_price.

        the expected value for the competitor is : 16.4
        the expected value for the product is : 30.07
        the expected values for the tiers are : [22.48, 29.02]

        """
        self.fixture.given_an_event(b2b_max_price_less_than_min_price_T297)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.4)
        self.fixture.then_standard_product_updated_price_should_be(30.07)
        self.fixture.then_b2b_product_updated_price_should_be([22.48, 29.02])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_max_price_equal_to_min_price(self):
        """
        This test case(298) is designed to update the price of the product for
        when max_price is equal than min_price.

        the expected value for the competitor is : 16.8
        the expected value for the product is : 30.07
        the expected values for the tiers are : [23.08, 31.28]

        """
        self.fixture.given_an_event(b2b_max_price_equal_to_min_price_T298)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.8)
        self.fixture.then_standard_product_updated_price_should_be(30.07)
        self.fixture.then_b2b_product_updated_price_should_be([23.08, 31.08])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_listed_price_greater_than_max_price(self):
        """
        This test case(299) is designed to update the price of the product for
        when listed_price is greater than max_price.

        the expected value for the competitor is : 17.2
        the expected value for the product is : 30.07
        the expected values for the tiers are : [38.44, 40.22]

        """
        self.fixture.given_an_event(b2b_listed_price_greater_than_max_price_T299)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.2)
        self.fixture.then_standard_product_updated_price_should_be(30.07)
        self.fixture.then_b2b_product_updated_price_should_be([39.14, 40.92])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_beat_by_value_is_missing(self):
        """
        This test case(300) is designed to update the price of the product for
        when beat_by value is missing

        the expected value for the competitor is : 17.2
        the expected value for the product is : 30.07
        the expected values for the tiers are : [38.44, 40.22]

        """
        self.fixture.given_an_event(b2b_beat_by_value_is_missing_T300)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.2)
        self.fixture.then_standard_product_updated_price_should_be(30.07)
        self.fixture.then_b2b_product_updated_price_should_be([38.44, 40.22])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_compete_rule_is_missing(self):
        """
        This test case(301) is designed to update the price of the product for
        when compete_rule is missing

        the expected value for the competitor is : 17.2
        the expected value for the product is : 30.07
        the expected values for the tiers are : [38.74, 40.52]

        """
        self.fixture.given_an_event(b2b_compete_rule_is_missing_T301)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.2)
        self.fixture.then_standard_product_updated_price_should_be(30.07)
        self.fixture.then_b2b_product_updated_price_should_be([38.74, 40.52])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_tier_competitor_is_missing(self):
        """
        This test case(302) is designed to update the price of the product for
        when tier's competitor_price is missing

        the expected value for the competitor is : 17.2
        the expected value for the product is : 30.07
        the expected values for the tiers are : [None, 40.52]

        """
        self.fixture.given_an_event(b2b_tier_competitor_is_missing_T302)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.2)
        self.fixture.then_standard_product_updated_price_should_be(30.07)
        self.fixture.then_b2b_product_updated_price_should_be([None, 40.52])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_compatitor_price_greater_than_max_price(self):
        """
        This test case(304) is designed to update the price of the product for
        when compatitor_price is greater than max_price

        the expected value for the competitor is : 65.70
        the expected value for the product is : 60.72
        the expected values for the tiers are : [43.22, 41.07]

        """
        self.fixture.given_an_event(b2b_compatitor_price_greater_than_max_price_T304)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(65.70)
        self.fixture.then_standard_product_updated_price_should_be(60.72)
        self.fixture.then_b2b_product_updated_price_should_be([43.22, 41.07])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_replace_new_to_newItem(self):
        """
        This test case(305) is designed to update the price of the product for
        replacing item_condition new with newItem

        the expected value for the competitor is : 43.73
        the expected value for the product is : 36.09
        the expected values for the tiers are : [36.09, 36.10]

        """
        self.fixture.given_an_event(b2b_replace_new_to_newItem_T305)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(43.73)
        self.fixture.then_standard_product_updated_price_should_be(36.09)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_replace_new_to_used(self):
        """
        This test case(306) is designed to update the price of the product for
        setting item_condition in listing data as "NewOpenBox" and in
        payload as "used".

        the expected value for the competitor is : 13.98
        the expected value for the product is : 31.75

        """
        self.fixture.given_an_event(b2b_replace_new_to_used_T306)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(13.98)
        self.fixture.then_standard_product_updated_price_should_be(31.75)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_item_condition_CollectibleGood(self):
        """
        This test case(307) is designed to update the price of the product for
        setting item_condition in listing data as "CollectibleGood" and in
        payload as "Collectible".

        the expected value for the competitor is : 13.98
        the expected value for the product is : 31.75
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_item_condition_CollectibleGood_T307)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(13.98)
        self.fixture.then_standard_product_updated_price_should_be(31.75)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_only_offer_each_has_competitor(self):
        """
        This test case(308) is designed to update the price of the product for
        single offer in b2b and every tier's has its own default_price.

        the expected value for the competitor is : None
        the expected value for the product is : 22.22
        the expected values for the tiers are : [20.20, 21.21]

        """
        self.fixture.given_an_event(b2b_only_offer_T308)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(None)
        self.fixture.then_standard_product_updated_price_should_be(22.22)
        self.fixture.then_b2b_product_updated_price_should_be([20.20, 21.21])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_only_offer_mean_case(self):
        """
        This test case(309) is designed to update the price of the product for
        single offer in b2b where tier's and b2b standard has not its default_price,
        in this case it will take mean value.

        the expected value for the competitor is : None
        the expected value for the product is : 19.33
        the expected values for the tiers are : [30.0, 30.0]

        """
        self.fixture.given_an_event(b2b_only_offer_T309)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(None)
        self.fixture.then_standard_product_updated_price_should_be(19.33)
        self.fixture.then_b2b_product_updated_price_should_be([30.0, 30.0])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_only_offer_onetier_has_default_price_and_second_not(self):
        """
        This test case(310) is designed to update the price of the product for
        single offer in b2b where tier's and b2b standard where one tier has its default value
        and other has not.

        the expected value for the competitor is : None
        the expected value for the product is : 19.33
        the expected values for the tiers are : [30.0, 33.33]

        """
        self.fixture.given_an_event(b2b_only_offer_T310)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(None)
        self.fixture.then_standard_product_updated_price_should_be(19.33)
        self.fixture.then_b2b_product_updated_price_should_be([30.0, 33.33])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_only_offer_not_default_price_nor_min(self):
        """
        This test case(311) is designed to update the price of the product for
        single offer in b2b where tier's and b2b standard has neither default_value nor
        min_price.

        the expected value for the competitor is : None
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_only_offer_T311)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(None)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_standard_competitor_not_available_tiers_have(self):
        """
        This test case(312) is designed to update the price of the product where
        standard comprtitor not available but tier's competitor's availbale

        """
        self.fixture.given_an_event(b2b_standard_has_not_competitor)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(None)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([63.7, 68.11])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_test_for_uk_seller_and_us_market(self):
        """
        This test case(313) is designed to update the price of the product for
        single offer in b2b where tier's and b2b standard has neither default_value nor
        min_price.

        the expected value for the competitor is : None
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_test_for_uk_seller_and_us_market)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()

        self.assertEqual(str(context.exception),
                         "Skipping Repricing! (Seller (SELLER_ID: SX313 marketplace is different than the payload)")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_marketplace_test_for_uk_seller_and_uk_market(self):
        """
        This test case(314) is designed to update the price of the product for
        UK SELLER and UK MARKETPLACE_ID

        the expected value for the competitor is :15.2
        the expected value for the product is : 25.71
        the expected values for the tiers are : [50.0, 45.0]

        """
        self.fixture.given_an_event(b2b_marketplace_test_for_uk_seller_and_uk_market_314)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.2)
        self.fixture.then_standard_product_updated_price_should_be(25.71)
        self.fixture.then_b2b_product_updated_price_should_be([50.0, 45.0])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_test_for_us_seller_and_uk_market(self):
        """
        This test case(315) is designed to update the price of the product for
        US SELLER and UK MARKETPLACE_ID

        exception will raise here : Seller marketplace is different than the payload

        """
        self.fixture.given_an_event(b2b_test_for_us_seller_and_uk_market_315)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_test_for_us_seller_and_us_market(self):
        """
        This test case(316) is designed to update the price of the product for
        US SELLER and US MARKETPLACE_ID

        the expected value for the competitor is :15.2
        the expected value for the product is : 25.71
        the expected values for the tiers are : [50.0, 45.0]

        """
        self.fixture.given_an_event(b2b_test_for_us_seller_and_us_market_316)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(15.2)
        self.fixture.then_standard_product_updated_price_should_be(25.71)
        self.fixture.then_b2b_product_updated_price_should_be([50.0, 45.0])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_tiers_have_our_seller_id(self):
        """
        This test case(317) is designed to update the price of the product for
        where tier's competitor in match buy-box has seller_ids of our own seller.

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 17.1
        the expected value for the product is : 18.21
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_match_buybox_tiers_have_our_seller_id_317)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.1)
        self.fixture.then_standard_product_updated_price_should_be(18.21)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_only_one_tier_have_our_seller_id(self):
        """
        This test case(318) is designed to update the price of the product for
        where one tier in match-buybox has seller_id of our own seller and second has not.

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 17.1
        the expected value for the product is : 18.21
        the expected values for the tiers are : [None, 20.42]

        """
        self.fixture.given_an_event(b2b_match_buybox_only_one_tier_have_our_seller_id_318)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(17.1)
        self.fixture.then_standard_product_updated_price_should_be(18.21)
        self.fixture.then_b2b_product_updated_price_should_be([None, 20.42])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_standard_seller_id_of_our_seller_tiers_not(self):
        """
        This test case(319) is designed to update the price of the product for
        where in match-buybox standard-competitor has its our seller-id but tiers have not.

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MIN_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : None
        the expected value for the product is : None
        the expected values for the tiers are : [24.91, 20.42]

        """
        self.fixture.given_an_event(b2b_match_buybox_standard_seller_id_of_our_seller_tiers_not_319)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(None)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([24.91, 20.42])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_price_positive_defaultprice_negative_applied(self):
        """
        This test case(320) is designed to update the price of the product for
        where in listed_data , default_price for standard and business is negative

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 42.92
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_price_positive_defaultprice_negative_applied_T320)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(42.92)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_price_positive_one_tier_defaultprice_negative_applied(self):
        """
        This test case(321) is designed to update the price of the product for
        where in listed_data , default_price for tier 05 is negative.

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 42.9
        the expected value for the product is : None
        the expected values for the tiers are : [None, None]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_price_positive_defaultprice_negative_applied_T321)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(42.92)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_buybox_default_price_positive_standatd_defaultprice_negative_applied(self):
        """
        This test case(322) is designed to update the price of the product for
        where in listed_data , default_price for b2b standard is negative.

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_VALUE
        BEAT_BY : (+)
        ---------------------

        the expected value for the competitor is : 42.9
        the expected value for the product is : None
        the expected values for the tiers are : [None, 43.31]

        """
        self.fixture.given_an_event(b2b_match_buybox_default_price_positive_standatd_defaultprice_negative_applied_322)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(42.92)
        self.fixture.then_standard_product_updated_price_should_be(None)
        self.fixture.then_b2b_product_updated_price_should_be([None, 43.31])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_pick_competitor_price_from_fulfillmentChannel_Merchant(self):
        """
        This test case (323), is designed to update the price of the product where
        competitor price should pick from there, where fulfillmentChannel is Merchant.

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 13.98
        the expected value for the product is : 13.48
        the expected values for the tiers are : [45.76, 44.77]

        """
        self.fixture.given_an_sigle_api_event(b2b_pick_lowest_price_from_merchant_323)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(66.7)
        self.fixture.then_standard_product_updated_price_should_be(35.75)
        self.fixture.then_b2b_product_updated_price_should_be([45.76, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_lowest_price_with_fullfilment_channel_Merchant_and_item_condition_new(self):
        """
        This test case (324) is designed to update the price of the product.
        where fulfillment_channel is merchant and item_condition is new.

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 60.0
        the expected value for the product is : 35.75
        the expected values for the tiers are : [45.76, 44.77]

        """
        self.fixture.given_an_sigle_api_event(b2b_lowest_price_with_Amazon_and_Merchant_fullfilment_type_324)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(60.0)
        self.fixture.then_standard_product_updated_price_should_be(35.75)
        self.fixture.then_b2b_product_updated_price_should_be([45.76, 44.77])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_match_bybox_item_condition_new_325(self):
        """
        This test case(325) is designed to update the price of the product for
        where competitor_price should pick from where item_condition key's value
        is new.

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 16.7
        the expected value for the product is : 16.2
        the expected values for the tiers are : [38.42, 38.38]

        """
        self.fixture.given_an_event(b2b_match_bybox_item_condition_325)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(16.7)
        self.fixture.then_standard_product_updated_price_should_be(16.2)
        self.fixture.then_b2b_product_updated_price_should_be([38.42, 38.88])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_pick_competitor_price_from_compete_with_match_buybox_326(self):
        """
        This test case (326), is designed to update the price of the product where
        competitor price should pick from there Summary when compete_with is match_buybox.

        TEST VALUES
        -------------------
        COMPETE WITH : MATCH_BUYBOX
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 67.0
        the expected value for the product is : 35.75
        the expected values for the tiers are : [45.76 , None]
        """
        self.fixture.given_an_sigle_api_event(b2b_pick_competitor_price_from_compete_with_match_buybox_326)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(67.0)
        self.fixture.then_standard_product_updated_price_should_be(35.75)
        self.fixture.then_b2b_product_updated_price_should_be([45.76, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_pick_competitor_price_from_compete_with_lowest_price_327(self):
        """
        This test case (327), is designed to update the price of the product where
        competitor price should pick from there Summary when compete_with is lowest_price.

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 60.0
        the expected value for the product is : 35.75
        the expected values for the tiers are : [45.76 , 44.77]

        """
        self.fixture.given_an_sigle_api_event(b2b_pick_competitor_price_from_compete_with_lowest_price_327)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(60.0)
        self.fixture.then_standard_product_updated_price_should_be(35.75)
        self.fixture.then_b2b_product_updated_price_should_be([45.76, 44.77])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_pick_competitor_price_from_compete_with_lowest_fba_price_328(self):
        """
        This test case (328), is designed to update the price of the product where
        competitor price should pick from there Summary when compete_with is lowest_fba_price.

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------

        the expected value for the competitor is : 65.89
        the expected value for the product is : 35.75
        the expected values for the tiers are : [None , None]

        """
        self.fixture.given_an_sigle_api_event(b2b_pick_competitor_price_from_compete_with_lowest_fba_price_328)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(65.89)
        self.fixture.then_standard_product_updated_price_should_be(35.75)
        self.fixture.then_b2b_product_updated_price_should_be([None, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_pick_competitor_price_from_fulfillmentChannel_Merchant_by_inventory_age_329(self):
        """
        This test case (329), is designed to update the price of the product where
        competitor price should pick from there, where fulfillmentChannel is Merchant and strategy is applied
        according to the inventory age rules
        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------
        the expected value for the competitor is : 66.7
        the expected value for the product is : 45.0
        """
        self.fixture.given_an_sigle_api_event(pick_lowest_price_from_merchant_by_inventory_age_329)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_strategy_id_should_be(99994)
        self.fixture.then_standard_product_competitor_price_should_be(66.7)
        self.fixture.then_standard_product_updated_price_should_be(45.0)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_b2b_pick_competitor_price_from_fulfillmentChannel_Merchant_by_inventory_age_330(self):
        """
        This test case (330), is designed to update the price of the product where
        competitor price should pick from there, where fulfillmentChannel is Merchant.

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        MAX_PRICE_RULE : DEFAULT_PRICE
        BEAT_BY : (-)
        ---------------------
        the expected value for the competitor is : 13.98
        the expected value for the product is : 13.48
        the expected values for the tiers are : [45.76, 44.77]
        """
        self.fixture.given_an_sigle_api_event(b2b_pick_lowest_price_from_merchant_by_inventory_age_330)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_strategy_id_should_be(99994)
        self.fixture.then_standard_product_competitor_price_should_be(66.7)
        self.fixture.then_standard_product_updated_price_should_be(36.12)
        self.fixture.then_b2b_product_updated_price_should_be([57.72, None])
        self.fixture.then_remove_asin_seller_from_redis()

    def test_pick_competitor_price_from_fulfillmentChannel_Merchant_by_inventory_age_331(self):
        """
        This test case (331), is designed to update the price of the product where
        competitor price should pick from there, where fulfillmentChannel is Merchant and strategy is applied
        according to the inventory age rules
        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------
        the expected exception value should be: Strategy does not exists in cache...
        """

        self.fixture.given_an_sigle_api_event(
            pick_lowest_price_from_merchant_when_strategy_not_in_redis_by_inventory_age_331)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()
        self.assertEqual(str(context.exception), f"Strategy does not exists in cache...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_pick_competitor_price_from_fulfillmentChannel_Merchant_when_inventory_age_rules_not_given_332(self):
        """
        This test case (332), is designed to update the price of the product where
        competitor price should pick from there, where fulfillmentChannel is Merchant and strategy is applied
        according to the inventory age rules
        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------
        the expected value for the competitor is : 66.7
        the expected value for the product is : 45.0
        """

        self.fixture.given_an_sigle_api_event(pick_lowest_price_from_merchant_when_inventory_age_rules_not_given_332)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_strategy_id_should_be(9999)
        self.fixture.then_standard_product_competitor_price_should_be(66.7)
        self.fixture.then_standard_product_updated_price_should_be(35.0)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_pick_competitor_price_from_fulfillmentChannel_Merchant_when_inventory_age_rules_not_given_333(self):
        """
        This test case (333), is designed to update the price of the product where
        competitor price should pick from there, where fulfillmentChannel is Merchant and strategy is applied
        according to the inventory age rules
        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_FBA_PRICE
        MAX_PRICE_RULE : JUMP_TO_MAX
        BEAT_BY : (-)
        ---------------------
        the expected value for the competitor is : 66.7
        the expected value for the product is : 45.0
        """

        self.fixture.given_an_sigle_api_event(pick_lowest_price_from_merchant_when_inventory_age_not_given_333)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_strategy_id_should_be(9999)
        self.fixture.then_standard_product_competitor_price_should_be(66.7)
        self.fixture.then_standard_product_updated_price_should_be(35.0)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_repricing_is_not_happening_when_disabled_334(self):
        """
        This test case (334), is designed to check that repricing is not
        happening when it is disabled
        TEST VALUES
        -------------------
        repricer_enabled : False
        ---------------------
        the expected exception value should be: Repricer is disable for ASIN: AX0329
        """

        self.fixture.given_an_sigle_api_event(repricing_is_disabled_for_asin_334)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()
        self.assertEqual(str(context.exception), f"Repricer is disable for ASIN: AX0329")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_asins_payloads_is_getting_stored_in_redis_335(self):
        """
        This test case (335), is designed to check whether ASIN_PAYLOADS
        is getting stored in redis
        """

        self.fixture.given_an_sigle_api_event(asins_payloads_is_getting_stored_in_redis_335)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.when_asin_payloads_key_is_extracted("ASIN_PAYLOADS", "AX0329")
        self.fixture.then_asin_payload_key_should_exist()
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_avg_negative_min_rule_applied_336(self):
        """
        This test case(336) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_AVG
        BEAT_BY : (-5)
        ---------------------

        the expected value for the competitor is : 12
        the expected value for the product is: 12.5

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Avg_negative_rule_applied_336)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(12)
        self.fixture.then_standard_product_updated_price_should_be(12.5)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_avg_postive_max_rule_applied_337(self):
        """
        This test case(337) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_AVG
        BEAT_BY : (+50)
        ---------------------

        the expected value for the competitor is : 12
        the expected value for the product is: 12.5

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Avg_postive_rule_applied_337)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        self.fixture.when_strategy_applied()
        self.fixture.then_standard_product_competitor_price_should_be(12)
        self.fixture.then_standard_product_updated_price_should_be(12.5)
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_avg_min_price_not_exists_338(self):
        """
        This test case(338) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (+50)
        ---------------------

        the expected exception value should be: Rule is set to jump_to_max, but max price is missing...

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Avg_min_price_not_exists_applied_338)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()
        self.assertEqual(str(context.exception),
                         f"Rule is set to jump_to_avg, but min price is missing for ASIN: AX07...")
        self.fixture.then_remove_asin_seller_from_redis()

    def test_lowest_price_jump_to_avg_max_price_not_exists_339(self):
        """
        This test case(339) is designed to update the price of the product for

        TEST VALUES
        -------------------
        COMPETE WITH : LOWEST_PRICE
        COMPETE RULE : JUMP_TO_MAX
        BEAT_BY : (-5)
        ---------------------

        the expected exception value should be: Rule is set to jump_to_avg, but max price is missing for ASIN: AX07...

        """
        self.fixture.given_an_event(Lowest_Price_Jump_to_Avg_max_price_not_exists_applied_339)
        self.fixture.given_a_payload()
        self.fixture.given_platform_from_event()
        with self.assertRaises(SkipProductRepricing) as context:
            self.fixture.when_strategy_applied()
        self.assertEqual(str(context.exception),
                         f"Rule is set to jump_to_avg, but max price is missing for ASIN: AX07...")
        self.fixture.then_remove_asin_seller_from_redis()

    class _Fixture(Fixture):

        def when_strategy_applied(self):

            for seller_id, seller in self.sellers.items():
                seller = json.loads(seller, object_hook=CustomJSON)
                account = Account(seller_id)

                self.payload = self.payload.get('body.payload')
                for sku, listing in seller.items():

                    self.product = self.service.process(account, sku, listing)

                    if self.product:
                        ApplyStrategyService().apply(self.product)

                    else:
                        print("************** Competitor not find or some missing values **************")
                        raise Exception("Competitor not find or some missing values")

        def given_platform_from_event(self):
            self.platform = AMAZON

        def given_an_event(self, event):
            self.event = event

        def given_an_sigle_api_event(self, event):
            listing_data = event.pop("listing_data")
            strategy_data = event.pop("strategy_data")
            payload = check_missing_values_in_message(event)

            self.event = {
                "listing_data": listing_data,
                "strategy_data": strategy_data,
                "body": payload.get("responses")[0].get("body"),
                "request": payload.get("responses")[0].get("request")
            }

        def given_a_payload(self):
            message = self.event

            set_data = SetData()
            listing_data = message.get("listing_data")
            set_data.set_data_in_redis(listing_data)
            strategy_data = message.get("strategy_data")
            set_data.set_data_in_redis(strategy_data)
            for key, nested_dict in listing_data[0].items():
                for field, data in nested_dict.items():
                    seller_id = field

            marketplace_type = message.get("marketplace_type", "UK")
            set_data.set_data_in_redis([{"seller_id": seller_id, "marketplace_type": marketplace_type}])

            self.payload = json.loads(json.dumps(message), object_hook=CustomJSON)
            self.service = MessageProcessor(self.payload)
            self.sellers = self.service.retrieve_sellers()

        def then_product_strategy_type_should_be(self, expected_value):
            self.assertAlmostEqual(self.product.strategy_type, expected_value)

        def then_standard_product_updated_price_should_be(self, expected_value):
            self.assertEqual(self.product.updated_price, expected_value)

        def then_standard_product_competitor_price_should_be(self, expected_value):
            self.assertEqual(self.product.competitor_price, expected_value)

        def invalid_payload(self, data):
            self.assertTrue(data == 'Invalid Payload' or data is None)

        def then_b2b_product_updated_price_should_be(self, expected_value):
            n = 0
            for tier in self.product.tiers.values():
                self.assertEqual(tier.updated_price, expected_value[n])
                n += 1

        def then_strategy_id_should_be(self, expected_value):
            self.assertEqual(self.product.strategy_id, expected_value)

        def then_remove_asin_seller_from_redis(self):
            """
            Picks ASIN and Seller ID from the event data and deletes corresponding data from Redis.
            """

            asin = list(self.event["listing_data"][0].keys())[0]
            sellerid = list(self.event["listing_data"][0][asin].keys())[0]
            self.delete_redis_data(asin)
            self.delete_redis_data(f"account.{sellerid}")
            self.delete_strategies_from_redis("strategy.")
            self.delete_redis_data("ASIN_PAYLOADS")

        def when_asin_payloads_key_is_extracted(self, key_name, asin):
            self.actual_value = self.get_value_from_redis(key_name, asin)

        def then_asin_payload_key_should_exist(self):
            self.assertNotEqual(self.actual_value, None)

        def get_value_from_redis(self, key, field):
            redis_client = redis.Redis(
                host=os.getenv("HOST"),
                port=os.getenv("REDIS_MASTER_PORT")
            )

            value = redis_client.hget(key, field)

            if value is not None:
                value_dict = json.loads(value)
                return value_dict
            else:
                return None

        def delete_redis_data(self, key_name):
            """
              Deletes data from Redis based on the provided key.

              Args:
              - key_name (str): The key to identify the data in Redis.
            """

            redis_client.delete_key(key_name)

        def delete_strategies_from_redis(self, prefix):
            keys_to_delete = redis_client.match_pattern(f"{prefix}*")
            for key in keys_to_delete:
                redis_client.delete_key(key)


if __name__ == '__main__':
    unittest.main()
