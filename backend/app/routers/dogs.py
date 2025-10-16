from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
import os
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional
import math

from ..db import get_db
from ..models import Dog, UserDog, User
from ..schemas import DogCreate, DogUpdate, DogOut
from .users import get_current_user
from ..services import storage as storage_mod

router = APIRouter()


def _ensure_owner(db: Session, user_id: str, dog_id: int) -> Dog:
    dog = db.get(Dog, dog_id)
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    link = (
        db.query(UserDog)
        .filter(and_(UserDog.user_id == user_id, UserDog.dog_id == dog_id, UserDog.is_owner.is_(True)))
        .first()
    )
    if not link:
        raise HTTPException(status_code=403, detail="Not an owner")
    return dog


@router.get("/me", response_model=list[DogOut])
def list_my_dogs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(Dog)
        .join(UserDog, UserDog.dog_id == Dog.id)
        .filter(UserDog.user_id == current_user.id)
        .order_by(Dog.created_at.desc())
        .all()
    )
    return rows


@router.post("/", response_model=DogOut)
def create_dog(payload: DogCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dog = Dog(
        name=payload.name,
        photo_url=payload.photo_url,
        birth_month=payload.birth_month,
        birth_year=payload.birth_year,
        sex=payload.sex
    )
    db.add(dog)
    db.flush()  # get id
    db.add(UserDog(user_id=current_user.id, dog_id=dog.id, is_owner=True))
    db.commit()
    db.refresh(dog)
    return dog


@router.put("/{dog_id}", response_model=DogOut)
def update_dog(dog_id: int, payload: DogUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dog = _ensure_owner(db, current_user.id, dog_id)
    # Enforce name immutability
    if getattr(payload, "name", None) is not None:
        raise HTTPException(status_code=400, detail="Dog name is immutable")
    if payload.photo_url is not None:
        dog.photo_url = payload.photo_url
    if payload.birth_month is not None:
        dog.birth_month = payload.birth_month
    if payload.birth_year is not None:
        dog.birth_year = payload.birth_year
    if payload.sex is not None:
        dog.sex = payload.sex
    db.add(dog)
    db.commit()
    db.refresh(dog)
    return dog


@router.delete("/{dog_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dog(dog_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dog = _ensure_owner(db, current_user.id, dog_id)
    # Cascade via relationships will remove links
    db.delete(dog)
    db.commit()
    return


@router.post("/{dog_id}/photo", response_model=DogOut)
def upload_dog_photo(
    dog_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dog = _ensure_owner(db, current_user.id, dog_id)
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")
    try:
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)
    except Exception:
        size = 0
    if size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    storage = storage_mod.get_storage()
    # Save with original filename to preserve extension if present
    filename = file.filename or "upload"
    url = storage.save(file.file, filename, content_type=file.content_type)
    dog.photo_url = url
    db.add(dog)
    db.commit()
    db.refresh(dog)
    return dog


@router.post("/{dog_id}/coowners/{user_id}", status_code=200)
def add_coowner(dog_id: int, user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ = _ensure_owner(db, current_user.id, dog_id)
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(UserDog).filter(and_(UserDog.user_id == user_id, UserDog.dog_id == dog_id)).first()
    if existing:
        existing.is_owner = True
        db.add(existing)
    else:
        db.add(UserDog(user_id=user_id, dog_id=dog_id, is_owner=True))
    db.commit()
    return {"status": "ok"}


@router.delete("/{dog_id}/coowners/{user_id}", status_code=200)
def remove_coowner(dog_id: int, user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ = _ensure_owner(db, current_user.id, dog_id)
    link = db.query(UserDog).filter(and_(UserDog.user_id == user_id, UserDog.dog_id == dog_id)).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    db.delete(link)
    db.commit()
    return {"status": "ok"}


@router.get("/search", response_model=dict)
def search_dogs(
    name: Optional[str] = Query(None, description="Search by dog name (partial match)"),
    lat: Optional[float] = Query(None, description="Search latitude for proximity"),
    lng: Optional[float] = Query(None, description="Search longitude for proximity"),
    radius_km: Optional[float] = Query(10.0, description="Search radius in kilometers"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search for dogs with optional filters.

    - name: Partial case-insensitive match on dog name
    - lat/lng: Filter by proximity (requires both)
    - radius_km: Distance radius when using lat/lng (default: 10km)
    """
    query = db.query(Dog).join(UserDog, UserDog.dog_id == Dog.id)

    # Filter by name (partial match, case-insensitive)
    if name:
        query = query.filter(Dog.name.ilike(f"%{name}%"))

    # Filter by location proximity using haversine formula
    if lat is not None and lng is not None:
        # Haversine distance calculation
        # This is an approximation - for production, consider PostGIS
        earth_radius_km = 6371.0
        lat_rad = func.radians(lat)

        # Calculate distance for each user who owns dogs
        # Filter users within radius
        query = query.join(User, UserDog.user_id == User.id).filter(
            and_(
                User.location_lat.isnot(None),
                User.location_lng.isnot(None),
            )
        ).filter(
            # Simplified haversine: approximate distance filter
            # For production, use proper geospatial queries with PostGIS
            or_(
                # Within bounding box (rough filter)
                and_(
                    User.location_lat >= lat - (radius_km / 111.0),
                    User.location_lat <= lat + (radius_km / 111.0),
                    User.location_lng >= lng - (radius_km / (111.0 * func.cos(lat_rad))),
                    User.location_lng <= lng + (radius_km / (111.0 * func.cos(lat_rad)))
                )
            )
        )

    # Get total count
    total = query.count()

    # Pagination
    items = (
        query
        .order_by(Dog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Calculate distance if lat/lng provided
    results = []
    for dog in items:
        dog_dict = {
            "id": dog.id,
            "name": dog.name,
            "photo_url": dog.photo_url,
            "created_at": dog.created_at.isoformat()
        }

        # Add distance if searching by location
        if lat is not None and lng is not None:
            # Get owner's location
            owner_link = db.query(UserDog).filter(
                and_(UserDog.dog_id == dog.id, UserDog.is_owner.is_(True))
            ).first()
            if owner_link:
                owner = db.get(User, owner_link.user_id)
                if owner and owner.location_lat and owner.location_lng:
                    # Simple haversine distance
                    dlat = math.radians(owner.location_lat - lat)
                    dlng = math.radians(owner.location_lng - lng)
                    a = (math.sin(dlat / 2) ** 2 +
                         math.cos(math.radians(lat)) * math.cos(math.radians(owner.location_lat)) *
                         math.sin(dlng / 2) ** 2)
                    c = 2 * math.asin(math.sqrt(a))
                    distance_km = earth_radius_km * c
                    dog_dict["distance_km"] = round(distance_km, 2)

        results.append(dog_dict)

    # Sort by distance if available
    if lat is not None and lng is not None:
        results.sort(key=lambda x: x.get("distance_km", float('inf')))

    return {
        "items": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page * page_size) < total
    }
