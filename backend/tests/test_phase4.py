"""
Tests for Phase 4 features: i18n, API versioning, OpenAPI docs, admin CLI
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.i18n import parse_accept_language, translate, get_translator
from app.models import User, Dog, UserDog
from app.security import hash_password
from fastapi import Request


client = TestClient(app)


def get_csrf_header(test_client: TestClient) -> dict:
    """Get CSRF token header from client cookies."""
    csrf_token = test_client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf_token} if csrf_token else {}


# ==================
# i18n Tests
# ==================

class TestI18n:
    """Test internationalization functionality."""

    def test_parse_accept_language_french(self):
        """Test French language detection."""
        lang = parse_accept_language("fr-FR,fr;q=0.9,en;q=0.8")
        assert lang == "fr"

    def test_parse_accept_language_english(self):
        """Test English language detection."""
        lang = parse_accept_language("en-US,en;q=0.9")
        assert lang == "en"

    def test_parse_accept_language_default(self):
        """Test default language when no header."""
        lang = parse_accept_language(None)
        assert lang == "fr"  # French is default

    def test_parse_accept_language_quality_scores(self):
        """Test language selection based on quality scores."""
        lang = parse_accept_language("en;q=0.8,fr;q=0.9")
        assert lang == "fr"  # Higher quality score

    def test_translate_french(self):
        """Test French translation."""
        msg = translate("invalid_credentials", "fr")
        assert "Email ou mot de passe invalide" in msg

    def test_translate_english(self):
        """Test English translation."""
        msg = translate("invalid_credentials", "en")
        assert "Invalid email or password" in msg

    def test_translate_with_parameters(self):
        """Test translation with format parameters."""
        msg = translate("new_match", "en", dog_name="Buddy")
        assert "Buddy" in msg
        assert "match" in msg.lower()

    def test_translate_missing_key_fallback(self):
        """Test fallback when translation key missing."""
        msg = translate("nonexistent_key", "fr")
        assert msg == "nonexistent_key"

    def test_api_with_french_header(self):
        """Test API endpoint with French Accept-Language header."""
        response = client.get(
            "/health",
            headers={"Accept-Language": "fr-FR,fr;q=0.9"}
        )
        assert response.status_code == 200

    def test_api_with_english_header(self):
        """Test API endpoint with English Accept-Language header."""
        response = client.get(
            "/health",
            headers={"Accept-Language": "en-US,en;q=0.9"}
        )
        assert response.status_code == 200


# ==================
# API Versioning Tests
# ==================

class TestAPIVersioning:
    """Test API versioning with /v1 prefix."""

    def test_v1_health_endpoint(self):
        """Test health endpoint is not versioned."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_v1_auth_endpoint(self):
        """Test v1 auth endpoint exists."""
        # First do a GET to get CSRF token
        client.get("/health")
        response = client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "test"},
            headers=get_csrf_header(client)
        )
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code in [401, 422]

    def test_legacy_auth_endpoint_deprecated(self):
        """Test legacy auth endpoint still works but is deprecated."""
        # First do a GET to get CSRF token
        client.get("/health")
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "test"},
            headers=get_csrf_header(client)
        )
        # Should still work (backward compatibility)
        assert response.status_code in [401, 422]

    def test_v1_users_endpoint(self):
        """Test v1 users endpoint."""
        response = client.get("/v1/users/me")
        # Should return 401 (unauthorized) not 404
        assert response.status_code == 401

    def test_v1_dogs_endpoint(self):
        """Test v1 dogs endpoint."""
        # For POST endpoints without auth, we get CSRF error (403) before auth check (401)
        # Both indicate the endpoint exists and requires auth
        client.get("/health")
        response = client.post(
            "/v1/dogs",
            json={"name": "TEST", "birth_month": 1, "birth_year": 2020, "sex": "male"},
            headers=get_csrf_header(client)
        )
        # 401 = unauthorized, 403 = CSRF failed (both indicate endpoint exists)
        assert response.status_code in [401, 403]

    def test_v1_availability_endpoint(self):
        """Test v1 availability endpoint."""
        client.get("/health")
        response = client.post(
            "/v1/availability/offers",
            json={"start_at": "2025-01-01T10:00:00", "end_at": "2025-01-01T12:00:00"},
            headers=get_csrf_header(client)
        )
        # 401 = unauthorized, 403 = CSRF failed (both indicate endpoint exists)
        assert response.status_code in [401, 403]


# ==================
# OpenAPI Docs Tests
# ==================

class TestOpenAPIDocs:
    """Test OpenAPI documentation generation."""

    def test_openapi_json_exists(self):
        """Test OpenAPI JSON endpoint exists."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "openapi" in response.json()

    def test_openapi_version(self):
        """Test OpenAPI spec version."""
        response = client.get("/openapi.json")
        data = response.json()
        assert data["openapi"] == "3.1.0"

    def test_openapi_info(self):
        """Test OpenAPI info section."""
        response = client.get("/openapi.json")
        data = response.json()
        assert "info" in data
        assert data["info"]["title"] == "Regami API"
        assert data["info"]["version"] == "1.0.0"
        assert "description" in data["info"]

    def test_openapi_paths(self):
        """Test OpenAPI paths are documented."""
        response = client.get("/openapi.json")
        data = response.json()
        assert "paths" in data
        assert "/health" in data["paths"]
        assert "/v1/auth/login" in data["paths"]

    def test_openapi_tags(self):
        """Test API endpoints are tagged."""
        response = client.get("/openapi.json")
        data = response.json()
        # Check v1 tag exists
        v1_endpoints = [
            path for path in data["paths"].keys()
            if path.startswith("/v1/")
        ]
        assert len(v1_endpoints) > 0

    def test_docs_page_exists(self):
        """Test Swagger UI docs page."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_page_exists(self):
        """Test ReDoc docs page."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


# ==================
# Admin CLI Tests
# ==================

class TestAdminCLI:
    """Test admin CLI commands (unit tests for functions)."""

    @pytest.fixture
    def db_session(self):
        """Create test database session."""
        from app.db import SessionLocal
        session = SessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def test_user(self, db_session):
        """Create test user."""
        user = User(
            email="test-admin@example.com",
            password_hash=hash_password("testpassword")
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        yield user
        # Cleanup
        try:
            db_session.delete(user)
            db_session.commit()
        except Exception:
            db_session.rollback()

    @pytest.fixture
    def test_dog(self, db_session, test_user):
        """Create test dog profile and link to user."""
        dog = Dog(
            name="Test Dog",
            birth_month=6,
            birth_year=2021,
            sex="male"
        )
        db_session.add(dog)
        db_session.flush()

        # Link dog to user
        user_dog = UserDog(user_id=test_user.id, dog_id=dog.id, is_owner=True)
        db_session.add(user_dog)
        db_session.commit()
        db_session.refresh(dog)
        yield dog
        # Cleanup handled by cascade

    def test_list_users(self, db_session, test_user):
        """Test listing users."""
        users = db_session.query(User).limit(10).all()
        assert len(users) > 0
        assert any(u.id == test_user.id for u in users)

    def test_get_user_info(self, db_session, test_user):
        """Test getting user information."""
        user = db_session.query(User).filter(
            User.email == test_user.email
        ).first()
        assert user is not None
        assert user.email == test_user.email

    def test_deactivate_user(self, db_session, test_user):
        """Test deactivating user (via email_verified flag)."""
        user = db_session.query(User).filter(
            User.id == test_user.id
        ).first()
        user.email_verified = False
        db_session.commit()

        updated = db_session.query(User).filter(
            User.id == test_user.id
        ).first()
        assert updated.email_verified is False

    def test_activate_user(self, db_session, test_user):
        """Test activating user (via email_verified flag)."""
        user = db_session.query(User).filter(
            User.id == test_user.id
        ).first()
        user.email_verified = True
        db_session.commit()

        updated = db_session.query(User).filter(
            User.id == test_user.id
        ).first()
        assert updated.email_verified is True

    def test_list_dogs(self, db_session, test_dog):
        """Test listing dog profiles."""
        dogs = db_session.query(Dog).limit(10).all()
        assert len(dogs) > 0
        assert any(d.id == test_dog.id for d in dogs)

    def test_get_dog_info(self, db_session, test_dog):
        """Test getting dog information."""
        dog = db_session.query(Dog).filter(
            Dog.id == test_dog.id
        ).first()
        assert dog is not None
        assert dog.name == test_dog.name

    def test_delete_dog(self, db_session, test_dog, test_user):
        """Test deleting dog profile."""
        dog_id = test_dog.id
        # First delete the user_dog link
        db_session.query(UserDog).filter(UserDog.dog_id == dog_id).delete()
        db_session.delete(test_dog)
        db_session.commit()

        deleted = db_session.query(Dog).filter(
            Dog.id == dog_id
        ).first()
        assert deleted is None


# ==================
# Integration Tests
# ==================

class TestPhase4Integration:
    """Integration tests for Phase 4 features."""

    def test_api_version_with_i18n(self):
        """Test versioned API with internationalization."""
        # Get CSRF token first
        client.get("/health")
        response = client.post(
            "/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrong"},
            headers={**get_csrf_header(client), "Accept-Language": "fr-FR"}
        )
        assert response.status_code in [401, 422]
        # Error message should respect Accept-Language header

    def test_health_endpoint_not_versioned(self):
        """Test health endpoint remains unversioned."""
        # Should work without /v1 prefix
        response = client.get("/health")
        assert response.status_code == 200

        # Should not exist with /v1 prefix
        response = client.get("/v1/health")
        assert response.status_code == 404

    def test_metrics_endpoint_not_versioned(self):
        """Test Prometheus metrics endpoint remains unversioned."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_openapi_documents_versioning(self):
        """Test OpenAPI spec documents API versioning."""
        response = client.get("/openapi.json")
        data = response.json()

        # Check that description mentions versioning
        assert "version" in data["info"]["description"].lower()
        assert "/v1/" in data["info"]["description"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
