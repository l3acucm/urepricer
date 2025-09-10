"""Integration tests for Redis operations and business logic."""

import os
import sys
import django
import unittest

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from .fixtures import *
from project.ah_authentication.redis_cache import RedisCache
from project.ah_authentication.tasks import (
    update_or_create_user_account,
    handle_delete_message,
    process_redis_data,
    delete_asins_payloads,
)
from project.ah_authentication.services.redis_service import RedisService
from project.ah_authentication.services.price_reset_service import PriceResetService

redis_client = RedisCache()


class Fixture(unittest.TestCase):
    pass


class TestIntegration(unittest.TestCase):
    """Integration tests for Redis operations and business logic."""

    def setUp(self):
        self.fixture = self._Fixture()

    def test_missing_key_in_user_credentials_raises_key_error(self):
        """
        Test to ensure a KeyError is raised when a 'enabled' key is missing in user credentials.
        """
        self.fixture.given_an_event(user_credentials_data_with_missing_key)
        self.fixture.when_received_credentials()

        with self.assertRaises(KeyError) as context:
            self.fixture.then_update_or_create_user_account()

        self.assertEqual(str(context.exception), "'enabled'")
        self.fixture.then_delete_asin_from_redis(f"B08F")

    def test_listings_sku_data_is_deleted_from_redis(self):
        """
        Test to ensure that SKU data for a given seller and ASIN is deleted from Redis.
        """
        self.fixture.given_an_payload(redis_listing_data_of_sku)
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.then_delete_listing_data(
            "B08F2QH222", "AQ934580H6222", "I8-4V38-B222"
        )
        self.fixture.then_verify_listing_data_sku_value("B08F2QH222", "AQ934580H6222")
        self.fixture.then_value_should_equal({})
        self.fixture.then_delete_asin_from_redis("B08F2QH222")

    def test_listings_data_for_seller_is_deleted_from_redis(self):
        """
        Test to ensure that listing data for a specific seller is deleted from Redis.
        """
        self.fixture.given_an_payload(redis_listing_data_of_asin_and_seller)
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.then_delete_seller_listings("B08F2QHJTR", "AQ934580H1234")
        self.fixture.then_verify_listing_data_sku_value("B08F2QHJTR", "AQ934580H1234")
        self.fixture.then_value_should_be_none()
        self.fixture.then_delete_asin_from_redis("B08F2QHJT")

    def test_listings_data_for_multiple_seller_is_deleted_from_redis(self):
        """
        Test to ensure that listing data for multiple sellers is properly handled.
        """
        self.fixture.given_an_payload(redis_listing_data_of_asin)
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.then_delete_seller_listings("B08F2QH111", "AQ934580H1235")
        self.fixture.then_verify_listing_data_sku_value("B08F2QH111", "AQ934580H1235")
        self.fixture.then_value_should_be_none()
        self.fixture.then_delete_asin_from_redis("B08F2QH111")

    def test_seller_is_removed_from_asin_listings(self):
        """
        Test to ensure that a seller is completely removed from ASIN listings.
        """
        self.fixture.given_an_payload(redis_listing_data_of_asin)
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.then_delete_seller_from_asins("AQ934580H1235")
        self.fixture.then_verify_listing_data_sku_value("B08F2QH111", "AQ934580H1235")
        self.fixture.then_value_should_be_none()
        self.fixture.then_delete_asin_from_redis("B08F2QH111")

    def test_account_data_is_deleted_from_redis(self):
        """
        Test to ensure that account data is properly deleted from Redis.
        """
        self.fixture.given_an_payload(redis_data_of_account)
        self.fixture.set_account_data_in_redis()
        self.fixture.then_delete_account_data_from_redis("AQ934580H1236")
        self.fixture.then_verify_redis_key_value("account.AQ934580H1236")
        self.fixture.then_value_should_equal({})

    def test_check_processing_of_updated_in_redis_data(self):
        """
        Test to check processing of Redis data with old updated_at timestamps.
        """
        self.fixture.given_an_payload(redis_listing_data_to_process_updated_at_with_old_date)
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.then_process_redis_data("process_key_for_updated_at", [])
        self.fixture.then_verify_listing_data_sku_value("B08F2QH123", "AQ934580H1237")
        self.fixture.then_value_should_be_none()
        self.fixture.then_delete_asin_from_redis("B08F2QH123")

    def test_check_processing_of_updated_in_redis_data_with_current_date(self):
        """
        Test to check processing of Redis data with current updated_at timestamps.
        """
        self.fixture.given_an_payload(redis_listing_data_to_process_updated_at_with_current_date)
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.then_process_redis_data("process_key_for_updated_at", [])
        self.fixture.then_verify_listing_data_sku_value("B08F2QH234", "AQ934580H1238")
        self.fixture.then_value_should_not_be_none()
        self.fixture.then_delete_asin_from_redis("B08F2QH234")

    def test_check_processing_of_listed_price_for_price_reset_with_max_price_not_exist(
        self,
    ):
        """
        Test to check processing of listed price for price reset when max price doesn't exist.
        """
        self.fixture.given_an_payload(
            redis_listing_data_listed_price_for_price_reset_with_only_min_price
        )
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.set_account_data_in_redis()
        self.fixture.then_process_redis_data(
            "process_key_for_listed_price",
            ["AQ934580H1234567"],
            "trigger_price_reset_time",
        )
        self.fixture.then_verify_listing_data_sku_value(
            "B08F2QH120", "AQ934580H1234567_test"
        )
        self.fixture.then_value_should_equal(23.175)
        self.fixture.then_delete_asin_from_redis("B08F2QH120")
        self.fixture.then_delete_account_data_from_redis("AQ934580H1234567")

    def test_check_processing_of_listed_price_for_price_reset_with_max_price_exist(
        self,
    ):
        """
        Test to check processing of listed price for price reset when max price exists.
        """
        self.fixture.given_an_payload(
            redis_listing_data_listed_price_for_price_reset_with_max_price
        )
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.set_account_data_in_redis()
        self.fixture.then_process_redis_data(
            "process_key_for_listed_price",
            ["AQ934580H123456"],
            "trigger_price_reset_time",
        )
        self.fixture.then_verify_listing_data_sku_value(
            "B08F2QH120", "AQ934580H123456_test"
        )
        self.fixture.then_value_should_equal(25.99)
        self.fixture.then_delete_asin_from_redis("B08F2QH120")
        self.fixture.then_delete_account_data_from_redis("AQ934580H123456")

    def test_check_processing_of_listed_price_for_price_reset_with_max_price_and_min_price_not_exist(
        self,
    ):
        """
        Test to check processing of listed price for price reset when both max and min prices don't exist.
        """
        self.fixture.given_an_payload(redis_listing_data_listed_price_for_price_reset)
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.set_account_data_in_redis()
        self.fixture.then_process_redis_data(
            "process_key_for_listed_price",
            ["AQ934580H123456"],
            "trigger_price_reset_time",
        )
        self.fixture.then_verify_listing_data_sku_value(
            "B08F2QH120", "AQ934580H123456_test"
        )
        self.fixture.then_value_should_equal(25.99)
        self.fixture.then_delete_asin_from_redis("B08F2QH120")
        self.fixture.then_delete_account_data_from_redis("AQ934580H123456")

    def test_check_processing_of_listed_price_for_price_reset_with_no_listed_price(
        self,
    ):
        """
        Test to check the processing of listed price for price reset when no listed price is available.
        """
        self.fixture.given_an_payload(
            redis_listing_data_listed_price_for_price_reset_with_no_listed_price
        )
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.set_account_data_in_redis()
        self.fixture.then_process_redis_data(
            "process_key_for_listed_price",
            ["AQ934580H123489"],
            "trigger_price_reset_time",
        )
        self.fixture.then_verify_listing_data_sku_value(
            "B08F2QH121", "AQ934580H123489_test"
        )
        self.fixture.then_value_should_equal(None)
        self.fixture.then_delete_asin_from_redis("B08F2QH121")
        self.fixture.then_delete_account_data_from_redis("AQ934580H123489")

    def test_check_processing_of_price_resume(self):
        """
        Test to check the processing of listed price for triggering price resume time.
        """
        self.fixture.given_an_payload(redis_listing_data_listed_price_for_price_resume)
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.set_account_data_in_redis()
        self.fixture.then_process_redis_data(
            "process_key_for_listed_price",
            ["AQ934580H123888"],
            "trigger_price_resume_time",
        )
        self.fixture.then_verify_listing_data_sku_value("B08F2QH122", "AQ934580H123888")
        self.fixture.then_value_should_equal(
            {
                "I8-4V38-BY39": {
                    "strategy_id": "2",
                    "fullfilment_type": "AMAZON",
                    "item_condition": "NewItem",
                    "inventory_quantity": 3,
                    "listed_price": 15.5,
                    "inventory_age": 0,
                    "status": "Active",
                    "updated_at": "2023-10-23T07:52:13.680028",
                    "repricer_enabled": True,
                }
            }
        )
        self.fixture.then_delete_asin_from_redis("B08F2QH122")
        self.fixture.then_delete_account_data_from_redis("AQ934580H123888")

    def test_check_processing_of_check_price_range_lp_less_then_min_price(self):
        """
        Test to check price range processing when listed price is less than minimum price.
        """
        self.fixture.given_an_payload(
            redis_listing_data_listed_price_for_check_price_range_lp_less_than_min
        )
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.set_account_data_in_redis()
        self.fixture.then_process_redis_data(
            "process_key_for_listed_price",
            ["AQ934580H123999"],
            "check_price_in_range",
        )
        self.fixture.then_verify_listing_data_sku_value(
            "B08F2QH123", "AQ934580H123999_test"
        )
        expected_message = "Standard Listing Data \n Asin: B08F2QH123  \n Seller: AQ934580H123999  \n Sku:I8-4V38-BY39  \n Listed Price (15.5) is less than Min Price (20.45)  \n"
        self.fixture.then_value_should_equal(expected_message)
        self.fixture.then_delete_asin_from_redis("B08F2QH123")
        self.fixture.then_delete_account_data_from_redis("AQ934580H123999")

    def test_check_processing_of_check_price_range_lp_greater_then_max_price(self):
        """
        Test to check price range processing when listed price is greater than maximum price.
        """
        self.fixture.given_an_payload(
            redis_listing_data_listed_price_for_check_price_range_lp_greater_than_max
        )
        self.fixture.when_listing_data_set_in_redis()
        self.fixture.set_account_data_in_redis()
        self.fixture.then_process_redis_data(
            "process_key_for_listed_price",
            ["AQ934580H123000"],
            "check_price_in_range",
        )
        self.fixture.then_verify_listing_data_sku_value(
            "B08F2QH124", "AQ934580H123000_test"
        )
        expected_message = "Standard Listing Data \n Asin: B08F2QH124  \n Seller: AQ934580H123000  \n Sku:I8-4V38-BY39  \n Listed Price (30.5) is greater than Max Price (25.99)  \n"
        self.fixture.then_value_should_equal(expected_message)
        self.fixture.then_delete_asin_from_redis("B08F2QH124")
        self.fixture.then_delete_account_data_from_redis("AQ934580H123000")

    def test_delete_asins_from_payload(self):
        """
        Test to ensure ASINs are properly deleted from payload.
        """
        redis_client.hset("ASIN_PAYLOADS", "B08F2QH456", "test_payload")
        self.fixture.when_delete_asins_from_payloads()
        self.fixture.then_total_asins_payloads_will_be(0)

    def test_current_hour_outside_of_interval(self):
        """
        Test to check if current hour is outside of a given interval.
        """
        price_reset_service = PriceResetService()
        self.fixture.when_is_outside_interval_called(10, 14, 18)
        self.fixture.then_value_should_equal(True)

    def test_current_hour_inside_of_interval(self):
        """
        Test to check if current hour is inside of a given interval.
        """
        price_reset_service = PriceResetService()
        self.fixture.when_is_outside_interval_called(16, 14, 18)
        self.fixture.then_value_should_equal(False)

    def test_current_hour_equals_start_of_interval(self):
        """
        Test to check if current hour equals the start of the interval.
        """
        price_reset_service = PriceResetService()
        self.fixture.when_is_outside_interval_called(14, 14, 18)
        self.fixture.then_value_should_equal(False)

    def test_current_hour_equals_end_of_interval(self):
        """
        Test to check if current hour equals the end of the interval.
        """
        price_reset_service = PriceResetService()
        self.fixture.when_is_outside_interval_called(18, 14, 18)
        self.fixture.then_value_should_equal(False)

    def test_current_hour_before_midnight_outside_of_interval(self):
        """
        Test to check current hour before midnight outside of interval.
        """
        price_reset_service = PriceResetService()
        self.fixture.when_is_outside_interval_called(23, 22, 2)
        self.fixture.then_value_should_equal(False)

    def test_current_hour_after_midnight_outside_of_interval(self):
        """
        Test to check current hour after midnight outside of interval.
        """
        price_reset_service = PriceResetService()
        self.fixture.when_is_outside_interval_called(1, 22, 2)
        self.fixture.then_value_should_equal(False)

    def test_current_hour_outside_of_interval_wrapping_midnight(self):
        """
        Test to check current hour outside of interval wrapping around midnight.
        """
        price_reset_service = PriceResetService()
        self.fixture.when_is_outside_interval_called(12, 22, 2)
        self.fixture.then_value_should_equal(True)

    def test_interval_is_full_day(self):
        """
        Test to check behavior when interval spans a full day.
        """
        price_reset_service = PriceResetService()
        self.fixture.when_is_outside_interval_called(12, 0, 23)
        self.fixture.then_value_should_equal(False)

    def test_strategy_data_is_deleted_from_redis(self):
        """
        Test to ensure that strategy data is properly deleted from Redis.
        """
        self.fixture.given_an_payload(redis_strategy_data)
        self.fixture.set_strategy_data_in_redis()
        strategy_data_for_delete = [{"strategy_id": "1"}]
        self.fixture.then_delete_strategy_from_redis(strategy_data_for_delete)
        self.fixture.then_verify_redis_key_value("strategy.1")
        self.fixture.then_value_should_equal({})

    class _Fixture(Fixture):

        def given_an_event(self, event):
            self.event = event

        def given_an_payload(self, payload):
            self.payload = payload

        def when_received_credentials(self):
            pass

        def when_is_outside_interval_called(
            self, current_hour, reset_time_hour, resume_time_hour
        ):
            price_reset_service = PriceResetService()
            self.value = price_reset_service.is_outside_interval(
                current_hour, reset_time_hour, resume_time_hour
            )

        def when_listing_data_set_in_redis(self):
            messages = self.payload

            for message in messages:
                key = message.get("asin")
                field = message.get("seller_id")
                data = message.get("data")
                redis_client.hset(key, field, data)

        def set_account_data_in_redis(self):
            messages = self.payload

            for message in messages:
                seller_id = message.get("seller_id")
                key = f"account.{seller_id}"

                field_values = {
                    "refresh_token": message.get("refresh_token"),
                    "marketplace_type": message.get("marketplace_type"),
                    "user_id": message.get("user_id"),
                }
                for field, value in field_values.items():
                    redis_client.hset(key, field, value)

        def set_strategy_data_in_redis(self):
            messages = self.payload

            for message in messages:
                strategy_id = message.get("strategy_id")
                key = f"strategy.{strategy_id}"
                field = "compete_with"
                value = message.get("compete_with")
                redis_client.hset(key, field, value)

        def then_delete_strategy_from_redis(self, strategy_data):
            handle_delete_message(strategy_data)

        def then_update_or_create_user_account(self):
            update_or_create_user_account(self.event)

        def then_delete_listing_data(self, asin, seller, sku):
            redis_service = RedisService()
            redis_service.delete_sku_details(asin, seller, sku)

        def then_delete_seller_listings(self, asin, seller):
            redis_service = RedisService()
            redis_service.delete_seller(asin, seller)

        def then_delete_seller_from_asins(self, seller):
            redis_service = RedisService()
            redis_service.delete_seller_from_asins(seller)

        def when_delete_asins_from_payloads(self):
            redis_service = RedisService()
            redis_service.delete_asins_payloads()
            self.value = len(redis_client.hkeys("ASIN_PAYLOADS"))

        def then_delete_account_data_from_redis(self, seller):
            from project.ah_authentication.services.user_account_service import UserAccountService
            user_service = UserAccountService()
            user_service.delete_account_from_redis(seller)

        def then_verify_listing_data_sku_value(self, key, field):
            self.value = redis_client.hget(key, field)

        def then_verify_redis_key_value(self, key):
            self.value = redis_client.hgetall(key)

        def then_process_redis_data(
            self, task_name, accounts, utility_function_name="check_price_in_range"
        ):
            redis_service = RedisService()
            redis_service.process_redis_data(task_name, accounts, utility_function_name)

        def then_value_should_equal(self, expected_value):
            self.assertEqual(self.value, expected_value)

        def then_value_should_be_none(self):
            self.assertIsNone(self.value)

        def then_value_should_not_be_none(self):
            self.assertIsNotNone(self.value)

        def then_total_asins_payloads_will_be(self, expected_value):
            self.assertEqual(self.value, expected_value)

        def then_delete_asin_from_redis(self, prefix):
            keys_to_delete = redis_client.match_pattern(f"{prefix}*")
            for key in keys_to_delete:
                redis_client.delete_key(key)


if __name__ == "__main__":
    unittest.main()