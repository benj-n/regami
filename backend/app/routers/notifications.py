from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Notification, User
from .users import get_current_user


router = APIRouter()


@router.get("/me", response_model=dict)
def my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    total = q.count()
    items = (
        q.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {"id": n.id, "message": n.message, "is_read": n.is_read, "created_at": n.created_at.isoformat()} for n in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.put("/{notification_id}/read", response_model=dict)
def mark_read(notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != current_user.id:
        return {"status": "ignored"}
    n.is_read = True
    db.add(n)
    db.commit()
    return {"status": "ok"}


@router.post("/me/read-all", response_model=dict)
def mark_all_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Mark only unread notifications for this user
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False)
    ).update({Notification.is_read: True})
    db.commit()
    return {"status": "ok"}
