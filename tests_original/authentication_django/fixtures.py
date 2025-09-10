"""Test fixtures and mock data for integration tests."""

from datetime import datetime

user_credentials_data_with_missing_key = {
    "user_id": "Test1433",
    "seller_id": "TestA25M6ZYMJHWYLU",
    "refresh_token": "Test123",
    "marketplace_type": "UK",
}


redis_listing_data_of_sku = [
    {
        "asin": "B08F2QH222",
        "seller_id": "AQ934580H6222",
        "data": {
            "I8-4V38-B222": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "listed_price": 15.45,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
            }
        },
    }
]
redis_listing_data_of_asin_and_seller = [
    {
        "asin": "B08F2QHJTR",
        "seller_id": "AQ934580H1234",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "listed_price": 15.45,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
            }
        },
    },
    {
        "asin": "B08F2QHJT1",
        "seller_id": "AQ934580H6666",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "listed_price": 15.45,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
            }
        },
    },
]
redis_listing_data_of_asin = [
    {
        "asin": "B08F2QH111",
        "seller_id": "AQ934580H1235",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "listed_price": 15.45,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
            }
        },
    },
    {
        "asin": "B08F2QH111",
        "seller_id": "AQ934580H1235",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "listed_price": 15.45,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
            }
        },
    },
]

redis_data_of_account = [
    {
        "seller_id": "AQ934580H1236",
        "marketplace_type": "UK",
        "refresh_token": "ABCD",
        "user_id": 1234,
    }
]

redis_listing_data_to_process_updated_at_with_old_date = [
    {
        "asin": "B08F2QH123",
        "seller_id": "AQ934580H1237",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "listed_price": 15.45,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
            }
        },
    }
]
redis_listing_data_to_process_updated_at_with_current_date = [
    {
        "asin": "B08F2QH234",
        "seller_id": "AQ934580H1238",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "listed_price": 15.45,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
            }
        },
    }
]

redis_listing_data_listed_price_for_price_reset = [
    {
        "asin": "B08F2QH120",
        "seller_id": "AQ934580H123456",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "max_price": 25.99,
                "listed_price": 15.5,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
                "repricer_enabled": True,
            }
        },
    }
]

redis_listing_data_listed_price_for_price_reset_with_max_price = [
    {
        "asin": "B08F2QH120",
        "seller_id": "AQ934580H123456",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "max_price": 25.99,
                "listed_price": 15.5,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
                "repricer_enabled": True,
            }
        },
    }
]

redis_listing_data_listed_price_for_price_reset_with_only_min_price = [
    {
        "asin": "B08F2QH120",
        "seller_id": "AQ934580H1234567",
        "refresh_token": "test_refresh_token",
        "marketplace_type": "US",
        "user_id": "test_user_1234567",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "listed_price": 15.5,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
                "repricer_enabled": True,
            }
        },
    }
]

redis_listing_data_listed_price_for_price_reset_with_no_listed_price = [
    {
        "asin": "B08F2QH121",
        "seller_id": "AQ934580H123489",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 15.45,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
                "repricer_enabled": True,
            }
        },
    }
]

redis_listing_data_listed_price_for_price_resume = [
    {
        "asin": "B08F2QH122",
        "seller_id": "AQ934580H123888",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "listed_price": 15.5,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
                "repricer_enabled": False,
            }
        },
    }
]

redis_listing_data_listed_price_for_check_price_range_lp_less_than_min = [
    {
        "asin": "B08F2QH123",
        "seller_id": "AQ934580H123999",
        "refresh_token": "test_refresh_token",
        "marketplace_type": "US",
        "user_id": "test_user_123999",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 20.45,
                "max_price": 25.99,
                "listed_price": 15.5,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
                "repricer_enabled": True,
            }
        },
    }
]

redis_listing_data_listed_price_for_check_price_range_lp_greater_than_max = [
    {
        "asin": "B08F2QH124",
        "seller_id": "AQ934580H123000",
        "refresh_token": "test_refresh_token",
        "marketplace_type": "US",
        "user_id": "test_user_123000",
        "data": {
            "I8-4V38-BY39": {
                "strategy_id": "2",
                "fullfilment_type": "AMAZON",
                "item_condition": "NewItem",
                "inventory_quantity": 3,
                "min_price": 20.45,
                "max_price": 25.99,
                "listed_price": 30.5,
                "inventory_age": 0,
                "status": "Active",
                "updated_at": "2023-10-23T07:52:13.680028",
                "repricer_enabled": True,
            }
        },
    }
]

redis_strategy_data = [
    {
        "strategy_id": "1",
        "compete_with": '["BuyBox", "LowestPrice"]',
    }
]