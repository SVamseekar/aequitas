"""Pure redirect validation; no provider, real identity or database."""

import pytest

from aequitas.api.auth.return_path import safe_return_path


@pytest.mark.parametrize(
    "path",
    [
        "/app/ireland/access?region=dublin&pack=2026-08-01",
        "/invite/isolated-proof",
        "/conversations?conversation=isolated-proof",
        "/saved",
    ],
)
def test_preserves_known_local_destination(path: str) -> None:
    assert safe_return_path(path) == path


@pytest.mark.parametrize(
    "path",
    [
        "https://example.org",
        "//example.org",
        "/\\example.org",
        "/auth",
        "/app/unknown",
        "/app/ireland/not-a-page",
        "/invite/../../evil",
        "/saved\r\nLocation: evil",
    ],
)
def test_rejects_external_and_unrecognised_destination(path: str) -> None:
    assert safe_return_path(path) == "/app/england"


def test_oauth_roundtrip_preserves_validated_destination(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from fastapi import FastAPI
    from fastapi.responses import RedirectResponse
    from fastapi.testclient import TestClient
    from starlette.middleware.sessions import SessionMiddleware

    from aequitas.api.auth import db
    from aequitas.api.routers import auth

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "isolated-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "isolated-secret")
    monkeypatch.setenv("SESSION_SECRET", "isolated-session-secret")
    monkeypatch.setattr(
        auth,
        "get_google_oauth_client",
        lambda: SimpleNamespace(
            google=SimpleNamespace(
                authorize_redirect=AsyncMock(
                    return_value=RedirectResponse("/provider-placeholder")
                ),
                authorize_access_token=AsyncMock(
                    return_value={"userinfo": {"email": "unit@example.test", "sub": "unit-subject"}}
                ),
            )
        ),
    )
    monkeypatch.setattr(db, "get_pool", AsyncMock(return_value=object()))
    monkeypatch.setattr(db, "get_or_create_user", AsyncMock(return_value={"id": "unit-user"}))
    monkeypatch.setattr(
        db, "list_memberships_for_user", AsyncMock(return_value=[{"tenant_id": "unit-workspace"}])
    )
    monkeypatch.setattr(db, "create_session", AsyncMock(return_value={"id": "unit-session"}))
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="isolated-test-only")
    app.include_router(auth.router, prefix="/api")
    path = "/app/ireland/access?region=dublin&pack=2026-08-01"
    with TestClient(app, follow_redirects=False) as client:
        login = client.get("/api/auth/login/google", params={"returnTo": path})
        assert login.status_code == 307
        callback = client.get("/api/auth/callback/google")
    assert callback.status_code == 307
    assert callback.headers["location"].endswith(path)
