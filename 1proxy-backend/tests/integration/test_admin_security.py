"""
Integration tests for admin endpoint security.
Tests that admin endpoints properly enforce authorization.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_user
from app.db_models import User

client = TestClient(app)


def test_admin_endpoints_require_authentication():
    """Test that admin endpoints return 401 when not authenticated."""
    # Try to access admin stats without authentication
    response = client.get("/api/v1/admin/validation-stats")
    assert response.status_code == 401 or response.status_code == 403

    response = client.get("/api/v1/admin/quality-distribution")
    assert response.status_code == 401 or response.status_code == 403

    response = client.get("/api/v1/admin/recent-validations")
    assert response.status_code == 401 or response.status_code == 403


def test_admin_endpoints_reject_regular_users():
    """Test that admin endpoints return 403 when accessed by non-admin users."""

    # Mock a regular user (not admin)
    def get_mock_user():
        return User(
            id=1,
            oauth_provider="test",
            oauth_id="test123",
            email="user@test.com",
            username="testuser",
            role="user",  # NOT admin
        )

    app.dependency_overrides[get_current_user] = get_mock_user

    try:
        response = client.get("/api/v1/admin/validation-stats")
        assert response.status_code == 403
        assert "Admin access required" in response.json().get("detail", "")

        response = client.get("/api/v1/admin/quality-distribution")
        assert response.status_code == 403

        response = client.get("/api/v1/admin/recent-validations")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_scrape_endpoints_require_admin():
    """Test that scrape endpoints require admin authentication."""
    # Test without authentication
    response = client.post(
        "/api/v1/proxies/scrape",
        json={"url": "https://example.com/proxies.txt", "type": "github_raw"},
    )
    assert response.status_code == 401 or response.status_code == 403

    response = client.post("/api/v1/proxies/demo")
    assert response.status_code == 401 or response.status_code == 403

    response = client.post("/api/v1/proxies/scrape-all")
    assert response.status_code == 401 or response.status_code == 403


def test_scrape_endpoints_reject_regular_users():
    """Test that scrape endpoints reject regular users."""

    def get_mock_user():
        return User(
            id=1,
            oauth_provider="test",
            oauth_id="test123",
            email="user@test.com",
            username="testuser",
            role="user",
        )

    app.dependency_overrides[get_current_user] = get_mock_user

    try:
        response = client.post(
            "/api/v1/proxies/scrape",
            json={"url": "https://example.com/proxies.txt", "type": "github_raw"},
        )
        assert response.status_code == 403

        response = client.post("/api/v1/proxies/demo")
        assert response.status_code == 403

        response = client.post("/api/v1/proxies/scrape-all")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_admin_user_can_access_admin_endpoints():
    """Test that admin users CAN access admin endpoints."""

    def get_mock_admin():
        return User(
            id=1,
            oauth_provider="test",
            oauth_id="admin123",
            email="admin@test.com",
            username="admin",
            role="admin",  # IS admin
        )

    app.dependency_overrides[get_current_user] = get_mock_admin

    try:
        # Admin should be able to access these endpoints
        # (They might return errors due to missing data, but should not return 403)
        response = client.get("/api/v1/admin/validation-stats")
        assert response.status_code != 403  # Should not be forbidden

        response = client.get("/api/v1/admin/quality-distribution")
        assert response.status_code != 403

        response = client.get("/api/v1/admin/recent-validations")
        assert response.status_code != 403
    finally:
        app.dependency_overrides.clear()


def test_public_endpoints_remain_accessible():
    """Test that public endpoints don't require authentication."""
    # These endpoints should be accessible without auth
    response = client.get("/")
    assert response.status_code == 200

    response = client.get("/health")
    assert response.status_code == 200

    response = client.get("/api/v1/sources")
    assert response.status_code == 200

    # Proxies endpoint should work without auth (public service)
    response = client.get("/api/v1/proxies?limit=10")
    assert response.status_code == 200
