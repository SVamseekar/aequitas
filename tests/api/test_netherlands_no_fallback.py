"""country=netherlands must not fall back to England numbers."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aequitas.api.app import create_app


def test_unknown_pack_404() -> None:
    client = TestClient(create_app())
    r = client.get("/api/score", params={"country": "netherlands", "pack": "2099-01-01"})
    assert r.status_code == 404
    assert "england" not in r.text.lower() or "not falling back" in r.text.lower()


def test_time_unknown_pack_404() -> None:
    client = TestClient(create_app())
    r = client.get("/api/time", params={"country": "netherlands", "pack": "2099-01-01"})
    assert r.status_code == 404


def test_france_without_warehouse_stays_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aequitas.api.deps import _state
    missing = tmp_path / 'missing-france.duckdb'
    monkeypatch.setenv('AEQUITAS_FR_DB_PATH', str(missing))
    monkeypatch.setitem(_state, 'fr_db_path', missing)
    client = TestClient(create_app())
    r = client.get("/api/score", params={"country": "france"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("score") is None
