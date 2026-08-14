"""Dated pack registry — two fixtures, different computed scores."""

from __future__ import annotations

import duckdb
import json

from aequitas.warehouse.packs import (
    extract_metrics,
    list_packs,
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
