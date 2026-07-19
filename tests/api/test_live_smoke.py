"""End-to-end smoke of auth + tenant-scoped routers via TestClient.

Requires DATABASE_URL. Uses DEV_AUTH_BYPASS for a signed-in session without Google.
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    "DATABASE_URL" not in os.environ,
    reason="DATABASE_URL not set",
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SESSION_SECRET", os.environ.get("SESSION_SECRET", "smoke-secret"))


def test_app_module_exports_app():
    from aequitas.api import app as app_module

    assert hasattr(app_module, "app")
    assert app_module.app is not None
    assert app_module.app.title == "Aequitas API"


def test_full_tenant_smoke(api_client):
    # me
    me = api_client.get("/api/auth/me")
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["user"]["email"]
    tenant_id = body["active_tenant"]["id"]
    assert tenant_id

    # conversations
    conv = api_client.post("/api/conversations", json={"title": "smoke"})
    assert conv.status_code == 201, conv.text
    cid = conv.json()["id"]
    msg = api_client.post(
        f"/api/conversations/{cid}/messages",
        json={"role": "user", "content": "hi"},
    )
    assert msg.status_code == 201, msg.text
    listed = api_client.get("/api/conversations")
    assert listed.status_code == 200
    assert any(c["id"] == cid for c in listed.json())

    # saved analyses
    sa = api_client.post(
        "/api/saved-analyses",
        json={"title": "t", "content": "c", "dimension": "equity"},
    )
    assert sa.status_code == 201, sa.text

    # policy notes
    pn = api_client.post(
        "/api/policy-notes",
        json={"dimension": "equity", "stance": "monitor", "thesis": "smoke thesis"},
    )
    assert pn.status_code == 201, pn.text

    # saved regions
    sr = api_client.post(
        "/api/saved-regions",
        json={"region_code": "E12000007", "region_name": "London"},
    )
    assert sr.status_code == 201, sr.text

    # profile
    prof = api_client.get("/api/profile")
    assert prof.status_code == 200, prof.text
    patched = api_client.patch(
        "/api/profile", json={"policy_interests": ["equity", "access"]}
    )
    assert patched.status_code == 200
    assert "equity" in patched.json()["policy_interests"]

    # invite + public lookup
    inv = api_client.post(
        f"/api/tenants/{tenant_id}/invites",
        json={"email": "smoke-invitee@example.com", "role": "member"},
    )
    assert inv.status_code == 200, inv.text
    token = inv.json()["token"]
    assert inv.json()["link"]
    pub = api_client.get(f"/api/invites/{token}")
    assert pub.status_code == 200
    assert pub.json()["role"] == "member"

    # members + audit
    members = api_client.get(f"/api/tenants/{tenant_id}/members")
    assert members.status_code == 200
    assert len(members.json()) >= 1
    audit = api_client.get(f"/api/tenants/{tenant_id}/audit-log")
    assert audit.status_code == 200
    assert any(e["action"] == "invite_created" for e in audit.json())

    # export still requires auth and returns PDF
    exp = api_client.get("/api/export/equity")
    assert exp.status_code == 200
    assert exp.headers["content-type"] == "application/pdf"

    # logout
    out = api_client.post("/api/auth/logout")
    assert out.status_code == 200
