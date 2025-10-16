"""Custom Prometheus metrics for business logic tracking.

This module defines custom metrics to track business-critical events:
- User registrations
- Matches created/accepted/confirmed/rejected
- Messages sent
- Dog profiles created
- Availability periods created
"""

from prometheus_client import Counter, Histogram, Gauge
from functools import wraps
import time
from typing import Callable
from .logging_config import get_logger

logger = get_logger(__name__)

# User metrics
user_registrations_total = Counter(
    "regami_user_registrations_total",
    "Total number of user registrations",
    ["role"]  # owner | sitter
)

user_login_total = Counter(
    "regami_user_login_total",
    "Total number of user logins",
    ["method"]  # cookie | bearer
)

# Match metrics
matches_created_total = Counter(
    "regami_matches_created_total",
    "Total number of matches created",
    ["match_type"]  # request_to_offer | offer_to_request
)

matches_accepted_total = Counter(
    "regami_matches_accepted_total",
    "Total number of matches accepted"
)

matches_confirmed_total = Counter(
    "regami_matches_confirmed_total",
    "Total number of matches confirmed (both parties accepted)"
)

matches_rejected_total = Counter(
    "regami_matches_rejected_total",
    "Total number of matches rejected"
)

match_status_gauge = Gauge(
    "regami_matches_by_status",
    "Number of matches by status",
    ["status"]  # pending | accepted | confirmed | rejected
)

# Message metrics
messages_sent_total = Counter(
    "regami_messages_sent_total",
    "Total number of messages sent"
)

message_send_duration_seconds = Histogram(
    "regami_message_send_duration_seconds",
    "Time taken to send a message"
)

# Dog profile metrics
dogs_created_total = Counter(
    "regami_dogs_created_total",
    "Total number of dog profiles created"
)

dogs_with_photos_total = Counter(
    "regami_dogs_with_photos_total",
    "Total number of dogs with at least one photo"
)

# Availability metrics
availability_periods_created_total = Counter(
    "regami_availability_periods_created_total",
    "Total number of availability periods created",
    ["period_type"]  # offer | request
)

# Notification metrics
fcm_notifications_sent_total = Counter(
    "regami_fcm_notifications_sent_total",
    "Total number of FCM push notifications sent",
    ["notification_type"]  # new_match | match_accepted | match_confirmed | etc.
)

fcm_notifications_failed_total = Counter(
    "regami_fcm_notifications_failed_total",
    "Total number of failed FCM notifications",
    ["error_type"]  # unregistered | network | unknown
)

# WebSocket metrics
websocket_connections_total = Gauge(
    "regami_websocket_connections_total",
    "Current number of active WebSocket connections"
)

websocket_messages_sent_total = Counter(
    "regami_websocket_messages_sent_total",
    "Total number of WebSocket messages sent",
    ["message_type"]  # new_match | match_update | etc.
)

# Email metrics
emails_sent_total = Counter(
    "regami_emails_sent_total",
    "Total number of emails sent",
    ["email_type"]  # confirmation | match_notification | etc.
)

emails_failed_total = Counter(
    "regami_emails_failed_total",
    "Total number of failed email sends"
)

# Database query metrics
db_query_duration_seconds = Histogram(
    "regami_db_query_duration_seconds",
    "Database query duration",
    ["operation"]  # select | insert | update | delete
)

# Photo upload metrics
photo_uploads_total = Counter(
    "regami_photo_uploads_total",
    "Total number of photo uploads",
    ["storage_backend"]  # local | s3
)

photo_upload_size_bytes = Histogram(
    "regami_photo_upload_size_bytes",
    "Photo upload size in bytes",
    buckets=[10_000, 50_000, 100_000, 500_000, 1_000_000, 5_000_000]  # 10KB to 5MB
)


# Helper decorators for automatic metric tracking

def track_duration(histogram: Histogram, operation: str):
    """Decorator to track duration of a function call.

    Example:
        @track_duration(db_query_duration_seconds, "select")
        def get_users():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                histogram.labels(operation=operation).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                histogram.labels(operation=operation).observe(duration)

        # Return async wrapper if function is async, otherwise sync wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def increment_counter(counter: Counter, **labels):
    """Helper to increment a counter with labels.

    Example:
        increment_counter(matches_created_total, match_type="request_to_offer")
    """
    try:
        if labels:
            counter.labels(**labels).inc()
        else:
            counter.inc()
    except Exception as e:
        logger.error(
            "metric_increment_failed",
            counter_name=counter._name,
            error=str(e),
            error_type=type(e).__name__
        )


def set_gauge(gauge: Gauge, value: float, **labels):
    """Helper to set a gauge value with labels.

    Example:
        set_gauge(websocket_connections_total, 42)
    """
    try:
        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)
    except Exception as e:
        logger.error(
            "metric_set_failed",
            gauge_name=gauge._name,
            error=str(e),
            error_type=type(e).__name__
        )


def observe_histogram(histogram: Histogram, value: float, **labels):
    """Helper to observe a histogram value with labels.

    Example:
        observe_histogram(photo_upload_size_bytes, 1_234_567, storage_backend="s3")
    """
    try:
        if labels:
            histogram.labels(**labels).observe(value)
        else:
            histogram.observe(value)
    except Exception as e:
        logger.error(
            "metric_observe_failed",
            histogram_name=histogram._name,
            error=str(e),
            error_type=type(e).__name__
        )
