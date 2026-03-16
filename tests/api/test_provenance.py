def test_provenance_found(api_client):
    resp = api_client.get("/api/provenance/gini_national")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric_id"] == "gini_national"
    assert data["value"] == 0.5741
    assert "AUC" in data["formula"]


def test_provenance_not_found(api_client):
    resp = api_client.get("/api/provenance/nonexistent")
    assert resp.status_code == 404
