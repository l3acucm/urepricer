"""Dependency injection configuration for the urepricer application."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from containers import container
from core.config import Settings
from services.error_handler import ErrorHandler
from services.message_processor import MessageProcessor
from services.redis_service import RedisService
from services.repricing_engine import RepricingEngine
from services.repricing_orchestrator import RepricingOrchestrator
from services.sqs_consumer import SQSConsumer


# Dependency providers for FastAPI
async def get_settings() -> Settings:
    """Get Settings from DI container."""
    return container.settings()


async def get_logger(name: str) -> logging.Logger:
    """Get Logger from DI container."""
    return container.logger_factory(name)


async def get_redis_service() -> RedisService:
    """Get Redis service from DI container."""
    return container.redis_service()


async def get_repricing_engine() -> RepricingEngine:
    """Get RepricingEngine from DI container."""
    return container.repricing_engine()


async def get_repricing_orchestrator() -> RepricingOrchestrator:
    """Get RepricingOrchestrator from DI container."""
    return container.repricing_orchestrator()


async def get_message_processor() -> MessageProcessor:
    """Get MessageProcessor from DI container."""
    return container.message_processor()


async def get_sqs_consumer() -> SQSConsumer:
    """Get SQSConsumer from DI container."""
    return container.sqs_consumer()


async def get_error_handler() -> ErrorHandler:
    """Get ErrorHandler from DI container."""
    return container.error_handler()


# Legacy alias for backward compatibility
async def get_settings_from_di() -> Settings:
    """Get Settings from DI container (legacy alias)."""
    return await get_settings()


# Context manager for proper cleanup
@asynccontextmanager
async def get_di_lifespan() -> AsyncGenerator[None, None]:
    """Manage DI container lifecycle."""
    try:
        # Initialize the container
        container.init_resources()
        yield
    finally:
        # Cleanup resources - explicitly close Redis connection
        try:
            if hasattr(container.redis_service, '_provided'):
                redis_service = container.redis_service()
                await redis_service.close_connection()
        except Exception:
            pass  # Ignore cleanup errors
        finally:
            container.shutdown_resources()
