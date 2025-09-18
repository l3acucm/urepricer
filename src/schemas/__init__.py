"""
Pydantic schemas for Arbitrage Hero API.
Provides request/response validation and serialization for all endpoints.
"""
from .messages import WalmartWebhookMessage, ComprehensiveCompetitionData, CompetitorInfo, ProcessedOfferData, \
    WalmartOfferChange

# Export all schemas for easy importing
__all__ = [
    "WalmartWebhookMessage",
    "ProcessedOfferData",
    "WalmartOfferChange",
    "ComprehensiveCompetitionData",
    "CompetitorInfo"
]
