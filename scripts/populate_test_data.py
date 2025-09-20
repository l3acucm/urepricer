#!/usr/bin/env python3
"""
Test data population script for urepricer development environment.

Creates realistic test data for 500 sellers each on Amazon and Walmart platforms
with various pricing scenarios including competitive situations.
"""

import asyncio
import json
import random
import string
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, List

import redis.asyncio as redis

from src.core.config import get_settings


@dataclass
class TestSeller:
    """Test seller data structure."""
    seller_id: str
    platform: str  # 'amazon' or 'walmart'
    marketplace_type: str
    active_listings: int
    strategy_types: List[str]


@dataclass
class TestProduct:
    """Test product data structure."""
    asin: str
    sku: str
    seller_id: str
    platform: str
    marketplace_type: str
    listed_price: float
    min_price: float
    max_price: float
    default_price: float
    competitor_price: float
    strategy_id: str
    is_b2b: bool
    product_name: str
    scenario: str  # 'competitive', 'solo_seller', 'buybox_winner', 'out_of_bounds'


class TestDataPopulator:
    """Populates Redis with comprehensive test data."""

    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None
        
        # Predefined strategy configurations
        self.strategies = {
            "1": {"type": "LOWEST_PRICE", "beat_by": "-0.01", "min_price_rule": "JUMP_TO_MIN", "max_price_rule": "JUMP_TO_MAX"},
            "2": {"type": "MATCH_BUYBOX", "beat_by": "-0.01", "min_price_rule": "JUMP_TO_MIN", "max_price_rule": "JUMP_TO_MAX"},
            "3": {"type": "FBA_LOWEST", "beat_by": "-0.05", "min_price_rule": "JUMP_TO_MIN", "max_price_rule": "JUMP_TO_MAX"},
            "4": {"type": "LOWEST_PRICE", "beat_by": "0.00", "min_price_rule": "DO_NOTHING", "max_price_rule": "DO_NOTHING"},
            "5": {"type": "MATCH_BUYBOX", "beat_by": "-0.10", "min_price_rule": "DEFAULT_PRICE", "max_price_rule": "DEFAULT_PRICE"},
        }
        
        # Product categories for realistic ASINs
        self.categories = [
            "Electronics", "Home & Kitchen", "Sports & Outdoors", "Health & Personal Care",
            "Beauty & Personal Care", "Automotive", "Tools & Home Improvement", "Toys & Games",
            "Books", "Clothing", "Shoes", "Baby", "Pet Supplies", "Garden & Outdoor"
        ]

    async def connect_redis(self):
        """Connect to Redis."""
        self.redis_client = redis.Redis(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            password=getattr(self.settings, 'redis_password', None),
            decode_responses=True
        )
        await self.redis_client.ping()
        print("✅ Connected to Redis")

    async def close_redis(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

    def generate_asin(self) -> str:
        """Generate a realistic ASIN."""
        return 'B' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=9))

    def generate_seller_id(self, platform: str) -> str:
        """Generate a realistic seller ID."""
        if platform == 'amazon':
            return 'A' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=13))
        else:  # walmart
            return 'WM' + ''.join(random.choices(string.digits, k=8))

    def generate_sku(self, seller_id: str) -> str:
        """Generate a realistic SKU."""
        prefix = seller_id[:3]
        return f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"

    def generate_test_sellers(self, count: int, platform: str) -> List[TestSeller]:
        """Generate test sellers for a platform."""
        sellers = []
        marketplaces = ['US', 'UK', 'CA', 'AU'] if platform == 'amazon' else ['US']
        strategy_types = ['LOWEST_PRICE', 'MATCH_BUYBOX', 'FBA_LOWEST', 'FIXED_PRICE']
        
        # First, add guaranteed QUICKSTART seller
        if platform == 'amazon':
            quickstart_seller = TestSeller(
                seller_id="A1234567890123",
                platform=platform,
                marketplace_type="US",
                active_listings=50,
                strategy_types=['MATCH_BUYBOX', 'LOWEST_PRICE']
            )
            sellers.append(quickstart_seller)
        elif platform == 'walmart':
            quickstart_seller = TestSeller(
                seller_id="WM12345678",
                platform=platform,
                marketplace_type="US",
                active_listings=25,
                strategy_types=['FIXED_PRICE']
            )
            sellers.append(quickstart_seller)
        
        # Generate remaining sellers (count - 1 to account for quickstart seller)
        for i in range(count - 1):
            seller = TestSeller(
                seller_id=self.generate_seller_id(platform),
                platform=platform,
                marketplace_type=random.choice(marketplaces),
                active_listings=random.randint(10, 1000),
                strategy_types=random.sample(strategy_types, random.randint(1, 3))
            )
            sellers.append(seller)
        
        return sellers

    def generate_pricing_scenario(self) -> Dict[str, Any]:
        """Generate realistic pricing scenario."""
        scenarios = ['competitive', 'solo_seller', 'buybox_winner', 'out_of_bounds']
        scenario = random.choice(scenarios)
        
        base_price = round(random.uniform(5.0, 200.0), 2)
        min_price = round(base_price * random.uniform(0.7, 0.9), 2)
        max_price = round(base_price * random.uniform(1.1, 1.5), 2)
        
        if scenario == 'competitive':
            listed_price = round(base_price * random.uniform(0.95, 1.05), 2)
            competitor_price = round(base_price * random.uniform(0.9, 1.1), 2)
        elif scenario == 'solo_seller':
            listed_price = round(base_price, 2)
            competitor_price = None
        elif scenario == 'buybox_winner':
            listed_price = round(base_price * 0.95, 2)
            competitor_price = round(base_price * random.uniform(1.05, 1.2), 2)
        else:  # out_of_bounds
            listed_price = round(base_price * random.uniform(1.6, 2.0), 2)  # Above max
            competitor_price = round(base_price * random.uniform(0.9, 1.1), 2)
        
        return {
            'scenario': scenario,
            'listed_price': listed_price,
            'min_price': min_price,
            'max_price': max_price,
            'default_price': base_price,
            'competitor_price': competitor_price
        }

    def create_quickstart_products(self) -> List[TestProduct]:
        """Create guaranteed products for QUICKSTART.md examples."""
        quickstart_products = []
        
        # Amazon product from QUICKSTART.md
        amazon_pricing = self.generate_pricing_scenario()
        amazon_product = TestProduct(
            asin="B01234567890",
            sku="A12-QUICKSTART01",
            seller_id="A1234567890123",
            platform="amazon",
            marketplace_type="US",
            listed_price=amazon_pricing['listed_price'],
            min_price=amazon_pricing['min_price'],
            max_price=amazon_pricing['max_price'],
            default_price=amazon_pricing['default_price'],
            competitor_price=amazon_pricing['competitor_price'],
            strategy_id="1",  # WIN_BUYBOX strategy
            is_b2b=False,
            product_name="QUICKSTART Amazon Test Product",
            scenario=amazon_pricing['scenario']
        )
        quickstart_products.append(amazon_product)
        
        # Walmart product from QUICKSTART.md
        walmart_pricing = self.generate_pricing_scenario()
        walmart_product = TestProduct(
            asin="WM123456789",
            sku="WM12-QUICKSTART01",
            seller_id="WM12345678",
            platform="walmart",
            marketplace_type="US",
            listed_price=walmart_pricing['listed_price'],
            min_price=walmart_pricing['min_price'],
            max_price=walmart_pricing['max_price'],
            default_price=walmart_pricing['default_price'],
            competitor_price=walmart_pricing['competitor_price'],
            strategy_id="3",  # ONLY_SELLER strategy
            is_b2b=False,
            product_name="QUICKSTART Walmart Test Product",
            scenario=walmart_pricing['scenario']
        )
        quickstart_products.append(walmart_product)
        
        return quickstart_products

    def generate_test_products(self, sellers: List[TestSeller]) -> List[TestProduct]:
        """Generate test products for sellers."""
        products = []
        
        # First, create guaranteed products for QUICKSTART.md examples
        quickstart_products = self.create_quickstart_products()
        products.extend(quickstart_products)
        
        for seller in sellers:
            # Generate 2-5 products per seller
            for _ in range(random.randint(2, 5)):
                pricing = self.generate_pricing_scenario()
                
                product = TestProduct(
                    asin=self.generate_asin(),
                    sku=self.generate_sku(seller.seller_id),
                    seller_id=seller.seller_id,
                    platform=seller.platform,
                    marketplace_type=seller.marketplace_type,
                    listed_price=pricing['listed_price'],
                    min_price=pricing['min_price'],
                    max_price=pricing['max_price'],
                    default_price=pricing['default_price'],
                    competitor_price=pricing['competitor_price'],
                    strategy_id=random.choice(list(self.strategies.keys())),
                    is_b2b=False,  # B2B complexity removed
                    product_name=f"{random.choice(self.categories)} Product {random.randint(100, 999)}",
                    scenario=pricing['scenario']
                )
                products.append(product)
        
        return products

    async def save_strategies(self):
        """Save strategy configurations to Redis."""
        print("💾 Saving strategy configurations...")
        
        for strategy_id, config in self.strategies.items():
            redis_key = f"strategy.{strategy_id}"
            for field, value in config.items():
                await self.redis_client.hset(redis_key, field, str(value))
            await self.redis_client.expire(redis_key, 7200)  # 2 hours TTL
        
        print(f"✅ Saved {len(self.strategies)} strategy configurations")

    async def save_product_data(self, products: List[TestProduct]):
        """Save product data to Redis."""
        print("💾 Saving product data...")
        
        saved_count = 0
        for product in products:
            # Create simplified product data structure (only essential fields)
            product_data = {
                "listed_price": product.listed_price,
                "min_price": product.min_price,
                "max_price": product.max_price,
                "default_price": product.default_price,
                "strategy_id": product.strategy_id,
                "status": "Active",
                "item_condition": "New",
                "quantity": random.randint(1, 100)
            }
            
            # B2B complexity removed for simplified schema
            
            # Save to Redis with ASIN structure
            redis_key = f"ASIN_{product.asin}"
            seller_sku_key = f"{product.seller_id}:{product.sku}"
            
            await self.redis_client.hset(
                redis_key,
                seller_sku_key,
                json.dumps(product_data)
            )
            await self.redis_client.expire(redis_key, 7200)  # 2 hours TTL
            
            saved_count += 1
            
            # Print progress every 100 products
            if saved_count % 100 == 0:
                print(f"  📦 Saved {saved_count} products...")
        
        print(f"✅ Saved {saved_count} product listings")

    def generate_b2b_tiers(self, product: TestProduct) -> Dict[str, Any]:
        """B2B tiers removed from simplified schema."""
        return {}

    async def save_seller_accounts(self, sellers: List[TestSeller]):
        """Seller account data removed from simplified schema."""
        print("✅ Skipping seller account data (removed from simplified schema)")

    async def create_scenario_summary(self, products: List[TestProduct]):
        """Create a summary of test scenarios."""
        scenarios = {}
        platforms = {}
        
        for product in products:
            scenario = product.scenario
            scenarios[scenario] = scenarios.get(scenario, 0) + 1
            
            platform = product.platform
            platforms[platform] = platforms.get(platform, 0) + 1
        
        summary = {
            "total_products": len(products),
            "scenarios": scenarios,
            "platforms": platforms,
            "generated_at": datetime.now(UTC).isoformat()
        }
        
        await self.redis_client.set("test_data_summary", json.dumps(summary), ex=7200)
        
        print("\n📊 Test Data Summary:")
        print(f"  Total products: {summary['total_products']}")
        print(f"  Scenarios: {scenarios}")
        print(f"  Platforms: {platforms}")

    async def populate_all_data(self):
        """Populate all test data."""
        print("🚀 Starting test data population...")
        print("=" * 50)
        
        try:
            await self.connect_redis()
            
            # Clear existing test data
            print("🧹 Clearing existing test data...")
            await self.redis_client.flushdb()
            
            # Generate sellers
            print("👥 Generating sellers...")
            amazon_sellers = self.generate_test_sellers(500, 'amazon')
            walmart_sellers = self.generate_test_sellers(500, 'walmart')
            all_sellers = amazon_sellers + walmart_sellers
            print(f"✅ Generated {len(all_sellers)} sellers (500 Amazon + 500 Walmart)")
            
            # Generate products
            print("📦 Generating products...")
            all_products = self.generate_test_products(all_sellers)
            print(f"✅ Generated {len(all_products)} products")
            
            # Save data to Redis
            await self.save_strategies()
            await self.save_seller_accounts(all_sellers)
            await self.save_product_data(all_products)
            await self.create_scenario_summary(all_products)
            
            print("\n" + "=" * 50)
            print("🎉 Test data population completed successfully!")
            print("\nYou can now:")
            print("  1. Run tests against this data")
            print("  2. Test repricing strategies")
            print("  3. Emulate price change notifications")
            print("  4. Perform load testing")
            
        except Exception as e:
            print(f"❌ Error populating test data: {e}")
            raise
        finally:
            await self.close_redis()


async def main():
    """Main entry point."""
    populator = TestDataPopulator()
    await populator.populate_all_data()


if __name__ == "__main__":
    asyncio.run(main())