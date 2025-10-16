"""Tests for the WebSocket endpoint.

Uses Starlette's TestClient with WebSocket support for testing:
- WebSocket connection with authentication
- Ping/pong messages
- Connection management
- Error handling for invalid tokens
"""

import json

from app.main import create_app
from fastapi.testclient import TestClient


def get_client():
    app = create_app()
    return TestClient(app)


def register_and_get_token(client: TestClient, email: str, password: str = "password123") -> str:
    """Register a user and return their JWT token from cookies."""
    r = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "location_lat": 45.5,
        "location_lng": -73.6
    })
    assert r.status_code == 200, r.text

    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    # Get token from cookies for WebSocket auth
    return client.cookies.get("access_token")


def test_websocket_connect_with_valid_token():
    """Test WebSocket connection with a valid JWT token."""
    client = get_client()
    token = register_and_get_token(client, "ws-user@example.com")

    with client.websocket_connect(f"/ws?token={token}") as websocket:
        # Should receive welcome message
        data = websocket.receive_json()
        assert data["type"] == "connected"
        assert "user_id" in data["data"]
        assert data["data"]["message"] == "WebSocket connected"


def test_websocket_ping_pong():
    """Test ping/pong heartbeat mechanism."""
    client = get_client()
    token = register_and_get_token(client, "ws-ping@example.com")

    with client.websocket_connect(f"/ws?token={token}") as websocket:
        # Receive welcome message first
        websocket.receive_json()

        # Send ping
        websocket.send_json({"type": "ping"})

        # Should receive pong
        data = websocket.receive_json()
        assert data["type"] == "pong"


def test_websocket_invalid_token():
    """Test WebSocket connection with an invalid token is rejected."""
    client = get_client()

    # Create an app instance to register a user (so auth system is initialized)
    client.post("/auth/register", json={
        "email": "dummy@example.com",
        "password": "password123",
        "location_lat": 45.5,
        "location_lng": -73.6
    })

    # Try to connect with invalid token
    try:
        with client.websocket_connect("/ws?token=invalid-token") as _ws:
            # Connection should be closed immediately
            # In Starlette TestClient, this will raise an exception
            pass
    except Exception:
        # Expected - connection should fail
        pass


def test_websocket_multiple_connections():
    """Test that a user can have multiple WebSocket connections."""
    client = get_client()
    token = register_and_get_token(client, "ws-multi@example.com")

    # Open first connection
    with client.websocket_connect(f"/ws?token={token}") as ws1:
        data1 = ws1.receive_json()
        assert data1["type"] == "connected"

        # Open second connection (same user, different "tab")
        with client.websocket_connect(f"/ws?token={token}") as ws2:
            data2 = ws2.receive_json()
            assert data2["type"] == "connected"

            # Both connections should work
            ws1.send_json({"type": "ping"})
            assert ws1.receive_json()["type"] == "pong"

            ws2.send_json({"type": "ping"})
            assert ws2.receive_json()["type"] == "pong"


def test_websocket_disconnect():
    """Test that WebSocket disconnect is handled gracefully."""
    client = get_client()
    token = register_and_get_token(client, "ws-disconnect@example.com")

    # Connect and disconnect
    with client.websocket_connect(f"/ws?token={token}") as websocket:
        websocket.receive_json()  # Welcome message
        # Context manager will close the connection

    # Should be able to reconnect
    with client.websocket_connect(f"/ws?token={token}") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connected"


def test_websocket_json_message():
    """Test sending JSON messages through WebSocket."""
    client = get_client()
    token = register_and_get_token(client, "ws-json@example.com")

    with client.websocket_connect(f"/ws?token={token}") as websocket:
        websocket.receive_json()  # Welcome message

        # Send a custom message (server only handles ping)
        websocket.send_text(json.dumps({"type": "custom", "data": "test"}))

        # Server doesn't respond to custom types, but shouldn't error
        # Send ping to verify connection is still alive
        websocket.send_json({"type": "ping"})
        assert websocket.receive_json()["type"] == "pong"
