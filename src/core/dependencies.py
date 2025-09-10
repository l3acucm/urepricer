"""
FastAPI dependency injection setup.
Provides service layer dependencies following SOLID principles.
"""
from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.config import get_settings, Settings
from src.services.accounts_service import AccountsService
from src.services.repricing_service import RepricingService
from src.services.feeds_service import FeedsService
from src.services.listings_service import ListingsService
from src.services.amazon_api_service import AmazonApiService
from src.services.notification_service import NotificationService


# Type aliases for dependency injection
DatabaseDep = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache()
def get_amazon_api_service() -> AmazonApiService:
    """Get cached Amazon API service instance."""
    return AmazonApiService()


@lru_cache()
def get_notification_service() -> NotificationService:
    """Get cached notification service instance."""
    return NotificationService()


def get_accounts_service(
    db: DatabaseDep,
    settings: SettingsDep,
    amazon_api: Annotated[AmazonApiService, Depends(get_amazon_api_service)],
    notification: Annotated[NotificationService, Depends(get_notification_service)]
) -> AccountsService:
    """Get accounts service with injected dependencies."""
    return AccountsService(
        db=db,
        settings=settings,
        amazon_api=amazon_api,
        notification=notification
    )


def get_repricing_service(
    db: DatabaseDep,
    settings: SettingsDep,
) -> RepricingService:
    """Get repricing service with injected dependencies."""
    return RepricingService(db=db, settings=settings)


def get_feeds_service(
    db: DatabaseDep,
    settings: SettingsDep,
    amazon_api: Annotated[AmazonApiService, Depends(get_amazon_api_service)],
) -> FeedsService:
    """Get feeds service with injected dependencies."""
    return FeedsService(db=db, settings=settings, amazon_api=amazon_api)


def get_listings_service(
    db: DatabaseDep,
    settings: SettingsDep,
    notification: Annotated[NotificationService, Depends(get_notification_service)]
) -> ListingsService:
    """Get listings service with injected dependencies."""
    return ListingsService(db=db, settings=settings, notification=notification)


# Type aliases for service dependencies
AccountsServiceDep = Annotated[AccountsService, Depends(get_accounts_service)]
RepricingServiceDep = Annotated[RepricingService, Depends(get_repricing_service)]
FeedsServiceDep = Annotated[FeedsService, Depends(get_feeds_service)]
ListingsServiceDep = Annotated[ListingsService, Depends(get_listings_service)]