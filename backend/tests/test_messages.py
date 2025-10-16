"""Tests for the messaging API endpoints.

Covers:
- POST /messages - Send a message
- GET /messages/conversations - List all conversations
- GET /messages/conversations/{user_id} - Get conversation thread
- PATCH /messages/{message_id}/read - Mark message as read
"""

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


def get_client():
    """Create a new TestClient using the shared app instance."""
    return TestClient(get_app())


def get_csrf_header(client: TestClient) -> dict:
    """Get CSRF token header from client cookies."""
    csrf_token = client.cookies.get("csrf_token")
    if csrf_token:
        return {"X-CSRF-Token": csrf_token}
    return {}


def register_and_login(
    client: TestClient, email: str, password: str = "password123"
) -> tuple[TestClient, str]:
    """Register a user and return (client_with_cookies, user_id)."""
    r = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "location_lat": 45.5,
        "location_lng": -73.6
    })
    assert r.status_code == 200, f"Registration failed for {email}: {r.text}"
    user_id = r.json()["id"]

    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    # Cookies are automatically set on the client
    return client, user_id


def test_send_message():
    """Test sending a message to another user."""
    # Use separate clients for each user to maintain separate cookie sessions
    client_alice = get_client()
    client_bob = get_client()

    # Register two users
    client_alice, alice_id = register_and_login(client_alice, "alice-msg@example.com")
    client_bob, bob_id = register_and_login(client_bob, "bob-msg@example.com")

    # Alice sends a message to Bob (POST needs CSRF token)
    r = client_alice.post(
        "/messages",
        json={"recipient_id": bob_id, "content": "Hello Bob!"},
        headers=get_csrf_header(client_alice)
    )
    assert r.status_code == 201, r.text
    msg = r.json()
    assert msg["content"] == "Hello Bob!"
    assert msg["sender_id"] == alice_id
    assert msg["recipient_id"] == bob_id
    assert msg["is_read"] is False
    assert msg["sender_email"] == "alice-msg@example.com"
    assert msg["recipient_email"] == "bob-msg@example.com"


def test_send_message_to_nonexistent_user():
    """Test sending a message to a user that doesn't exist."""
    client = get_client()
    client, _ = register_and_login(client, "sender@example.com")

    r = client.post(
        "/messages",
        json={"recipient_id": "nonexistent-user-id", "content": "Hello?"},
        headers=get_csrf_header(client)
    )
    assert r.status_code == 404
    # Bilingual error messages - check for "not found" in either language
    assert "not found" in r.json()["detail"].lower() or "introuvable" in r.json()["detail"].lower()


def test_send_message_to_self():
    """Test that a user cannot send a message to themselves."""
    client = get_client()
    client, user_id = register_and_login(client, "self-sender@example.com")

    r = client.post(
        "/messages",
        json={"recipient_id": user_id, "content": "Talking to myself"},
        headers=get_csrf_header(client)
    )
    assert r.status_code == 400
    # Check error message (bilingual or specific)
    detail = r.json()["detail"].lower()
    assert "yourself" in detail or "vous-même" in detail or "self" in detail


def test_list_conversations():
    """Test listing all conversations for a user."""
    # Use separate clients for each user
    client_alice = get_client()
    client_bob = get_client()
    client_carol = get_client()

    # Register three users
    client_alice, alice_id = register_and_login(client_alice, "alice-conv@example.com")
    client_bob, bob_id = register_and_login(client_bob, "bob-conv@example.com")
    client_carol, carol_id = register_and_login(client_carol, "carol-conv@example.com")

    # Alice sends messages to Bob and Carol
    client_alice.post(
        "/messages",
        json={"recipient_id": bob_id, "content": "Hi Bob!"},
        headers=get_csrf_header(client_alice)
    )
    client_alice.post(
        "/messages",
        json={"recipient_id": carol_id, "content": "Hi Carol!"},
        headers=get_csrf_header(client_alice)
    )

    # Bob replies to Alice
    client_bob.post(
        "/messages",
        json={"recipient_id": alice_id, "content": "Hey Alice!"},
        headers=get_csrf_header(client_bob)
    )

    # Check Alice's conversations (GET doesn't need CSRF)
    r = client_alice.get("/messages/conversations")
    assert r.status_code == 200
    convos = r.json()
    assert len(convos) == 2

    # Conversations should be sorted by most recent first
    # Bob replied last, so Bob should be first
    assert convos[0]["other_user_email"] == "bob-conv@example.com"
    assert convos[0]["last_message"] == "Hey Alice!"
    assert convos[0]["unread_count"] == 1  # Bob's reply is unread

    assert convos[1]["other_user_email"] == "carol-conv@example.com"
    assert convos[1]["last_message"] == "Hi Carol!"
    assert convos[1]["unread_count"] == 0  # Alice sent this, no unread


def test_get_conversation_thread():
    """Test getting the full message thread with a specific user."""
    client_alice = get_client()
    client_bob = get_client()

    client_alice, alice_id = register_and_login(client_alice, "alice-thread@example.com")
    client_bob, bob_id = register_and_login(client_bob, "bob-thread@example.com")

    # Exchange some messages
    client_alice.post(
        "/messages",
        json={"recipient_id": bob_id, "content": "Message 1"},
        headers=get_csrf_header(client_alice)
    )
    client_bob.post(
        "/messages",
        json={"recipient_id": alice_id, "content": "Message 2"},
        headers=get_csrf_header(client_bob)
    )
    client_alice.post(
        "/messages",
        json={"recipient_id": bob_id, "content": "Message 3"},
        headers=get_csrf_header(client_alice)
    )

    # Get the thread from Alice's perspective (GET doesn't need CSRF)
    r = client_alice.get(f"/messages/conversations/{bob_id}")
    assert r.status_code == 200
    messages = r.json()
    assert len(messages) == 3

    # Messages should be ordered by most recent first (desc)
    assert messages[0]["content"] == "Message 3"
    assert messages[1]["content"] == "Message 2"
    assert messages[2]["content"] == "Message 1"


def test_get_conversation_with_nonexistent_user():
    """Test getting a conversation with a user that doesn't exist."""
    client = get_client()
    client, _ = register_and_login(client, "viewer@example.com")

    r = client.get("/messages/conversations/nonexistent-user-id")
    assert r.status_code == 404
    # Bilingual error messages
    assert "not found" in r.json()["detail"].lower() or "introuvable" in r.json()["detail"].lower()


def test_get_conversation_marks_as_read():
    """Test that viewing a conversation marks messages as read."""
    client_alice = get_client()
    client_bob = get_client()

    client_alice, alice_id = register_and_login(client_alice, "alice-read@example.com")
    client_bob, bob_id = register_and_login(client_bob, "bob-read@example.com")

    # Bob sends a message to Alice
    client_bob.post(
        "/messages",
        json={"recipient_id": alice_id, "content": "Read me!"},
        headers=get_csrf_header(client_bob)
    )

    # Check Alice's unread count
    r = client_alice.get("/messages/conversations")
    assert r.json()[0]["unread_count"] == 1

    # Alice views the conversation (marks as read)
    client_alice.get(f"/messages/conversations/{bob_id}")

    # Check unread count again - should be 0
    r = client_alice.get("/messages/conversations")
    assert r.json()[0]["unread_count"] == 0


def test_mark_message_as_read():
    """Test marking a specific message as read."""
    client_alice = get_client()
    client_bob = get_client()

    client_alice, alice_id = register_and_login(client_alice, "alice-mark@example.com")
    client_bob, bob_id = register_and_login(client_bob, "bob-mark@example.com")

    # Bob sends a message to Alice
    r = client_bob.post(
        "/messages",
        json={"recipient_id": alice_id, "content": "Mark me read!"},
        headers=get_csrf_header(client_bob)
    )
    message_id = r.json()["id"]

    # Alice marks it as read (PATCH needs CSRF)
    r = client_alice.patch(
        f"/messages/{message_id}/read",
        headers=get_csrf_header(client_alice)
    )
    assert r.status_code == 200
    assert r.json()["is_read"] is True


def test_mark_nonexistent_message_as_read():
    """Test marking a nonexistent message as read."""
    client = get_client()
    client, _ = register_and_login(client, "marker@example.com")

    r = client.patch("/messages/99999/read", headers=get_csrf_header(client))
    assert r.status_code == 404
    # Bilingual error messages
    assert "not found" in r.json()["detail"].lower() or "introuvable" in r.json()["detail"].lower()


def test_mark_other_users_message_as_read():
    """Test that a user cannot mark another user's received message as read."""
    client_alice = get_client()
    client_bob = get_client()
    client_carol = get_client()

    client_alice, alice_id = register_and_login(client_alice, "alice-other@example.com")
    client_bob, bob_id = register_and_login(client_bob, "bob-other@example.com")
    client_carol, _ = register_and_login(client_carol, "carol-other@example.com")

    # Alice sends a message to Bob
    r = client_alice.post(
        "/messages",
        json={"recipient_id": bob_id, "content": "For Bob only"},
        headers=get_csrf_header(client_alice)
    )
    message_id = r.json()["id"]

    # Carol tries to mark it as read (she's not the recipient)
    r = client_carol.patch(
        f"/messages/{message_id}/read",
        headers=get_csrf_header(client_carol)
    )
    assert r.status_code == 403
    # Bilingual error messages
    detail = r.json()["detail"].lower()
    assert "mark other" in detail or "other user" in detail or "forbidden" in detail or "interdit" in detail


def test_unauthenticated_access():
    """Test that unauthenticated requests are rejected."""
    client = get_client()

    # All endpoints should require authentication
    # POST/PATCH may return 403 (CSRF) before reaching auth check, or 401 (auth)
    assert client.post("/messages", json={"recipient_id": "x", "content": "test"}).status_code in (401, 403)
    assert client.get("/messages/conversations").status_code == 401
    assert client.get("/messages/conversations/some-id").status_code == 401
    assert client.patch("/messages/1/read").status_code in (401, 403)
