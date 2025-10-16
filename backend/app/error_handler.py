"""
Error Handler Module

This module provides error sanitization and user-friendly error messages to prevent
information leakage in production environments. It maps technical errors to safe,
user-friendly messages while logging full details for debugging.

Security Features:
- Hides stack traces from API responses in production
- Sanitizes database errors to prevent schema exposure
- Removes file paths and internal system details
- Logs full error details with request IDs for debugging
- Maps common errors to user-friendly messages
"""

import logging
import traceback
from typing import Dict, Optional, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, DataError
from pydantic import ValidationError

logger = logging.getLogger(__name__)


# User-friendly error messages for common scenarios
ERROR_MESSAGES = {
    # Authentication & Authorization
    "invalid_credentials": "Identifiants invalides / Invalid credentials",
    "unauthorized": "Non autorisé / Unauthorized",
    "forbidden": "Accès interdit / Forbidden",
    "token_expired": "Session expirée / Session expired",
    "invalid_token": "Jeton invalide / Invalid token",

    # Database & Data
    "duplicate_entry": "Cette entrée existe déjà / This entry already exists",
    "not_found": "Ressource introuvable / Resource not found",
    "database_error": "Erreur de base de données / Database error",
    "constraint_violation": "Violation de contrainte / Constraint violation",

    # Validation
    "validation_error": "Données invalides / Invalid data",
    "missing_field": "Champ requis manquant / Required field missing",
    "invalid_format": "Format invalide / Invalid format",
    "value_too_large": "Valeur trop grande / Value too large",

    # File Operations
    "file_too_large": "Fichier trop volumineux (max 10MB) / File too large (max 10MB)",
    "invalid_file_type": "Type de fichier invalide / Invalid file type",
    "file_not_found": "Fichier introuvable / File not found",

    # Rate Limiting
    "rate_limit_exceeded": "Trop de requêtes. Veuillez réessayer plus tard / Too many requests. Please try again later",

    # CSRF
    "csrf_failed": "Échec de validation CSRF / CSRF validation failed",

    # Generic
    "internal_error": "Erreur interne du serveur / Internal server error",
    "service_unavailable": "Service temporairement indisponible / Service temporarily unavailable",
}


def sanitize_error_message(error: Exception, include_details: bool = False) -> str:
    """
    Sanitize error message to prevent information leakage.

    Args:
        error: The exception to sanitize
        include_details: If True, include more details (for development)

    Returns:
        User-friendly error message
    """
    error_str = str(error)
    error_type = type(error).__name__

    # Map specific error types to user-friendly messages
    if isinstance(error, IntegrityError):
        # Database integrity errors often contain sensitive schema info
        if "UNIQUE constraint" in error_str or "duplicate" in error_str.lower():
            return ERROR_MESSAGES["duplicate_entry"]
        return ERROR_MESSAGES["constraint_violation"]

    elif isinstance(error, OperationalError):
        # Database connection/operational errors
        return ERROR_MESSAGES["database_error"]

    elif isinstance(error, DataError):
        # Data type/format errors
        if "too long" in error_str.lower() or "too large" in error_str.lower():
            return ERROR_MESSAGES["value_too_large"]
        return ERROR_MESSAGES["validation_error"]

    elif isinstance(error, ValidationError):
        # Pydantic validation errors
        if include_details:
            # In development, show validation details
            return f"{ERROR_MESSAGES['validation_error']}: {error_str}"
        return ERROR_MESSAGES["validation_error"]

    elif isinstance(error, ValueError):
        # Generic value errors
        return ERROR_MESSAGES["invalid_format"]

    elif isinstance(error, FileNotFoundError):
        return ERROR_MESSAGES["file_not_found"]

    elif isinstance(error, PermissionError):
        return ERROR_MESSAGES["forbidden"]

    # Default to generic error message
    if include_details:
        # In development, show the error type and message
        return f"{error_type}: {error_str}"

    return ERROR_MESSAGES["internal_error"]


def sanitize_error_details(error: Exception) -> Dict[str, Any]:
    """
    Extract safe error details for logging and debugging.

    Args:
        error: The exception to extract details from

    Returns:
        Dictionary with sanitized error details
    """
    return {
        "type": type(error).__name__,
        "message": str(error),
        "module": error.__class__.__module__,
    }


def get_error_response(
    error: Exception,
    request: Request,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    custom_message: Optional[str] = None
) -> JSONResponse:
    """
    Create a sanitized error response for API endpoints.

    Args:
        error: The exception that occurred
        request: The FastAPI request object
        status_code: HTTP status code to return
        custom_message: Optional custom error message

    Returns:
        JSONResponse with sanitized error
    """
    from .core.config import settings

    # Determine if we should include detailed errors
    include_details = settings.app_env != "prod"

    # Get request ID for correlation
    request_id = getattr(request.state, "request_id", "unknown")

    # Sanitize the error message
    if custom_message:
        user_message = custom_message
    else:
        user_message = sanitize_error_message(error, include_details)

    # Log the full error with stack trace for debugging
    logger.error(
        f"Error handling request {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "status_code": status_code,
        },
        exc_info=True
    )

    # Build response payload
    response_data = {
        "detail": user_message,
        "request_id": request_id,
    }

    # In development, include additional debug information
    if include_details:
        response_data["debug"] = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            # Only include stack trace in development
            "stack_trace": traceback.format_exc().split("\n")[:10],  # Limit to 10 lines
        }

    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


def handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle FastAPI HTTPException with sanitized messages.

    Args:
        request: The FastAPI request object
        exc: The HTTPException

    Returns:
        JSONResponse with sanitized error
    """
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail

        # Sanitize certain error messages based on status code
        if status_code == status.HTTP_401_UNAUTHORIZED:
            detail = ERROR_MESSAGES["unauthorized"]
        elif status_code == status.HTTP_403_FORBIDDEN:
            # Check if it's a CSRF error
            if "CSRF" in str(detail):
                detail = ERROR_MESSAGES["csrf_failed"]
            else:
                detail = ERROR_MESSAGES["forbidden"]
        elif status_code == status.HTTP_404_NOT_FOUND:
            detail = ERROR_MESSAGES["not_found"]
        elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            detail = ERROR_MESSAGES["rate_limit_exceeded"]

        return JSONResponse(
            status_code=status_code,
            content={
                "detail": detail,
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        )

    # Fallback for non-HTTP exceptions
    return get_error_response(exc, request)


def handle_validation_exception(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Handle Pydantic ValidationError with user-friendly messages.

    Args:
        request: The FastAPI request object
        exc: The ValidationError

    Returns:
        JSONResponse with validation errors
    """
    from .core.config import settings

    request_id = getattr(request.state, "request_id", "unknown")

    # In production, simplify validation errors
    if settings.app_env == "prod":
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": ERROR_MESSAGES["validation_error"],
                "request_id": request_id
            }
        )

    # In development, show detailed validation errors
    errors = exc.errors()
    formatted_errors = []
    for error in errors:
        formatted_errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": ERROR_MESSAGES["validation_error"],
            "errors": formatted_errors,
            "request_id": request_id
        }
    )


def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle any unhandled exception with sanitized error message.

    Args:
        request: The FastAPI request object
        exc: The exception

    Returns:
        JSONResponse with sanitized error
    """
    # Log the full error
    logger.exception(
        f"Unhandled exception in {request.method} {request.url.path}",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown")
        }
    )

    return get_error_response(
        exc,
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
