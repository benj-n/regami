from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session
from typing import Optional

from ..db import get_db
from ..models import AvailabilityOffer, AvailabilityRequest, Match, MatchStatus, Notification, User
from .users import get_current_user
from ..services.email import send_email
from .. import fcm


router = APIRouter()


def _get_user_first_dog(user: User):
    """Get the first dog linked to a user, or None if no dogs."""
    if user and user.dog_links:
        return user.dog_links[0].dog
    return None


class SlotIn(BaseModel):
    start_at: datetime
    end_at: datetime

    @property
    def valid(self) -> bool:
        return self.end_at > self.start_at


class MatchOut(BaseModel):
    id: int
    offer_id: int
    request_id: int
    status: str
    pending_user_id: str | None
    created_at: datetime
    updated_at: datetime

    # Include related data for easier display
    offer_start: datetime | None = None
    offer_end: datetime | None = None
    request_start: datetime | None = None
    request_end: datetime | None = None
    offer_owner_email: str | None = None
    requester_email: str | None = None


def _notify(db: Session, user: User, message: str) -> None:
    """Create a notification and send email (legacy plain text)."""
    notif = Notification(user_id=user.id, message=message)
    db.add(notif)
    send_email(user.email, "Regami - Nouvelle correspondance", body=message)


def _send_match_email(
    db: Session,
    user: User,
    template: str,
    subject: str,
    match: Match
) -> None:
    """Send HTML email for match-related notifications."""
    notif = Notification(user_id=user.id, message=subject)
    db.add(notif)

    context = {
        "user_email": user.email,
        "start_date": match.offer.start_at.strftime('%Y-%m-%d %H:%M') if match.offer else "",
        "end_date": match.offer.end_at.strftime('%Y-%m-%d %H:%M') if match.offer else "",
        "offer_owner_email": match.offer.user.email if match.offer and match.offer.user else "",
        "requester_email": match.request.user.email if match.request and match.request.user else "",
    }

    send_email(user.email, subject, template=template, context=context)


def _create_match(db: Session, offer: AvailabilityOffer, request: AvailabilityRequest) -> Match:
    """Create a pending match with transaction-level locking.

    Uses SELECT FOR UPDATE to prevent race conditions where two users
    might try to match with the same offer/request simultaneously.
    """
    # Lock both offer and request rows to prevent concurrent matches
    locked_offer = (
        db.query(AvailabilityOffer)
        .filter(AvailabilityOffer.id == offer.id)
        .with_for_update()
        .first()
    )
    locked_request = (
        db.query(AvailabilityRequest)
        .filter(AvailabilityRequest.id == request.id)
        .with_for_update()
        .first()
    )

    if not locked_offer or not locked_request:
        raise HTTPException(status_code=404, detail="Offer or request no longer available")

    # Check if match already exists (shouldn't happen with unique constraint, but safe check)
    existing = (
        db.query(Match)
        .filter(
            Match.offer_id == offer.id,
            Match.request_id == request.id,
            Match.status.in_([MatchStatus.PENDING.value, MatchStatus.ACCEPTED.value])
        )
        .first()
    )
    if existing:
        return existing

    # Create new match in pending state
    # Offer owner needs to respond first
    match = Match(
        offer_id=offer.id,
        request_id=request.id,
        status=MatchStatus.PENDING.value,
        pending_user_id=offer.user_id  # Offer owner responds first
    )
    db.add(match)
    db.flush()  # Get the ID without committing

    # Notify offer owner with HTML email
    _send_match_email(
        db,
        locked_offer.user,
        "email/match_pending.html",
        "Regami - Nouvelle demande de garde",
        match
    )

    # Send push notification to offer owner
    requester_dog = _get_user_first_dog(locked_request.user)
    fcm.notify_new_match(
        db=db,
        user_id=locked_offer.user_id,
        match_id=str(match.id),
        dog_name=requester_dog.name if requester_dog else "un chien"
    )

    return match


def _match_offer(db: Session, offer: AvailabilityOffer) -> list[Match]:
    """Find requests that fit within offer window and create pending matches."""
    created_matches = []

    # Find requests that fit within offer window (with locking)
    requests = (
        db.query(AvailabilityRequest)
        .filter(
            and_(
                AvailabilityRequest.start_at >= offer.start_at,
                AvailabilityRequest.end_at <= offer.end_at,
                AvailabilityRequest.user_id != offer.user_id,
            )
        )
        .all()
    )

    for req in requests:
        try:
            match = _create_match(db, offer, req)
            created_matches.append(match)
        except HTTPException:
            # Skip if match already exists or other error
            continue

    return created_matches


def _match_request(db: Session, request: AvailabilityRequest) -> list[Match]:
    """Find offers that contain the requested window and create pending matches."""
    created_matches = []

    # Find offers that contain the requested window
    offers = (
        db.query(AvailabilityOffer)
        .filter(
            and_(
                AvailabilityOffer.start_at <= request.start_at,
                AvailabilityOffer.end_at >= request.end_at,
                AvailabilityOffer.user_id != request.user_id,
            )
        )
        .all()
    )

    for off in offers:
        try:
            match = _create_match(db, off, request)
            created_matches.append(match)
        except HTTPException:
            # Skip if match already exists or other error
            continue

    return created_matches


@router.post("/offers", response_model=dict)
def create_offer(slot: SlotIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not slot.valid:
        raise HTTPException(status_code=400, detail="Invalid time range")
    # Prevent past and overlapping windows
    now = datetime.utcnow()
    if slot.end_at <= now or slot.start_at <= now:
        raise HTTPException(status_code=400, detail="Time range must be in the future")
    overlap = (
        db.query(AvailabilityOffer)
        .filter(
            AvailabilityOffer.user_id == current_user.id,
            # overlap if start < existing.end and end > existing.start
            AvailabilityOffer.start_at < slot.end_at,
            AvailabilityOffer.end_at > slot.start_at,
        )
        .first()
    )
    if overlap:
        raise HTTPException(status_code=400, detail="Overlapping offer exists")
    offer = AvailabilityOffer(user_id=current_user.id, start_at=slot.start_at, end_at=slot.end_at)
    db.add(offer)
    db.commit()
    db.refresh(offer)
    _match_offer(db, offer)
    db.commit()
    return {"id": offer.id}


@router.post("/requests", response_model=dict)
def create_request(slot: SlotIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not slot.valid:
        raise HTTPException(status_code=400, detail="Invalid time range")
    # Prevent past and overlapping windows
    now = datetime.utcnow()
    if slot.end_at <= now or slot.start_at <= now:
        raise HTTPException(status_code=400, detail="Time range must be in the future")
    overlap = (
        db.query(AvailabilityRequest)
        .filter(
            AvailabilityRequest.user_id == current_user.id,
            AvailabilityRequest.start_at < slot.end_at,
            AvailabilityRequest.end_at > slot.start_at,
        )
        .first()
    )
    if overlap:
        raise HTTPException(status_code=400, detail="Overlapping request exists")
    req = AvailabilityRequest(user_id=current_user.id, start_at=slot.start_at, end_at=slot.end_at)
    db.add(req)
    db.commit()
    db.refresh(req)
    _match_request(db, req)
    db.commit()
    return {"id": req.id}


@router.delete("/offers/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_offer(offer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.get(AvailabilityOffer, offer_id)
    if not obj or obj.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    db.delete(obj)
    db.commit()
    return


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.get(AvailabilityRequest, request_id)
    if not obj or obj.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Request not found")
    db.delete(obj)
    db.commit()
    return


@router.get("/offers/mine", response_model=dict)
def my_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
    sort: str = "-start_at",  # - for desc
):
    q = db.query(AvailabilityOffer).filter(AvailabilityOffer.user_id == current_user.id)
    total = q.count()
    order_col = AvailabilityOffer.start_at
    order = desc(order_col) if sort.startswith('-') else asc(order_col)
    items = (
        q.order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [{"id": r.id, "start_at": r.start_at.isoformat(), "end_at": r.end_at.isoformat()} for r in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/requests/mine", response_model=dict)
def my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
    sort: str = "-start_at",
):
    q = db.query(AvailabilityRequest).filter(AvailabilityRequest.user_id == current_user.id)
    total = q.count()
    order_col = AvailabilityRequest.start_at
    order = desc(order_col) if sort.startswith('-') else asc(order_col)
    items = (
        q.order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [{"id": r.id, "start_at": r.start_at.isoformat(), "end_at": r.end_at.isoformat()} for r in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ========== Search/Filter Endpoints ==========


@router.get("/offers/search", response_model=dict)
def search_offers(
    start_date: Optional[datetime] = Query(None, description="Filter by start date (>=)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (<=)"),
    exclude_mine: bool = Query(False, description="Exclude current user's offers"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("-start_at", description="Sort field (prefix with - for desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search availability offers with filters.

    - start_date: Filter offers starting on or after this date
    - end_date: Filter offers ending on or before this date
    - exclude_mine: Don't include current user's offers
    - sort: Sort by field (start_at, end_at, created_at). Prefix with - for descending
    """
    query = db.query(AvailabilityOffer)

    # Filter by date range
    if start_date:
        query = query.filter(AvailabilityOffer.start_at >= start_date)
    if end_date:
        query = query.filter(AvailabilityOffer.end_at <= end_date)

    # Exclude current user's offers
    if exclude_mine:
        query = query.filter(AvailabilityOffer.user_id != current_user.id)

    # Get total count
    total = query.count()

    # Sorting
    sort_field = sort.lstrip('-')
    is_desc = sort.startswith('-')

    if sort_field == "start_at":
        order_col = AvailabilityOffer.start_at
    elif sort_field == "end_at":
        order_col = AvailabilityOffer.end_at
    elif sort_field == "created_at":
        order_col = AvailabilityOffer.created_at
    else:
        order_col = AvailabilityOffer.start_at

    order = desc(order_col) if is_desc else asc(order_col)

    # Pagination
    items = (
        query
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "start_at": r.start_at.isoformat(),
                "end_at": r.end_at.isoformat(),
                "created_at": r.created_at.isoformat(),
            }
            for r in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page * page_size) < total
    }


@router.get("/requests/search", response_model=dict)
def search_requests(
    start_date: Optional[datetime] = Query(None, description="Filter by start date (>=)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (<=)"),
    exclude_mine: bool = Query(False, description="Exclude current user's requests"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("-start_at", description="Sort field (prefix with - for desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search availability requests with filters.

    - start_date: Filter requests starting on or after this date
    - end_date: Filter requests ending on or before this date
    - exclude_mine: Don't include current user's requests
    - sort: Sort by field (start_at, end_at, created_at). Prefix with - for descending
    """
    query = db.query(AvailabilityRequest)

    # Filter by date range
    if start_date:
        query = query.filter(AvailabilityRequest.start_at >= start_date)
    if end_date:
        query = query.filter(AvailabilityRequest.end_at <= end_date)

    # Exclude current user's requests
    if exclude_mine:
        query = query.filter(AvailabilityRequest.user_id != current_user.id)

    # Get total count
    total = query.count()

    # Sorting
    sort_field = sort.lstrip('-')
    is_desc = sort.startswith('-')

    if sort_field == "start_at":
        order_col = AvailabilityRequest.start_at
    elif sort_field == "end_at":
        order_col = AvailabilityRequest.end_at
    elif sort_field == "created_at":
        order_col = AvailabilityRequest.created_at
    else:
        order_col = AvailabilityRequest.start_at

    order = desc(order_col) if is_desc else asc(order_col)

    # Pagination
    items = (
        query
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "start_at": r.start_at.isoformat(),
                "end_at": r.end_at.isoformat(),
                "created_at": r.created_at.isoformat(),
            }
            for r in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page * page_size) < total
    }


# ========== Match Management Endpoints (Two-Way Confirmation) ==========


@router.get("/matches/pending", response_model=dict)
def get_pending_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
):
    """Get all matches where current user needs to respond."""
    q = (
        db.query(Match)
        .filter(
            Match.pending_user_id == current_user.id,
            Match.status.in_([MatchStatus.PENDING.value, MatchStatus.ACCEPTED.value])
        )
        .join(Match.offer)
        .join(Match.request)
    )

    total = q.count()
    items = (
        q.order_by(Match.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result_items = []
    for match in items:
        result_items.append({
            "id": match.id,
            "offer_id": match.offer_id,
            "request_id": match.request_id,
            "status": match.status,
            "pending_user_id": match.pending_user_id,
            "created_at": match.created_at.isoformat(),
            "updated_at": match.updated_at.isoformat(),
            "offer_start": match.offer.start_at.isoformat() if match.offer else None,
            "offer_end": match.offer.end_at.isoformat() if match.offer else None,
            "request_start": match.request.start_at.isoformat() if match.request else None,
            "request_end": match.request.end_at.isoformat() if match.request else None,
            "offer_owner_email": match.offer.user.email if match.offer and match.offer.user else None,
            "requester_email": match.request.user.email if match.request and match.request.user else None,
        })

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/matches/my-matches", response_model=dict)
def get_my_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
):
    """Get all matches involving current user's offers or requests."""
    # Get matches where user is either offer owner or requester
    q = (
        db.query(Match)
        .join(Match.offer)
        .join(Match.request)
        .filter(
            (AvailabilityOffer.user_id == current_user.id) |
            (AvailabilityRequest.user_id == current_user.id)
        )
    )

    if status_filter:
        q = q.filter(Match.status == status_filter)

    total = q.count()
    items = (
        q.order_by(Match.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result_items = []
    for match in items:
        result_items.append({
            "id": match.id,
            "offer_id": match.offer_id,
            "request_id": match.request_id,
            "status": match.status,
            "pending_user_id": match.pending_user_id,
            "created_at": match.created_at.isoformat(),
            "updated_at": match.updated_at.isoformat(),
            "offer_start": match.offer.start_at.isoformat() if match.offer else None,
            "offer_end": match.offer.end_at.isoformat() if match.offer else None,
            "request_start": match.request.start_at.isoformat() if match.request else None,
            "request_end": match.request.end_at.isoformat() if match.request else None,
            "offer_owner_email": match.offer.user.email if match.offer and match.offer.user else None,
            "requester_email": match.request.user.email if match.request and match.request.user else None,
            "is_my_offer": match.offer.user_id == current_user.id if match.offer else False,
            "is_my_request": match.request.user_id == current_user.id if match.request else False,
        })

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/matches/{match_id}/accept", response_model=dict)
def accept_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a pending match (offer owner accepts request)."""
    # Lock the match row
    match = (
        db.query(Match)
        .filter(Match.id == match_id)
        .with_for_update()
        .first()
    )

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Verify user is the pending responder
    if match.pending_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to respond to this match")

    # Can only accept from PENDING status
    if match.status != MatchStatus.PENDING.value:
        raise HTTPException(status_code=400, detail=f"Cannot accept match in {match.status} status")

    # Update status and change pending user to requester
    match.status = MatchStatus.ACCEPTED.value
    match.pending_user_id = match.request.user_id
    match.updated_at = datetime.utcnow()

    db.add(match)
    db.flush()

    # Notify requester with HTML email
    _send_match_email(
        db,
        match.request.user,
        "email/match_accepted.html",
        "Regami - Votre demande a été acceptée!",
        match
    )

    # Send push notification to requester
    offer_dog = _get_user_first_dog(match.offer.user)
    fcm.notify_match_accepted(
        db=db,
        user_id=match.request.user_id,
        match_id=str(match.id),
        dog_name=offer_dog.name if offer_dog else "un chien"
    )

    db.commit()

    return {
        "status": "accepted",
        "match_id": match.id,
        "pending_user_id": match.pending_user_id
    }


@router.post("/matches/{match_id}/confirm", response_model=dict)
def confirm_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm an accepted match (requester confirms)."""
    # Lock the match row
    match = (
        db.query(Match)
        .filter(Match.id == match_id)
        .with_for_update()
        .first()
    )

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Verify user is the pending responder
    if match.pending_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to respond to this match")

    # Can only confirm from ACCEPTED status
    if match.status != MatchStatus.ACCEPTED.value:
        raise HTTPException(status_code=400, detail=f"Cannot confirm match in {match.status} status")

    # Final confirmation - mark as CONFIRMED
    match.status = MatchStatus.CONFIRMED.value
    match.pending_user_id = None  # No one needs to respond anymore
    match.updated_at = datetime.utcnow()

    db.add(match)
    db.flush()

    # Notify both parties with HTML email
    _send_match_email(
        db,
        match.offer.user,
        "email/match_confirmed.html",
        "Regami - Garde confirmée!",
        match
    )
    _send_match_email(
        db,
        match.request.user,
        "email/match_confirmed.html",
        "Regami - Garde confirmée!",
        match
    )

    # Send push notifications to both parties
    offer_dog = _get_user_first_dog(match.offer.user)
    request_dog = _get_user_first_dog(match.request.user)
    fcm.notify_match_confirmed(
        db=db,
        user_id=match.offer.user_id,
        match_id=str(match.id),
        dog_name=request_dog.name if request_dog else "un chien"
    )
    fcm.notify_match_confirmed(
        db=db,
        user_id=match.request.user_id,
        match_id=str(match.id),
        dog_name=offer_dog.name if offer_dog else "un chien"
    )

    db.commit()

    return {
        "status": "confirmed",
        "match_id": match.id,
        "offer_owner_email": match.offer.user.email,
        "requester_email": match.request.user.email,
    }


@router.post("/matches/{match_id}/reject", response_model=dict)
def reject_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a match (either party can reject)."""
    # Lock the match row
    match = (
        db.query(Match)
        .filter(Match.id == match_id)
        .with_for_update()
        .first()
    )

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Verify user is involved in this match
    is_offer_owner = match.offer.user_id == current_user.id if match.offer else False
    is_requester = match.request.user_id == current_user.id if match.request else False

    if not (is_offer_owner or is_requester):
        raise HTTPException(status_code=403, detail="Not authorized to reject this match")

    # Can only reject PENDING or ACCEPTED matches
    if match.status not in [MatchStatus.PENDING.value, MatchStatus.ACCEPTED.value]:
        raise HTTPException(status_code=400, detail=f"Cannot reject match in {match.status} status")

    # Mark as rejected
    match.status = MatchStatus.REJECTED.value
    match.pending_user_id = None
    match.updated_at = datetime.utcnow()

    db.add(match)
    db.flush()

    # Notify the other party with HTML email
    other_user = match.offer.user if is_requester else match.request.user
    _send_match_email(
        db,
        other_user,
        "email/match_rejected.html",
        "Regami - Demande de garde annulée",
        match
    )

    # Send push notification to the other party
    fcm.notify_match_rejected(
        db=db,
        user_id=other_user.id,
        match_id=str(match.id)
    )

    db.commit()

    return {
        "status": "rejected",
        "match_id": match.id
    }
