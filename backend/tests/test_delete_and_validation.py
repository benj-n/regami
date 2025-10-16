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


def test_delete_offer_and_request_with_ownership():
    # Each user needs their own client to maintain separate sessions
    client1 = reg_login("owner@example.com")
    client2 = reg_login("other@example.com")

    now = datetime.utcnow()
    offer = {"start_at": (now + timedelta(hours=1)).isoformat(), "end_at": (now + timedelta(hours=2)).isoformat()}
    req = {"start_at": (now + timedelta(hours=3)).isoformat(), "end_at": (now + timedelta(hours=4)).isoformat()}

    # Create offer and request as client1
    r = client1.post("/availability/offers", json=offer, headers=get_csrf_header(client1))
    assert r.status_code == 200, r.text
    offer_id = r.json()["id"]

    r = client1.post("/availability/requests", json=req, headers=get_csrf_header(client1))
    assert r.status_code == 200, r.text
    req_id = r.json()["id"]

    # Other user cannot delete
    r = client2.delete(f"/availability/offers/{offer_id}", headers=get_csrf_header(client2))
    assert r.status_code == 404
    r = client2.delete(f"/availability/requests/{req_id}", headers=get_csrf_header(client2))
    assert r.status_code == 404

    # Owner can delete
    r = client1.delete(f"/availability/offers/{offer_id}", headers=get_csrf_header(client1))
    assert r.status_code == 204
    r = client1.delete(f"/availability/requests/{req_id}", headers=get_csrf_header(client1))
    assert r.status_code == 204

    # Lists should be empty
    r = client1.get("/availability/offers/mine")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    r = client1.get("/availability/requests/mine")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0


def test_validation_invalid_and_overlapping_and_past():
    client = reg_login("val@example.com")

    now = datetime.utcnow()

    # invalid: end <= start
    bad = {"start_at": (now + timedelta(hours=2)).isoformat(), "end_at": (now + timedelta(hours=1)).isoformat()}
    r = client.post("/availability/offers", json=bad, headers=get_csrf_header(client))
    assert r.status_code == 400
    r = client.post("/availability/requests", json=bad, headers=get_csrf_header(client))
    assert r.status_code == 400

    # past: any part in past is rejected
    past = {"start_at": (now - timedelta(hours=2)).isoformat(), "end_at": (now - timedelta(hours=1)).isoformat()}
    r = client.post("/availability/offers", json=past, headers=get_csrf_header(client))
    assert r.status_code == 400
    r = client.post("/availability/requests", json=past, headers=get_csrf_header(client))
    assert r.status_code == 400

    # ok slot
    a = {"start_at": (now + timedelta(hours=1)).isoformat(), "end_at": (now + timedelta(hours=2)).isoformat()}
    r = client.post("/availability/offers", json=a, headers=get_csrf_header(client))
    assert r.status_code == 200
    # overlapping with 'a'
    a2 = {"start_at": (now + timedelta(hours=1, minutes=30)).isoformat(), "end_at": (now + timedelta(hours=2, minutes=30)).isoformat()}
    r = client.post("/availability/offers", json=a2, headers=get_csrf_header(client))
    assert r.status_code == 400

    # same for requests
    r = client.post("/availability/requests", json=a, headers=get_csrf_header(client))
    assert r.status_code == 200
    r = client.post("/availability/requests", json=a2, headers=get_csrf_header(client))
    assert r.status_code == 400
