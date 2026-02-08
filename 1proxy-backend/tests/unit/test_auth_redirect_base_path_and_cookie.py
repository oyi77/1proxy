import pytest

from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.routers import auth as auth_router


def _make_test_app():
    app = FastAPI()

    async def override_get_db():
        yield None

    app.dependency_overrides[get_db] = override_get_db
    app.include_router(auth_router.router)
    return app


@pytest.mark.unit
def test_github_callback_redirect_includes_frontend_base_path_and_sets_samesite_none(
    monkeypatch,
):
    # Configure frontend hosting under a subpath (GitHub Pages / reverse proxy)
    fake_settings = SimpleNamespace(
        FRONTEND_URL="https://oyi77.is-a.dev",
        FRONTEND_BASE_PATH="/1proxy",
        API_URL="https://backend.example",
        GITHUB_CLIENT_ID="x",
        GOOGLE_CLIENT_ID="x",
    )
    monkeypatch.setattr(auth_router, "settings", fake_settings)

    async def fake_github_callback(code, session):
        return SimpleNamespace(id=1), "token123"

    async def fake_log_usage(*args, **kwargs):
        return None

    monkeypatch.setattr(
        auth_router.oauth_handler, "github_callback", fake_github_callback
    )
    monkeypatch.setattr(auth_router, "log_usage", fake_log_usage)

    app = _make_test_app()
    client = TestClient(app)

    res = client.get("/auth/github/callback?code=abc", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert res.headers["location"] == "https://oyi77.is-a.dev/1proxy/dashboard"

    set_cookie = res.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "Secure" in set_cookie
    # Cross-site cookie for static GH Pages -> backend must be SameSite=None
    assert "samesite=none" in set_cookie.lower()


@pytest.mark.unit
def test_github_callback_error_redirect_includes_frontend_base_path(monkeypatch):
    fake_settings = SimpleNamespace(
        FRONTEND_URL="https://oyi77.is-a.dev",
        FRONTEND_BASE_PATH="/1proxy",
        API_URL="https://backend.example",
        GITHUB_CLIENT_ID="x",
        GOOGLE_CLIENT_ID="x",
    )
    monkeypatch.setattr(auth_router, "settings", fake_settings)

    async def boom(code, session):
        raise RuntimeError("nope")

    monkeypatch.setattr(auth_router.oauth_handler, "github_callback", boom)

    app = _make_test_app()
    client = TestClient(app)

    res = client.get("/auth/github/callback?code=abc", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert res.headers["location"].startswith("https://oyi77.is-a.dev/1proxy/login")
