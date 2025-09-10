"""Structured logging configuration."""

import atexit
import logging
import queue
import sys
import threading
import time
from typing import Any, Optional
from zoneinfo import ZoneInfo
from datetime import datetime
import json

import requests
import structlog

from config import settings


def setup_logging() -> structlog.BoundLogger:
    """Configure structured logging once per entrypoint."""

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Add ELK handler if configured
    elk_host = getattr(settings, "elasticsearch_host", None)
    if elk_host and elk_host.strip():
        try:
            elk_handler = ELKHandler()

            # Check if we're in a solo pool environment (no threading)
            import os
            if os.getenv("CELERY_POOL") == "solo":
                elk_handler.direct_send = True
                print("ELK handler configured for direct send (solo pool)")

            logging.getLogger().addHandler(elk_handler)
            print("ELK handler added to root logger")
        except Exception as e:
            print(f"Failed to add ELK handler: {e}")
    else:
        print("ELK handler not configured - elasticsearch_host not set")

    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_thread_info,
        add_host_info,
        redis_stats_processor,
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    print("Structured logging configuration completed")
    return structlog.get_logger()


def add_thread_info(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add thread information to log entries."""
    event_dict["thread_name"] = threading.current_thread().name
    return event_dict


def add_host_info(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add thread information to log entries."""
    event_dict["host"] = settings.host
    return event_dict


def _increment_redis_stats(event_name: str, host: str) -> None:
    """Increment Redis stats for a specific event name."""
    try:
        # Import here to avoid circular imports
        from utils.redis_client import redis_client

        # Run the increment operation
        redis_client.increment_stats(event_name)
        redis_client.increment_stats(f'processed-messages-{host}')
    except Exception:
        # Silently ignore Redis errors to avoid disrupting logging
        pass


def redis_stats_processor(
        logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Process log events and increment Redis stats asynchronously."""
    # Extract event name (first positional argument or 'event' key)
    event_name = None
    if "event" in event_dict:
        event_name = event_dict["event"]
    elif len(event_dict.get("positional_args", [])) > 0:
        event_name = event_dict["positional_args"][0]
    if event_name == 'message_processing_result':
        # Skip Redis-related events to avoid infinite loops
        status = event_dict['status']
        host = event_dict['host']
        threading.Thread(target=_increment_redis_stats, args=(status, host), daemon=True).start()

    return event_dict


class ELKHandler(logging.Handler):
    """Handler for forwarding logs to ELK stack using shared sender."""

    _shared_sender: Optional["ELKSender"] = None
    _sender_lock = threading.Lock()

    def __init__(self):
        super().__init__()
        self.enabled = bool(getattr(settings, "elasticsearch_host", None))
        self.direct_send = False  # Flag to send directly without background thread

        if self.enabled:
            self._ensure_sender()

    def _ensure_sender(self):
        """Ensure shared sender exists."""
        with self._sender_lock:
            if self._shared_sender is None:
                self._shared_sender = ELKSender(settings.elasticsearch_host)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit log record to ELK."""
        if not self.enabled:
            return

        try:
            # Parse message data
            try:
                message_data = json.loads(record.getMessage())
            except (json.JSONDecodeError, TypeError):
                message_data = {"message": record.getMessage()}

            # Build log entry
            log_entry = {
                **message_data,
                "timestamp": datetime.fromtimestamp(record.created, tz=ZoneInfo("UTC")).astimezone().isoformat(),
                "level": record.levelname,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "thread_name": threading.current_thread().name,
            }

            # Send directly or via background thread
            if self.direct_send:
                self._send_direct(log_entry)
            elif self._shared_sender:
                self._shared_sender.send(log_entry)

        except Exception:
            pass  # Fail silently

    def _send_direct(self, log_entry: dict) -> None:
        """Send log entry directly to ELK without background thread."""
        try:
            elk_host = getattr(settings, "elasticsearch_host", None)
            if not elk_host:
                return

            bulk_url = f"http://{elk_host}/_bulk"
            index_name = getattr(settings, "log_index_name", "image-comparison-logs")

            # Build bulk request body
            bulk_body = []
            bulk_body.append(json.dumps({"index": {"_index": index_name}}))
            bulk_body.append(json.dumps(log_entry))
            bulk_data = "\n".join(bulk_body) + "\n"

            response = requests.post(
                bulk_url,
                data=bulk_data,
                headers={"Content-Type": "application/x-ndjson"},
                auth=(getattr(settings, "elasticsearch_username", None),
                      getattr(settings, "elasticsearch_password", None)),
                timeout=2.0,
            )

            # Don't log errors to avoid infinite loops

        except Exception:
            pass  # Fail silently


class ELKSender:
    """Dedicated thread for sending logs to ELK stack."""

    def __init__(self, elk_host: str):
        self.elk_host = elk_host
        self.bulk_url = f"http://{elk_host}/_bulk"
        self.log_queue = queue.Queue(maxsize=settings.log_queue_size)
        self.stop_event = threading.Event()
        self.batch_size = settings.log_batch_size  # Send 50 logs per batch
        self.batch_timeout = settings.log_batch_timeout  # Send batch every 1 second max
        self.thread = threading.Thread(target=self._worker, name="ELKSender", daemon=True)
        self.thread.start()
        atexit.register(self.stop)

    def _worker(self):
        """Worker thread that sends logs to ELK using batching."""

        batch = []
        last_send_time = time.time()

        while not self.stop_event.is_set():
            try:
                log_entry = self.log_queue.get(timeout=0.1)
                batch.append(log_entry)
                self.log_queue.task_done()

                # Send batch if size limit reached or timeout exceeded
                current_time = time.time()
                should_send = (
                        len(batch) >= self.batch_size
                        or (current_time - last_send_time) >= self.batch_timeout
                )

                if should_send and batch:
                    self._send_batch(batch, requests)
                    batch = []
                    last_send_time = current_time

            except queue.Empty:
                # Send remaining batch on timeout
                current_time = time.time()
                if batch and (current_time - last_send_time) >= self.batch_timeout:
                    self._send_batch(batch, requests)
                    batch = []
                    last_send_time = current_time
                continue
        else:
            print('LOG WORKER STOPPED!!!!')

        # Send remaining logs when stopping
        if batch:
            self._send_batch(batch, requests)

    def _send_batch(self, batch: list, requests) -> None:
        """Send batch of logs to ELK using bulk API."""
        if not batch:
            return

        # Build bulk request body
        bulk_body = []
        index_name = settings.log_index_name

        # Debug index name

        for log_entry in batch:
            # Add index operation
            bulk_body.append(json.dumps({"index": {"_index": index_name}}))
            bulk_body.append(json.dumps(log_entry))

        bulk_data = "\n".join(bulk_body) + "\n"

        # Debug first few lines of bulk data
        lines = bulk_data.split('\n')[:4]

        try:
            response = requests.post(
                self.bulk_url,
                data=bulk_data,
                headers={"Content-Type": "application/x-ndjson"},
                auth=(settings.elasticsearch_username, settings.elasticsearch_password),
                timeout=5.0,
            )

            # Check for Elasticsearch bulk API errors
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get("errors"):
                        print(f"DEBUG: ELK bulk errors: {response_data}", flush=True)
                except json.JSONDecodeError:
                    print("DEBUG: ELK response not JSON, but status 200", flush=True)
            else:
                print(f"DEBUG: ELK error response: {response.text}", flush=True)

        except requests.RequestException as e:
            print(f"DEBUG: Failed to send batch to ELK: {e}", flush=True)

    def send(self, log_entry: dict[str, Any]) -> None:
        """Send log entry to ELK (non-blocking)."""
        try:
            self.log_queue.put_nowait(log_entry)
        except queue.Full:
            print("DEBUG: ELK queue FULL - dropping log", flush=True)
            pass  # Drop log if queue is full

    def stop(self):
        """Stop the sender thread."""
        self.stop_event.set()
        try:
            self.log_queue.join()
        except Exception:
            pass
        self.thread.join(timeout=2.0)
