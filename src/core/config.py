"""
Application configuration using Pydantic Settings.
Consolidates all environment variables from the original modules.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Testing mode
    testing: bool = Field(default=False, description="Testing mode")

    # Application settings
    debug: bool = Field(default=False, description="Debug mode")
    secret_key: str = Field(default="test-secret-key", description="Secret key")
    cors_origins: List[str] = Field(default=["*"], description="CORS origins")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Redis configuration (for Celery only)
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")

    # AWS Configuration
    aws_access_key_id: str = Field(default="test-access-key", description="AWS access key")
    aws_secret_access_key: str = Field(
        default="test-secret-key", description="AWS secret key"
    )
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_endpoint_url: Optional[str] = Field(
        default=None, description="AWS endpoint URL (for LocalStack)"
    )

    # SQS Configuration
    sqs_queue_url_any_offer: str = Field(description="SQS queue URL for any offer"
    )
    sqs_queue_url_feed_processing: str = Field(description="SQS queue URL for feed processing"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level")

    # MySQL Configuration
    mysql_host: str = Field(default="localhost", description="MySQL host")
    mysql_port: int = Field(default=3306, description="MySQL port")
    mysql_database: str = Field(default="your_database_name", description="MySQL database")
    mysql_username: str = Field(default="your_username", description="MySQL username")
    mysql_password: str = Field(default="your_password", description="MySQL password")

    # Logging Configuration
    log_format: str = Field(default="console", description="Log format: json or console")
    host: str = Field(default="localhost", description="Host identifier for logs")
    
    # ELK Stack Configuration
    elasticsearch_host: Optional[str] = Field(default=None, description="Elasticsearch host")
    elasticsearch_username: Optional[str] = Field(default=None, description="Elasticsearch username")
    elasticsearch_password: Optional[str] = Field(default=None, description="Elasticsearch password")
    log_index_name: str = Field(default="arbitrage-hero-logs", description="Elasticsearch log index name")
    log_queue_size: int = Field(default=1000, description="Log queue size")
    log_batch_size: int = Field(default=50, description="Log batch size for ELK")
    log_batch_timeout: float = Field(default=1.0, description="Log batch timeout in seconds")
    
    # Alerting Configuration
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL for error alerts")
    email_alerts_enabled: bool = Field(default=False, description="Enable email alerts")
    email_alert_recipients: List[str] = Field(default=[], description="Email recipients for alerts")
    alert_file_directory: str = Field(default="/tmp/urepricer_alerts", description="Directory for alert files")
    
    # Notification Configuration
    redis_notifications_enabled: bool = Field(default=True, description="Enable Redis pubsub notifications")
    file_notifications_enabled: bool = Field(default=False, description="Enable file-based notifications")
    notifications_directory: str = Field(default="/tmp/urepricer_notifications", description="Directory for notification files")
    
    # Amazon Product Data Constants
    amazon_output_fields: List[str] = Field(
        default=["asin", "sku", "seller_id", "updated_price", "listed_price"],
        description="Fields to include in Amazon product output"
    )
    amazon_log_fields: List[str] = Field(
        default=["asin", "sku", "seller_id", "updated_price", "listed_price", "time"],
        description="Fields to include in Amazon product logs"
    )

    model_config = ConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",
        # Environment variable mappings
        env_nested_delimiter="__",
        extra="ignore",  # Ignore extra environment variables
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
