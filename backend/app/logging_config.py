"""Structured logging configuration using structlog.

This module sets up structured logging with JSON output, request ID tracking,
user context, and sensitive data redaction.
"""

import logging
import logging.config
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from .core.config import settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries."""
    event_dict["app"] = "regami"
    event_dict["environment"] = settings.app_env
    return event_dict


def censor_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Redact sensitive data from log entries.

    Censors:
    - password fields
    - token fields
    - authorization headers
    - api_key fields
    """
    sensitive_keys = {
        "password",
        "pwd",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "apikey",
        "secret",
        "private_key",
        "fcm_token",
    }

    for key in list(event_dict.keys()):
        key_lower = key.lower()
        # Check if key matches sensitive patterns
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            event_dict[key] = "***REDACTED***"

        # Also check nested dictionaries and lists
        elif isinstance(event_dict[key], dict):
            event_dict[key] = _censor_dict(event_dict[key], sensitive_keys)
        elif isinstance(event_dict[key], list):
            event_dict[key] = _censor_list(event_dict[key], sensitive_keys)

    return event_dict


def _censor_dict(data: dict, sensitive_keys: set) -> dict:
    """Recursively censor sensitive keys in nested dictionaries."""
    censored = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            censored[key] = "***REDACTED***"
        elif isinstance(value, dict):
            censored[key] = _censor_dict(value, sensitive_keys)
        elif isinstance(value, list):
            censored[key] = _censor_list(value, sensitive_keys)
        else:
            censored[key] = value
    return censored


def _censor_list(data: list, sensitive_keys: set) -> list:
    """Recursively censor sensitive keys in lists."""
    censored = []
    for item in data:
        if isinstance(item, dict):
            censored.append(_censor_dict(item, sensitive_keys))
        elif isinstance(item, list):
            censored.append(_censor_list(item, sensitive_keys))
        else:
            censored.append(item)
    return censored


def configure_logging() -> None:
    """Configure structlog and stdlib logging.

    Sets up:
    - JSON output in production
    - Console output in development
    - Request ID tracking
    - User context
    - Sensitive data redaction
    """
    # Determine log level from environment
    log_level = logging.DEBUG if settings.app_env == "dev" else logging.INFO

    # Configure stdlib logging
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
        # Silence noisy third-party loggers
        "loggers": {
            "uvicorn.access": {"level": logging.WARNING},
            "uvicorn.error": {"level": logging.INFO},
            "boto3": {"level": logging.WARNING},
            "botocore": {"level": logging.WARNING},
            "urllib3": {"level": logging.WARNING},
        },
    })

    # Build processor chain
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_app_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        censor_sensitive_data,
    ]

    # Add appropriate final processor based on environment
    if settings.app_env == "dev":
        # Pretty console output for development
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # JSON output for production (log aggregation)
        processors.extend([
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ])

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ from calling module).
              If None, uses the root logger.

    Returns:
        Configured structlog logger with bound context.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_registered", user_id="123", email="user@example.com")
    """
    return structlog.get_logger(name)
