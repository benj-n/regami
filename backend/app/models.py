import secrets
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Integer, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
import enum

from .db import Base


class MatchStatus(str, enum.Enum):
    """Status of a match between an offer and a request.

    Flow: pending → accepted → confirmed (or rejected at any step)
    """
    PENDING = "pending"      # Initial state: match found, awaiting offer owner response
    ACCEPTED = "accepted"    # Offer owner accepted, awaiting requester confirmation
    CONFIRMED = "confirmed"  # Both parties agreed, slot is assigned
    REJECTED = "rejected"    # Either party rejected the match


def generate_user_id() -> str:
    """Generate a cryptographically secure random user ID.

    Uses secrets.token_urlsafe(16) which produces ~21 characters of URL-safe
    base64-encoded random data. This is much more secure than truncated UUIDs
    and prevents user enumeration attacks.
    """
    return secrets.token_urlsafe(16)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_user_id)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Email verification fields
    email_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    email_verification_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Password reset fields
    password_reset_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Profile fields (dogs moved to separate table with ownership links)
    # Approximate location (low-precision GPS as text for now)
    location_lat: Mapped[float | None] = mapped_column(nullable=True)
    location_lng: Mapped[float | None] = mapped_column(nullable=True)

    # FCM push notification token for mobile devices
    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    offers: Mapped[list["AvailabilityOffer"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    requests: Mapped[list["AvailabilityRequest"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    # Dogs association links
    dog_links: Mapped[list["UserDog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    # Messages
    sent_messages: Mapped[list["Message"]] = relationship(
        foreign_keys="[Message.sender_id]",
        back_populates="sender",
        cascade="all, delete-orphan"
    )
    received_messages: Mapped[list["Message"]] = relationship(
        foreign_keys="[Message.recipient_id]",
        back_populates="recipient",
        cascade="all, delete-orphan"
    )


class AvailabilityOffer(Base):
    __tablename__ = "availability_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="offers")


class AvailabilityRequest(Base):
    __tablename__ = "availability_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="requests")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="notifications")


class Dog(Base):
    __tablename__ = "dogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    birth_month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12
    birth_year: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g., 2020
    sex: Mapped[str] = mapped_column(String(6), nullable=False)  # 'male' or 'female'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user_links: Mapped[list["UserDog"]] = relationship(back_populates="dog", cascade="all, delete-orphan")

    @property
    def age_years(self) -> int:
        """Calculate dog's age in years from birth_month and birth_year."""
        from datetime import date
        today = date.today()
        age = today.year - self.birth_year

        # Subtract 1 if birthday hasn't occurred yet this year
        if today.month < self.birth_month:
            age -= 1

        return max(0, age)  # Never return negative age


class UserDog(Base):
    __tablename__ = "user_dogs"
    __table_args__ = (
        UniqueConstraint('user_id', 'dog_id', name='uq_user_dog'),
        Index('ix_user_dogs_user_id', 'user_id'),
        Index('ix_user_dogs_dog_id', 'dog_id'),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    dog_id: Mapped[int] = mapped_column(ForeignKey("dogs.id"), primary_key=True)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="dog_links")
    dog: Mapped[Dog] = relationship(back_populates="user_links")


class Match(Base):
    """Represents a match between an availability offer and request.

    Implements two-way confirmation flow:
    1. System creates match in PENDING status
    2. Offer owner accepts/rejects (→ ACCEPTED or REJECTED)
    3. If accepted, requester confirms/rejects (→ CONFIRMED or REJECTED)

    Unique constraint prevents multiple active matches for same offer-request pair.
    """
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint('offer_id', 'request_id', name='uq_offer_request'),
        Index('ix_matches_offer_id', 'offer_id'),
        Index('ix_matches_request_id', 'request_id'),
        Index('ix_matches_status', 'status'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("availability_offers.id"), nullable=False)
    request_id: Mapped[int] = mapped_column(ForeignKey("availability_requests.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=MatchStatus.PENDING.value)

    # Track who needs to respond
    pending_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    offer: Mapped[AvailabilityOffer] = relationship()
    request: Mapped[AvailabilityRequest] = relationship()
    pending_user: Mapped[User | None] = relationship()


class Message(Base):
    """Represents a direct message between two users.

    Messages are organized into conversations between two users. Each message
    has a sender and recipient, content, and read status.
    """
    __tablename__ = "messages"
    __table_args__ = (
        Index('ix_messages_sender_id', 'sender_id'),
        Index('ix_messages_recipient_id', 'recipient_id'),
        Index('ix_messages_created_at', 'created_at'),
        # Composite index for fetching conversations
        Index('ix_messages_conversation', 'sender_id', 'recipient_id', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    sender: Mapped[User] = relationship(foreign_keys=[sender_id], back_populates="sent_messages")
    recipient: Mapped[User] = relationship(foreign_keys=[recipient_id], back_populates="received_messages")
