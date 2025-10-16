from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import create_app


# Create a single app instance for all tests
_app = None


def get_app():
    """Get or create the shared app instance."""
    global _app
    if _app is None:
        _app = create_app()
    return _app


def get_client() -> TestClient:
    """Create a new TestClient using the shared app instance."""
    return TestClient(get_app())


def get_csrf_header(client: TestClient) -> dict:
    """Get CSRF token header from client cookies."""
    csrf_token = client.cookies.get("csrf_token")
    if csrf_token:
        return {"X-CSRF-Token": csrf_token}
    return {}


def reg_login(email: str) -> TestClient:
    """Register and login a user, return client with cookies."""
    client = get_client()
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200, f"Registration failed for {email}: {r.text}"
    r = client.post("/auth/login", data={"username": email, "password": "password123"})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return client


def test_request_matches_offer_creates_notifications():
    client1 = reg_login("u1@example.com")
    client2 = reg_login("u2@example.com")

    now = datetime.utcnow()
    offer = {"start_at": (now + timedelta(hours=1)).isoformat(), "end_at": (now + timedelta(hours=4)).isoformat()}
    req = {"start_at": (now + timedelta(hours=2)).isoformat(), "end_at": (now + timedelta(hours=3)).isoformat()}

    r = client1.post("/availability/offers", json=offer, headers=get_csrf_header(client1))
    assert r.status_code == 200

    r = client2.post("/availability/requests", json=req, headers=get_csrf_header(client2))
    assert r.status_code == 200

    # Offer owner should get a notification
    r = client1.get("/notifications/me")
    assert r.status_code == 200
    notifs = r.json()
    assert len(notifs) >= 1


def test_offer_matches_existing_request_creates_notifications():
    client1 = reg_login("u3@example.com")
    client2 = reg_login("u4@example.com")

    now = datetime.utcnow()
    offer = {"start_at": (now + timedelta(hours=1)).isoformat(), "end_at": (now + timedelta(hours=4)).isoformat()}
    req = {"start_at": (now + timedelta(hours=2)).isoformat(), "end_at": (now + timedelta(hours=3)).isoformat()}

    r = client2.post("/availability/requests", json=req, headers=get_csrf_header(client2))
    assert r.status_code == 200

    r = client1.post("/availability/offers", json=offer, headers=get_csrf_header(client1))
    assert r.status_code == 200

    # Requester should get a notification
    r = client2.get("/notifications/me")
    assert r.status_code == 200
    notifs = r.json()
    assert len(notifs) >= 1
