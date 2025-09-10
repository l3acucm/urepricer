"""
Application configuration using Pydantic Settings.
Consolidates all environment variables from the original modules.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Testing mode
    testing: bool = Field(default=False, env="TESTING")
    
    # Application settings
    debug: bool = Field(default=False, env="DEBUG")
    secret_key: str = Field(default="test-secret-key", env="SECRET_KEY")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Database configuration
    database_url: str = Field(default="postgresql://test:test@localhost/test", env="DATABASE_URL")
    db_name: str = Field(env="DB_NAME", default="arbitrage_hero")
    db_user: str = Field(env="USER_NAME", default="postgres")
    db_password: str = Field(default="test-password", env="PASSWORD")
    db_host: str = Field(env="HOST", default="localhost")
    db_port: int = Field(env="POSTGRES_PORT", default=5432)
    
    # Redis configuration (for Celery only)
    redis_url: str = Field(env="REDIS_URL", default="redis://localhost:6379/0")
    redis_host: str = Field(env="REDIS_HOST", default="localhost")
    redis_port: int = Field(env="REDIS_PORT", default=6379)
    redis_password: Optional[str] = Field(env="REDIS_PASSWORD", default=None)
    
    # Celery configuration
    celery_broker_url: str = Field(env="CELERY_BROKER_URL", default="redis://localhost:6379/0")
    celery_result_backend: str = Field(env="CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
    
    # JWT Configuration
    jwt_secret_key: str = Field(default="test-jwt-secret", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60 * 24 * 7, env="JWT_EXPIRE_MINUTES")  # 7 days
    
    # Amazon SP-API Configuration
    amazon_client_id: str = Field(default="test-client-id", env="AMAZON_CLIENT_ID")
    amazon_client_secret: str = Field(default="test-client-secret", env="AMAZON_CLIENT_SECRET")
    amazon_refresh_token: str = Field(default="test-refresh-token", env="AMAZON_REFRESH_TOKEN")
    
    # AWS Configuration
    aws_access_key_id: str = Field(default="test-access-key", env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="test-secret-key", env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(env="AWS_REGION", default="us-east-1")
    role_arn: Optional[str] = Field(env="ROLE_ARN", default=None)
    aws_endpoint_url: Optional[str] = Field(env="AWS_ENDPOINT_URL", default=None)  # For LocalStack
    
    # SQS Configuration
    sqs_queue_url_any_offer: str = Field(default="test-queue-url", env="SQS_QUEUE_URL_ANY_OFFER")
    sqs_queue_url_feed_processing: str = Field(default="test-queue-url", env="SQS_QUEUE_URL_FEED_PROCESSING")
    
    # Notification destinations (per marketplace)
    destination_id_us: str = Field(default="test-destination-us", env="DESTINATION_ID_US")
    destination_id_uk: str = Field(default="test-destination-uk", env="DESTINATION_ID_UK")
    destination_id_ca: str = Field(default="test-destination-ca", env="DESTINATION_ID_CA")
    destination_id_au: Optional[str] = Field(env="DESTINATION_ID_AU", default=None)
    
    # Kafka Configuration (for external integrations only)
    kafka_bootstrap_servers: str = Field(env="KAFKA_BOOTSTRAP_SERVERS", default="localhost:9092")
    kafka_topics: dict = Field(default={
        "alert_user_topic": "alert_user_topic",
        "price_updates": "price_updates",
        "notifications": "notifications"
    })
    
    # Slack notifications
    slack_webhook_url: Optional[str] = Field(env="SLACK_WEBHOOK_URL", default=None)
    
    # Business logic settings
    default_min_price: float = Field(default=1.00, env="DEFAULT_MIN_PRICE")
    default_max_price: float = Field(default=999.99, env="DEFAULT_MAX_PRICE")
    feed_batch_size: int = Field(default=1000, env="FEED_BATCH_SIZE")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Marketplace configuration
    marketplace_timezones: dict = Field(default={
        "US": "America/New_York",
        "UK": "Europe/London",
        "AU": "Australia/Sydney",
        "CA": "America/Toronto"
    })
    
    marketplace_ids: dict = Field(default={
        "US": "ATVPDKIKX0DER",
        "UK": "A1F83G8C2ARO7P", 
        "AU": "A39IBJ37TRP1C6",
        "CA": "A2EUQ1WTGCTBG2"
    })
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @property
    def sync_database_url(self) -> str:
        """Get synchronous database URL for SQLAlchemy."""
        return str(self.database_url).replace("postgresql+asyncpg://", "postgresql://")


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()