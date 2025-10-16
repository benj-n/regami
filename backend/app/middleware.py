"""Custom middleware for the Regami API."""

import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .core.config import settings


logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID for tracing and logging with structlog."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add X-Request-ID header to request/response and bind to logging context."""
        # Check if request already has an ID (from proxy/load balancer)
        request_id = request.headers.get("X-Request-ID")

        # Generate new ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for access in route handlers
        request.state.request_id = request_id

        # Bind to logging context (will be included in all logs for this request)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        # Log request start
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
        )

        # Process request
        try:
            response = await call_next(request)

            # Log request completion
            logger.info(
                "request_completed",
                status_code=response.status_code,
            )

            # Add request ID to response headers for client correlation
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Log request error
            logger.error(
                "request_failed",
                exc_info=exc,
                error=str(exc),
            )
            raise
        finally:
            # Clear context vars after request
            structlog.contextvars.clear_contextvars()


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to redirect HTTP requests to HTTPS in production."""

    async def dispatch(self, request: Request, call_next):
        """Redirect HTTP to HTTPS if in production environment."""
        if settings.app_env == "prod":
            # Check if request is HTTP (not HTTPS)
            # Handle both direct HTTPS and proxy scenarios (X-Forwarded-Proto header)
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
            scheme = forwarded_proto if forwarded_proto else request.url.scheme

            if scheme == "http":
                # Build HTTPS URL
                https_url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(https_url), status_code=301)

        # Process request normally
        response = await call_next(request)
        return response
