#!/usr/bin/env python3
"""
Database seeding script for development and testing.

Usage:
    python backend/scripts/seed.py --environment dev
    python backend/scripts/seed.py --environment test --clear
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.dog import Dog
from app.models.user import User
from app.models.user_dog import UserDog
from app.models.availability import AvailabilityOffer, AvailabilityRequest
from app.models.match import Match
from app.models.message import Message
from app.models.notification import Notification
from app.core.security import get_password_hash


# Sample data
SAMPLE_USERS = [
    {
        "email": "alice@example.com",
        "password": "password123",
        "full_name": "Alice Johnson",
        "phone_number": "+1234567890",
        "location": "San Francisco, CA",
        "bio": "Dog lover and outdoor enthusiast!",
    },
    {
        "email": "bob@example.com",
        "password": "password123",
        "full_name": "Bob Smith",
        "phone_number": "+1234567891",
        "location": "Seattle, WA",
        "bio": "Looking for play dates for my energetic pup.",
    },
    {
        "email": "carol@example.com",
        "password": "password123",
        "full_name": "Carol Davis",
        "phone_number": "+1234567892",
        "location": "Portland, OR",
        "bio": "Experienced dog sitter available weekends.",
    },
    {
        "email": "david@example.com",
        "password": "password123",
        "full_name": "David Lee",
        "phone_number": "+1234567893",
        "location": "San Francisco, CA",
        "bio": "First-time dog owner seeking advice and companionship.",
    },
]

SAMPLE_DOGS = [
    {
        "name": "Max",
        "breed": "Golden Retriever",
        "age": 3,
        "size": "large",
        "temperament": "friendly",
        "special_needs": "None",
        "description": "Loves to play fetch and swim!",
    },
    {
        "name": "Bella",
        "breed": "French Bulldog",
        "age": 2,
        "size": "small",
        "temperament": "calm",
        "special_needs": "Needs short walks due to breathing",
        "description": "Sweet and cuddly companion.",
    },
    {
        "name": "Charlie",
        "breed": "Mixed Breed",
        "age": 5,
        "size": "medium",
        "temperament": "energetic",
        "special_needs": "None",
        "description": "High energy, loves running and hiking.",
    },
    {
        "name": "Luna",
        "breed": "Labrador Retriever",
        "age": 1,
        "size": "large",
        "temperament": "friendly",
        "special_needs": "None",
        "description": "Puppy in training, very playful!",
    },
]


async def clear_database(session: AsyncSession):
    """Clear all data from database."""
    print("Clearing database...")

    # Delete in reverse dependency order
    await session.execute("DELETE FROM notifications")
    await session.execute("DELETE FROM messages")
    await session.execute("DELETE FROM matches")
    await session.execute("DELETE FROM availability_requests")
    await session.execute("DELETE FROM availability_offers")
    await session.execute("DELETE FROM user_dogs")
    await session.execute("DELETE FROM dogs")
    await session.execute("DELETE FROM users")

    await session.commit()
    print("Database cleared.")


async def seed_users(session: AsyncSession) -> List[User]:
    """Create sample users."""
    print(f"Creating {len(SAMPLE_USERS)} users...")

    users = []
    for user_data in SAMPLE_USERS:
        user = User(
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            full_name=user_data["full_name"],
            phone_number=user_data["phone_number"],
            location=user_data["location"],
            bio=user_data["bio"],
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(user)
        users.append(user)

    await session.commit()

    # Refresh to get IDs
    for user in users:
        await session.refresh(user)

    print(f"Created {len(users)} users.")
    return users


async def seed_dogs(session: AsyncSession, users: List[User]) -> List[Dog]:
    """Create sample dogs and associate with users."""
    print(f"Creating {len(SAMPLE_DOGS)} dogs...")

    dogs = []
    for i, dog_data in enumerate(SAMPLE_DOGS):
        dog = Dog(
            name=dog_data["name"],
            breed=dog_data["breed"],
            age=dog_data["age"],
            size=dog_data["size"],
            temperament=dog_data["temperament"],
            special_needs=dog_data["special_needs"],
            description=dog_data["description"],
            created_at=datetime.utcnow(),
        )
        session.add(dog)
        dogs.append(dog)

    await session.commit()

    # Refresh to get IDs
    for dog in dogs:
        await session.refresh(dog)

    # Create user-dog associations (each user owns one dog)
    for i, (user, dog) in enumerate(zip(users, dogs)):
        user_dog = UserDog(
            user_id=user.id,
            dog_id=dog.id,
            relationship="owner",
            created_at=datetime.utcnow(),
        )
        session.add(user_dog)

    await session.commit()
    print(f"Created {len(dogs)} dogs and associations.")
    return dogs


async def seed_availability(session: AsyncSession, users: List[User]):
    """Create sample availability offers and requests."""
    print("Creating availability offers and requests...")

    # User 0 (Alice) offers dog sitting
    offer1 = AvailabilityOffer(
        user_id=users[0].id,
        start_date=datetime.utcnow() + timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=7),
        service_type="dog_sitting",
        location=users[0].location,
        description="Available for dog sitting next week!",
        created_at=datetime.utcnow(),
    )
    session.add(offer1)

    # User 2 (Carol) offers dog walking
    offer2 = AvailabilityOffer(
        user_id=users[2].id,
        start_date=datetime.utcnow() + timedelta(days=2),
        end_date=datetime.utcnow() + timedelta(days=14),
        service_type="dog_walking",
        location=users[2].location,
        description="Weekend dog walking available.",
        created_at=datetime.utcnow(),
    )
    session.add(offer2)

    # User 1 (Bob) requests play date
    request1 = AvailabilityRequest(
        user_id=users[1].id,
        start_date=datetime.utcnow() + timedelta(days=3),
        end_date=datetime.utcnow() + timedelta(days=10),
        service_type="play_date",
        location=users[1].location,
        description="Looking for a play date for my energetic dog!",
        created_at=datetime.utcnow(),
    )
    session.add(request1)

    # User 3 (David) requests dog sitting
    request2 = AvailabilityRequest(
        user_id=users[3].id,
        start_date=datetime.utcnow() + timedelta(days=5),
        end_date=datetime.utcnow() + timedelta(days=8),
        service_type="dog_sitting",
        location=users[3].location,
        description="Need a sitter for 3 days while traveling.",
        created_at=datetime.utcnow(),
    )
    session.add(request2)

    await session.commit()
    print("Created availability offers and requests.")


async def seed_matches(session: AsyncSession, users: List[User]):
    """Create sample matches between users."""
    print("Creating matches...")

    # Alice and David match (sitting offer meets request)
    match1 = Match(
        requester_id=users[3].id,
        provider_id=users[0].id,
        status="confirmed",
        created_at=datetime.utcnow() - timedelta(days=2),
        confirmed_at=datetime.utcnow() - timedelta(days=1),
    )
    session.add(match1)

    # Bob and Carol match (play date pending)
    match2 = Match(
        requester_id=users[1].id,
        provider_id=users[2].id,
        status="pending",
        created_at=datetime.utcnow() - timedelta(hours=12),
    )
    session.add(match2)

    await session.commit()

    # Refresh to get IDs
    await session.refresh(match1)
    await session.refresh(match2)

    print(f"Created 2 matches.")
    return [match1, match2]


async def seed_messages(session: AsyncSession, users: List[User], matches: List[Match]):
    """Create sample messages between matched users."""
    print("Creating messages...")

    # Messages between Alice and David (confirmed match)
    messages = [
        Message(
            sender_id=users[3].id,
            receiver_id=users[0].id,
            content="Hi Alice! I saw your dog sitting offer. Are you still available next week?",
            created_at=datetime.utcnow() - timedelta(days=2, hours=2),
        ),
        Message(
            sender_id=users[0].id,
            receiver_id=users[3].id,
            content="Hi David! Yes, I'm available. I'd love to help!",
            created_at=datetime.utcnow() - timedelta(days=2, hours=1),
        ),
        Message(
            sender_id=users[3].id,
            receiver_id=users[0].id,
            content="Great! Can we meet up this weekend to discuss details?",
            created_at=datetime.utcnow() - timedelta(days=1, hours=20),
        ),
        Message(
            sender_id=users[0].id,
            receiver_id=users[3].id,
            content="Sounds perfect! Saturday afternoon works for me.",
            created_at=datetime.utcnow() - timedelta(days=1, hours=18),
        ),
        # Messages between Bob and Carol (pending match)
        Message(
            sender_id=users[1].id,
            receiver_id=users[2].id,
            content="Hi Carol! Would you be interested in a play date for our dogs?",
            created_at=datetime.utcnow() - timedelta(hours=10),
        ),
    ]

    for message in messages:
        session.add(message)

    await session.commit()
    print(f"Created {len(messages)} messages.")


async def seed_notifications(session: AsyncSession, users: List[User]):
    """Create sample notifications."""
    print("Creating notifications...")

    notifications = [
        Notification(
            user_id=users[0].id,
            title="New Match!",
            message="You have a new match with David.",
            type="match",
            created_at=datetime.utcnow() - timedelta(days=2),
            read=True,
        ),
        Notification(
            user_id=users[3].id,
            title="Match Confirmed",
            message="Alice has confirmed your dog sitting request!",
            type="match",
            created_at=datetime.utcnow() - timedelta(days=1),
            read=True,
        ),
        Notification(
            user_id=users[1].id,
            title="New Message",
            message="You have a new message from Carol.",
            type="message",
            created_at=datetime.utcnow() - timedelta(hours=8),
            read=False,
        ),
        Notification(
            user_id=users[2].id,
            title="New Match Request",
            message="Bob is interested in a play date!",
            type="match",
            created_at=datetime.utcnow() - timedelta(hours=12),
            read=False,
        ),
    ]

    for notification in notifications:
        session.add(notification)

    await session.commit()
    print(f"Created {len(notifications)} notifications.")


async def main():
    parser = argparse.ArgumentParser(description="Seed database with sample data")
    parser.add_argument(
        "--environment",
        choices=["dev", "test"],
        default="dev",
        help="Environment to seed (dev or test)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before seeding",
    )
    parser.add_argument(
        "--database-url",
        help="Database URL (overrides environment default)",
    )

    args = parser.parse_args()

    # Determine database URL
    if args.database_url:
        database_url = args.database_url
    elif args.environment == "test":
        database_url = "sqlite+aiosqlite:///./test.db"
    else:
        database_url = "sqlite+aiosqlite:///./regami.db"

    print(f"Seeding {args.environment} database: {database_url}")

    # Create async engine with connection timeout
    connect_args = {"timeout": 10} if "sqlite" in database_url else {"connect_timeout": 10}
    engine = create_async_engine(database_url, echo=False, connect_args=connect_args)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            if args.clear:
                await clear_database(session)

            # Seed data in order
            users = await seed_users(session)
            dogs = await seed_dogs(session, users)
            await seed_availability(session, users)
            matches = await seed_matches(session, users)
            await seed_messages(session, users, matches)
            await seed_notifications(session, users)

            print("\n✓ Database seeding completed successfully!")
            print(f"\nSample login credentials (all passwords: 'password123'):")
            for user in users:
                print(f"  - {user.email}")

        except Exception as e:
            print(f"\n✗ Error seeding database: {e}", file=sys.stderr)
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
