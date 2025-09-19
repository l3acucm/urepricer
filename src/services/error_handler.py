"""Comprehensive error handling and dead letter queue support."""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, UTC
from enum import Enum
from loguru import logger
import boto3

from schemas.messages import ProcessedOfferData, RepricingDecision
from core.config import get_settings


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    NETWORK = "network"
    CONFIGURATION = "configuration"


class RepricingError:
    """Structured error information for repricing operations."""
    
    def __init__(
        self,
        error_type: str,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
        retry_count: int = 0,
        max_retries: int = 3
    ):
        self.error_type = error_type
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.original_exception = original_exception
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.timestamp = datetime.now(UTC)
        self.error_id = self._generate_error_id()
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID."""
        import uuid
        return f"err_{int(self.timestamp.timestamp())}_{str(uuid.uuid4())[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timestamp": self.timestamp.isoformat(),
            "exception_type": type(self.original_exception).__name__ if self.original_exception else None
        }
    
    def is_retryable(self) -> bool:
        """Check if error is retryable."""
        return (
            self.retry_count < self.max_retries and
            self.category in [ErrorCategory.NETWORK, ErrorCategory.EXTERNAL_SERVICE] and
            self.severity != ErrorSeverity.CRITICAL
        )
    
    def should_alert(self) -> bool:
        """Check if error should trigger alerts."""
        return self.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]


class ErrorHandler:
    """Comprehensive error handling for the repricing pipeline."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logger.bind(service="error_handler")
        
        # Initialize SQS client for DLQ operations
        self.sqs = boto3.client(
            'sqs',
            region_name=getattr(self.settings, 'aws_region', 'us-east-1'),
            aws_access_key_id=getattr(self.settings, 'aws_access_key_id', None),
            aws_secret_access_key=getattr(self.settings, 'aws_secret_access_key', None)
        )
        
        # Error statistics
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "retry_attempts": 0,
            "dlq_sends": 0,
            "alerts_sent": 0
        }
        
        # DLQ URLs (configured via settings)
        self.dlq_urls = {
            "amazon": getattr(self.settings, 'amazon_dlq_url', None),
            "walmart": getattr(self.settings, 'walmart_dlq_url', None),
            "general": getattr(self.settings, 'general_dlq_url', None)
        }
    
    async def handle_message_processing_error(
        self,
        error: Exception,
        message: Dict[str, Any],
        message_type: str = "unknown",
        context: Optional[Dict[str, Any]] = None
    ) -> RepricingError:
        """
        Handle errors during message processing.
        
        Args:
            error: The exception that occurred
            message: The message that caused the error
            message_type: Type of message (amazon, walmart, etc.)
            context: Additional context information
            
        Returns:
            RepricingError: Structured error information
        """
        error_context = {
            "message_type": message_type,
            "message_id": message.get("MessageId", message.get("webhookId", "unknown")),
            **(context or {})
        }
        
        # Classify the error
        category, severity = self._classify_error(error)
        
        repricing_error = RepricingError(
            error_type=type(error).__name__,
            message=str(error),
            category=category,
            severity=severity,
            context=error_context,
            original_exception=error
        )
        
        # Log the error
        await self._log_error(repricing_error)
        
        # Update statistics
        self._update_error_stats(repricing_error)
        
        # Handle error based on severity
        await self._handle_error_by_severity(repricing_error, message, message_type)
        
        return repricing_error
    
    async def handle_repricing_decision_error(
        self,
        error: Exception,
        processed_data: ProcessedOfferData,
        context: Optional[Dict[str, Any]] = None
    ) -> RepricingError:
        """Handle errors during repricing decision making."""
        error_context = {
            "asin": processed_data.product_id,
            "seller_id": processed_data.seller_id,
            "platform": processed_data.platform,
            **(context or {})
        }
        
        category, severity = self._classify_error(error)
        
        repricing_error = RepricingError(
            error_type=type(error).__name__,
            message=str(error),
            category=category,
            severity=severity,
            context=error_context,
            original_exception=error
        )
        
        await self._log_error(repricing_error)
        self._update_error_stats(repricing_error)
        
        return repricing_error
    
    async def handle_price_calculation_error(
        self,
        error: Exception,
        decision: RepricingDecision,
        context: Optional[Dict[str, Any]] = None
    ) -> RepricingError:
        """Handle errors during price calculation."""
        error_context = {
            "asin": decision.asin,
            "sku": decision.sku,
            "seller_id": decision.seller_id,
            "strategy_id": decision.strategy_id,
            **(context or {})
        }
        
        category, severity = self._classify_error(error)
        
        repricing_error = RepricingError(
            error_type=type(error).__name__,
            message=str(error),
            category=category,
            severity=severity,
            context=error_context,
            original_exception=error
        )
        
        await self._log_error(repricing_error)
        self._update_error_stats(repricing_error)
        
        return repricing_error
    
    async def send_to_dead_letter_queue(
        self,
        message: Dict[str, Any],
        error: RepricingError,
        queue_type: str = "general"
    ) -> bool:
        """
        Send failed message to dead letter queue.
        
        Args:
            message: Original message that failed
            error: Error information
            queue_type: Type of DLQ (amazon, walmart, general)
            
        Returns:
            bool: True if successfully sent to DLQ
        """
        dlq_url = self.dlq_urls.get(queue_type)
        if not dlq_url:
            self.logger.warning(f"No DLQ configured for type: {queue_type}")
            return False
        
        try:
            # Prepare DLQ message with error information
            dlq_message = {
                "original_message": message,
                "error_info": error.to_dict(),
                "failed_at": datetime.now(UTC).isoformat(),
                "queue_type": queue_type
            }
            
            # Send to DLQ
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.sqs.send_message(
                    QueueUrl=dlq_url,
                    MessageBody=json.dumps(dlq_message),
                    MessageAttributes={
                        'ErrorType': {
                            'StringValue': error.error_type,
                            'DataType': 'String'
                        },
                        'ErrorSeverity': {
                            'StringValue': error.severity.value,
                            'DataType': 'String'
                        },
                        'QueueType': {
                            'StringValue': queue_type,
                            'DataType': 'String'
                        }
                    }
                )
            )
            
            self.error_stats["dlq_sends"] += 1
            
            self.logger.info(
                f"Message sent to DLQ: {queue_type}",
                extra={
                    "error_id": error.error_id,
                    "message_id": message.get("MessageId", "unknown"),
                    "dlq_url": dlq_url
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to send message to DLQ: {str(e)}",
                extra={
                    "error_id": error.error_id,
                    "dlq_url": dlq_url
                }
            )
            return False
    
    async def send_error_alert(self, error: RepricingError) -> bool:
        """
        Send error alert for critical/high severity errors.
        
        This is a placeholder that can be integrated with various alerting systems:
        - Slack
        - Email
        - PagerDuty
        - AWS SNS
        etc.
        """
        if not error.should_alert():
            return False
        
        try:
            alert_data = {
                "error_id": error.error_id,
                "error_type": error.error_type,
                "message": error.message,
                "severity": error.severity.value,
                "category": error.category.value,
                "context": error.context,
                "timestamp": error.timestamp.isoformat()
            }
            
            # TODO: Implement actual alerting mechanism
            # For now, just log the alert
            self.logger.critical(
                f"HIGH SEVERITY ERROR ALERT: {error.message}",
                extra=alert_data
            )
            
            self.error_stats["alerts_sent"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send error alert: {str(e)}")
            return False
    
    def _classify_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by category and severity."""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Classification rules
        if "validation" in error_message or "invalid" in error_message:
            return ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM
        
        elif "connection" in error_message or "timeout" in error_message:
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        
        elif "redis" in error_message or "database" in error_message:
            return ErrorCategory.EXTERNAL_SERVICE, ErrorSeverity.HIGH
        
        elif "strategy" in error_message or "price" in error_message:
            return ErrorCategory.BUSINESS_LOGIC, ErrorSeverity.MEDIUM
        
        elif error_type in ["KeyError", "AttributeError", "TypeError"]:
            return ErrorCategory.SYSTEM, ErrorSeverity.HIGH
        
        elif "configuration" in error_message or "config" in error_message:
            return ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH
        
        elif error_type in ["MemoryError", "SystemError"]:
            return ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL
        
        else:
            # Default classification
            return ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM
    
    async def _handle_error_by_severity(
        self,
        error: RepricingError,
        message: Dict[str, Any],
        message_type: str
    ):
        """Handle error based on its severity."""
        if error.severity == ErrorSeverity.CRITICAL:
            # Critical errors: send alert and DLQ immediately
            await self.send_error_alert(error)
            await self.send_to_dead_letter_queue(message, error, message_type)
        
        elif error.severity == ErrorSeverity.HIGH:
            # High severity: send alert, may retry once
            await self.send_error_alert(error)
            if not error.is_retryable():
                await self.send_to_dead_letter_queue(message, error, message_type)
        
        elif error.severity == ErrorSeverity.MEDIUM:
            # Medium severity: retry if possible
            if not error.is_retryable():
                await self.send_to_dead_letter_queue(message, error, message_type)
        
        # Low severity errors are just logged
    
    async def _log_error(self, error: RepricingError):
        """Log error with appropriate level."""
        log_data = error.to_dict()
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(error.message, extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(error.message, extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(error.message, extra=log_data)
        else:
            self.logger.info(error.message, extra=log_data)
    
    def _update_error_stats(self, error: RepricingError):
        """Update error statistics."""
        self.error_stats["total_errors"] += 1
        
        # Count by category
        category_key = error.category.value
        self.error_stats["errors_by_category"][category_key] = \
            self.error_stats["errors_by_category"].get(category_key, 0) + 1
        
        # Count by severity
        severity_key = error.severity.value
        self.error_stats["errors_by_severity"][severity_key] = \
            self.error_stats["errors_by_severity"].get(severity_key, 0) + 1
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get current error statistics."""
        stats = self.error_stats.copy()
        stats["timestamp"] = datetime.now(UTC).isoformat()
        return stats
    
    def reset_error_stats(self):
        """Reset error statistics."""
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "retry_attempts": 0,
            "dlq_sends": 0,
            "alerts_sent": 0
        }
        
        self.logger.info("Error statistics reset")


class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        return (
            self.last_failure_time and
            datetime.now(UTC) - self.last_failure_time >= timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"