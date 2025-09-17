"""
Application configuration using Pydantic Settings.
Consolidates all environment variables from the original modules.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Testing mode
    testing: bool = Field(default=False, env="TESTING")
    
    # Application settings
    debug: bool = Field(default=False, env="DEBUG")
    secret_key: str = Field(default="test-secret-key", env="SECRET_KEY")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")

    # Redis configuration (for Celery only)
    redis_host: str = Field(env="REDIS_HOST", default="localhost")
    redis_port: int = Field(env="REDIS_PORT", default=6379)
    redis_password: Optional[str] = Field(env="REDIS_PASSWORD", default=None)

    # AWS Configuration
    aws_access_key_id: str = Field(default="test-access-key", env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="test-secret-key", env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(env="AWS_REGION", default="us-east-1")
    aws_endpoint_url: Optional[str] = Field(env="AWS_ENDPOINT_URL", default=None)  # For LocalStack
    
    # SQS Configuration
    sqs_queue_url_any_offer: str = Field(default="test-queue-url", env="SQS_QUEUE_URL_ANY_OFFER")
    sqs_queue_url_feed_processing: str = Field(default="test-queue-url", env="SQS_QUEUE_URL_FEED_PROCESSING")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()