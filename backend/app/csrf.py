"""
CSRF (Cross-Site Request Forgery) Protection

This module provides CSRF token generation and validation for state-changing requests.
The CSRF token is stored in a separate cookie (not httpOnly) so JavaScript can read it
and include it in request headers.

Security Model:
- CSRF token stored in a readable cookie (csrf_token)
- Frontend reads token from cookie and sends in X-CSRF-Token header
- Backend validates that cookie value matches header value
- Only validates on state-changing methods (POST, PUT, PATCH, DELETE)
- Safe methods (GET, HEAD, OPTIONS) bypass validation
- Combined with SameSite cookies for defense-in-depth

This protects against CSRF attacks where a malicious site tries to make requests
on behalf of the user. The attacker can make the browser send cookies but cannot
read the CSRF token to include it in the header.
"""

import secrets
from typing import Optional
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# Methods that require CSRF validation
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths that don't require CSRF validation
CSRF_EXEMPT_PATHS = {
    "/auth/login",  # Login creates the CSRF token
    "/auth/logout",  # Logout clears the CSRF token
    "/auth/register",  # Registration is before authentication
    "/auth/register-multipart",  # Multipart registration
    "/auth/forgot-password",  # Forgot password (no auth required)
    "/auth/reset-password",  # Reset password (token-based auth)
    "/auth/verify-email",  # Email verification (token-based auth)
    "/v1/auth/login",  # Versioned login
    "/v1/auth/logout",  # Versioned logout
    "/v1/auth/register",  # Versioned registration
    "/v1/auth/register-multipart",  # Versioned multipart registration
    "/v1/auth/forgot-password",  # Versioned forgot password
    "/v1/auth/reset-password",  # Versioned reset password
    "/v1/auth/verify-email",  # Versioned email verification
    "/docs",  # Swagger UI
    "/openapi.json",  # OpenAPI schema
    "/health",  # Health check
}


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def get_csrf_token_from_cookie(request: Request) -> Optional[str]:
    """Extract CSRF token from cookie."""
    return request.cookies.get("csrf_token")


def get_csrf_token_from_header(request: Request) -> Optional[str]:
    """Extract CSRF token from X-CSRF-Token header."""
    return request.headers.get("X-CSRF-Token")


def validate_csrf_token(request: Request) -> bool:
    """
    Validate CSRF token by comparing cookie value with header value.

    Returns True if:
    - Method is safe (GET, HEAD, OPTIONS)
    - Path is in exempt list
    - Cookie and header tokens match

    Returns False if validation fails.
    """
    # Safe methods don't need CSRF validation
    if request.method not in STATE_CHANGING_METHODS:
        return True

    # Check if path is exempt
    path = request.url.path
    if path in CSRF_EXEMPT_PATHS:
        return True

    # Get tokens from cookie and header
    cookie_token = get_csrf_token_from_cookie(request)
    header_token = get_csrf_token_from_header(request)

    # Both must be present and match
    if not cookie_token or not header_token:
        return False

    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(cookie_token, header_token)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate CSRF tokens on state-changing requests.

    This middleware checks that state-changing requests (POST, PUT, PATCH, DELETE)
    include a valid CSRF token in the X-CSRF-Token header that matches the
    csrf_token cookie.
    """

    async def dispatch(self, request: Request, call_next):
        # Validate CSRF token for state-changing requests
        if not validate_csrf_token(request):
            # Return 403 Forbidden for CSRF validation failure
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token validation failed. Missing or invalid token."}
            )

        # Token is valid or validation not required, proceed with request
        response = await call_next(request)
        return response


def set_csrf_cookie(response: Response, token: Optional[str] = None) -> str:
    """
    Set CSRF token in a cookie that JavaScript can read.

    Args:
        response: FastAPI Response object
        token: CSRF token to set (generates new one if not provided)

    Returns:
        The CSRF token that was set

    Cookie attributes:
    - httponly=False: JavaScript must read this to include in headers
    - secure: Only HTTPS in production
    - samesite='strict': Stricter than JWT cookie for additional protection
    """
    if token is None:
        token = generate_csrf_token()

    # Import here to avoid circular dependency
    from .core.config import settings

    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # Must be readable by JavaScript
        secure=settings.app_env == "prod",  # HTTPS only in production
        samesite="strict",  # Stricter CSRF protection
        max_age=settings.access_token_expire_minutes * 60,  # Match JWT expiry
    )

    return token
