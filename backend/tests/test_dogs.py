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


def login_client(email: str) -> TestClient:
    """Register and login, return client with cookies set."""
    client = get_client()
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "pass12345",
            "location_lat": None,
            "location_lng": None,
        },
    )
    r = client.post("/auth/login", data={"username": email, "password": "pass12345"})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return client


def test_create_list_update_delete_dog_and_photo(tmp_path):
    client = login_client("dogowner@example.com")

    # Create a dog (POST needs CSRF)
    r = client.post("/dogs/", json={"name": "BUDDY21", "birth_month": 6, "birth_year": 2020, "sex": "male"}, headers=get_csrf_header(client))
    assert r.status_code == 200, r.text
    dog = r.json()
    dog_id = dog["id"]

    # List my dogs (GET doesn't need CSRF)
    r = client.get("/dogs/me")
    assert r.status_code == 200
    items = r.json()
    assert any(d["id"] == dog_id for d in items)

    # Update name should be rejected (immutable)
    r = client.put(f"/dogs/{dog_id}", json={"name": "BUDDY22"}, headers=get_csrf_header(client))
    assert r.status_code == 400

    # Upload a photo (local storage mounted under /static/uploads)
    # Create a tiny bytes payload
    payload = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    files = {"file": ("photo.png", payload, "image/png")}
    r = client.post(f"/dogs/{dog_id}/photo", files=files, headers=get_csrf_header(client))
    assert r.status_code == 200, r.text
    photo_url = r.json()["photo_url"]
    assert photo_url is not None
    assert "/static/uploads/" in photo_url or photo_url.startswith("s3://") or photo_url.startswith("http")

    # Delete (DELETE needs CSRF)
    r = client.delete(f"/dogs/{dog_id}", headers=get_csrf_header(client))
    assert r.status_code == 204


def test_coowner_and_permissions():
    # Each user needs their own client
    client_a = login_client("a@example.com")
    client_b = login_client("b@example.com")
    client_c = login_client("c@example.com")

    # Create by A
    r = client_a.post("/dogs/", json={"name": "ROXY99", "birth_month": 3, "birth_year": 2019, "sex": "female"}, headers=get_csrf_header(client_a))
    assert r.status_code == 200
    dog = r.json()
    dog_id = dog["id"]

    # Get B's user id
    me_b = client_b.get("/users/me").json()
    b_id = me_b["id"]

    # Add co-owner B
    r = client_a.post(f"/dogs/{dog_id}/coowners/{b_id}", headers=get_csrf_header(client_a))
    assert r.status_code == 200

    # B sees the dog in list
    r = client_b.get("/dogs/me")
    assert any(d["id"] == dog_id for d in r.json())

    # C cannot update or delete (not linked)
    r = client_c.put(f"/dogs/{dog_id}", json={"name": "HACK00"}, headers=get_csrf_header(client_c))
    assert r.status_code == 403
    r = client_c.delete(f"/dogs/{dog_id}", headers=get_csrf_header(client_c))
    assert r.status_code == 403

    # Remove co-owner B
    r = client_a.delete(f"/dogs/{dog_id}/coowners/{b_id}", headers=get_csrf_header(client_a))
    assert r.status_code == 200

    # B no longer sees the dog
    r = client_b.get("/dogs/me")
    assert all(d["id"] != dog_id for d in r.json())


def test_upload_photo_with_s3_mock(monkeypatch):
    # Patch storage.get_storage to return a fake that yields deterministic URL
    from app.services import storage as storage_mod

    class FakeS3(storage_mod.StorageService):
        def save(self, fileobj, filename, content_type=None) -> str:
            return "http://minio/regami/dogs/fake-key.png"

    monkeypatch.setattr(storage_mod, "get_storage", lambda: FakeS3())

    client = login_client("s3user@example.com")

    # Create dog
    r = client.post("/dogs/", json={"name": "S3DOG42", "birth_month": 1, "birth_year": 2021, "sex": "male"}, headers=get_csrf_header(client))
    assert r.status_code == 200
    dog_id = r.json()["id"]

    payload = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    files = {"file": ("photo.png", payload, "image/png")}
    r = client.post(f"/dogs/{dog_id}/photo", files=files, headers=get_csrf_header(client))
    assert r.status_code == 200, r.text
    assert r.json()["photo_url"] == "http://minio/regami/dogs/fake-key.png"
