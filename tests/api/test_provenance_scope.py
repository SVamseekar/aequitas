"""Provenance must use the selected country and dated warehouse."""

from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from aequitas.api.app import create_app
from aequitas.api.deps import _state


def test_provenance_does_not_borrow_england_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, value, filename in [("db_path", 0.5, "England"), ("ie_db_path", 0.2, "Ireland")]:
        path = tmp_path / f"{filename}.duckdb"
        with duckdb.connect(str(path)) as db:
            db.execute(
                "CREATE TABLE provenance (metric_id VARCHAR, value DOUBLE, formula VARCHAR, "
                "inputs JSON, source_files VARCHAR[])"
            )
            db.execute(
                "INSERT INTO provenance VALUES ('gini_national', ?, 'formula', '{}', [?])",
                [value, filename],
            )
        monkeypatch.setitem(_state, key, path)
    client = TestClient(create_app())
    result = client.get("/api/provenance/gini", params={"country": "ireland"})
    assert result.status_code == 200
    assert result.json()["value"] == 0.2
    assert result.json()["source_files"] == ["Ireland"]
    monkeypatch.setitem(_state, "ie_db_path", None)
    assert client.get("/api/provenance/gini", params={"country": "ireland"}).status_code == 404


def test_provenance_unknown_country_and_date_do_not_fall_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AEQUITAS_PACKS_DIR", str(tmp_path / "packs"))
    client = TestClient(create_app())
    assert client.get("/api/provenance/gini", params={"country": "unknown"}).status_code == 422
    assert client.get("/api/provenance/gini", params={"pack": "2099-01-01"}).status_code == 404
