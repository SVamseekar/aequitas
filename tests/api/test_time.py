"""Time series API + pack 404."""

from __future__ import annotations

import duckdb
import json

import pytest
from fastapi.testclient import TestClient


def _warehouse(path, pct: float) -> None:
    conn = duckdb.connect(str(path))
    conn.execute(
        """
        CREATE TABLE section_results (
            region VARCHAR, urban_rural VARCHAR, section_id VARCHAR,
            stats JSON, chart_data JSON, narrative VARCHAR,
            PRIMARY KEY (region, urban_rural, section_id)
        )
        """
    )
    conn.execute(
        "INSERT INTO section_results VALUES ('all','all','a3_walking_distance', ?, '{}', '')",
        [json.dumps({"pct_covered": pct, "n_lsoas": 50})],
    )
    conn.execute("CREATE TABLE metadata (key VARCHAR PRIMARY KEY, value VARCHAR)")
    conn.close()


@pytest.fixture
def time_client(tmp_path, monkeypatch):
    packs = tmp_path / "packs"
    monkeypatch.setenv("AEQUITAS_PACKS_DIR", str(packs))
    a = tmp_path / "a.duckdb"
    b = tmp_path / "b.duckdb"
    _warehouse(a, 90.0)
    _warehouse(b, 30.0)
    monkeypatch.setenv("AEQUITAS_DB_PATH", str(b))
    monkeypatch.setenv("AEQUITAS_FAISS_INDEX", str(tmp_path / "faiss.bin"))
    monkeypatch.setenv("AEQUITAS_FAISS_METADATA", str(tmp_path / "faiss_meta.json"))
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")

    from aequitas.warehouse.packs import extract_metrics, register_pack

    register_pack("england", "2021-01-01", warehouse=a, metrics=extract_metrics(a), current=False)
    register_pack("england", "2021-06-01", warehouse=b, metrics=extract_metrics(b), current=True)

    from aequitas.api.app import create_app

    with TestClient(create_app()) as client:
        yield client


def test_time_series_two_dates(time_client):
    resp = time_client.get("/api/time?country=england&metric=score")
    assert resp.status_code == 200
    body = resp.json()
    assert body["one_date"] is False
    assert len(body["points"]) == 2
    assert body["area_noun"] == "LSOAs"
    scores = [p["value"] for p in body["points"]]
    assert scores[0] != scores[1]


def test_score_pack_a_vs_b(time_client):
    a = time_client.get("/api/score?country=england&pack=2021-01-01")
    b = time_client.get("/api/score?country=england&pack=2021-06-01")
    assert a.status_code == 200
    assert b.status_code == 200
    assert a.json()["score"] != b.json()["score"]


def test_unknown_pack_404(time_client):
    resp = time_client.get("/api/score?country=ireland&pack=1999-01-01")
    assert resp.status_code == 404
    assert "ireland" in resp.text.lower()


def test_time_unknown_pack_404_england(time_client):
    resp = time_client.get("/api/time?country=england&pack=2099-01-01")
    assert resp.status_code == 404
    assert "2099-01-01" in resp.text
    assert "current" not in resp.text.lower() or "not falling back" in resp.text.lower()


def test_time_unknown_pack_404_ireland(time_client):
    resp = time_client.get("/api/time?country=ireland&pack=2099-01-01")
    assert resp.status_code == 404
    assert "ireland" in resp.text.lower()


def test_nl_time_one_point(time_client, tmp_path):
    from pathlib import Path

    live = Path("data/aequitas_netherlands.duckdb")
    if live.exists():
        from aequitas.warehouse.packs import extract_metrics, register_pack

        register_pack(
            "netherlands",
            "2026-08-13",
            warehouse=live,
            metrics=extract_metrics(live),
            current=True,
        )
    resp = time_client.get("/api/time?country=netherlands")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("area_noun") == "buurten"
    assert "CSO" not in (body.get("note") or "")
    assert "Pobal" not in (body.get("note") or "")
    if live.exists():
        assert body.get("empty") is not True
        assert body.get("points")
    bad = time_client.get("/api/time?country=netherlands&pack=2099-01-01")
    assert bad.status_code == 404


def test_ireland_area_noun():
    from aequitas.api.routers.time_series import get_time_series

    # Direct: empty registry still names Small Areas
    out = get_time_series(country="ireland", region="all", urban_rural="all", metric="score")
    assert out["area_noun"] == "Small Areas"
