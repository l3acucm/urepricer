"""Dependency injection container configuration using dependency-injector."""

import structlog
from dependency_injector import containers, providers

from core.config import get_settings
from core.logging import setup_logging
from services.error_handler import ErrorHandler
from services.message_processor import MessageProcessor
from services.redis_service import RedisService
from services.repricing_engine import RepricingEngine
from services.repricing_orchestrator import RepricingOrchestrator
from services.sqs_consumer import SQSConsumer
from services.update_product_service import AmazonProductPrice

# Initialize structlog once
_structlog_initialized = False


def create_logger(name: str, settings=None) -> structlog.BoundLogger:
    """Create and configure a structlog logger instance."""
    global _structlog_initialized
    
    if not _structlog_initialized:
        setup_logging()
        _structlog_initialized = True
    
    return structlog.get_logger(name)


class Container(containers.DeclarativeContainer):
    """Main DI container for the urepricer application."""

    # Configuration
    config = providers.Configuration()

    # Settings provider
    settings = providers.Singleton(
        get_settings,
    )

    # Logger factory
    logger_factory = providers.Factory(
        create_logger,
        settings=settings,
    )

    # Core services
    redis_service = providers.Singleton(
        RedisService,
        settings=settings,
        logger=logger_factory("redis_service"),
    )

    # Business logic services
    repricing_engine = providers.Singleton(
        RepricingEngine,
        redis_service=redis_service,
        settings=settings,
        logger=logger_factory("repricing_engine"),
    )

    message_processor = providers.Singleton(
        MessageProcessor,
        redis_service=redis_service,
        settings=settings,
        logger=logger_factory("message_processor"),
    )

    repricing_orchestrator = providers.Singleton(
        RepricingOrchestrator,
        redis_service=redis_service,
        settings=settings,
        logger=logger_factory("repricing_orchestrator"),
        message_processor=message_processor,
        repricing_engine=repricing_engine,
    )

    # Infrastructure services
    sqs_consumer = providers.Singleton(
        SQSConsumer,
        settings=settings,
        logger=logger_factory("sqs_consumer"),
        redis_service=redis_service,
        repricing_orchestrator=repricing_orchestrator,
    )

    amazon_product_price = providers.Singleton(
        AmazonProductPrice,
        redis_service=redis_service,
        settings=settings,
        logger=logger_factory("amazon_product_price"),
    )

    error_handler = providers.Singleton(
        ErrorHandler,
        settings=settings,
        logger=logger_factory("error_handler"),
    )

    def init_resources(self):
        """Initialize container resources."""
        # The container initializes resources lazily when they are first accessed
        pass

    def shutdown_resources(self):
        """Cleanup container resources."""
        # Reset providers to clean up resources
        self.reset_singletons()


# Global container instance
container = Container()