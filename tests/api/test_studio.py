"""Studio job / result schema."""

from aequitas.analytics.studio import parse_studio_patch


def test_job_and_result_schema(api_client):
    payload = {
        "country": "england",
        "region": "all",
        "urban_rural": "all",
        "source": "drawn",
        "ops": [{"op": "add_stop", "lat": 52.48, "lon": -1.9, "name": "Test stop"}],
    }
    parsed, err = parse_studio_patch(payload)
    assert err is None and parsed
    resp = api_client.post("/api/studio/jobs", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= {"id", "status"}
    job_id = body["id"]
    # Tiny job should finish during the sync join window.
    if body["status"] != "done":
        st = api_client.get(f"/api/studio/jobs/{job_id}")
        assert st.status_code == 200
        assert "status" in st.json()
    result = api_client.get(f"/api/studio/jobs/{job_id}/result")
    if result.status_code == 409:
        return
    assert result.status_code == 200
    data = result.json()
    assert set(data) >= {
        "ok",
        "mode",
        "note",
        "patch",
        "score_before",
        "score_after",
        "people_gained",
        "people_lost",
        "deciles",
        "areas",
        "reach_available",
        "needs_r5py",
    }
    assert "45-minute jobs" in data["note"] or "centroids" in data["note"] or "r5py" in data["note"]
    # Never invent a 45-min bar when reach is missing
    if not data["reach_available"]:
        assert data["mode"] != "r5_delta"


def test_bad_patch_is_english(api_client):
    resp = api_client.post(
        "/api/studio/jobs",
        json={"country": "england", "ops": [{"op": "teleport"}]},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "teleport" in detail.lower() or "Unknown" in detail
