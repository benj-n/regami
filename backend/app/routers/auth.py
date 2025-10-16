from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request, Response
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, Dog, UserDog
from ..schemas import UserCreate, UserOut, ForgotPasswordRequest, ResetPasswordRequest, ResendVerificationRequest
from ..security import hash_password, verify_password, create_access_token
from ..services import storage as storage_mod
from ..services.email import send_email
from ..rate_limit import limiter


router = APIRouter()


@router.post("/register", response_model=UserOut)
@limiter.limit("5/minute")
def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    from ..core.config import settings

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate email verification token
    verification_token = secrets.token_urlsafe(32)

    user = User(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        location_lat=user_in.location_lat,
        location_lng=user_in.location_lng,
        email_verified=False,
        email_verification_token=verification_token,
    )
    db.add(user)
    db.flush()  # get user id

    # Optional: create a Dog linked to the user if dog_name provided
    if user_in.dog_name:
        from datetime import datetime
        name = user_in.dog_name.upper()
        # Use defaults for quick registration (user can update later)
        current_year = datetime.now().year
        dog = Dog(
            name=name,
            birth_month=1,  # January (placeholder)
            birth_year=current_year - 2,  # Assume ~2 years old
            sex="male"  # Placeholder (user can update)
        )
        db.add(dog)
        db.flush()
        db.add(UserDog(user_id=user.id, dog_id=dog.id, is_owner=True))

    db.commit()
    db.refresh(user)

    # Build verification URL
    frontend_url = settings.cors_origins.split(",")[0].strip() if settings.cors_origins else "http://localhost:5173"
    verification_url = f"{frontend_url}/verify-email/{verification_token}"

    # Send verification email
    send_email(
        user.email,
        "Regami - Verify Your Email / Verifiez votre email",
        template="email/verify_email.html",
        context={
            "user_email": user.email,
            "verification_url": verification_url,
        }
    )
    return user


@router.post("/register-multipart", response_model=UserOut)
@limiter.limit("5/minute")
def register_multipart(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    dog_name: str | None = Form(default=None),
    location_lat: float | None = Form(default=None),
    location_lng: float | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    from ..core.config import settings

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate email verification token
    verification_token = secrets.token_urlsafe(32)

    user = User(
        email=email,
        password_hash=hash_password(password),
        location_lat=location_lat,
        location_lng=location_lng,
        email_verified=False,
        email_verification_token=verification_token,
    )
    db.add(user)
    db.flush()

    photo_url: str | None = None
    if file is not None:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image uploads are allowed")
        # Enforce max size 10MB
        try:
            file.file.seek(0, os.SEEK_END)
            size = file.file.tell()
            file.file.seek(0)
        except Exception:
            size = 0
        if size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
        storage = storage_mod.get_storage()
        filename = file.filename or "upload"
        photo_url = storage.save(file.file, filename, content_type=file.content_type)

    if dog_name:
        from datetime import datetime
        name = dog_name.upper()
        # Validate pattern: uppercase letters/digits ending with two digits
        if not re.fullmatch(r"^[A-Z0-9]{1,98}[0-9]{2}$", name):
            raise HTTPException(status_code=400, detail="Invalid dog name format")
        # Use defaults for quick registration (user can update later)
        current_year = datetime.now().year
        dog = Dog(
            name=name,
            photo_url=photo_url,
            birth_month=1,  # January (placeholder)
            birth_year=current_year - 2,  # Assume ~2 years old
            sex="male"  # Placeholder (user can update)
        )
        db.add(dog)
        db.flush()
        db.add(UserDog(user_id=user.id, dog_id=dog.id, is_owner=True))

    db.commit()
    db.refresh(user)

    # Build verification URL
    frontend_url = settings.cors_origins.split(",")[0].strip() if settings.cors_origins else "http://localhost:5173"
    verification_url = f"{frontend_url}/verify-email/{verification_token}"

    # Send verification email
    send_email(
        user.email,
        "Regami - Verify Your Email / Verifiez votre email",
        template="email/verify_email.html",
        context={
            "user_email": user.email,
            "verification_url": verification_url,
        }
    )
    return user


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(subject=user.id)

    # Set JWT in httpOnly cookie for security
    # httpOnly: prevents JavaScript access (XSS protection)
    # secure: only sent over HTTPS in production
    # samesite: CSRF protection
    from ..core.config import settings
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.app_env == "prod",  # HTTPS only in production
        samesite="lax",  # Allow same-site navigation
        max_age=settings.access_token_expire_minutes * 60,  # Convert minutes to seconds
    )

    # Set CSRF token in a separate readable cookie
    # JavaScript needs to read this to include in request headers
    from ..csrf import set_csrf_cookie
    set_csrf_cookie(response)

    return {"message": "Login successful", "user_id": user.id}


@router.post("/logout")
def logout(response: Response):
    """Clear the authentication and CSRF cookies."""
    from ..core.config import settings

    # Delete cookies by setting them with Max-Age=0
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        secure=settings.app_env == "prod",
        samesite="lax",
        max_age=0  # Expire immediately
    )
    response.set_cookie(
        key="csrf_token",
        value="",
        httponly=False,
        secure=settings.app_env == "prod",
        samesite="strict",
        max_age=0  # Expire immediately
    )
    return {"message": "Logout successful"}


@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request a password reset email.

    Always returns success to prevent email enumeration attacks.
    """
    from ..core.config import settings

    user = db.query(User).filter(User.email == data.email).first()

    if user:
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)

        # Set token and expiration (1 hour from now)
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()

        # Build reset URL
        # Use frontend URL, not API URL
        frontend_url = settings.cors_origins.split(",")[0].strip() if settings.cors_origins else "http://localhost:5173"
        reset_url = f"{frontend_url}/reset-password/{reset_token}"

        # Send reset email
        send_email(
            user.email,
            "Regami - Password Reset / Reinitialisation du mot de passe",
            template="email/password_reset.html",
            context={
                "user_email": user.email,
                "reset_url": reset_url,
            }
        )

    # Always return success to prevent email enumeration
    return {"message": "If an account exists with this email, a password reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using a valid reset token.
    """
    # Find user with matching token
    user = db.query(User).filter(User.password_reset_token == data.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Check if token has expired
    if user.password_reset_expires is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Handle timezone-aware comparison
    expires = user.password_reset_expires
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires:
        # Clear expired token
        user.password_reset_token = None
        user.password_reset_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )

    # Update password
    user.password_hash = hash_password(data.new_password)

    # Clear reset token
    user.password_reset_token = None
    user.password_reset_expires = None

    db.commit()

    return {"message": "Password has been reset successfully. You can now log in with your new password."}


@router.post("/verify-email/{token}")
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify email address using the verification token.
    """
    # Find user with matching token
    user = db.query(User).filter(User.email_verification_token == token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

    if user.email_verified:
        return {"message": "Email already verified"}

    # Mark email as verified and clear token
    user.email_verified = True
    user.email_verification_token = None
    db.commit()

    # Send welcome email now that email is verified
    send_email(
        user.email,
        "Bienvenue / Welcome to Regami",
        template="email/welcome.html",
        context={"user_email": user.email}
    )

    return {"message": "Email verified successfully. Welcome to Regami!"}


@router.post("/resend-verification")
@limiter.limit("3/minute")
def resend_verification(request: Request, data: ResendVerificationRequest, db: Session = Depends(get_db)):
    """
    Resend email verification link.

    Always returns success to prevent email enumeration.
    """
    from ..core.config import settings

    user = db.query(User).filter(User.email == data.email).first()

    if user and not user.email_verified:
        # Generate new verification token
        verification_token = secrets.token_urlsafe(32)
        user.email_verification_token = verification_token
        db.commit()

        # Build verification URL
        frontend_url = settings.cors_origins.split(",")[0].strip() if settings.cors_origins else "http://localhost:5173"
        verification_url = f"{frontend_url}/verify-email/{verification_token}"

        # Send verification email
        send_email(
            user.email,
            "Regami - Verify Your Email / Verifiez votre email",
            template="email/verify_email.html",
            context={
                "user_email": user.email,
                "verification_url": verification_url,
            }
        )

    # Always return success to prevent email enumeration
    return {"message": "If an account exists with this email and is not yet verified, a verification link has been sent."}
