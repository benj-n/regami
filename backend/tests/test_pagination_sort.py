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


def test_offers_pagination_and_sort():
    client = reg_login("pager@example.com")

    now = datetime.utcnow()
    # Create 5 offers spaced by 1 hour
    for i in range(5):
        start = now + timedelta(hours=1 + i)
        end = start + timedelta(hours=1)
        r = client.post(
            "/availability/offers",
            json={"start_at": start.isoformat(), "end_at": end.isoformat()},
            headers=get_csrf_header(client)
        )
        assert r.status_code == 200

    # Desc sort (default): latest first - GET doesn't need CSRF
    r = client.get("/availability/offers/mine?page=1&page_size=2")
    data = r.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    first_page = data["items"]

    r = client.get("/availability/offers/mine?page=2&page_size=2")
    data2 = r.json()
    assert len(data2["items"]) == 2
    # Ensure order is descending by start_at
    assert first_page[0]["start_at"] > data2["items"][0]["start_at"]

    # Asc sort
    r = client.get("/availability/offers/mine?page=1&page_size=1&sort=start_at")
    asc_first = r.json()["items"][0]["start_at"]
    r = client.get("/availability/offers/mine?page=5&page_size=1&sort=start_at")
    asc_last = r.json()["items"][0]["start_at"]
    assert asc_first < asc_last


def test_requests_pagination_and_sort():
    client = reg_login("pager2@example.com")

    now = datetime.utcnow()
    # Create 3 requests spaced by 2 hours
    for i in range(3):
        start = now + timedelta(hours=2 * i + 1)
        end = start + timedelta(hours=1)
        r = client.post(
            "/availability/requests",
            json={"start_at": start.isoformat(), "end_at": end.isoformat()},
            headers=get_csrf_header(client)
        )
        assert r.status_code == 200

    r = client.get("/availability/requests/mine?page=1&page_size=2")
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    # Asc
    r = client.get("/availability/requests/mine?page=1&page_size=1&sort=start_at")
    first = r.json()["items"][0]["start_at"]
    r = client.get("/availability/requests/mine?page=3&page_size=1&sort=start_at")
    last = r.json()["items"][0]["start_at"]
    assert first < last
