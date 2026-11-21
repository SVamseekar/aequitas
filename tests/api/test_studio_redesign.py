"""Studio redesign contracts; all worker dependencies are isolated fixtures."""

import base64
import io
import zipfile
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from aequitas.analytics.studio import parse_studio_patch
from aequitas.api.routers import studio


@pytest.mark.parametrize("country", ["netherlands", "france", "unknown"])
def test_unsupported_calculation_does_not_start_worker(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch, country: str
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Unsupported calculation accessed the worker")

    monkeypatch.setattr(studio, "_run_job", forbidden)
    response = api_client.post(
        "/api/studio/jobs",
        json={
            "country": country,
            "ops": [{"op": "add_stop", "lat": 52.48, "lon": -1.9}],
        },
    )
    assert response.status_code == 400
    assert "England and Ireland only" in response.json()["detail"]


def test_historical_calculation_is_rejected(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/studio/jobs",
        json={
            "country": "england",
            "pack": "2025-01-01",
            "ops": [{"op": "add_stop", "lat": 52.48, "lon": -1.9}],
        },
    )
    assert response.status_code == 400
    assert "current warehouse" in response.json()["detail"]


def test_explicit_current_pack_keeps_current_calculation_available(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aequitas.api.deps import _state
    from aequitas.warehouse import packs

    live = _state.get("db_path")
    monkeypatch.setattr(packs, "resolve_pack", lambda *args: {"current": True})
    monkeypatch.setattr(packs, "warehouse_for_pack", lambda *args: live)
    monkeypatch.setattr(studio, "_run_job", lambda *args: None)
    response = api_client.post(
        "/api/studio/jobs",
        json={
            "country": "england",
            "pack": "current-date-fixture",
            "ops": [{"op": "add_stop", "lat": 52.48, "lon": -1.9}],
        },
    )
    assert response.status_code == 200
    assert response.json()["stage"] == "validated"
    assert response.json()["patch"]["country"] == "england"


def test_zip_upload_is_stop_review_not_timetable_import(api_client: TestClient) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("feed/stops.txt", "stop_lat,stop_lon,stop_name\n52.48,-1.9,Fixture\n")
    response = api_client.post(
        "/api/studio/parse",
        json={
            "filename": "feed.zip",
            "country": "england",
            "archive_base64": base64.b64encode(buffer.getvalue()).decode(),
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"]
    assert response.json()["ops"] == [
        {"op": "add_stop", "lat": 52.48, "lon": -1.9, "name": "Fixture"}
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "lat,lon\nNaN,-1.9"},
        {"text": '{"type":"Point","coordinates":["bad",52]}'},
        {"text": "[]", "filename": "broken.geojson"},
        {"text": "lat,lon\n48.8,2.3"},
        {"archive_base64": "not-a-zip"},
    ],
)
def test_invalid_upload_has_no_partial_draft(
    api_client: TestClient, payload: dict[str, Any]
) -> None:
    response = api_client.post("/api/studio/parse", json={"country": "england", **payload})
    assert response.status_code == 200
    assert not response.json()["ok"]
    assert response.json()["error"]
    assert response.json()["ops"] == []


@pytest.mark.parametrize(
    "operation",
    [
        {"op": "frequency_uplift", "factor": "bad"},
        {"op": "frequency_uplift", "factor": float("inf")},
        {"op": "frequency_uplift", "extra_trips": -1},
        {"op": "remove_stop"},
        {"op": "add_trips", "line": [[-1.9, 52], [2.3, 48.8]]},
    ],
)
def test_patch_validation_returns_errors_instead_of_crashing(operation: dict[str, Any]) -> None:
    patch, error = parse_studio_patch({"country": "england", "ops": [operation]})
    assert patch is None and error


def test_worker_reports_real_stages_and_retains_failed_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aequitas.api.deps import _state

    patch, error = parse_studio_patch(
        {"country": "ireland", "ops": [{"op": "add_stop", "lat": 51.9, "lon": -8.47}]}
    )
    assert patch and not error
    monkeypatch.setitem(_state, "ie_db_path", None)
    seen = []

    def centroids(*args: object) -> list[Any]:
        seen.append(studio._JOBS["fixture"]["stage"])
        return []

    def compute(*args: object, **kwargs: object) -> SimpleNamespace:
        seen.append(studio._JOBS["fixture"]["stage"])
        assert kwargs["processed_dir"].name == "ireland"
        return SimpleNamespace(to_dict=lambda: {"ok": True, "patch": patch.to_dict()})

    monkeypatch.setattr(studio, "_load_centroids", centroids)
    monkeypatch.setattr(studio, "_load_baseline_stops", lambda *args: [])
    monkeypatch.setattr(studio, "_other_terms", lambda *args: {})
    monkeypatch.setattr(studio, "apply_studio", compute)
    monkeypatch.setitem(
        studio._JOBS, "fixture", {"id": "fixture", "status": "running", "patch": patch.to_dict()}
    )
    studio._run_job("fixture", patch)
    assert seen == ["baseline", "coverage"]
    assert studio.job_status("fixture")["stage"] == "results"
    assert studio.job_status("fixture")["status"] == "done"

    def failure(*args: object, **kwargs: object) -> None:
        raise ValueError("Fixture coverage failure")

    monkeypatch.setattr(studio, "apply_studio", failure)
    studio._run_job("fixture", patch)
    assert studio.job_status("fixture")["stage"] == "coverage"
    assert studio.job_status("fixture")["status"] == "error"
