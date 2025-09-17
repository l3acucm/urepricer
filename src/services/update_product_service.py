import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from distutils.util import strtobool

from ..models.product import Product
from typing import Any as LogEntry  # LogEntry type placeholder - needs proper definition
from ..core.config import get_settings


settings = get_settings()


class AmazonProductPrice:
    def __init__(self):
        self.debug = getattr(settings, 'debug', False)

    def call(self, product: Product, testing: bool = False) -> None:
        sku = product.sku
        redis_list = f"{product.account.seller_id}_repriced_products"
        data_hash = {
            "asin": product.asin,
            "sku": product.sku,
            "seller_id": product.account.seller_id
        }

        # Standard product data only (B2B support removed)
        data_hash['Standard'] = self._get_dataclass_attrs(product, self._get_amazon_output_list())
        log_entry = self._get_dataclass_attrs(product, self._get_amazon_logs())
        log_entry['quantity'] = 1
        log_entry['product_type'] = 'Standard'
        log_entry['time'] = datetime.now()

        if not self.debug:
            self._save_data_in_redis(redis_list, sku, data_hash)
        else:
            self._send_repricer_output_notification(log_entry)

        print(f"Repriced data: {data_hash}")

    def _get_dataclass_attrs(self, product: Product, output_list: list) -> Dict[str, Any]:
        data_hash = {}
        for data in output_list:
            try:
                data_hash[data] = getattr(product, data)
            except AttributeError:
                data_hash[data] = None
        return data_hash


    def _save_log_entry(self, log_entry: LogEntry) -> None:
        print(f"Saving log entry: {log_entry}")

    def _save_data_in_redis(self, redis_list: str, sku: str, data: Dict[str, Any]) -> None:
        # TODO: Implement Redis cache functionality
        print(f"Would save to Redis: {redis_list}, {sku}, {data}")

    def _send_repricer_output_notification(self, log_entry: Dict[str, Any]) -> None:
        # TODO: Implement notification functionality
        print(f"Would send notification: {log_entry}")

    def _get_amazon_output_list(self) -> list:
        # TODO: Move these constants to a proper location
        return ['asin', 'sku', 'seller_id', 'updated_price', 'listed_price']

    def _get_amazon_logs(self) -> list:
        return ['asin', 'sku', 'seller_id', 'updated_price', 'listed_price', 'time']


