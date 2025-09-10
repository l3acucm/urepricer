import sys, os, json, unittest
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)
from test_data import *
from dotenv import load_dotenv
import os ,unittest, json, redis
from helpers.data_to_redis import SetData
from helpers.utils import split_data_into_lists,append_repricer_service_key

load_dotenv()

class Fixture(unittest.TestCase):
  pass

class TestStrategies(unittest.TestCase):
  def setUp(self):
    self.fixture = self._Fixture()

  def test_inventory_age_is_missing_01(self):
    """
    This test case is designed to check if "inventory_age" key does not exist in payload
    then it will keep inventory_age in redis with value 0.
    """
    self.fixture.given_an_event(inventory_age_is_missing_01)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_expected_value('inventory_age')
    self.fixture.then_redis_comparison_values_should_be((True, True, True))
    self.fixture.then_remove_asin_seller_from_redis()
  
  def test_status_is_missing_02(self):
    """
    This test case is designed to check if "status" key does not exist in payload
    then it will keep status in redis with value Active.
    """
    self.fixture.given_an_event(status_is_missing_02)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_expected_value('status')
    self.fixture.then_redis_comparison_values_should_be((True, True, True))
    self.fixture.then_remove_asin_seller_from_redis()
  
  def test_inventory_quantity_is_missing_03(self):
    """
    This test case is designed to check if "status" key does not exist in payload
    then it will keep status in redis.
    """
    self.fixture.given_an_event(inventory_qunatity_is_missing_03)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_expected_value('inventory_quantity')
    self.fixture.then_redis_comparison_values_should_be((True, True, True))
    self.fixture.then_remove_asin_seller_from_redis()

  def test_item_condition_is_missing_04(self):
    """
    This test case is designed to check if "item_condition" key does not exist in payload
    then it will keep status in redis with the value new.
    """
    self.fixture.given_an_event(item_condition_is_missing_04)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_expected_value('item_condition')
    self.fixture.then_redis_comparison_values_should_be((True, True, True))
    self.fixture.then_remove_asin_seller_from_redis()
  
  def test_replace_min_with_min_price_05(self):
    """
    This test case is designed to check if "min" key exist in payload
    then it will replace it with min_price.
    """
    self.fixture.given_an_event(replace_min_with_min_price_05)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_expected_value('min')
    self.fixture.then_redis_comparison_values_should_be((False, True, True))
    self.fixture.then_remove_asin_seller_from_redis()
  

  def test_replace_max_with_max_price_06(self):
    """
    This test case is designed to check if "max" key exist in payload
    then it will replace it with max_price.
    """
    self.fixture.given_an_event(replace_max_with_max_price_06)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_expected_value('max')
    self.fixture.then_redis_comparison_values_should_be((False, True, True))
    self.fixture.then_remove_asin_seller_from_redis()
  
  def test_convert_default_price_to_float_07(self):
    """
    This test case is designed to check if "default_price" key exist in payload
    then it will convert it into float data-type.
    """
    self.fixture.given_an_event(convert_default_price_to_float_07)
    self.fixture.when_given_a_payload()
    self.fixture.check_single_float_value('default_price')
    self.fixture.then_redis_comparison_values_should_be((True, True, True))
    self.fixture.then_remove_asin_seller_from_redis()
  
  def test_convert_listed_price_to_float_08(self):
    """
    This test case is designed to check if "listed_price" key exist in payload
    then it will convert it into float data-type.
    """
    self.fixture.given_an_event(convert_listed_price_to_float_08)
    self.fixture.when_given_a_payload()
    self.fixture.check_single_float_value('default_price')
    self.fixture.then_redis_comparison_values_should_be((True, True, True))
    self.fixture.then_remove_asin_seller_from_redis()
  
  def test_min_not_present_in_payload_09(self):
    """
    This test case is designed to check if "min" key does not exist in payload
    then it will not set in redis too.
    """
    self.fixture.given_an_event(min_not_present_in_payload_09)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_expected_value('min_price')
    self.fixture.then_redis_comparison_values_should_be((False, True, True))
    self.fixture.then_remove_asin_seller_from_redis()
  
  def test_max_not_present_in_payload_10(self):
    """
    This test case is designed to check if "max" key does not exist in payload
    then it will not set in redis too.
    """
    self.fixture.given_an_event(max_not_present_in_payload_10)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_expected_value('max_price')
    self.fixture.then_redis_comparison_values_should_be((False, True, True))
    self.fixture.then_remove_asin_seller_from_redis()

  def test_default_price_not_in_range_11(self):
    """
    This test case is designed to check whether the errors sent to the user
    are in chunks less than 10MB
    """
    self.fixture.given_an_event(error_notifications)
    self.fixture.when_data_is_split_between_lists()
    self.fixture.then_each_notification_should_have_size(MESSAGE_SIZE)

  def test_repricer_enabled_is_missing_12(self):
    """
    This test case is designed to check whether repricer_enabled key
    is added when it is missing from the payload and has a True value
    """
    self.fixture.given_an_event(repricer_enabled_is_missing_12)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_repricer_enabled_value()
    self.fixture.then_repricer_enabled_value_is(True)
    self.fixture.then_remove_asin_seller_from_redis()

  def test_repricer_enabled_has_correct_value_13(self):
    """
    This test case is designed to check whether the correct value of
    repricer_enabled key is added when we pass in the payload
    """
    self.fixture.given_an_event(repricer_enabled_correct_value_13)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_repricer_enabled_value()
    self.fixture.then_repricer_enabled_value_is(False)
    self.fixture.then_remove_asin_seller_from_redis()

  def test_repricer_enabled_old_value_is_stored_14(self):
    """
    This test case is designed to check whether the correct value of
    repricer_enabled key is added when we pass in the payload
    """
    self.fixture.given_an_event(repricer_enabled_old_value_is_stored_14)
    self.fixture.when_given_a_payload()
    self.fixture.given_an_event(repricer_enabled_new_value_is_stored_15)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_repricer_enabled_value()
    self.fixture.then_repricer_enabled_value_is(False)
    self.fixture.then_remove_asin_seller_from_redis()

  def test_repricer_enabled_old_value_is_stored_15(self):
    """
    This test case is designed to check whether the correct value of
    repricer_enabled key is added when we pass in the payload
    """
    self.fixture.given_an_event(repricer_enabled_old_value_is_stored_16)
    self.fixture.when_given_a_payload()
    self.fixture.given_an_event(repricer_enabled_new_value_is_stored_17)
    self.fixture.when_given_a_payload()
    self.fixture.when_extract_repricer_enabled_value()
    self.fixture.then_repricer_enabled_value_is(True)
    self.fixture.then_remove_asin_seller_from_redis()

  class _Fixture(Fixture):

    def given_an_event(self, event):
      self.event = event

    def when_given_a_payload(self):
      message = self.event
      message_item = next(item for item in message)
      self.asin = next(asin for asin in message_item.keys())
      self.seller = next(seller for seller in message_item[self.asin].keys())
      SetData().set_data_in_redis(message)
      self.redis_data = self.get_redis_values(self.asin , self.seller)
      self.price_type = self.check_float_values(self.redis_data)
      self.redis_value_keys = self.check_keys_present_or_not(self.redis_data)
    
    def when_extract_expected_value(self, key):
      self.expected_value = any(key in subdict for subdict in self.redis_data.values())

    def when_extract_repricer_enabled_value(self):
      listed_data = self.get_redis_values(self.asin,self.seller)
      self.actual_value = next(asin for asin in listed_data.values()).get("repricer_enabled")
    
    def then_each_notification_should_have_size(self,expected_value):
      for notification in self.notification:
        self.assertLessEqual(sys.getsizeof(notification['data'])/1024 ,expected_value)

    def _split_data_between_lists(self, notifications):
      lists_in_chunks = split_data_into_lists(notifications["data"],9000)
      all_notifications = []
      for message in lists_in_chunks:
        error_notification = append_repricer_service_key(message)
        all_notifications.append(error_notification)
      self.notification = all_notifications

    def when_data_is_split_between_lists(self):
       self._split_data_between_lists(self.event)
    
    def then_repricer_enabled_value_is(self,expected_value):
      self.assertEqual(self.actual_value,expected_value)

    def then_redis_comparison_values_should_be(self, expected_value):
      self.assertEqual((self.expected_value, self.price_type, self.redis_value_keys),expected_value )

    def get_redis_values(self, asin , seller):
      return self.get_value_from_redis(asin , seller)
   
    def check_float_values(self, redis_data):
      price_type = all(isinstance(redis_data.get(key), float) for key in ['min_price', 'max_price', 'default_price', 'listed_price'] if key in redis_data)
      return price_type
    
    def check_single_float_value(self, key):
      self.expected_value = all(isinstance(value, float) for value in self.redis_data.get(key, {}).values())

    def check_keys_present_or_not(self, redis_data):
      keys_to_check = ['status', 'item_condition', 'inventory_quantity', 'inventory_age', 'repricer_enabled']
      redis_data = all(key in redis_data or any(key in subdict for subdict in redis_data.values()) for key in keys_to_check)
      return redis_data

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
    

    def then_remove_asin_seller_from_redis(self):
      """
      Picks ASIN and Seller ID from the event data and deletes corresponding data from Redis.
      """
      asin = list(self.event[0].keys())[0]
      sellerid = list(self.event[0][asin].keys())[0]
      self.delete_redis_data(asin)
      self.delete_redis_data(f"account.{sellerid}")
    
    def delete_redis_data(self, key_name):
      """
        Deletes data from Redis based on the provided key.

        Args:
        - key_name (str): The key to identify the data in Redis.
      """
      redis_client = SetData()

      redis_client.delete_key(key_name)

if __name__ == '__main__':
    unittest.main()
