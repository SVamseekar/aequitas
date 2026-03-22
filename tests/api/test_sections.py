def test_get_sections_returns_dimension(api_client):
    resp = api_client.get("/api/sections", params={"dimension": "equity"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["dimension"] == "equity"
    assert len(data["sections"]) >= 1
    section = data["sections"][0]
    assert section["section_id"] == "f1_gini"
    assert section["dimension"] == "equity"
    assert "gini" in section["stats"]
    assert section["narrative"].startswith("**")


def test_get_sections_missing_dimension_returns_422(api_client):
    resp = api_client.get("/api/sections")
    assert resp.status_code == 422


def test_get_sections_unknown_dimension_returns_empty(api_client):
    resp = api_client.get("/api/sections", params={"dimension": "nonexistent"})
    assert resp.status_code == 200
    assert resp.json()["sections"] == []
