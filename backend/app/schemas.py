from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Password reset schemas
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class UserBase(BaseModel):
    email: EmailStr
    location_lat: Optional[float] = Field(None, ge=-90, le=90)
    location_lng: Optional[float] = Field(None, ge=-180, le=180)


class UserCreate(UserBase):
    password: str = Field(min_length=8)
    # Optional dog name at registration time will create a Dog entity
    dog_name: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=100,
        pattern=r"^[A-Z0-9]{1,98}[0-9]{2}$",
    )


class UserUpdate(BaseModel):
    location_lat: Optional[float] = Field(None, ge=-90, le=90)
    location_lng: Optional[float] = Field(None, ge=-180, le=180)


class FCMTokenUpdate(BaseModel):
    fcm_token: str = Field(min_length=1, max_length=255)


class UserOut(UserBase):
    id: str
    created_at: datetime
    email_verified: bool = False

    class Config:
        from_attributes = True


# Resend verification email request
class ResendVerificationRequest(BaseModel):
    email: EmailStr


# Dogs
class DogBase(BaseModel):
    name: str = Field(min_length=3, max_length=100, pattern=r"^[A-Z0-9]{1,98}[0-9]{2}$")
    photo_url: Optional[str] = None
    birth_month: int = Field(ge=1, le=12, description="Month of birth (1-12)")
    birth_year: int = Field(ge=1995, description="Year of birth (1995-current year)")
    sex: str = Field(pattern=r"^(male|female)$", description="Dog's sex: 'male' or 'female'")

    @field_validator('birth_year')
    @classmethod
    def validate_birth_year(cls, v: int) -> int:
        """Validate that birth year is not in the future."""
        from datetime import date
        current_year = date.today().year
        if v > current_year:
            raise ValueError(f"Birth year cannot be in the future (max: {current_year})")
        return v


class DogCreate(DogBase):
    pass


class DogUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100, pattern=r"^[A-Z0-9]{1,98}[0-9]{2}$")
    photo_url: Optional[str] = None
    birth_month: Optional[int] = Field(None, ge=1, le=12)
    birth_year: Optional[int] = Field(None, ge=1995)
    sex: Optional[str] = Field(None, pattern=r"^(male|female)$")


class DogOut(DogBase):
    id: int
    created_at: datetime
    age_years: int = Field(description="Calculated age in years")

    class Config:
        from_attributes = True


# Messages
class MessageCreate(BaseModel):
    recipient_id: str = Field(description="ID of the user receiving the message")
    content: str = Field(min_length=1, max_length=5000, description="Message content")


class MessageResponse(BaseModel):
    id: int
    sender_id: str
    recipient_id: str
    content: str
    is_read: bool
    created_at: datetime
    sender_email: Optional[str] = None
    recipient_email: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    other_user_id: str
    other_user_email: str
    last_message: str
    last_message_at: datetime
    unread_count: int
