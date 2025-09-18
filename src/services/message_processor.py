"""Message processing service for Amazon SQS and Walmart webhook notifications."""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from loguru import logger

from schemas.messages import (
    WalmartWebhookMessage, ProcessedOfferData, WalmartOfferChange, ComprehensiveCompetitionData,
    CompetitorInfo
)


class MessageProcessor:
    """Processes incoming messages from Amazon SQS and Walmart webhooks."""
    
    def __init__(self):
        self.logger = logger.bind(service="message_processor")
    
    async def process_amazon_sqs_message(self, raw_message: Dict[str, Any]) -> ProcessedOfferData:
        """
        Process Amazon SQS ANY_OFFER_CHANGED notification with SP-API compliance.
        
        Args:
            raw_message: Raw SQS message payload
            
        Returns:
            ProcessedOfferData: Cleaned and normalized offer data
        """
        try:
            # Parse the SQS message structure
            self.logger.debug(f"Raw Amazon SQS message: {raw_message}")
            message_body = json.loads(raw_message.get("Body", "{}"))
            self.logger.debug(f"Parsed message body: {message_body}")
            
            # Extract notification from SNS message or direct SQS
            if message_body.get("Type") == "Notification":
                notification_data = json.loads(message_body.get("Message", "{}"))
            else:
                notification_data = message_body
            
            self.logger.debug(f"Notification data: {notification_data}")
            
            # Parse the SP-API compliant ANY_OFFER_CHANGED notification
            payload_data = notification_data.get("Payload")
            
            # Extract OfferChangeTrigger, Summary, and Offers
            trigger_data = payload_data.get("OfferChangeTrigger", {})
            summary_data = payload_data.get("Summary", {})
            offers_data = payload_data.get("Offers", [])
            
            # Extract core identification
            asin = trigger_data.get("ASIN") or trigger_data.get("asin", "")
            marketplace_id = trigger_data.get("MarketplaceId")
            item_condition = trigger_data.get("ItemCondition")
            time_of_change = self._parse_timestamp(
                trigger_data.get("TimeOfOfferChange")
            )

            # Extract comprehensive competitive data for all strategies
            competition_data = self._extract_comprehensive_competition_data(
                summary_data, offers_data, item_condition
            )
            
            # For seller_id, try to extract from offers if not in trigger
            seller_id = trigger_data.get("SellerId") or self._extract_target_seller(offers_data, asin)
            
            # Normalize to ProcessedOfferData
            processed_data = ProcessedOfferData(
                product_id=asin,
                seller_id=seller_id,
                marketplace=self._extract_marketplace(marketplace_id),
                platform="AMAZON",
                event_time=time_of_change,
                item_condition=item_condition.upper(),
                
                # Comprehensive competition data
                competition_data=competition_data,
                
                # Primary competitor price (prefer lowest price for most strategies)
                competitor_price=competition_data.lowest_price_competitor.price if competition_data.lowest_price_competitor else None,
                
                # Legacy fields for backward compatibility
                lowest_price=competition_data.lowest_price_competitor.price if competition_data.lowest_price_competitor else None,
                lowest_price_competitor=competition_data.lowest_price_competitor.seller_id if competition_data.lowest_price_competitor else None,
                buybox_winner=competition_data.buybox_winner.seller_id if competition_data.buybox_winner else None,
                total_offers=competition_data.total_offers,
                
                # Include raw data for detailed processing
                raw_offers=offers_data,
                raw_summary=summary_data
            )
            
            self.logger.info(
                f"Processed Amazon SQS message for ASIN {processed_data.product_id}",
                extra={
                    "asin": processed_data.product_id,
                    "seller_id": processed_data.seller_id,
                    "marketplace": processed_data.marketplace,
                    "competitor_price": processed_data.lowest_price,
                    "buybox_winner": processed_data.buybox_winner,
                    "total_offers": processed_data.total_offers
                }
            )
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Failed to process Amazon SQS message: {str(e)}")
            raise ValueError(f"Invalid Amazon SQS message format: {str(e)}")
    
    async def process_walmart_webhook(self, raw_payload: Dict[str, Any]) -> ProcessedOfferData:
        """
        Process Walmart buy box changed webhook.
        
        Args:
            raw_payload: Raw webhook payload
            
        Returns:
            ProcessedOfferData: Cleaned and normalized offer data
        """
        try:
            # Create structured offer change
            offer_change = WalmartOfferChange(
                item_id=raw_payload.get("itemId"),
                seller_id=raw_payload.get("sellerId"),
                marketplace=raw_payload.get("marketplace", "US"),
                event_time=self._parse_timestamp(raw_payload.get("eventTime")),
                current_buybox_price=raw_payload.get("currentBuyboxPrice"),
                current_buybox_winner=raw_payload.get("currentBuyboxWinner"),
                offers=raw_payload.get("offers", [])
            )
            
            # Create the full webhook message structure
            webhook_message = WalmartWebhookMessage(
                event_type=raw_payload.get("eventType", "buybox_changed"),
                webhook_id=raw_payload.get("webhookId", ""),
                timestamp=self._parse_timestamp(raw_payload.get("timestamp")),
                offer_change=offer_change
            )
            
            # Extract competition data for Walmart
            competition_data = self._extract_walmart_competition_data(offer_change)
            
            # Normalize to ProcessedOfferData
            processed_data = ProcessedOfferData(
                product_id=offer_change.item_id,
                seller_id=offer_change.seller_id,
                marketplace=offer_change.marketplace,
                platform="WALMART",
                event_time=offer_change.event_time,
                item_condition="NEW",  # Walmart typically deals with new items
                
                # Comprehensive competition data
                competition_data=competition_data,
                
                # Primary competitor price (prefer lowest price for most strategies)
                competitor_price=competition_data.lowest_price_competitor.price if competition_data.lowest_price_competitor else None,
                
                # Legacy fields for backward compatibility
                lowest_price=competition_data.lowest_price_competitor.price if competition_data.lowest_price_competitor else None,
                lowest_price_competitor=competition_data.lowest_price_competitor.seller_id if competition_data.lowest_price_competitor else None,
                buybox_winner=competition_data.buybox_winner.seller_id if competition_data.buybox_winner else None,
                total_offers=competition_data.total_offers,
                
                raw_offers=offer_change.offers
            )
            
            self.logger.info(
                f"Processed Walmart webhook for item {processed_data.product_id}",
                extra={
                    "item_id": processed_data.product_id,
                    "seller_id": processed_data.seller_id,
                    "marketplace": processed_data.marketplace
                }
            )
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Failed to process Walmart webhook: {str(e)}")
            raise ValueError(f"Invalid Walmart webhook format: {str(e)}")
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return datetime.now(timezone.utc)
        
        try:
            # Try ISO format first
            if timestamp_str.endswith('Z'):
                return datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
            elif '+' in timestamp_str or timestamp_str.endswith('UTC'):
                return datetime.fromisoformat(timestamp_str.replace('UTC', '+00:00'))
            else:
                return datetime.fromisoformat(timestamp_str)
        except ValueError:
            # Fallback to current time if parsing fails
            self.logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return datetime.now(timezone.utc)
    
    def _extract_marketplace(self, marketplace_id: str) -> str:
        """Extract marketplace code from Amazon marketplace ID."""
        marketplace_mapping = {
            "ATVPDKIKX0DER": "US",
            "A1PA6795UKMFR9": "DE", 
            "A1RKKUPIHCS9HS": "ES",
            "A13V1IB3VIYZZH": "FR",
            "A21TJRUUN4KGV": "IN",
            "APJ6JRA9NG5V4": "IT",
            "A1F83G8C2ARO7P": "UK",
            "A2Q3Y263D00KWC": "BR",
            "A2EUQ1WTGCTBG2": "CA",
            "A1AM78C64UM0Y8": "MX",
            "A39IBJ37TRP1C6": "AU",
            "A17E79C6D8DWNP": "SA",
            "ARBP9OOSHTCHU": "EG",
            "A33AVAJ2PDY3EV": "TR",
            "A19VAU5U5O7RUS": "SG",
            "A39IBJ37TRP1C6": "AU",
            "A2VIGQ35RCS4UG": "AE",
            "A1805IZSGTT6HS": "NL",
            "A1C3SOZRARQ6R3": "PL"
        }
        
        return marketplace_mapping.get(marketplace_id, "US")
    
    def _extract_walmart_competition_data(self, offer_change: WalmartOfferChange) -> ComprehensiveCompetitionData:
        """Extract competition data from Walmart offer change."""
        all_competitors = []
        lowest_price_competitor = None
        buybox_winner = None
        
        if offer_change.offers:
            # Extract all competitors (excluding ourselves)
            for offer in offer_change.offers:
                seller_id = offer.get("sellerId", "")
                price = offer.get("price")
                
                if seller_id != offer_change.seller_id and price:
                    competitor = CompetitorInfo(
                        seller_id=seller_id,
                        price=float(price),
                        is_fba=None,  # Walmart doesn't have FBA concept
                        is_buybox_winner=seller_id == offer_change.current_buybox_winner,
                        condition="NEW"  # Walmart typically deals with new items
                    )
                    all_competitors.append(competitor)
            
            # Find lowest price competitor
            if all_competitors:
                lowest_price_competitor = min(all_competitors, key=lambda x: x.price)
            
            # Find buybox winner
            if offer_change.current_buybox_winner:
                buybox_winner = next(
                    (comp for comp in all_competitors if comp.seller_id == offer_change.current_buybox_winner),
                    None
                )
        
        # If no competitors found but we have buybox info, create competitor from buybox data
        if not lowest_price_competitor and offer_change.current_buybox_price:
            if offer_change.current_buybox_winner and offer_change.current_buybox_winner != offer_change.seller_id:
                competitor = CompetitorInfo(
                    seller_id=offer_change.current_buybox_winner,
                    price=offer_change.current_buybox_price,
                    is_fba=None,
                    is_buybox_winner=True,
                    condition="NEW"
                )
                lowest_price_competitor = competitor
                buybox_winner = competitor
                all_competitors = [competitor]
        
        return ComprehensiveCompetitionData(
            lowest_price_competitor=lowest_price_competitor,
            lowest_fba_competitor=None,  # Walmart doesn't have FBA
            buybox_winner=buybox_winner,
            total_offers=len(offer_change.offers) if offer_change.offers else None,
            all_competitors=all_competitors
        )
    
    def _extract_comprehensive_competition_data(
        self, 
        summary_data: Dict[str, Any], 
        offers_data: List[Dict[str, Any]], 
        item_condition: str
    ) -> ComprehensiveCompetitionData:
        """Extract comprehensive competitive data for all strategy types."""
        
        # Extract all competitors from offers data
        all_competitors = self._extract_all_competitors(offers_data, item_condition)
        
        # Find specific competitors for each strategy type
        lowest_price_competitor = self._find_lowest_price_competitor(summary_data, item_condition)
        lowest_fba_competitor = self._find_lowest_fba_competitor(offers_data, item_condition)
        buybox_winner = self._find_buybox_winner(offers_data, item_condition)
        
        # Extract total offers
        total_offers = self._extract_total_offers(summary_data)
        
        return ComprehensiveCompetitionData(
            lowest_price_competitor=lowest_price_competitor,
            lowest_fba_competitor=lowest_fba_competitor,
            buybox_winner=buybox_winner,
            total_offers=total_offers,
            all_competitors=all_competitors
        )
    
    def _extract_all_competitors(self, offers_data: List[Dict[str, Any]], item_condition: str) -> List[CompetitorInfo]:
        """Extract all competitors from offers data."""
        competitors = []
        
        for offer in offers_data:
            # Filter by condition
            offer_condition = offer.get("SubCondition", "").lower()
            if offer_condition != item_condition.lower():
                continue
                
            # Extract price (prefer landed price, fallback to listing price)
            price = self._extract_price_from_offer(offer)
            if price is None:
                continue
                
            competitor = CompetitorInfo(
                seller_id=offer.get("SellerId", ""),
                price=price,
                is_fba=offer.get("IsFulfilledByAmazon", False),
                is_buybox_winner=offer.get("IsBuyBoxWinner", False),
                condition=offer_condition
            )
            competitors.append(competitor)
        
        return sorted(competitors, key=lambda x: x.price)
    
    def _find_lowest_price_competitor(self, summary_data: Dict[str, Any], item_condition: str) -> Optional[CompetitorInfo]:
        """Find the overall lowest price competitor (for LOWEST_PRICE strategy)."""
        if not summary_data:
            return None
        
        lowest_prices = summary_data.get("LowestPrices", [])
        for price_info in lowest_prices:
            condition = price_info.get("Condition", "").lower()
            if condition == item_condition.lower():
                price = self._extract_price_from_price_info(price_info)
                if price is not None:
                    return CompetitorInfo(
                        seller_id=price_info.get("SellerId", ""),
                        price=price,
                        is_fba=None,  # Not available in summary data
                        is_buybox_winner=None,  # Not available in summary data
                        condition=condition
                    )
        return None
    
    def _find_lowest_fba_competitor(self, offers_data: List[Dict[str, Any]], item_condition: str) -> Optional[CompetitorInfo]:
        """Find the lowest FBA competitor (for LOWEST_FBA_PRICE strategy)."""
        fba_competitors = []
        
        for offer in offers_data:
            # Filter by condition and FBA status
            offer_condition = offer.get("SubCondition", "").lower()
            if (offer_condition != item_condition.lower() or 
                not offer.get("IsFulfilledByAmazon", False)):
                continue
                
            price = self._extract_price_from_offer(offer)
            if price is not None:
                fba_competitors.append(CompetitorInfo(
                    seller_id=offer.get("SellerId", ""),
                    price=price,
                    is_fba=True,
                    is_buybox_winner=offer.get("IsBuyBoxWinner", False),
                    condition=offer_condition
                ))
        
        # Return the cheapest FBA competitor
        return min(fba_competitors, key=lambda x: x.price) if fba_competitors else None
    
    def _find_buybox_winner(self, offers_data: List[Dict[str, Any]], item_condition: str) -> Optional[CompetitorInfo]:
        """Find the buybox winner (for MATCH_BUYBOX strategy)."""
        for offer in offers_data:
            if offer.get("IsBuyBoxWinner"):
                # Verify condition matches
                offer_condition = offer.get("SubCondition", "").lower()
                if offer_condition == item_condition.lower():
                    price = self._extract_price_from_offer(offer)
                    if price is not None:
                        return CompetitorInfo(
                            seller_id=offer.get("SellerId", ""),
                            price=price,
                            is_fba=offer.get("IsFulfilledByAmazon", False),
                            is_buybox_winner=True,
                            condition=offer_condition
                        )
        return None
    
    def _extract_price_from_offer(self, offer: Dict[str, Any]) -> Optional[float]:
        """Extract price from offer data, preferring landed price."""
        # Prefer landed price (includes shipping), fallback to listing price
        landed_price = offer.get("LandedPrice", {})
        listing_price = offer.get("ListingPrice", {})
        
        if landed_price and landed_price.get("Amount"):
            return float(landed_price["Amount"])
        elif listing_price and listing_price.get("Amount"):
            return float(listing_price["Amount"])
        return None
    
    def _extract_price_from_price_info(self, price_info: Dict[str, Any]) -> Optional[float]:
        """Extract price from summary price info."""
        # Prefer landed price (includes shipping), fallback to listing price
        landed_price = price_info.get("LandedPrice", {})
        listing_price = price_info.get("ListingPrice", {})
        
        if landed_price and landed_price.get("Amount"):
            return float(landed_price["Amount"])
        elif listing_price and listing_price.get("Amount"):
            return float(listing_price["Amount"])
        return None
    
    def _extract_total_offers(self, summary_data: Dict[str, Any]) -> Optional[int]:
        """Extract total number of offers from Summary."""
        if not summary_data:
            return None
            
        number_of_offers = summary_data.get("NumberOfOffers", [])
        if number_of_offers:
            return sum(offer_count.get("OfferCount", 0) for offer_count in number_of_offers)
        return None
    
    def _extract_target_seller(self, offers_data: List[Dict[str, Any]], asin: str) -> str:
        """Extract target seller ID from our product database for this ASIN."""
        # Look up the ASIN in Redis to find our seller for this product
        try:
            import redis
            from ..core.config import get_settings
            
            settings = get_settings()
            
            # Create synchronous Redis connection for this lookup
            sync_redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=True
            )
            
            # Look up the product by ASIN key
            asin_key = f"ASIN_{asin}"
            # Redis HGETALL returns a dict, we need to find our seller
            product_data = sync_redis.hgetall(asin_key)
            
            if product_data:
                # Look for our seller in the product data
                for field, data_str in product_data.items():
                    if ":" in field:  # Format is "seller_id:sku"
                        seller_id = field.split(":")[0]
                        return seller_id
            
            sync_redis.close()
        except Exception as e:
            self.logger.warning(f"Could not lookup seller for ASIN {asin}: {e}")
        
        # Fallback to default test seller
        return "A1234567890123"


class MessageExtractor:
    """Extracts only necessary fields from processed messages for pipeline efficiency."""
    
    @staticmethod
    def extract_essential_fields(processed_data: ProcessedOfferData) -> Dict[str, Any]:
        """
        Extract only essential fields needed for repricing pipeline.
        
        This reduces memory usage and processing overhead for high-throughput scenarios.
        
        Args:
            processed_data: Full processed offer data
            
        Returns:
            Dict containing only essential fields
        """
        essential_fields = {
            # Core identification
            "product_id": processed_data.product_id,
            "seller_id": processed_data.seller_id,
            "platform": processed_data.platform,
            "marketplace": processed_data.marketplace,
            
            # Essential competition data
            "competitor_price": processed_data.competitor_price,
            "item_condition": processed_data.item_condition,
            "event_time": processed_data.event_time.isoformat(),
            
            # Processing metadata
            "processed_time": processed_data.processed_time.isoformat(),
        }
        
        # Add buybox information if available
        if processed_data.buybox_winner:
            essential_fields["buybox_winner"] = processed_data.buybox_winner
            
        if processed_data.total_offers:
            essential_fields["total_offers"] = processed_data.total_offers
        
        return essential_fields