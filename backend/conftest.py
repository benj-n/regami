import os
import sys
from pathlib import Path

import pytest


# Add the app/ directory to PYTHONPATH for tests
APP_DIR = Path(__file__).resolve().parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# Configure test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test_regami.db"
os.environ["RESET_DB_ON_STARTUP"] = "true"
os.environ["TESTING"] = "1"  # Disable rate limiting for tests


@pytest.fixture(scope="function", autouse=True)
def reset_database():
    """Reset the database before each test for isolation."""
    from app.db import Base, engine

    # Drop and recreate all tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    # Optional: cleanup after test (tables will be dropped before next test anyway)
