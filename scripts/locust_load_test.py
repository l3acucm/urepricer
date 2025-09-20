#!/usr/bin/env python3
"""
Load testing script for urepricer using Locust.

Tests the system's ability to handle high volumes of price change notifications
from Amazon and Walmart platforms.
"""

import json
import random
import string
from datetime import UTC, datetime
from typing import Any, Dict

from locust import HttpUser, between, task


class AmazonNotificationUser(HttpUser):
    """Simulates Amazon price change notifications via SQS message format."""
    
    wait_time = between(0.1, 0.5)  # Wait 0.1 to 0.5 seconds between requests
    
    def on_start(self):
        """Initialize test data."""
        self.test_asins = [f"B{''.join(random.choices(string.ascii_uppercase + string.digits, k=9))}" for _ in range(100)]
        self.test_seller_ids = [f"A{''.join(random.choices(string.ascii_uppercase + string.digits, k=13))}" for _ in range(50)]
        self.marketplaces = ["US", "UK", "CA", "AU"]
    
    def generate_amazon_sqs_message(self) -> Dict[str, Any]:
        """Generate realistic Amazon SQS message."""
        asin = random.choice(self.test_asins)
        seller_id = random.choice(self.test_seller_ids)
        marketplace = random.choice(self.marketplaces)
        
        # Generate offer data
        num_offers = random.randint(1, 5)
        offers = []
        
        for i in range(num_offers):
            offer = {
                "SellerId": random.choice(self.test_seller_ids),
                "SubCondition": "New",
                "ShippingTime": {
                    "MaximumHours": random.randint(24, 168),
                    "MinimumHours": random.randint(12, 24),
                    "AvailableDate": None,
                    "AvailabilityType": "NOW"
                },
                "ListingPrice": {
                    "Amount": round(random.uniform(10.0, 200.0), 2),
                    "CurrencyCode": "USD"
                },
                "Shipping": {
                    "Amount": round(random.uniform(0.0, 15.99), 2),
                    "CurrencyCode": "USD"
                },
                "ShipsDomestically": True,
                "IsFulfilledByAmazon": random.choice([True, False]),
                "IsBuyBoxWinner": i == 0,  # First offer is buybox winner
                "PrimeInformation": {
                    "IsPrime": random.choice([True, False]),
                    "IsNationalPrime": random.choice([True, False])
                }
            }
            offers.append(offer)
        
        return {
            "NotificationType": "AnyOfferChanged",
            "PayloadVersion": "1.0",
            "EventTime": datetime.now(UTC).isoformat(),
            "Payload": {
                "AnyOfferChangedNotification": {
                    "SellerId": seller_id,
                    "MarketplaceId": {
                        "US": "ATVPDKIKX0DER",
                        "UK": "A1F83G8C2ARO7P",
                        "CA": "A2EUQ1WTGCTBG2",
                        "AU": "A39IBJ37TRP1C6"
                    }[marketplace],
                    "ASIN": asin,
                    "ItemCondition": "New",
                    "TimeOfOfferChange": datetime.now(UTC).isoformat(),
                    "OfferChangeTrigger": {
                        "MarketplaceId": marketplace,
                        "ASIN": asin,
                        "ItemCondition": "New",
                        "TimeOfOfferChange": datetime.now(UTC).isoformat()
                    },
                    "Summary": {
                        "NumberOfOffers": [
                            {
                                "Condition": "New",
                                "FulfillmentChannel": "Merchant",
                                "OfferCount": len([o for o in offers if not o["IsFulfilledByAmazon"]])
                            },
                            {
                                "Condition": "New", 
                                "FulfillmentChannel": "Amazon",
                                "OfferCount": len([o for o in offers if o["IsFulfilledByAmazon"]])
                            }
                        ],
                        "BuyBoxPrices": [
                            {
                                "Condition": "New",
                                "FulfillmentChannel": "Merchant",
                                "ListingPrice": {
                                    "Amount": offers[0]["ListingPrice"]["Amount"],
                                    "CurrencyCode": "USD"
                                },
                                "Shipping": offers[0]["Shipping"]
                            }
                        ],
                        "LowestPrices": [
                            {
                                "Condition": "New",
                                "FulfillmentChannel": "Merchant",
                                "ListingPrice": {
                                    "Amount": min(o["ListingPrice"]["Amount"] for o in offers),
                                    "CurrencyCode": "USD"
                                },
                                "Shipping": {
                                    "Amount": 0.0,
                                    "CurrencyCode": "USD"
                                }
                            }
                        ]
                    },
                    "Offers": offers
                }
            }
        }
    
    @task(3)
    def post_amazon_sqs_message(self):
        """Send Amazon SQS message format to repricing endpoint."""
        message = self.generate_amazon_sqs_message()
        
        # Wrap in SQS message format
        sqs_message = {
            "MessageId": f"msg-{random.randint(100000, 999999)}",
            "ReceiptHandle": f"receipt-{random.randint(100000, 999999)}",
            "Body": json.dumps(message),
            "Attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": str(int(datetime.now(UTC).timestamp() * 1000)),
                "ApproximateFirstReceiveTimestamp": str(int(datetime.now(UTC).timestamp() * 1000))
            }
        }
        
        response = self.client.post(
            "/amazon/sqs-webhook",
            json=sqs_message,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code not in [200, 202]:
            response.failure(f"Amazon SQS message failed: {response.status_code}")


class WalmartNotificationUser(HttpUser):
    """Simulates Walmart webhook notifications."""
    
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        """Initialize test data."""
        self.test_item_ids = [f"WM{random.randint(100000000, 999999999)}" for _ in range(100)]
        self.test_seller_ids = [f"WM{random.randint(10000000, 99999999)}" for _ in range(50)]
    
    def generate_walmart_webhook(self) -> Dict[str, Any]:
        """Generate realistic Walmart webhook."""
        item_id = random.choice(self.test_item_ids)
        seller_id = random.choice(self.test_seller_ids)
        
        # Generate competitor offers
        num_offers = random.randint(1, 4)
        offers = []
        
        for i in range(num_offers):
            offers.append({
                "sellerId": random.choice(self.test_seller_ids),
                "price": round(random.uniform(15.0, 150.0), 2),
                "shipping": round(random.uniform(0.0, 12.99), 2),
                "condition": "New",
                "availabilityStatus": "AVAILABLE",
                "fulfillmentLagTime": random.randint(1, 7)
            })
        
        return {
            "eventType": "buybox_changed",
            "itemId": item_id,
            "sellerId": seller_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "marketplace": "US",
            "changeDetails": {
                "previousBuyboxPrice": round(random.uniform(20.0, 100.0), 2),
                "currentBuyboxPrice": round(random.uniform(18.0, 95.0), 2),
                "priceChangePercent": round(random.uniform(-15.0, 15.0), 2)
            },
            "offers": offers,
            "competitorAnalysis": {
                "totalCompetitors": len(offers),
                "lowestPrice": min(o["price"] for o in offers),
                "averagePrice": round(sum(o["price"] for o in offers) / len(offers), 2),
                "priceSpread": max(o["price"] for o in offers) - min(o["price"] for o in offers)
            }
        }
    
    @task(2)
    def post_walmart_webhook(self):
        """Send Walmart webhook to repricing endpoint."""
        webhook_data = self.generate_walmart_webhook()
        
        response = self.client.post(
            "/walmart/webhook",
            json=webhook_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code not in [200, 202]:
            response.failure(f"Walmart webhook failed: {response.status_code}")


class MixedPlatformUser(HttpUser):
    """Simulates mixed traffic from both Amazon and Walmart."""
    
    wait_time = between(0.05, 0.2)  # Faster requests for mixed load
    
    def on_start(self):
        """Initialize for both platforms."""
        # Amazon data
        self.amazon_asins = [f"B{''.join(random.choices(string.ascii_uppercase + string.digits, k=9))}" for _ in range(50)]
        self.amazon_sellers = [f"A{''.join(random.choices(string.ascii_uppercase + string.digits, k=13))}" for _ in range(25)]
        
        # Walmart data  
        self.walmart_items = [f"WM{random.randint(100000000, 999999999)}" for _ in range(50)]
        self.walmart_sellers = [f"WM{random.randint(10000000, 99999999)}" for _ in range(25)]
    
    @task(1)
    def health_check(self):
        """Check system health."""
        response = self.client.get("/health")
        if response.status_code != 200:
            response.failure(f"Health check failed: {response.status_code}")
    
    @task(1) 
    def get_stats(self):
        """Get processing statistics."""
        response = self.client.get("/stats")
        if response.status_code != 200:
            response.failure(f"Stats check failed: {response.status_code}")
    
    @task(5)
    def amazon_notification(self):
        """Send Amazon notification."""
        asin = random.choice(self.amazon_asins)
        seller_id = random.choice(self.amazon_sellers)
        
        message = {
            "NotificationType": "AnyOfferChanged",
            "PayloadVersion": "1.0", 
            "EventTime": datetime.now(UTC).isoformat(),
            "Payload": {
                "AnyOfferChangedNotification": {
                    "SellerId": seller_id,
                    "MarketplaceId": "ATVPDKIKX0DER",
                    "ASIN": asin,
                    "ItemCondition": "New",
                    "TimeOfOfferChange": datetime.now(UTC).isoformat(),
                    "Summary": {
                        "BuyBoxPrices": [{
                            "Condition": "New",
                            "FulfillmentChannel": "Merchant", 
                            "ListingPrice": {
                                "Amount": round(random.uniform(20.0, 100.0), 2),
                                "CurrencyCode": "USD"
                            }
                        }]
                    },
                    "Offers": [{
                        "SellerId": random.choice(self.amazon_sellers),
                        "SubCondition": "New",
                        "ListingPrice": {
                            "Amount": round(random.uniform(20.0, 100.0), 2),
                            "CurrencyCode": "USD"
                        },
                        "IsBuyBoxWinner": True,
                        "IsFulfilledByAmazon": random.choice([True, False])
                    }]
                }
            }
        }
        
        sqs_wrapper = {
            "MessageId": f"msg-{random.randint(100000, 999999)}",
            "Body": json.dumps(message)
        }
        
        response = self.client.post("/amazon/sqs-webhook", json=sqs_wrapper)
        if response.status_code not in [200, 202]:
            response.failure(f"Amazon notification failed: {response.status_code}")
    
    @task(3)
    def walmart_notification(self):
        """Send Walmart notification."""
        item_id = random.choice(self.walmart_items)
        seller_id = random.choice(self.walmart_sellers)
        
        webhook = {
            "eventType": "buybox_changed",
            "itemId": item_id,
            "sellerId": seller_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "offers": [{
                "sellerId": random.choice(self.walmart_sellers),
                "price": round(random.uniform(15.0, 85.0), 2),
                "condition": "New"
            }]
        }
        
        response = self.client.post("/walmart/webhook", json=webhook)
        if response.status_code not in [200, 202]:
            response.failure(f"Walmart notification failed: {response.status_code}")


# Configuration for different load test scenarios
if __name__ == "__main__":
    print("🚀 Locust Load Testing Configuration")
    print("=" * 50)
    print("Available user classes:")
    print("  1. AmazonNotificationUser - Amazon SQS notifications only")
    print("  2. WalmartNotificationUser - Walmart webhooks only") 
    print("  3. MixedPlatformUser - Mixed Amazon + Walmart traffic")
    print()
    print("Example commands:")
    print("  # Test Amazon notifications (10 users, 100/sec spawn rate)")
    print("  locust -f locust_load_test.py AmazonNotificationUser --users 10 --spawn-rate 100 --host http://localhost:8000")
    print()
    print("  # Test mixed platform load (50 users, 500/sec spawn rate)")
    print("  locust -f locust_load_test.py MixedPlatformUser --users 50 --spawn-rate 500 --host http://localhost:8000")
    print()
    print("  # Web UI mode (recommended)")
    print("  locust -f locust_load_test.py --host http://localhost:8000")
    print("  # Then visit: http://localhost:8089")