"""
Arbitrage Hero FastAPI Application
Main entry point for the consolidated arbitrage repricer system.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.webhook_router import router as webhook_router
from core.config import get_settings
from core.logging import setup_logging
from di_config import get_di_lifespan

# Initialize structlog
logger = setup_logging()

# Configure logging to suppress verbose boto3/botocore logs
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('botocore.endpoint').setLevel(logging.WARNING)
logging.getLogger('botocore.auth').setLevel(logging.WARNING)
logging.getLogger('botocore.retryhandler').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events with DI container management."""
    logger.info("starting_arbitrage_hero_api", 
               redis_structure="v2_optimized", version="1.0")

    # Initialize DI container
    async with get_di_lifespan():
        # Test Redis connection
        from di_config import get_redis_service

        redis_service = await get_redis_service()
        health = await redis_service.health_check()

        if health:
            logger.info("redis_structure_initialized_successfully", 
                       redis_health=health)
        else:
            logger.error("redis_connection_failed", 
                        redis_health=health)

        # Note: SQS consumer should be run separately via: python3 -m services.sqs_consumer

        logger.info("arbitrage_hero_api_started_successfully", 
                   redis_healthy=bool(health))
        yield

    logger.info("shutting_down_arbitrage_hero_api")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Arbitrage Hero API",
        description="Consolidated Amazon marketplace repricing system",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(webhook_router, tags=["webhooks"])

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "arbitrage-hero"}

    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
