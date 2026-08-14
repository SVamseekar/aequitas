"""Build data/aequitas_netherlands.duckdb — never overwrites England or Ireland."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from loguru import logger


def _clean(obj: Any) -> Any:
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _json_safe(obj: Any) -> str:
    return json.dumps(_clean(obj), default=str, allow_nan=False)

from aequitas.netherlands.constants import NL_EVENING_NOTE, NL_PROVINCES, STEDELIJKHEID_NOTE
from aequitas.netherlands.sections import catalogue_counts, precompute_netherlands

__all__ = ["build_netherlands_warehouse", "netherlands_warehouse_path"]


def netherlands_warehouse_path(project_root: Path) -> Path:
    return project_root / "data" / "aequitas_netherlands.duckdb"


def build_netherlands_warehouse(
    areas_by_mode: dict[str, pd.DataFrame],
    dest: Path,
    *,
    extras_by_mode: dict[str, dict[str, Any]] | None = None,
    vintages: dict[str, str] | None = None,
    stops_by_mode: dict[str, pd.DataFrame] | None = None,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".duckdb.tmp")
    if tmp.exists():
        tmp.unlink()
    conn = duckdb.connect(str(tmp))
    extras_by_mode = extras_by_mode or {}
    try:
        conn.execute(
            """
            CREATE TABLE section_results (
                region VARCHAR,
                urban_rural VARCHAR,
                section_id VARCHAR,
                mode VARCHAR,
                stats JSON,
                chart_data JSON,
                narrative VARCHAR,
                PRIMARY KEY (region, urban_rural, section_id, mode)
            )
            """
        )
        n_sections = 0
        default_areas = areas_by_mode["bus"] if "bus" in areas_by_mode else next(iter(areas_by_mode.values()))
        gini_v = None
        for mode, areas in areas_by_mode.items():
            extras = dict(extras_by_mode.get(mode) or {})
            extras["mode"] = mode
            extras.setdefault("vintage", (vintages or {}).get("gtfs", "OVapi"))
            rows = precompute_netherlands(areas, extras)
            n_sections += len(rows)
            if mode == "bus":
                nat = next(
                    (
                        r
                        for r in rows
                        if r["region"] == "all" and r["urban_rural"] == "all" and r["section_id"] == "f1_gini"
                    ),
                    None,
                )
                if nat:
                    gini_v = nat["stats"].get("gini")
            batch = []
            for r in rows:
                batch.append(
                    (
                        r["region"],
                        r["urban_rural"],
                        r["section_id"],
                        mode,
                        _json_safe(r["stats"]),
                        _json_safe(r["chart_data"]),
                        r["narrative"],
                    )
                )
                if len(batch) >= 200:
                    conn.executemany(
                        "INSERT INTO section_results VALUES (?, ?, ?, ?, ?, ?, ?)", batch
                    )
                    batch.clear()
            if batch:
                conn.executemany("INSERT INTO section_results VALUES (?, ?, ?, ?, ?, ?, ?)", batch)

        keep = [
            c
            for c in (
                "buurt_code",
                "sa_code",
                "lsoa_code",
                "name",
                "lat",
                "lon",
                "population",
                "region",
                "urban_rural",
                "stedelijkheid",
                "ses_decile",
                "ses_score",
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
                "unemp_rate",
                "no_car_share",
                "elderly_share",
                "income",
                "wmo_share",
                "labour_part",
                "huur_share",
                "buiten_europa_share",
            )
            if c in default_areas.columns
        ]
        demo = default_areas[keep].copy()
        conn.register("demo_df", demo)
        conn.execute("CREATE TABLE lsoa_demographics AS SELECT * FROM demo_df")
        conn.execute("CREATE TABLE lsoa_service_quality AS SELECT * FROM demo_df")
        cents = demo.rename(columns={"buurt_code": "area", "population": "pop", "ses_decile": "imd_decile"})
        if "area" not in cents.columns:
            cents["area"] = cents.get("sa_code", cents.get("lsoa_code"))
        conn.register("cents_df", cents[["area", "lat", "lon", "pop", "imd_decile", "region", "name"]])
        conn.execute("CREATE TABLE lsoa_centroids AS SELECT * FROM cents_df")
        if stops_by_mode and "bus" in stops_by_mode and not stops_by_mode["bus"].empty:
            conn.register("stops_df", stops_by_mode["bus"])
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
                    "population-weighted Gini of OVapi weekday trips/capita (buurten, bus mode)",
                    json.dumps({"n_buurten": int(len(default_areas)), **catalogue_counts()}),
                    ["ovapi", "cbs_ses_woa_86092NED", "cbs_kerncijfers_85984NED"],
                ],
            )

        conn.execute("CREATE TABLE metadata (key VARCHAR PRIMARY KEY, value VARCHAR)")
        vintages = vintages or {}
        counts = catalogue_counts()
        nh = default_areas[default_areas["region"] == "noord-holland"]
        gr = default_areas[default_areas["region"] == "groningen"]
        meta = {
            "country": "netherlands",
            "built_at": datetime.now(timezone.utc).isoformat(),
            "n_buurten": str(len(default_areas)),
            "n_provincies": str(default_areas["region"].nunique()),
            "evening_definition": NL_EVENING_NOTE,
            "urban_rural": STEDELIJKHEID_NOTE,
            "deprivation": "CBS SES-WOA 2023 (86092NED). Never labelled IMD.",
            "gtfs": vintages.get("gtfs", "OVapi gtfs-nl.zip"),
            "small_areas": vintages.get("small_areas", "CBS / PDOK buurt 2024"),
            "scope": "Netherlands only. BE/DE stops clipped.",
            "join_rate": vintages.get("join_rate", ""),
            "stedelijkheid": vintages.get("stedelijkheid", STEDELIJKHEID_NOTE),
            "modes": "bus,all",
            "catalogue_same": str(counts["same"]),
            "catalogue_replace": str(counts["replace"]),
            "catalogue_omit": str(counts["omit"]),
            "catalogue_answers": str(counts["answers"]),
            "score_noord_holland_bus": vintages.get("score_nh", ""),
            "score_groningen_bus": vintages.get("score_gr", ""),
            "n_noord_holland": str(len(nh)),
            "n_groningen": str(len(gr)),
        }
        conn.executemany("INSERT INTO metadata VALUES (?, ?)", list(meta.items()))
        regions = [{"code": "all", "name": "All Netherlands"}] + [
            {"code": s, "name": n} for s, n in NL_PROVINCES if s in set(default_areas["region"].astype(str))
        ]
        conn.execute("INSERT INTO metadata VALUES (?, ?)", ["regions_json", json.dumps(regions)])
        conn.close()
        try:
            if dest.exists():
                dest.unlink()
            tmp.replace(dest)
            written = dest
        except OSError as exc:
            alt = dest.with_name(dest.stem + ".next.duckdb")
            if alt.exists():
                alt.unlink()
            tmp.replace(alt)
            logger.warning("Could not replace {} ({}). Wrote {}", dest, exc, alt)
            written = alt
        logger.info("Netherlands warehouse {} ({} buurten, {} sections)", written, len(default_areas), n_sections)
        return written
    except Exception:
        conn.close()
        if tmp.exists():
            tmp.unlink()
        raise
