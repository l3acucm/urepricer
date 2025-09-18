"""Population script that reads data from MySQL and populates Redis with same structure."""

import asyncio
import json
import mysql.connector
from typing import Dict, Any, List
import redis.asyncio as redis
from loguru import logger

from src.core.config import get_settings


class MySQLRedisPopulator:
    """Populates Redis with real data from MySQL database."""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None
        self.mysql_conn = None
        
    async def connect_to_services(self):
        """Connect to both MySQL and Redis."""
        # Connect to MySQL
        try:
            self.mysql_conn = mysql.connector.connect(
                host=self.settings.mysql_host,
                port=self.settings.mysql_port,
                database=self.settings.mysql_database,
                user=self.settings.mysql_username,
                password=self.settings.mysql_password
            )
            logger.info("✅ Connected to MySQL")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MySQL: {e}")
            raise
            
        # Connect to Redis
        try:
            self.redis_client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def flush_redis(self):
        """Clear all Redis data before population."""
        logger.info("🧹 Clearing existing Redis data...")
        await self.redis_client.flushall()
        logger.info("✅ Redis cleared")
    
    def get_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all repricer strategies from MySQL."""
        cursor = self.mysql_conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM repricer_strategies")
            strategies = {}
            
            for row in cursor.fetchall():
                strategy_id = str(row['id'])
                
                # Parse settings JSON if it exists
                settings = {}
                if row['settings']:
                    try:
                        settings = json.loads(row['settings'])
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in strategy {strategy_id} settings")
                
                # Map MySQL fields to Redis structure
                strategy_data = {
                    "type": settings.get("compete_with", row['type']),  # Use settings first, fallback to type
                    "beat_by": str(settings.get("beat_by", "0.0")),
                    "min_price_rule": settings.get("min_price_rule", "JUMP_TO_MIN"),
                    "max_price_rule": settings.get("max_price_rule", "JUMP_TO_MAX")
                }
                
                strategies[strategy_id] = strategy_data
                
            logger.info(f"✅ Loaded {len(strategies)} strategies from MySQL")
            return strategies
            
        finally:
            cursor.close()
    
    def get_users_seller_mapping(self) -> Dict[int, Dict[str, str]]:
        """Get mapping from user IDs to seller IDs for both regions."""
        cursor = self.mysql_conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, uk_sellerId, us_sellerId FROM users")
            user_mapping = {}
            
            for row in cursor.fetchall():
                user_id = row['id']
                user_mapping[user_id] = {
                    'uk': row['uk_sellerId'] if row['uk_sellerId'] else f"UK_SELLER_{user_id}",
                    'us': row['us_sellerId'] if row['us_sellerId'] else f"US_SELLER_{user_id}"
                }
                
            logger.info(f"✅ Loaded {len(user_mapping)} user-seller mappings")
            return user_mapping
            
        finally:
            cursor.close()
    
    def get_inventory_data(self, region: str, offset: int = 0, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch inventory data from specified region with pagination."""
        table_name = f"inventory_{region}"
        cursor = self.mysql_conn.cursor(dictionary=True)
        
        try:
            # Only get active products with strategy IDs
            query = f"""
                SELECT * FROM {table_name} 
                WHERE enabled = 1 
                AND repricer_strategy_id IS NOT NULL 
                ORDER BY id 
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (limit, offset))
            return cursor.fetchall()
            
        finally:
            cursor.close()
    
    def get_total_inventory_count(self, region: str) -> int:
        """Get total count of inventory items for a region."""
        table_name = f"inventory_{region}"
        cursor = self.mysql_conn.cursor()
        
        try:
            query = f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE enabled = 1 
                AND repricer_strategy_id IS NOT NULL
            """
            cursor.execute(query)
            return cursor.fetchone()[0]
            
        finally:
            cursor.close()
    
    async def save_strategies_to_redis(self, strategies: Dict[str, Dict[str, Any]]):
        """Save strategy configurations to Redis."""
        logger.info("💾 Saving strategy configurations...")
        
        for strategy_id, strategy_data in strategies.items():
            redis_key = f"strategy.{strategy_id}"
            await self.redis_client.hset(redis_key, mapping=strategy_data)
        
        logger.info(f"✅ Saved {len(strategies)} strategy configurations")
    
    async def save_products_to_redis(self, products: List[Dict[str, Any]], user_mapping: Dict[int, Dict[str, str]], region: str):
        """Save product data to Redis."""
        saved_count = 0
        
        for product in products:
            try:
                # Get seller ID from user mapping
                user_id = product['userid']
                if user_id not in user_mapping:
                    logger.warning(f"User ID {user_id} not found in mapping")
                    continue
                    
                seller_id = user_mapping[user_id][region]
                asin = product['asin']
                sku = product['seller_sku']
                
                # Create Redis key format: ASIN_{asin}
                redis_key = f"ASIN_{asin}"
                field_name = f"{seller_id}:{sku}"
                
                # Map MySQL fields to Redis structure
                product_data = {
                    "listed_price": float(product['price']) if product['price'] else 0.0,
                    "min_price": float(product['repricer_min']) if product['repricer_min'] else None,
                    "max_price": float(product['repricer_max']) if product['repricer_max'] else None,
                    "default_price": float(product['price']) if product['price'] else 0.0,
                    "strategy_id": str(product['repricer_strategy_id']),
                    "status": "Active" if product['enabled'] else "Inactive",
                    "item_condition": product['condition_type'] if product['condition_type'] else "New",
                    "quantity": product['quantity'] if product['quantity'] else 0
                }
                
                # Save to Redis
                await self.redis_client.hset(redis_key, field_name, json.dumps(product_data))
                saved_count += 1
                
            except Exception as e:
                logger.warning(f"Error saving product {product.get('asin', 'unknown')}: {e}")
                continue
        
        return saved_count
    
    async def populate_region(self, region: str, user_mapping: Dict[int, Dict[str, str]], batch_size: int = 1000) -> int:
        """Populate Redis with data from a specific region."""
        total_count = self.get_total_inventory_count(region)
        logger.info(f"📦 Found {total_count} products in {region.upper()} region")
        
        total_saved = 0
        offset = 0
        
        while offset < total_count:
            # Fetch batch
            products = self.get_inventory_data(region, offset, batch_size)
            if not products:
                break
                
            # Save batch to Redis
            saved_count = await self.save_products_to_redis(products, user_mapping, region)
            total_saved += saved_count
            
            offset += batch_size
            logger.info(f"  📦 Saved {total_saved}/{total_count} products from {region.upper()}")
            
            # Optional: Add small delay to prevent overwhelming the database
            await asyncio.sleep(0.1)
        
        return total_saved
    
    async def populate_all_data(self, batch_size: int = 1000) -> Dict[str, Any]:
        """Main method to populate Redis with all MySQL data."""
        logger.info("🚀 Starting MySQL to Redis population...")
        
        results = {
            "strategies_saved": 0,
            "uk_products_saved": 0,
            "us_products_saved": 0,
            "total_products_saved": 0,
            "errors": []
        }
        
        try:
            # Connect to services
            await self.connect_to_services()
            
            # Flush Redis
            await self.flush_redis()
            
            # Get strategies and user mapping
            strategies = self.get_strategies()
            user_mapping = self.get_users_seller_mapping()
            
            # Save strategies to Redis
            await self.save_strategies_to_redis(strategies)
            results["strategies_saved"] = len(strategies)
            
            # Populate UK region
            try:
                uk_saved = await self.populate_region("uk", user_mapping, batch_size)
                results["uk_products_saved"] = uk_saved
            except Exception as e:
                error_msg = f"Error populating UK region: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
            
            # Populate US region
            try:
                us_saved = await self.populate_region("us", user_mapping, batch_size)
                results["us_products_saved"] = us_saved
            except Exception as e:
                error_msg = f"Error populating US region: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
            
            results["total_products_saved"] = results["uk_products_saved"] + results["us_products_saved"]
            
            logger.info("🎉 MySQL to Redis population completed!")
            logger.info(f"📊 Summary: {results['strategies_saved']} strategies, {results['total_products_saved']} products")
            
        except Exception as e:
            error_msg = f"Fatal error during population: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            raise
            
        finally:
            # Clean up connections
            if self.redis_client:
                await self.redis_client.aclose()
            if self.mysql_conn:
                self.mysql_conn.close()
        
        return results


async def main():
    """Main entry point for running the population script."""
    populator = MySQLRedisPopulator()
    results = await populator.populate_all_data()
    
    print("\n" + "="*50)
    print("🎉 Population Results:")
    print(f"  Strategies: {results['strategies_saved']}")
    print(f"  UK Products: {results['uk_products_saved']}")
    print(f"  US Products: {results['us_products_saved']}")
    print(f"  Total Products: {results['total_products_saved']}")
    
    if results["errors"]:
        print(f"  ❌ Errors: {len(results['errors'])}")
        for error in results["errors"]:
            print(f"    - {error}")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())