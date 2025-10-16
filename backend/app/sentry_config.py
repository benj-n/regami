"""Sentry error tracking configuration.

This module configures Sentry SDK for automatic error tracking, performance monitoring,
and user context attachment.
"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from .core.config import settings
from .logging_config import get_logger

logger = get_logger(__name__)


def init_sentry() -> None:
    """Initialize Sentry SDK with FastAPI integration.

    Features enabled:
    - Automatic exception capture
    - Performance monitoring (traces)
    - Request context (headers, body, user)
    - Breadcrumb tracking
    - Release tracking
    """
    if not settings.sentry_dsn:
        logger.info(
            "sentry_not_configured",
            message="Sentry DSN not provided, error tracking disabled"
        )
        return

    # Determine environment from settings or default to app_env
    environment = settings.sentry_environment or settings.app_env

    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=environment,
            # Integrations
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint",  # Group by endpoint, not URL params
                    failed_request_status_codes=[403, range(500, 599)],
                ),
                StarletteIntegration(
                    transaction_style="endpoint",
                ),
                SqlalchemyIntegration(),
                LoggingIntegration(
                    level=None,  # Don't capture logs as breadcrumbs (we use structlog)
                    event_level=None,  # Don't create events from logs
                ),
            ],
            # Performance monitoring
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            # Error sampling (capture all errors, sample transactions)
            sample_rate=1.0,
            # Request data
            send_default_pii=False,  # Don't send PII by default (we'll add user context manually)
            attach_stacktrace=True,
            # Before send hook to filter sensitive data
            before_send=before_send_filter,
        )

        logger.info(
            "sentry_initialized",
            environment=environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
        )
    except Exception as e:
        logger.error(
            "sentry_initialization_failed",
            error=str(e),
            error_type=type(e).__name__,
        )


def before_send_filter(event: dict, hint: dict) -> dict | None:
    """Filter sensitive data before sending to Sentry.

    This hook runs before each event is sent, allowing us to:
    - Remove sensitive headers (Authorization, Cookie)
    - Redact sensitive request body fields
    - Filter out certain types of errors
    """
    # Remove sensitive headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "***REDACTED***"

    # Redact sensitive body fields
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            sensitive_fields = ["password", "token", "api_key", "secret"]
            for field in sensitive_fields:
                if field in data:
                    data[field] = "***REDACTED***"

    return event


def set_user_context(user_id: str, email: str | None = None, role: str | None = None) -> None:
    """Set user context for Sentry error reports.

    This should be called after user authentication to attach user info to all
    subsequent error reports.

    Args:
        user_id: User's unique identifier
        email: User's email (optional)
        role: User's role (optional)
    """
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "role": role,
    })


def clear_user_context() -> None:
    """Clear user context (e.g., on logout)."""
    sentry_sdk.set_user(None)


def add_breadcrumb(message: str, category: str = "default", level: str = "info", **data) -> None:
    """Add a breadcrumb to track user actions leading to an error.

    Args:
        message: Breadcrumb message
        category: Category (e.g., "auth", "query", "navigation")
        level: Severity level ("debug", "info", "warning", "error")
        **data: Additional context data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data,
    )


def capture_exception(exception: Exception, **context) -> str | None:
    """Manually capture an exception with additional context.

    Args:
        exception: The exception to capture
        **context: Additional context to attach

    Returns:
        Sentry event ID if sent successfully, None otherwise
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_context(key, value)
        return sentry_sdk.capture_exception(exception)


def capture_message(message: str, level: str = "info", **context) -> str | None:
    """Capture a message (non-exception event) in Sentry.

    Args:
        message: The message to capture
        level: Severity level ("debug", "info", "warning", "error", "fatal")
        **context: Additional context to attach

    Returns:
        Sentry event ID if sent successfully, None otherwise
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_context(key, value)
        return sentry_sdk.capture_message(message, level=level)
