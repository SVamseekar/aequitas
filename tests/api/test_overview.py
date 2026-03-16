def test_health(api_client):
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_overview_returns_dimensions(api_client):
    resp = api_client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "dimensions" in data
    assert len(data["dimensions"]) == 8
