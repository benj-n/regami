from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Header
from sqlalchemy.orm import Session
from .. import schemas
from ..schemas import UserOut, UserUpdate, FCMTokenUpdate
from ..db import get_db
from ..models import User
from ..security import create_access_token, decode_access_token, hash_password as get_password_hash
from jose import JWTError
from datetime import timedelta
from ..core.config import settings
import structlog
from ..sentry_config import set_user_context


router = APIRouter()


async def get_current_user_ws(token: str, db: Session) -> User:
    """Get current authenticated user for WebSocket connections.

    WebSocket connections don't support cookies or headers in the same way,
    so we pass the JWT token as a query parameter.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user.

    Supports two authentication methods:
    1. Cookie-based (preferred, more secure): JWT in httpOnly cookie
    2. Header-based (backward compatible): Bearer token in Authorization header

    Also binds user context to structlog for request tracing.
    """
    token = None

    # Try cookie first (preferred method)
    if access_token:
        token = access_token
    # Fall back to Authorization header for API clients
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]

    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Bind user context to structlog for all logs in this request
    structlog.contextvars.bind_contextvars(
        user_id=user.id,
        user_email=user.email
    )

    # Set user context for Sentry error tracking
    set_user_context(
        user_id=user.id,
        email=user.email
    )

    return user


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(update: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/fcm-token", status_code=204)
def update_fcm_token(
    update: FCMTokenUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the current user's FCM (Firebase Cloud Messaging) token.

    This endpoint is called by mobile apps when they receive a new FCM token
    from Firebase. The token is used to send push notifications to the device.
    """
    current_user.fcm_token = update.fcm_token
    db.add(current_user)
    db.commit()
    return None


@router.delete("/me", status_code=204)
def delete_account(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete the current user's account permanently.

    This action is irreversible and will delete:
    - The user account
    - All associated dogs (via cascade)
    - All availability offers and requests
    - All messages
    - All notifications

    The user will be logged out after deletion.
    """
    # Delete the user - cascades will handle related records
    db.delete(current_user)
    db.commit()

    # Clear auth cookies
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        secure=settings.app_env == "prod",
        samesite="lax",
        max_age=0
    )
    response.set_cookie(
        key="csrf_token",
        value="",
        httponly=False,
        secure=settings.app_env == "prod",
        samesite="strict",
        max_age=0
    )

    return None
