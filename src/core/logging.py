"""
Logging configuration using Loguru.
Consolidates logging from all original modules.
"""
import sys
from loguru import logger
from src.core.config import get_settings


def setup_logging():
    """Configure Loguru logger with appropriate settings."""
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Add console handler with format
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )
    
    # Add file handler for production
    if not settings.debug:
        logger.add(
            "logs/arbitrage-hero.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level=settings.log_level,
            rotation="100 MB",
            retention="30 days",
            compression="gzip",
        )
    
    logger.info("Logging configuration initialized")


def get_logger(name: str):
    """Get a logger instance for a specific module."""
    return logger.bind(name=name)