"""Tests for Sentry error tracking configuration.

Tests verify:
- Sentry initialization with DSN
- User context attachment
- Sensitive data filtering
- Error capture
- Breadcrumb tracking
"""

import pytest
from unittest.mock import patch, MagicMock
import sentry_sdk

from app.sentry_config import (
    init_sentry,
    set_user_context,
    clear_user_context,
    add_breadcrumb,
    capture_exception,
    capture_message,
    before_send_filter,
)
from app.core.config import Settings


@pytest.fixture
def mock_sentry_init():
    """Mock sentry_sdk.init to prevent actual initialization."""
    with patch("app.sentry_config.sentry_sdk.init") as mock_init:
        yield mock_init


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings with Sentry configuration."""
    settings = Settings(
        sentry_dsn="https://public@sentry.io/123456",
        sentry_environment="test",
        sentry_traces_sample_rate=0.1,
        sentry_profiles_sample_rate=0.1,
        app_env="test",
    )
    monkeypatch.setattr("app.sentry_config.settings", settings)
    return settings


def test_init_sentry_with_dsn(mock_sentry_init, mock_settings):
    """Test Sentry initialization when DSN is provided."""
    init_sentry()

    # Verify sentry_sdk.init was called
    assert mock_sentry_init.called

    # Verify configuration
    call_kwargs = mock_sentry_init.call_args[1]
    assert call_kwargs["dsn"] == "https://public@sentry.io/123456"
    assert call_kwargs["environment"] == "test"
    assert call_kwargs["traces_sample_rate"] == 0.1
    assert call_kwargs["profiles_sample_rate"] == 0.1
    assert call_kwargs["sample_rate"] == 1.0
    assert call_kwargs["send_default_pii"] is False
    assert call_kwargs["attach_stacktrace"] is True


def test_init_sentry_without_dsn(mock_sentry_init, monkeypatch):
    """Test Sentry skips initialization when DSN is not provided."""
    settings = Settings(sentry_dsn=None, app_env="test")
    monkeypatch.setattr("app.sentry_config.settings", settings)

    init_sentry()

    # Verify sentry_sdk.init was NOT called
    assert not mock_sentry_init.called


def test_set_user_context():
    """Test setting user context for Sentry."""
    with patch("app.sentry_config.sentry_sdk.set_user") as mock_set_user:
        set_user_context(
            user_id="user123",
            email="test@example.com",
            role="owner"
        )

        mock_set_user.assert_called_once_with({
            "id": "user123",
            "email": "test@example.com",
            "role": "owner",
        })


def test_set_user_context_minimal():
    """Test setting user context with only user_id."""
    with patch("app.sentry_config.sentry_sdk.set_user") as mock_set_user:
        set_user_context(user_id="user456")

        mock_set_user.assert_called_once_with({
            "id": "user456",
            "email": None,
            "role": None,
        })


def test_clear_user_context():
    """Test clearing user context."""
    with patch("app.sentry_config.sentry_sdk.set_user") as mock_set_user:
        clear_user_context()

        mock_set_user.assert_called_once_with(None)


def test_add_breadcrumb():
    """Test adding breadcrumbs for event tracking."""
    with patch("app.sentry_config.sentry_sdk.add_breadcrumb") as mock_add_breadcrumb:
        add_breadcrumb(
            message="User logged in",
            category="auth",
            level="info",
            user_id="user123"
        )

        mock_add_breadcrumb.assert_called_once_with(
            message="User logged in",
            category="auth",
            level="info",
            data={"user_id": "user123"},
        )


def test_capture_exception():
    """Test manually capturing an exception."""
    with patch("app.sentry_config.sentry_sdk.capture_exception") as mock_capture:
        mock_capture.return_value = "event-id-123"

        exception = ValueError("Test error")
        event_id = capture_exception(exception, extra_context="value")

        assert event_id == "event-id-123"
        assert mock_capture.called


def test_capture_message():
    """Test capturing a message event."""
    with patch("app.sentry_config.sentry_sdk.capture_message") as mock_capture:
        mock_capture.return_value = "event-id-456"

        event_id = capture_message("Test message", level="warning", key="value")

        assert event_id == "event-id-456"
        assert mock_capture.called


def test_before_send_filter_removes_sensitive_headers():
    """Test that sensitive headers are redacted."""
    event = {
        "request": {
            "headers": {
                "authorization": "Bearer secret-token",
                "cookie": "session=abc123",
                "x-api-key": "api-key-secret",
                "user-agent": "Mozilla/5.0",
            }
        }
    }

    filtered = before_send_filter(event, {})

    assert filtered["request"]["headers"]["authorization"] == "***REDACTED***"
    assert filtered["request"]["headers"]["cookie"] == "***REDACTED***"
    assert filtered["request"]["headers"]["x-api-key"] == "***REDACTED***"
    assert filtered["request"]["headers"]["user-agent"] == "Mozilla/5.0"


def test_before_send_filter_redacts_body_fields():
    """Test that sensitive body fields are redacted."""
    event = {
        "request": {
            "data": {
                "email": "test@example.com",
                "password": "supersecret123",
                "token": "abc123",
                "name": "John Doe",
            }
        }
    }

    filtered = before_send_filter(event, {})

    assert filtered["request"]["data"]["password"] == "***REDACTED***"
    assert filtered["request"]["data"]["token"] == "***REDACTED***"
    assert filtered["request"]["data"]["email"] == "test@example.com"
    assert filtered["request"]["data"]["name"] == "John Doe"


def test_before_send_filter_handles_missing_fields():
    """Test that filter handles events without request data."""
    event = {
        "exception": {
            "values": [{
                "type": "ValueError",
                "value": "Test error"
            }]
        }
    }

    # Should not raise an error
    filtered = before_send_filter(event, {})
    assert filtered == event


def test_before_send_filter_handles_non_dict_data():
    """Test that filter handles non-dict request data."""
    event = {
        "request": {
            "data": "string data"
        }
    }

    # Should not raise an error
    filtered = before_send_filter(event, {})
    assert filtered["request"]["data"] == "string data"


def test_init_sentry_integrations(mock_sentry_init, mock_settings):
    """Test that all required integrations are configured."""
    init_sentry()

    call_kwargs = mock_sentry_init.call_args[1]
    integrations = call_kwargs["integrations"]

    # Check integration types
    integration_names = [type(i).__name__ for i in integrations]
    assert "FastApiIntegration" in integration_names
    assert "StarletteIntegration" in integration_names
    assert "SqlalchemyIntegration" in integration_names
    assert "LoggingIntegration" in integration_names


def test_init_sentry_uses_app_env_as_fallback(mock_sentry_init, monkeypatch):
    """Test that app_env is used when sentry_environment is not set."""
    settings = Settings(
        sentry_dsn="https://public@sentry.io/123456",
        sentry_environment=None,
        app_env="production",
    )
    monkeypatch.setattr("app.sentry_config.settings", settings)

    init_sentry()

    call_kwargs = mock_sentry_init.call_args[1]
    assert call_kwargs["environment"] == "production"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
