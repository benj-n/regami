"""Firebase Cloud Messaging (FCM) push notification helpers.

This module provides functions to send push notifications to mobile devices
using Firebase Cloud Messaging. Notifications are sent to users based on
various events like new matches, messages, etc.
"""

from typing import Optional
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session

from .models import User
from .logging_config import get_logger

logger = get_logger(__name__)

# Initialize Firebase Admin SDK
# The service account key should be placed at backend/firebase-service-account.json
# You can download it from Firebase Console > Project Settings > Service Accounts
_firebase_initialized = False


def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials.

    This should be called once during application startup.
    """
    global _firebase_initialized
    if _firebase_initialized:
        return

    service_account_path = Path(__file__).parent.parent / "firebase-service-account.json"

    if not service_account_path.exists():
        logger.warning(
            "firebase_service_account_not_found",
            service_account_path=str(service_account_path),
            message="Push notifications will not be sent"
        )
        return

    try:
        cred = credentials.Certificate(str(service_account_path))
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("firebase_initialized", service_account_path=str(service_account_path))
    except Exception as e:
        logger.error(
            "firebase_initialization_failed",
            error=str(e),
            error_type=type(e).__name__,
            service_account_path=str(service_account_path)
        )


def send_fcm_notification(
    user: User,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> bool:
    """Send a push notification to a specific user via FCM.

    Args:
        user: The user to send the notification to (must have fcm_token set)
        title: Notification title
        body: Notification body text
        data: Optional dictionary of custom data to include in the notification

    Returns:
        True if notification was sent successfully, False otherwise
    """
    if not _firebase_initialized:
        logger.warning("firebase_not_initialized", action="skipping_notification")
        return False

    if not user.fcm_token:
        logger.debug("user_has_no_fcm_token", user_id=user.id, action="skipping_notification")
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=user.fcm_token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    icon="ic_notification",
                    color="#FF6B6B",
                    channel_id="regami_notifications",
                ),
            ),
        )

        response = messaging.send(message)
        logger.info(
            "fcm_notification_sent",
            user_id=user.id,
            title=title,
            response=response
        )
        return True

    except messaging.UnregisteredError:
        logger.warning(
            "fcm_token_invalid",
            user_id=user.id,
            action="token_should_be_cleared"
        )
        # Token is no longer valid, clear it from the database
        # The calling code should provide the database session if needed
        return False
    except Exception as e:
        logger.error(
            "fcm_notification_failed",
            user_id=user.id,
            title=title,
            error=str(e),
            error_type=type(e).__name__
        )
        return False


def notify_new_match(db: Session, user_id: str, match_id: str, dog_name: str):
    """Send notification when a new match is created.

    Args:
        db: Database session
        user_id: ID of the user to notify
        match_id: ID of the match that was created
        dog_name: Name of the matched dog
    """
    user = db.get(User, user_id)
    if not user:
        return

    send_fcm_notification(
        user=user,
        title="Nouveau match ! 🎉",
        body=f"Vous avez un nouveau match avec {dog_name} !",
        data={
            "type": "new_match",
            "match_id": match_id,
            "deep_link": "/availability",
        },
    )


def notify_match_accepted(db: Session, user_id: str, match_id: str, dog_name: str):
    """Send notification when a match is accepted.

    Args:
        db: Database session
        user_id: ID of the user to notify
        match_id: ID of the match that was accepted
        dog_name: Name of the dog whose owner accepted
    """
    user = db.get(User, user_id)
    if not user:
        return

    send_fcm_notification(
        user=user,
        title="Match accepté ! 💚",
        body=f"{dog_name} a accepté votre match !",
        data={
            "type": "match_accepted",
            "match_id": match_id,
            "deep_link": "/availability",
        },
    )


def notify_match_confirmed(db: Session, user_id: str, match_id: str, dog_name: str):
    """Send notification when a match is confirmed by both parties.

    Args:
        db: Database session
        user_id: ID of the user to notify
        match_id: ID of the match that was confirmed
        dog_name: Name of the matched dog
    """
    user = db.get(User, user_id)
    if not user:
        return

    send_fcm_notification(
        user=user,
        title="Match confirmé ! 🎊",
        body=f"Votre rendez-vous avec {dog_name} est confirmé ! Vous pouvez maintenant échanger des messages.",
        data={
            "type": "match_confirmed",
            "match_id": match_id,
            "deep_link": "/messages",
        },
    )


def notify_match_rejected(db: Session, user_id: str, match_id: str):
    """Send notification when a match is rejected.

    Args:
        db: Database session
        user_id: ID of the user to notify
        match_id: ID of the match that was rejected
    """
    user = db.get(User, user_id)
    if not user:
        return

    send_fcm_notification(
        user=user,
        title="Match refusé",
        body="Un de vos matchs a été refusé.",
        data={
            "type": "match_rejected",
            "match_id": match_id,
            "deep_link": "/availability",
        },
    )


def notify_new_message(db: Session, user_id: str, sender_name: str, message_preview: str):
    """Send notification when a new message is received.

    Args:
        db: Database session
        user_id: ID of the user to notify (recipient)
        sender_name: Name of the user who sent the message
        message_preview: Preview of the message content (truncated if needed)
    """
    user = db.get(User, user_id)
    if not user:
        return

    # Truncate preview if too long
    if len(message_preview) > 100:
        message_preview = message_preview[:97] + "..."

    send_fcm_notification(
        user=user,
        title=f"Nouveau message de {sender_name}",
        body=message_preview,
        data={
            "type": "new_message",
            "sender_id": user_id,
            "deep_link": "/messages",
        },
    )
