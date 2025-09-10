import sys, os, unittest, unittest, os, django, random,string 

project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)
os.environ['DJANGO_SETTINGS_MODULE'] = 'ArbitrageFeedSubmission.settings'	
django.setup()

from test_data import *	
from create_feed import get_file_size_in_mb
from fetch_product import fetch_products_from_redis
from feed_submission.helpers.redis_cache import RedisCache
from create_feed import extract_out_of_range_products, process_data, create_amazon_feed	
from test_data import STANDARD_BUSINESS_FEED_SAMPLE, BUSINESS_FEED_SAMPLE, STANDARD_FEED_SAMPLE	
from feed_submission.tasks import process_feed_notification
from feed_submission.helpers.utils import split_list_into_chunks

redis_cache = RedisCache()


class Fixture(unittest.TestCase):
    pass


class TestStrategies(unittest.TestCase):
    def setUp(self):
        self.fixture = self._Fixture()

    def test_standard_updated_price_not_out_of_range_01(self):
        """
        This test case is designed to check when in Standard payload
        updated_price is not out_of_range. If it returns None, it means the value is
        not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(standard_updated_price_not_out_of_range_01)
        self.fixture.when_fetch_product_detail("AX01", "SX01")
        self.fixture.then_expected_result_is_none()

    def test_standard_updated_price_is_none_not_listed_price_02(self):
        """
        This test case is designed to check when in Standard payload
        updated_price is None but listed_price is not None. (listed_price_not_out_range)
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(standard_updated_price_is_none_not_listed_price_02)
        self.fixture.when_fetch_product_detail("AX02", "SX02")
        self.fixture.then_expected_result_is_none()

    def test_standard_min_price_is_none_max_price_not_03(self):
        """
        This test case is designed to check when in Standard payload
        min_price is None and max_price is not None (max_price_out_range)
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(standard_min_price_is_none_max_price_not_03)
        self.fixture.when_fetch_product_detail("AX03", "SX03")
        self.fixture.then_expected_result_should_be({'asin': 'AX03', 'sku': 'SX03'})

    def test_standard_max_price_is_none_min_price_not_04(self):
        """
        This test case is designed to check when in Standard payload
        max_price is None and min_price is not None(min_price_out_range)
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(standard_max_price_is_none_min_price_not_04)
        self.fixture.when_fetch_product_detail("AX04", "SX04")
        self.fixture.then_expected_result_should_be({'asin': 'AX04', 'sku': 'SX04'})

    def test_b2b_standard_updated_price_not_out_of_range_05(self):
        """
        This test case is designed to check when in B2B payload (tiers's not include)
        updated_price is not out_of_range.
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_updated_price_not_out_of_range_05)
        self.fixture.when_fetch_product_detail("AX05", "SX05")
        self.fixture.then_expected_result_is_none()

    def test_b2b_updated_price_is_none_not_listed_price_06(self):
        """
        This test case is designed to check when in B2B payload (tiers's not included)
        updated_price is None and listed_price is not None.
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_updated_price_is_none_not_listed_price_06)
        self.fixture.when_fetch_product_detail("AX06", "SX06")
        self.fixture.then_expected_result_is_none()

    def test_b2b_updated_price_min_price_is_none_max_price_not_07(self):
        """
        This test case is designed to check when in B2B payload (tiers's not included)
        min_price is None and max_price is not None. (max_price_out_range)
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_updated_price_min_price_is_none_max_price_not_07)
        self.fixture.when_fetch_product_detail("AX07", "SX07")
        self.fixture.then_expected_result_should_be({'asin': 'AX07', 'sku': 'SX07'})

    def test_b2b_updated_price_max_price_is_none_min_price_not_08(self):
        """
        This test case is designed to check when in B2B payload (tiers's not included)
        max_price is None and min_price is not None. (max_price_out_range)
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_updated_price_max_price_is_none_min_price_not_08)
        self.fixture.when_fetch_product_detail("AX08", "SX08")
        self.fixture.then_expected_result_should_be({'asin': 'AX08', 'sku': 'SX08'})

    def test_b2b_updated_price_not_out_of_range_but_for_tiers_09(self):
        """
        This test case is designed to check when in B2B payload (tiers's included)
        updated_price is not out_of_range , but for tier's updated_price is out-of-range.
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_updated_price_not_out_of_range_but_for_tiers_09_b2b)
        self.fixture.when_fetch_product_detail("AX09", "SX09")
        self.fixture.then_expected_result_is_none()

        self.fixture.given_an_event(b2b_updated_price_not_out_of_range_but_for_tiers_09_tiers)
        self.fixture.when_fetch_product_detail("AX09", "SX09")
        self.fixture.then_expected_result_should_be({'asin': 'AX09', 'sku': 'SX09'})

    def test_b2b_listed_price_not_out_of_range_but_for_tiers_10(self):
        """
        This test case is designed to check when in B2B payload (tiers's included)
        listed_price is not out_of_range , but for tier's listed_price is out-of-range.
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_listed_price_not_out_of_range_but_for_tiers_10_b2b)
        self.fixture.when_fetch_product_detail("AX010", "SX010")
        self.fixture.then_expected_result_is_none()

        self.fixture.given_an_event(b2b_listed_price_not_out_of_range_but_for_tiers_10_tiers)
        self.fixture.when_fetch_product_detail("AX010", "SX010")
        self.fixture.then_expected_result_should_be({'asin': 'AX010', 'sku': 'SX010'})

    def test_b2b_tiers_min_price_is_none_max_price_not_11(self):
        """
        This test case is designed to check when in B2B payload (tiers's included)
        tier's min_price is None but max_price is not None.
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_tiers_min_price_is_none_max_price_not_11_b2b)
        self.fixture.when_fetch_product_detail("AX011", "SX011")
        self.fixture.then_expected_result_is_none()

        self.fixture.given_an_event(b2b_tiers_min_price_is_none_max_price_not_11_tiers)
        self.fixture.when_fetch_product_detail("AX011", "SX011")
        self.fixture.then_expected_result_should_be({'asin': 'AX011', 'sku': 'SX011'})

    def test_b2b_tiers_max_price_is_none_min_price_not_12(self):
        """
        This test case is designed to check when in B2B payload (tiers's included)
        tier's max_price is None but min_price is not None.
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_tiers_max_price_is_none_min_price_not_12_b2b)
        self.fixture.when_fetch_product_detail("AX012", "SX012")
        self.fixture.then_expected_result_is_none()

        self.fixture.given_an_event(b2b_tiers_max_price_is_none_min_price_not_12_tier)
        self.fixture.when_fetch_product_detail("AX012", "SX012")
        self.fixture.then_expected_result_should_be({'asin': 'AX012', 'sku': 'SX012'})

    def test_b2b_standard_and_tiers_price_out_of_range_13(self):
        """
        This test case is designed to check when in B2B payload (tiers's included)
        tier's and b2b_standard prices are out of range.
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_standard_and_tiers_price_out_of_range_13_b2b)
        self.fixture.when_fetch_product_detail("AX013", "SX013")
        self.fixture.then_expected_result_should_be({'asin': 'AX013', 'sku': 'SX013'})

        self.fixture.given_an_event(b2b_standard_and_tiers_price_out_of_range_13_tiers)
        self.fixture.when_fetch_product_detail("AX013", "SX013")
        self.fixture.then_expected_result_should_be({'asin': 'AX013', 'sku': 'SX013'})

    def test_b2b_standard_updated_and_list_price_none_14(self):
        """
        This test case is designed to check when in standard paylaod
        listed_price and updated_price are None.
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_standard_updated_and_list_price_none_14)
        self.fixture.when_fetch_product_detail("AX014", "SX014")
        self.fixture.then_expected_result_is_none()

    def test_b2b_standard_and_tiers_updated_and_list_price_none_15(self):
        """
        This test case is designed to check when in B2B payload (tiers's included)
        b2b_standard and tiers both listed_prices and updated_prices are None.
        If it returns None, it means the value is not out of range; otherwise, it will return asin and sku.
        """
        self.fixture.given_an_event(b2b_standard_and_tiers_updated_and_list_price_none_15_b2b)
        self.fixture.when_fetch_product_detail("AX015", "SX015")
        self.fixture.then_expected_result_is_none()

        self.fixture.given_an_event(b2b_standard_and_tiers_updated_and_list_price_none_15_tiers)
        self.fixture.when_fetch_product_detail("AX015", "SX015")
        self.fixture.then_expected_result_is_none()

    def test_check_standard_feed_16(self):
        """
        This test case is designed to check whether the expected standard feed is exactly like
        the created a feed or not.
        """
        self.fixture.given_an_event(check_standard_feed_16)
        self.fixture.when_extract_feed("A25M6ZYMJHWYLU", "UK")
        self.fixture.then_expected_feed_should_be(STANDARD_FEED_SAMPLE)

    def test_check_b2b_feed_17(self):
        """
        This test case is designed to check whether the expected business feed is exactly like
        the created a feed or not.
        """
        self.fixture.given_an_event(check_b2b_feed_17)
        self.fixture.when_extract_feed("A25M6ZYMJHWYNN", "UK")
        self.fixture.then_expected_feed_should_be(BUSINESS_FEED_SAMPLE)

    def test_check_standard_b2b_feed_18(self):
        """
        This test case is designed to check whether the expected standard-business feed is exactly like
        the created a feed or not.
        """
        self.fixture.given_an_event(check_standard_b2b_feed_18)
        self.fixture.when_extract_feed("A25M6ZYMJHWYNN", "UK")
        self.fixture.then_expected_feed_should_be(STANDARD_BUSINESS_FEED_SAMPLE)

    def test_check_file_size_standard_b2b_feed_19(self):
        """
        This test case is designed to check whether the file created in XML format has a size 
        less than 10 MBs
        """
        self.fixture.given_data_stored_in_redis()
        self.fixture.when_file_is_created()
        self.fixture.then_expected_file_size_should_be_less_than(MAXIMUM_FILE_SIZE)

    def test_split_list_into_chunks_20(self):
        """
        This test case is designed to check whether the file created in XML format has a size 
        less than 10 MBs
        """
        self.fixture.given_an_event(error_notifications)
        self.fixture.when_data_is_split_between_lists()
        self.fixture.then_each_notification_size_is_less_than(10)
        
    def test_feed_submission_notifications_in_bulk_21(self):
        """
        This test case is designed to check whether the notifications are getting sent in bulk 
        in feedsubmission and producting messages in SQS queue 
        """
        self.fixture.given_feed_processing_notification_event(payloads_for_feed_submission_21, test_user_data)        
        self.fixture.when_feed_submission_notification_is_triggered()
        self.fixture.then_produced_feeds_should_be(4)

    class _Fixture(Fixture):

        def given_an_event(self, event):
            self.event = event

        def given_feed_processing_notification_event(self, event, account_data):
            self.event = event
            seller_id = account_data.pop("seller_id")
            key = f"account.{seller_id}"
            redis_cache.hsetall_account(key, account_data)


        def then_each_notification_size_is_less_than(self,size_in_mb):
            for notification in self.result:
                self.assertLessEqual(sys.getsizeof(notification)/1024,size_in_mb)                

        def when_data_is_split_between_lists(self):
            self.result = split_list_into_chunks(self.event)
        def when_given_a_payload(self):
            message = self.event
            self.result = extract_out_of_range_products(message, "", testing=True)

        def then_expected_file_size_should_be_less_than(self,file_size):            
            self.assertTrue(get_file_size_in_mb(self.file_name) <= file_size)
            os.remove(self.file_name)

        def when_extract_feed(self, seller_id, marketplace):
            self.feed_output, self.file, self.products = create_amazon_feed(
                seller_id, self.event, marketplace)

        def then_expected_result_should_be(self, expected_value):
            self.assertEqual(self.output_value, expected_value)

        def then_expected_result_is_none(self):
            self.assertIsNone(self.output_value)
        
        def when_feed_submission_notification_is_triggered(self):
            self.result = process_feed_notification(self.event)
        
        def then_produced_feeds_should_be(self,expected_value):
            self.assertEqual(len(self.result),expected_value)

        def then_expected_feed_should_be(self, expected_value):
            with open(self.file, 'r') as feed_file_content:
                self.assertEqual(feed_file_content.read(), expected_value)
            os.remove(self.file)

        def __generate_random_field_by_box_and_standard(self):
            return f"{seller_id}-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=22))

        def when_file_is_created(self):
            products = fetch_products_from_redis(f"{seller_id}")
            xml_content,self.file_name, products_data = create_amazon_feed(
                f"{seller_id}", products, "UK")        

        def __set_values_in_redis_by_box_and_standard(self):
            key = f"{seller_id}_repriced_products"
            for _ in range(10000):
                field = self.__generate_random_field_by_box_and_standard()
                value = repriced_products_data
                value["sku"]=field
                redis_cache.hset(key, field, value)

        def given_data_stored_in_redis(self):
            self.__set_values_in_redis_by_box_and_standard()

        def when_fetch_product_detail(self, asin, sku):
            self.output_value = process_data(self.event, asin, sku)


if __name__ == '__main__':
    unittest.main()
