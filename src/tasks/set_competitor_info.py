from typing import Dict, Any, Iterator, Optional
from ..utils.exceptions import SkipProductRepricing


class SetCompetitorInfo:
    """
    SetCompetitorInfo class applies competitive analysis to a product.

    Attributes:
        product (Product): The product data.
        payload (dict): The API payload containing competitor information.
    """
    SUMMARIES_PATH = {
        'MATCH_BUYBOX': 'Summary.BuyBoxPrices',
        'LOWEST_PRICE': 'Summary.LowestPrices',
        'LOWEST_FBA_PRICE': 'Summary.LowestPrices',
    }

    def __init__(self, product: Any, payload: Dict[str, Any]) -> None:
        """
        Initializes a SetCompetitorInfo object.

        Args:
            product: The product data.
            payload: The API payload containing competitor information.
        """
        self.product = product
        self.payload = payload

    def apply(self) -> Any:
        """
        Applies the competitor analysis to the product.

        Returns:
            Product: The product with the applied competitor information.
        """
        self._set_number_of_offers()

        if self.product.no_of_offers != 1:
            self._set_competitors_info()
            self._validate_product(self.product)

        return self.product

    def _set_number_of_offers(self) -> None:
        """Set total number of offers."""
        self.product.no_of_offers = self.payload.get('Summary.TotalOfferCount')

    def _set_competitors_info(self) -> None:
        """Sets the strategy rule based on the 'compete_with' value."""
        compete_with = self.product.strategy.compete_with
        
        if self.product.is_b2b:
            return self._set_b2b_price()

        if compete_with == 'LOWEST_FBA_PRICE':
            return self._set_fba_lowest_price()
        elif compete_with == 'LOWEST_PRICE':
            return self._set_min_price()
        elif compete_with == 'MATCH_BUYBOX':
            return self._set_buybox_price()

    def _set_b2b_price(self) -> None:
        """Retrieves pricing information for B2B products."""
        compete_with = self.product.strategy.compete_with
        path = self.SUMMARIES_PATH.get(compete_with)
        summaries = self.payload.get(path, [])

        filtered_offers = self._filter_compete_with_offers(summaries, compete_with)

        standard_offer = next(filtered_offers, {})
        if (
            not standard_offer.get("offerType") or
            standard_offer.get("offerType") == "B2C" or
            standard_offer.get("quantityTier") == 1
        ):
            seller_id = str(standard_offer.get('sellerId'))
            if seller_id != self.product.account.seller_id:
                self.product.competitor_price = standard_offer.get('ListingPrice.Amount')
        else:
            filtered_offers = iter(summaries)

        for offer in filtered_offers:
            competitor_quantity_tier = str(offer.get('quantityTier'))
            seller_id = str(offer.get('sellerId'))
            if tier := self.product.tiers.get(competitor_quantity_tier):
                if seller_id != self.product.account.seller_id:
                    tier.competitor_price = offer.get('ListingPrice.Amount')

    def _filter_compete_with_offers(self, offers: list, compete_with: str) -> Iterator[Dict[str, Any]]:
        """Get filtered offers based on the competition rule."""
        product_condition = self.product.mapped_item_condition
        
        if compete_with == 'LOWEST_FBA_PRICE':
            filtered_result = filter(
                lambda offer: offer.get('condition', '').lower() == product_condition 
                and offer.get('fulfillmentChannel') == 'AMAZON',
                offers
            )
        elif compete_with == 'LOWEST_PRICE':
            filtered_offers = [offer for offer in offers if 'OfferType' not in offer and 'quantityTier' not in offer]
            sorted_offers = sorted(filtered_offers, key=lambda offer: offer['ListingPrice']['Amount'])

            for i, offer in enumerate(sorted_offers):
                offers[i] = offer

            filtered_result = filter(
                lambda offer: offer.get('condition', '').lower() == product_condition, 
                offers
            )
        elif compete_with == "MATCH_BUYBOX":
            filtered_result = filter(
                lambda offer: offer.get('condition', '').lower() == product_condition,
                offers
            )
        else:
            filtered_result = iter([])

        return filtered_result

    def _set_fba_lowest_price(self) -> None:
        """Retrieves the minimum FBA price."""
        offers = self.payload.get('Offers', [])
        product_condition = self.product.mapped_item_condition
        
        filtered_offers = filter(
            lambda offer: offer.get('SubCondition', '').lower() == product_condition 
            and offer.get('IsFulfilledByAmazon'),
            offers
        )
        sorted_offers = sorted(filtered_offers, key=lambda offer: offer.get('ListingPrice.Amount', 0))

        if not sorted_offers:            
            raise SkipProductRepricing(f'Competitor not found for {self.product.asin}...')
        
        competitor_offer = sorted_offers[0]
        if competitor_offer.get('SellerId') == self.product.account.seller_id:
            if len(sorted_offers) > 1:
                competitor_offer = sorted_offers[1]
            else:
                raise SkipProductRepricing(
                    f'Skipping Repricing! of ASIN: {self.product.asin} for SELLER_ID: {self.product.account.seller_id} - (This seller has the only FBA offer)'
                )

        self.product.competitor_price = competitor_offer.get('ListingPrice.Amount')

    def _set_min_price(self) -> None:
        """Retrieves the minimum price from all offers."""
        offers = self.payload.get('Offers', [])
        product_condition = self.product.mapped_item_condition
        
        filtered_offers = filter(
            lambda offer: offer.get('SubCondition', '').lower() == product_condition,
            offers
        )
        sorted_offers = sorted(filtered_offers, key=lambda offer: offer.get('ListingPrice.Amount', 0))

        if not sorted_offers:
            raise SkipProductRepricing(f'Min price not found for ASIN: {self.product.asin}...')

        competitor_offer = sorted_offers[0]
        if competitor_offer.get('SellerId') == self.product.account.seller_id:
            if len(sorted_offers) > 1:
                competitor_offer = sorted_offers[1]
            else:
                raise SkipProductRepricing(
                    f'Skipping Repricing! of ASIN: {self.product.asin} for SELLER_ID: {self.product.account.seller_id} - (This seller has the only offer)'
                )

        self.product.competitor_price = competitor_offer.get('ListingPrice.Amount')

    def _set_buybox_price(self) -> None:
        """Retrieves the buybox price."""
        competitor_offer = self._get_competitor_offer()
        self.product.competitor_price = competitor_offer.get('ListingPrice.Amount')

    def _get_competitor_offer(self) -> Dict[str, Any]:
        """Retrieves the buybox winner offer."""
        offers = self.payload.get('Offers', [])
        competitor_offer = next((offer for offer in offers if offer.get('IsBuyBoxWinner')), None)

        if not competitor_offer:
            raise SkipProductRepricing(
                f'Buybox is suppressed. No competitor found for ASIN: {self.product.asin}...'
            )

        if competitor_offer.get('SellerId') == self.product.account.seller_id:
            self.product.is_seller_buybox_winner = True
            try:
                competitor_offer = offers[1]
            except IndexError:
                raise SkipProductRepricing(
                    f'Seller has the buy box, but competitor does not exist for ASIN: {self.product.asin}...'
                )

        return competitor_offer

    def _validate_product(self, product: Any) -> None:
        """Validate product data after competitor analysis."""
        # TODO: Implement product validation logic
        pass