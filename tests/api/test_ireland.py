"""Ireland API never returns England Gini 0.5741."""

import json

import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from aequitas.ireland.process import build_ireland_areas
from aequitas.ireland.warehouse import build_ireland_warehouse


@pytest.fixture
def ireland_client(tmp_path, monkeypatch):
    areas = pd.DataFrame(
        [
            {
                "sa_code": "SA001",
                "name": "Cork SA",
                "lat": 51.9,
                "lon": -8.47,
                "population": 500,
                "hp_relative": -5.0,
                "region": "cork",
                "area_km2": 0.5,
            },
            {
                "sa_code": "SA002",
                "name": "Kerry SA",
                "lat": 52.15,
                "lon": -9.5,
                "population": 400,
                "hp_relative": 4.0,
                "region": "kerry",
                "area_km2": 8.0,
            },
        ]
    )
    stops = pd.DataFrame(
        [{"stop_id": "1", "stop_name": "s", "stop_lat": 51.9001, "stop_lon": -8.4701}]
    )
    built = build_ireland_areas(areas=areas, stops=stops)
    ie = tmp_path / "aequitas_ireland.duckdb"
    build_ireland_warehouse(built, ie)

    en = tmp_path / "england.duckdb"
    conn = duckdb.connect(str(en))
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
        "INSERT INTO section_results VALUES ('all','all','f1_gini',?,?,?)",
        ['{"gini": 0.5741}', "{}", "England gini"],
    )
    conn.execute(
        "CREATE TABLE provenance (metric_id VARCHAR PRIMARY KEY, value DOUBLE, formula VARCHAR, inputs JSON, source_files VARCHAR[])"
    )
    conn.execute(
        "INSERT INTO provenance VALUES ('gini_national', 0.5741, 'x', '{}', ARRAY['e'])"
    )
    conn.close()

    monkeypatch.setenv("AEQUITAS_DB_PATH", str(en))
    monkeypatch.setenv("AEQUITAS_IE_DB_PATH", str(ie))
    monkeypatch.setenv("AEQUITAS_FAISS_INDEX", str(tmp_path / "faiss.bin"))
    monkeypatch.setenv("AEQUITAS_FAISS_METADATA", str(tmp_path / "faiss_meta.json"))
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")

    from aequitas.api.app import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client


def test_ireland_overview_not_england_gini(ireland_client):
    resp = ireland_client.get("/api/overview?country=ireland&region=all&urban_rural=all")
    assert resp.status_code == 200
    body = resp.json()
    equity = next(d for d in body["dimensions"] if d["id"] == "equity")
    assert equity["headline_stat"]["value"] != 0.5741
    assert body.get("score") != 80


def test_ireland_ticker_not_england_lock(ireland_client):
    resp = ireland_client.get("/api/metrics/ticker?country=ireland&region=all&urban_rural=all")
    assert resp.status_code == 200
    body = resp.json()
    gini = next(m for m in body if m["key"] == "gini")
    assert gini["value"] != "0.5741"
    eve = next((m for m in body if m["key"] == "evening_isolated"), None)
    if eve:
        assert eve["value"] != "15.4%"


def test_ireland_policy_is_nta_not_bsa(ireland_client):
    resp = ireland_client.get(
        "/api/sections?dimension=bus_services_act&country=ireland&region=all&urban_rural=all"
    )
    assert resp.status_code == 200
    sections = resp.json()["sections"]
    assert sections
    stats = sections[0]["stats"]
    if isinstance(stats, str):
        stats = json.loads(stats)
    assert stats.get("not_applicable") is not True
    blob = json.dumps(sections).lower()
    assert "connecting ireland" in blob or "nta" in blob or "busconnects" in blob
    assert "not applicable" not in blob


def test_ireland_economy_not_tag(ireland_client):
    resp = ireland_client.get(
        "/api/sections?dimension=economic&country=ireland&region=all&urban_rural=all"
    )
    assert resp.status_code == 200
    blob = json.dumps(resp.json()).lower()
    assert "not_applicable" not in blob or "caf" in blob or "epa" in blob
    assert "green book" not in blob or "not tag" in blob


def test_packs_endpoint(ireland_client):
    resp = ireland_client.get("/api/packs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ireland"]["packReady"] is True
    assert isinstance(body["netherlands"]["packReady"], bool)
