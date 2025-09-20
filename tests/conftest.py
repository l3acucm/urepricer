import os
import sys
from unittest.mock import AsyncMock, Mock

import pytest

# Add src directory to path BEFORE importing modules
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_dir)

from core.config import Settings  # noqa: E402
from services.message_processor import MessageProcessor  # noqa: E402
from services.redis_service import RedisService  # noqa: E402
from services.repricing_engine import RepricingEngine  # noqa: E402
from services.repricing_orchestrator import RepricingOrchestrator  # noqa: E402


@pytest.fixture
def mock_settings():
    """Create a mock settings object for tests."""
    settings = Settings(
        redis_host="localhost",
        redis_port=6379,
        log_level="INFO",
        debug=True,
        cors_origins=["*"]
    )
    return settings


@pytest.fixture
def mock_logger():
    """Create a mock structlog logger for tests."""
    # Simple mock that has the structlog interface
    mock_logger = Mock()
    mock_logger.info = Mock()
    mock_logger.error = Mock()
    mock_logger.warning = Mock()
    mock_logger.debug = Mock()
    return mock_logger


@pytest.fixture
def mock_redis_service(mock_settings, mock_logger):
    """Create a mock RedisService for tests."""
    redis_service = AsyncMock(spec=RedisService)
    redis_service.settings = mock_settings
    redis_service.logger = mock_logger
    return redis_service


@pytest.fixture
def message_processor(mock_redis_service, mock_settings, mock_logger):
    """Create a MessageProcessor instance with mocked dependencies."""
    return MessageProcessor(mock_redis_service, mock_settings, mock_logger)


@pytest.fixture
def repricing_engine(mock_redis_service, mock_settings, mock_logger):
    """Create a RepricingEngine instance with mocked dependencies."""
    return RepricingEngine(mock_redis_service, mock_settings, mock_logger)


@pytest.fixture
def repricing_orchestrator(mock_redis_service, mock_settings, mock_logger):
    """Create a RepricingOrchestrator instance with mocked dependencies."""
    return RepricingOrchestrator(
        redis_service=mock_redis_service,
        settings=mock_settings,
        logger=mock_logger,
        max_concurrent_workers=50,
        batch_size=100
    )
