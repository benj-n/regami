from fastapi.testclient import TestClient
from app.main import create_app


def get_client():
    app = create_app()
    return TestClient(app)


def get_csrf_header(client: TestClient) -> dict:
    """Get CSRF token header from client cookies."""
    csrf_token = client.cookies.get("csrf_token")
    if csrf_token:
        return {"X-CSRF-Token": csrf_token}
    return {}


def register_and_login(client: TestClient, email: str, password: str) -> TestClient:
    """Register a user and login. Returns the client with cookies set."""
    r = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "location_lat": 45.5,
        "location_lng": -73.6
    })
    assert r.status_code == 200, r.text

    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    # Login now sets cookies instead of returning access_token
    assert "access_token" in client.cookies
    return client


def test_register_login_profile_flow():
    client = get_client()
    client = register_and_login(client, "alice@example.com", "password123")

    # Cookie-based auth - no need for Authorization header
    r = client.get("/users/me")
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == "alice@example.com"

    # Update only location fields now (include CSRF token for state-changing request)
    r = client.put("/users/me", json={"location_lat": 46.0}, headers=get_csrf_header(client))
    assert r.status_code == 200
