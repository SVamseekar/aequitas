"""Dated pack registry — two fixtures, different computed scores."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from aequitas.warehouse.packs import (
    extract_metrics,
    list_packs,
    metrics_digest,
    register_pack,
    resolve_pack,
    warehouse_for_pack,
)


def _tiny_warehouse(path, pct_covered: float) -> None:
    conn = duckdb.connect(str(path))
    conn.execute(
        """
        CREATE TABLE section_results (
            region VARCHAR, urban_rural VARCHAR, section_id VARCHAR,
            stats JSON, chart_data JSON, narrative VARCHAR
        )
        """
    )
    stats = json.dumps(
        {
            "pct_covered": pct_covered,
            "n_lsoas": 100,
            "insufficient_data": False,
        }
    )
    conn.execute(
        "INSERT INTO section_results VALUES ('all','all','a3_walking_distance', ?, '{}', '')",
        [stats],
    )
    conn.close()


def test_committed_england_manifest_has_two_dates():
    data = json.loads(Path("data/packs/manifest.json").read_text(encoding="utf-8"))
    england = data["england"]
    assert [row["pack_id"] for row in england] == ["2026-08-01", "2026-09-25"]
    assert england[0]["current"] is True
    assert england[0]["score"] == 80.0
    assert england[1]["current"] is False
    assert [row["pack_id"] for row in data["ireland"]] == ["2026-08-13"]
    old = json.loads(Path("data/packs/england/2026-08-01/metrics.json").read_text(encoding="utf-8"))
    new = json.loads(Path("data/packs/england/2026-09-25/metrics.json").read_text(encoding="utf-8"))
    assert metrics_digest(old) != metrics_digest(new)
    assert new["gtfs_sha256"]
    assert new["feed_start_date"] == "20260924"


def test_register_pack_refuses_equal_metrics_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("AEQUITAS_PACKS_DIR", str(tmp_path / "packs"))
    metrics = {
        "score": 80.0,
        "pct_400m": 79.27,
        "evening_isolated_pct": 15.37,
        "mean_sqi": 65.42,
        "n_areas": None,
    }
    register_pack("england", "2026-08-01", warehouse=None, metrics=metrics, current=True)
    with pytest.raises(ValueError, match="metrics hash matches"):
        register_pack("england", "2026-09-25", warehouse=None, metrics=dict(metrics), current=False)
    assert [r["pack_id"] for r in list_packs("england")] == ["2026-08-01"]
    assert not (tmp_path / "packs" / "england" / "2026-09-25" / "metrics.json").exists()


def test_two_packs_different_scores(tmp_path, monkeypatch):
    monkeypatch.setenv("AEQUITAS_PACKS_DIR", str(tmp_path / "packs"))
    a = tmp_path / "a.duckdb"
    b = tmp_path / "b.duckdb"
    _tiny_warehouse(a, 80.0)
    _tiny_warehouse(b, 40.0)
    ma = extract_metrics(a)
    mb = extract_metrics(b)
    assert ma["score"] != mb["score"]
    register_pack("england", "2020-01-01", warehouse=a, metrics=ma, current=False, copy_db=False)
    register_pack("england", "2020-06-01", warehouse=b, metrics=mb, current=True, copy_db=False)
    rows = list_packs("england")
    assert [r["pack_id"] for r in rows] == ["2020-01-01", "2020-06-01"]
    assert resolve_pack("england", "2020-01-01")["score"] != resolve_pack("england", "2020-06-01")["score"]
    assert warehouse_for_pack("england", "2020-01-01", a) == a
    assert warehouse_for_pack("england", "missing-date", a) is None
