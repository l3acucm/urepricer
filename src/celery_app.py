"""Celery configuration for URepricer background tasks."""

from celery import Celery
from celery.schedules import crontab

from core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "urepricer",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}",
    backend=f"redis://{settings.redis_host}:{settings.redis_port}",
    include=["src.tasks.price_reset"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 60,  # 1 hour
    task_soft_time_limit=50 * 60,  # 50 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Schedule hourly price reset task
celery_app.conf.beat_schedule = {
    "hourly-price-reset": {
        "task": "src.tasks.price_reset.check_and_reset_prices",
        "schedule": crontab(minute=0),  # Run every hour on the hour
    },
}
celery_app.conf.timezone = "UTC"
