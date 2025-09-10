"""
SQLAlchemy models for Arbitrage Hero.
Consolidates all database models from the original Django modules.
"""

# Import all models to ensure they're registered with SQLAlchemy
from .accounts import UserAccount, PriceReset
from .feeds import Feed, Product, PriceChangeLog, RepricingStrategy
from .listings import ProductListing, CompetitorData, ListingAlert

# Export all models for easy importing
__all__ = [
    # Account models
    "UserAccount",
    "PriceReset",
    
    # Feed models
    "Feed", 
    "Product",
    "PriceChangeLog",
    "RepricingStrategy",
    
    # Listing models
    "ProductListing",
    "CompetitorData", 
    "ListingAlert",
]