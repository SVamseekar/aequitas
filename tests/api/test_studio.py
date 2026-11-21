"""Studio job / result schema."""

import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from aequitas.analytics.studio import parse_studio_patch


def test_job_and_result_schema(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from aequitas.api.routers import studio
    from aequitas.core import config

    isolated = config.PipelineConfig(processed_dir=tmp_path / "processed", raw_dir=tmp_path / "raw")
    monkeypatch.setattr(config, "PipelineConfig", lambda: isolated)
    centroids = pd.DataFrame(
        [
            {
                "area": "fixture-area",
                "name": "Fixture only",
                "lat": 52.48,
                "lon": -1.9,
                "pop": 100,
                "imd_decile": 1,
            }
        ]
    )
    monkeypatch.setattr(studio, "_load_centroids", lambda *args: centroids)
    monkeypatch.setattr(studio, "_load_baseline_stops", lambda *args: [])
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
    # Job creation is asynchronous. Wait for the real isolated worker result.
    for _ in range(100):
        st = api_client.get(f"/api/studio/jobs/{job_id}")
        assert st.status_code == 200
        assert "status" in st.json()
        if st.json()["status"] != "running":
            break
        time.sleep(0.01)
    assert st.json()["status"] == "done", st.json()
    result = api_client.get(f"/api/studio/jobs/{job_id}/result")
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
    assert data["people_gained"] == 100
    assert data["people_lost"] == 0
    csv = api_client.get(f"/api/studio/jobs/{job_id}/winners.csv")
    assert csv.status_code == 200
    assert "fixture-area" in csv.text


def test_bad_patch_is_english(api_client: TestClient) -> None:
    resp = api_client.post(
        "/api/studio/jobs",
        json={"country": "england", "ops": [{"op": "teleport"}]},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "teleport" in detail.lower() or "Unknown" in detail
