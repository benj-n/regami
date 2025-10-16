from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Message, User
from ..schemas import MessageCreate, MessageResponse, ConversationSummary
from .users import get_current_user
from .websocket import notify_new_message
from .. import fcm


router = APIRouter()


@router.post("", response_model=MessageResponse, status_code=201)
async def send_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message to another user."""
    # Verify recipient exists
    recipient = db.get(User, message_data.recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    # Can't send message to yourself
    if recipient.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot send message to yourself")

    # Create message
    message = Message(
        sender_id=current_user.id,
        recipient_id=message_data.recipient_id,
        content=message_data.content,
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # Build response with user emails
    response = MessageResponse.model_validate(message)
    response.sender_email = current_user.email
    response.recipient_email = recipient.email

    # Send WebSocket notification to recipient
    await notify_new_message(recipient.id, {
        "message_id": message.id,
        "sender_id": current_user.id,
        "sender_email": current_user.email,
        "content": message.content[:100],  # Preview
        "created_at": message.created_at.isoformat(),
    })

    # Send push notification to recipient
    fcm.notify_new_message(
        db=db,
        user_id=recipient.id,
        sender_name=current_user.email.split('@')[0],  # Use email username as name
        message_preview=message.content
    )

    return response


@router.get("/conversations", response_model=List[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of all conversation threads with unread counts."""
    # Subquery to get the latest message for each conversation
    # A conversation is defined by the pair of users (regardless of who sent first)

    # Get all unique users we've exchanged messages with
    sent_to = db.query(Message.recipient_id).filter(Message.sender_id == current_user.id).distinct()
    received_from = db.query(Message.sender_id).filter(Message.recipient_id == current_user.id).distinct()

    # Combine both sets
    all_users = set()
    for row in sent_to:
        all_users.add(row[0])
    for row in received_from:
        all_users.add(row[0])

    conversations = []
    for other_user_id in all_users:
        other_user = db.get(User, other_user_id)
        if not other_user:
            continue

        # Get last message in this conversation
        last_msg = (
            db.query(Message)
            .filter(
                or_(
                    and_(Message.sender_id == current_user.id, Message.recipient_id == other_user_id),
                    and_(Message.sender_id == other_user_id, Message.recipient_id == current_user.id),
                )
            )
            .order_by(Message.created_at.desc())
            .first()
        )

        if not last_msg:
            continue

        # Count unread messages from this user
        unread_count = (
            db.query(func.count(Message.id))
            .filter(
                Message.sender_id == other_user_id,
                Message.recipient_id == current_user.id,
                Message.is_read.is_(False),
            )
            .scalar()
        )

        conversations.append(
            ConversationSummary(
                other_user_id=other_user_id,
                other_user_email=other_user.email,
                last_message=last_msg.content[:100],  # Truncate to 100 chars
                last_message_at=last_msg.created_at,
                unread_count=unread_count,
            )
        )

    # Sort by most recent message first
    conversations.sort(key=lambda x: x.last_message_at, reverse=True)

    return conversations


@router.get("/conversations/{other_user_id}", response_model=List[MessageResponse])
def get_conversation_thread(
    other_user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 50,
):
    """Get full message thread with a specific user."""
    # Verify other user exists
    other_user = db.get(User, other_user_id)
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all messages between the two users
    messages = (
        db.query(Message)
        .filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.recipient_id == other_user_id),
                and_(Message.sender_id == other_user_id, Message.recipient_id == current_user.id),
            )
        )
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Build responses with user emails
    responses = []
    for msg in messages:
        response = MessageResponse.model_validate(msg)
        response.sender_email = current_user.email if msg.sender_id == current_user.id else other_user.email
        response.recipient_email = other_user.email if msg.recipient_id == other_user_id else current_user.email
        responses.append(response)

    # Mark all unread messages from other user as read
    db.query(Message).filter(
        Message.sender_id == other_user_id,
        Message.recipient_id == current_user.id,
        Message.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()

    return responses


@router.patch("/{message_id}/read", response_model=MessageResponse)
def mark_message_as_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a specific message as read."""
    message = db.get(Message, message_id)

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Can only mark messages you received as read
    if message.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot mark other user's messages as read")

    message.is_read = True
    db.add(message)
    db.commit()
    db.refresh(message)

    # Get sender and recipient emails
    sender = db.get(User, message.sender_id)
    response = MessageResponse.model_validate(message)
    response.sender_email = sender.email if sender else None
    response.recipient_email = current_user.email

    return response
