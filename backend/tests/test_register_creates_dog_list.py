from fastapi.testclient import TestClient
from app.main import create_app


def test_register_with_dog_name_creates_dog_link():
    app = create_app()
    client = TestClient(app)

    # Register with a valid dog name
    r = client.post("/auth/register", json={
        "email": "withdog@example.com",
        "password": "password123",
        "dog_name": "REX21"
    })
    assert r.status_code == 200, r.text

    # Login - cookies are automatically set
    r = client.post("/auth/login", data={"username": "withdog@example.com", "password": "password123"})
    assert r.status_code == 200, r.text

    # Dogs list should contain newly created dog (uppercased)
    r = client.get("/dogs/me")
    assert r.status_code == 200
    items = r.json()
    assert any(d["name"] == "REX21" for d in items)
