"""
Arbitrage Hero FastAPI Application
Main entry point for the consolidated arbitrage repricer system.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.core.config import get_settings
from src.api.webhook_router import router as webhook_router
from src.services.sqs_consumer import get_sqs_consumer
# from src.api.accounts.router import router as accounts_router
# from src.api.repricing.router import router as repricing_router
# from src.api.feeds.router import router as feeds_router
# from src.api.listings.router import router as listings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Arbitrage Hero API...")
    
    # Redis-only application - no database tables needed
    
    # Note: SQS consumer should be run separately via: python3 -m src.services.sqs_consumer
    
    logger.info("Arbitrage Hero API started successfully")
    yield
    
    logger.info("Shutting down Arbitrage Hero API...")


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
    # app.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
    # app.include_router(repricing_router, prefix="/repricing", tags=["repricing"])
    # app.include_router(feeds_router, prefix="/feeds", tags=["feeds"])
    # app.include_router(listings_router, prefix="/listings", tags=["listings"])
    
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
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )