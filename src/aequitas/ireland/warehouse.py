"""Build data/aequitas_ireland.duckdb — never overwrites England."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from loguru import logger

from aequitas.ireland.constants import (
    COUNTY_NAME_BY_SLUG,
    IRELAND_COUNTIES,
    IRELAND_EVENING_NOTE,
    URBAN_RURAL_NOTE,
)
from aequitas.ireland.saps import attach_saps_theme_shares, default_saps_path
from aequitas.ireland.sections import catalogue_counts, precompute_ireland

__all__ = [
    "build_ireland_warehouse",
    "ireland_warehouse_path",
    "precompute_ireland",
    "catalogue_counts",
    "rewrite_ireland_section_results",
]


def ireland_warehouse_path(project_root: Path) -> Path:
    return project_root / "data" / "aequitas_ireland.duckdb"


def build_ireland_warehouse(
    areas: pd.DataFrame,
    dest: Path,
    *,
    stops: pd.DataFrame | None = None,
    vintages: dict[str, str] | None = None,
    extras: dict[str, Any] | None = None,
) -> Path:
    """Write Ireland DuckDB. Atomic replace — never touches aequitas.duckdb."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".duckdb.tmp")
    if tmp.exists():
        tmp.unlink()
    conn = duckdb.connect(str(tmp))
    try:
        conn.execute(
            """
            CREATE TABLE section_results (
                region VARCHAR,
                urban_rural VARCHAR,
                section_id VARCHAR,
                stats JSON,
                chart_data JSON,
                narrative VARCHAR,
                PRIMARY KEY (region, urban_rural, section_id)
            )
            """
        )
        rows = precompute_ireland(areas, extras)
        nat = next(
            r
            for r in rows
            if r["region"] == "all" and r["urban_rural"] == "all" and r["section_id"] == "f1_gini"
        )
        gini_v = nat["stats"].get("gini")
        batch = []
        for r in rows:
            batch.append(
                (
                    r["region"],
                    r["urban_rural"],
                    r["section_id"],
                    json.dumps(r["stats"], default=str),
                    json.dumps(r["chart_data"], default=str),
                    r["narrative"],
                )
            )
            if len(batch) >= 200:
                conn.executemany("INSERT INTO section_results VALUES (?, ?, ?, ?, ?, ?)", batch)
                batch.clear()
        if batch:
            conn.executemany("INSERT INTO section_results VALUES (?, ?, ?, ?, ?, ?)", batch)
        n_sections = len(rows)
        del rows, batch
        keep = [
            c
            for c in (
                "sa_code",
                "lsoa_code",
                "name",
                "lat",
                "lon",
                "population",
                "region",
                "urban_rural",
                "hp_decile",
                "hp_relative",
                "imd_decile",
                "imd_score",
                "stop_count",
                "within_400m",
                "sqi",
                "weekday_trips",
                "evening_trips",
                "sunday_trips",
                "evening_isolated",
                "sunday_desert",
                "no_service",
                "trips_per_capita",
                "stops_per_1k",
                "sfca_score_norm",
                "area_km2",
                "nearest_stop_m",
            )
            if c in areas.columns
        ]
        demo = areas[keep].copy()
        conn.register("demo_df", demo)
        conn.execute("CREATE TABLE lsoa_demographics AS SELECT * FROM demo_df")
        conn.execute("CREATE TABLE lsoa_service_quality AS SELECT * FROM demo_df")
        cents = demo.rename(
            columns={
                "sa_code": "area",
                "population": "pop",
                "hp_decile": "imd_decile",
            }
        )[["area", "lat", "lon", "pop", "imd_decile", "region", "name"]]
        conn.register("cents_df", cents)
        conn.execute("CREATE TABLE lsoa_centroids AS SELECT * FROM cents_df")
        if stops is not None and not stops.empty:
            conn.register("stops_df", stops)
            conn.execute("CREATE TABLE naptan_stops AS SELECT * FROM stops_df")

        conn.execute(
            "CREATE TABLE provenance (metric_id VARCHAR PRIMARY KEY, value DOUBLE, formula VARCHAR, inputs JSON, source_files VARCHAR[])"
        )
        if isinstance(gini_v, (int, float)) and not (isinstance(gini_v, float) and math.isnan(gini_v)):
            conn.execute(
                "INSERT INTO provenance VALUES (?, ?, ?, ?, ?)",
                [
                    "gini_national",
                    float(gini_v),
                    "population-weighted Gini of TFI weekday trips/capita (Republic SAs)",
                    json.dumps({"n_sas": int(len(areas)), **catalogue_counts()}),
                    ["tfi", "pobal_hp_2022", "cso_sa_2022"],
                ],
            )

        conn.execute("CREATE TABLE metadata (key VARCHAR PRIMARY KEY, value VARCHAR)")
        vintages = vintages or {}
        counts = catalogue_counts()
        meta = {
            "country": "ireland",
            "built_at": datetime.now(timezone.utc).isoformat(),
            "n_sas": str(len(areas)),
            "n_counties": str(areas["region"].nunique()),
            "evening_definition": IRELAND_EVENING_NOTE,
            "urban_rural": URBAN_RURAL_NOTE,
            "deprivation": "Pobal HP Deprivation Index 2022 (relative index / decile). Not IMD.",
            "gtfs": vintages.get("gtfs", "TFI GTFS_All.zip"),
            "small_areas": vintages.get("small_areas", "CSO Small Areas 2022"),
            "scope": "Republic of Ireland only. Northern Ireland excluded.",
            "join_rate": vintages.get("join_rate", ""),
            "hp_url": vintages.get("hp", ""),
            "hp_note": vintages.get("hole", ""),
            "catalogue_same": str(counts["same"]),
            "catalogue_replace": str(counts["replace"]),
            "catalogue_omit": str(counts["omit"]),
            "catalogue_answers": str(counts["answers"]),
        }
        conn.executemany("INSERT INTO metadata VALUES (?, ?)", list(meta.items()))

        regions = [{"code": "all", "name": "All Ireland"}] + [
            {"code": s, "name": n} for s, n in IRELAND_COUNTIES if s in set(areas["region"].astype(str))
        ]
        known = {r["code"] for r in regions}
        for slug in sorted(set(areas["region"].astype(str))):
            if slug not in known:
                regions.append({"code": slug, "name": COUNTY_NAME_BY_SLUG.get(slug, slug.title())})
        conn.execute(
            "INSERT INTO metadata VALUES (?, ?)",
            ["regions_json", json.dumps(regions)],
        )
        conn.close()
        if dest.exists():
            dest.unlink()
        tmp.replace(dest)
        logger.info("Ireland warehouse {} ({} SAs, {} sections)", dest, len(areas), n_sections)
        return dest
    except Exception:
        conn.close()
        if tmp.exists():
            tmp.unlink()
        raise


def _extras_from_section_results(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    try:
        row = conn.execute(
            """
            SELECT stats FROM section_results
            WHERE region = 'all' AND urban_rural = 'all' AND section_id = 'c3_operator_hhi'
            """
        ).fetchone()
        if row:
            st = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            extras["hhi"] = st.get("hhi")
            extras["n_agencies"] = st.get("n_agencies")
        c1 = conn.execute(
            """
            SELECT stats FROM section_results
            WHERE region = 'all' AND urban_rural = 'all' AND section_id = 'c1_route_length'
            """
        ).fetchone()
        if c1:
            st = json.loads(c1[0]) if isinstance(c1[0], str) else c1[0]
            extras["n_routes"] = st.get("n_routes")
            extras["p50_stops"] = st.get("p50_stops")
        c2 = conn.execute(
            """
            SELECT stats FROM section_results
            WHERE region = 'all' AND urban_rural = 'all' AND section_id = 'c2_stops_per_route'
            """
        ).fetchone()
        if c2:
            st = json.loads(c2[0]) if isinstance(c2[0], str) else c2[0]
            extras["mean_stops_per_route"] = st.get("mean")
            extras.setdefault("n_routes", st.get("n_routes"))
        b4 = conn.execute(
            """
            SELECT stats FROM section_results
            WHERE region = 'all' AND urban_rural = 'all' AND section_id = 'b4_route_frequency'
            """
        ).fetchone()
        if b4:
            st = json.loads(b4[0]) if isinstance(b4[0], str) else b4[0]
            extras["agencies"] = st.get("agencies") or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not recover Ireland extras from section_results: {}", exc)
    return extras


def rewrite_ireland_section_results(dest: Path) -> int:
    """Rebuild section_results + narratives only. Does not re-ingest or drop area tables."""
    conn = duckdb.connect(str(dest))
    try:
        extras = _extras_from_section_results(conn)
        areas = conn.execute("SELECT * FROM lsoa_demographics").df()
        root = dest.resolve().parent.parent
        areas = attach_saps_theme_shares(areas, default_saps_path(root))
        try:
            conn.register("_ie_areas_saps", areas)
            conn.execute("CREATE OR REPLACE TABLE lsoa_demographics AS SELECT * FROM _ie_areas_saps")
            conn.unregister("_ie_areas_saps")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not persist SAPS theme shares: {}", exc)
        rows = precompute_ireland(areas, extras)
        conn.execute("DELETE FROM section_results")
        batch: list[tuple[Any, ...]] = []
        for r in rows:
            batch.append(
                (
                    r["region"],
                    r["urban_rural"],
                    r["section_id"],
                    json.dumps(r["stats"], default=str),
                    json.dumps(r["chart_data"], default=str),
                    r["narrative"],
                )
            )
            if len(batch) >= 200:
                conn.executemany("INSERT INTO section_results VALUES (?, ?, ?, ?, ?, ?)", batch)
                batch.clear()
        if batch:
            conn.executemany("INSERT INTO section_results VALUES (?, ?, ?, ?, ?, ?)", batch)
        n = len(rows)
        logger.info("Rewrote {} Ireland section rows in {}", n, dest)
        return n
    finally:
        conn.close()


def load_or_empty_ireland(path: Path) -> Path | None:
    return path if path.exists() else None
