def test_provenance_found(api_client):
    resp = api_client.get("/api/provenance/gini_national")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric_id"] == "gini_national"
    assert data["value"] == 0.5741
    assert "AUC" in data["formula"]


def test_provenance_alias_gini(api_client):
    """Public key /api/provenance/gini must resolve (Part E Task 4)."""
    resp = api_client.get("/api/provenance/gini")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric_id"] == "gini_national"
    assert data["value"] == 0.5741


def test_provenance_alias_section_id(api_client):
    resp = api_client.get("/api/provenance/f1_gini")
    assert resp.status_code == 200
    assert resp.json()["metric_id"] == "gini_national"


def test_provenance_not_found(api_client):
    resp = api_client.get("/api/provenance/nonexistent")
    assert resp.status_code == 404
