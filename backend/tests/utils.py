"""
Shared test utilities for cookie-based authentication and CSRF handling.
"""
from fastapi.testclient import TestClient

from app.main import create_app


def get_client() -> TestClient:
    """Create a new test client with a fresh app instance."""
    app = create_app()
    return TestClient(app)


def get_csrf_header(client: TestClient) -> dict:
    """Get CSRF token header from client cookies."""
    csrf_token = client.cookies.get("csrf_token")
    if csrf_token:
        return {"X-CSRF-Token": csrf_token}
    return {}


def register_and_login(
    client: TestClient,
    email: str,
    password: str,
    location_lat: float = 45.5,
    location_lng: float = -73.6,
    dog_name: str | None = None
) -> TestClient:
    """
    Register a user and login. Returns the client with cookies set.

    Args:
        client: TestClient instance to use
        email: User email
        password: User password
        location_lat: User latitude (default: 45.5)
        location_lng: User longitude (default: -73.6)
        dog_name: Optional dog name to register with

    Returns:
        The same client with authentication cookies set
    """
    registration_data = {
        "email": email,
        "password": password,
        "location_lat": location_lat,
        "location_lng": location_lng
    }
    if dog_name:
        registration_data["dog_name"] = dog_name

    r = client.post("/auth/register", json=registration_data)
    assert r.status_code == 200, f"Registration failed: {r.text}"

    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    # Login now sets cookies instead of returning access_token
    assert "access_token" in client.cookies, "No access_token cookie after login"
    return client


def create_authenticated_client(
    email: str,
    password: str,
    location_lat: float = 45.5,
    location_lng: float = -73.6,
    dog_name: str | None = None
) -> TestClient:
    """
    Create a new client and register/login a user.

    This is a convenience function that creates a new client and registers a user.
    Useful when you need multiple users with separate sessions.

    Returns:
        New TestClient with authentication cookies set
    """
    client = get_client()
    return register_and_login(client, email, password, location_lat, location_lng, dog_name)
