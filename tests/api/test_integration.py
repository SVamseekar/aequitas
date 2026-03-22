"""Integration test — runs API against the real DuckDB warehouse if available."""
import pytest
from pathlib import Path


pytestmark = pytest.mark.skipif(
    not Path("data/aequitas.duckdb").exists(),
    reason="No warehouse built — run pipeline first",
)


@pytest.fixture
def real_client(monkeypatch):
    """Create test client against real DuckDB warehouse."""
    monkeypatch.setenv("AEQUITAS_DB_PATH", "data/aequitas.duckdb")
    from aequitas.api.app import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_overview_returns_8_dimensions(real_client):
    resp = real_client.get("/api/overview")
    assert resp.status_code == 200
    dims = resp.json()["dimensions"]
    assert len(dims) == 8
    equity = [d for d in dims if d["id"] == "equity"][0]
    assert equity["headline_stat"]["value"] == pytest.approx(0.5741, abs=0.01)


def test_sections_equity_has_f_prefixed_sections(real_client):
    resp = real_client.get("/api/sections", params={"dimension": "equity"})
    assert resp.status_code == 200
    sections = resp.json()["sections"]
    assert len(sections) >= 1
    for s in sections:
        assert s["section_id"].startswith("f")
        assert s["dimension"] == "equity"


def test_provenance_gini_exists(real_client):
    resp = real_client.get("/api/provenance/gini_national")
    assert resp.status_code == 200
    assert resp.json()["value"] == pytest.approx(0.5741, abs=0.01)
