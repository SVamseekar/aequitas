"""Build data/aequitas_france.duckdb — never overwrites England/Ireland/Netherlands."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from loguru import logger

from aequitas.france.constants import DENSITY_NOTE, FR_EVENING_NOTE, FR_REGIONS
from aequitas.france.sections import catalogue_counts, precompute_france


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


def france_warehouse_path(project_root: Path) -> Path:
    return project_root / "data" / "aequitas_france.duckdb"


def build_france_warehouse(
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
        # Bus first, then mode=all in a later connection (NL SIGTRAP on dual 2k-row insert).
        mode_order = [m for m in ("bus", "all") if m in areas_by_mode]
        first = mode_order[0] if mode_order else next(iter(areas_by_mode))
        extras = dict(extras_by_mode.get(first) or {})
        extras["mode"] = first
        extras.setdefault("vintage", (vintages or {}).get("gtfs", "NAP"))
        rows = precompute_france(areas_by_mode[first], extras)
        n_sections += len(rows)
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
                    first,
                    _json_safe(r["stats"]),
                    _json_safe(r["chart_data"]),
                    r["narrative"],
                )
            )
            if len(batch) >= 80:
                conn.executemany("INSERT INTO section_results VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                batch.clear()
        if batch:
            conn.executemany("INSERT INTO section_results VALUES (?, ?, ?, ?, ?, ?, ?)", batch)

        keep = [
            c
            for c in (
                "iris_code",
                "sa_code",
                "lsoa_code",
                "name",
                "lat",
                "lon",
                "population",
                "region",
                "urban_rural",
                "density_level",
                "fedi_decile",
                "fedi_score",
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
                "immig_share",
                "activity_rate",
                "hlm_share",
            )
            if c in default_areas.columns
        ]
        demo = default_areas[keep].copy()
        conn.register("demo_df", demo)
        conn.execute("CREATE TABLE lsoa_demographics AS SELECT * FROM demo_df")
        conn.execute("CREATE TABLE lsoa_service_quality AS SELECT * FROM demo_df")
        cents = demo.rename(columns={"iris_code": "area", "population": "pop", "fedi_decile": "imd_decile"})
        if "area" not in cents.columns:
            cents["area"] = cents.get("sa_code", cents.get("lsoa_code"))
        conn.register("cents_df", cents[["area", "lat", "lon", "pop", "imd_decile", "region", "name"]])
        conn.execute("CREATE TABLE lsoa_centroids AS SELECT * FROM cents_df")
        if stops_by_mode and "bus" in stops_by_mode and not stops_by_mode["bus"].empty:
            raw_stops = stops_by_mode["bus"]
            if len(raw_stops) > 80_000:
                logger.info("Skipping naptan_stops write ({} rows — dual-mode SIGTRAP risk)", len(raw_stops))
            else:
                cols = [c for c in ("stop_id", "stop_lat", "stop_lon", "stop_name") if c in raw_stops.columns]
                conn.register("stops_df", raw_stops[cols])
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
                    "population-weighted Gini of NAP weekday trips/capita (IRIS, bus mode)",
                    json.dumps({"n_iris": int(len(default_areas)), **catalogue_counts()}),
                    ["nap_gtfs", "fedi_2021", "insee_iris_2018", "ign_wfs_iris"],
                ],
            )

        conn.execute("CREATE TABLE metadata (key VARCHAR PRIMARY KEY, value VARCHAR)")
        vintages = vintages or {}
        counts = catalogue_counts()
        idf = default_areas[default_areas["region"] == "ile-de-france"]
        occ = default_areas[default_areas["region"] == "occitanie"]
        meta = {
            "country": "france",
            "built_at": datetime.now(timezone.utc).isoformat(),
            "n_iris": str(len(default_areas)),
            "n_regions": str(default_areas["region"].nunique()),
            "evening_definition": FR_EVENING_NOTE,
            "urban_rural": DENSITY_NOTE,
            "deprivation": "F-EDI 2021 (EDI2021_IRIS). Never labelled IMD.",
            "gtfs": vintages.get("gtfs", "NAP harvest"),
            "small_areas": vintages.get("small_areas", "IGN WFS CONTOURS-IRIS"),
            "scope": "Metropolitan France. DOM out.",
            "join_rate": vintages.get("join_rate", ""),
            "modes": "bus,all",
            "catalogue_same": str(counts["same"]),
            "catalogue_replace": str(counts["replace"]),
            "catalogue_omit": str(counts["omit"]),
            "catalogue_answers": str(counts["answers"]),
            "score_ile_de_france_bus": vintages.get("score_idf", ""),
            "score_occitanie_bus": vintages.get("score_occ", ""),
            "n_ile_de_france": str(len(idf)),
            "n_occitanie": str(len(occ)),
            "nap_merged": vintages.get("nap_merged", ""),
            "nap_skipped": vintages.get("nap_skipped", ""),
            "harvest_note": vintages.get("harvest_note", ""),
            "n_with_index": vintages.get("n_with_index", ""),
            "n_without_index": vintages.get("n_without_index", ""),
        }
        conn.executemany("INSERT INTO metadata VALUES (?, ?)", list(meta.items()))
        regions = [{"code": "all", "name": "All France"}] + [
            {"code": s, "name": n} for s, n, _c in FR_REGIONS if s in set(default_areas["region"].astype(str))
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
        logger.info("France warehouse {} ({} IRIS, {} sections)", written, len(default_areas), n_sections)
        rest = [m for m in mode_order if m != first]
        if rest:
            try:
                append_france_mode(written, rest[0], areas_by_mode[rest[0]], extras_by_mode.get(rest[0]) or {})
            except Exception as exc:  # noqa: BLE001
                logger.warning("Append mode={} skipped after SIGTRAP risk: {}", rest[0], exc)
        return written
    except Exception:
        conn.close()
        if tmp.exists():
            tmp.unlink()
        raise


def append_france_mode(dest: Path, mode: str, areas: pd.DataFrame, extras: dict[str, Any]) -> None:
    """Append one mode after the bus warehouse is on disk (never two precomputes in one write)."""
    extras = dict(extras)
    extras["mode"] = mode
    rows = precompute_france(areas, extras)
    conn = duckdb.connect(str(dest))
    try:
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
            if len(batch) >= 80:
                conn.executemany("INSERT INTO section_results VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                batch.clear()
        if batch:
            conn.executemany("INSERT INTO section_results VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        logger.info("Appended mode={} ({} rows) to {}", mode, len(rows), dest)
    finally:
        conn.close()
