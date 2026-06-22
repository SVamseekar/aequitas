def test_export_without_auth_returns_401(api_client, monkeypatch):
    """Export must require auth like chat/conversations do."""
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")
    resp = api_client.get("/api/export/equity")
    assert resp.status_code == 401


def test_export_with_dev_bypass_succeeds(api_client):
    """With dev bypass enabled (set in conftest), export still works."""
    resp = api_client.get("/api/export/equity")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"