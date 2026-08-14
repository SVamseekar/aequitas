"""Read precomputed reach Parquet (or warehouse table) for the Access exhibit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from aequitas.analytics.reach import ITL1_NAMES, reach_output_path, summarise_reach
from aequitas.core.config import PipelineConfig


def load_reach_frame(cfg: PipelineConfig | None = None) -> pd.DataFrame:
    cfg = cfg or PipelineConfig()
    path = reach_output_path(cfg.processed_dir)
    if path.exists():
        return pd.read_parquet(path)
    warehouse = cfg.warehouse_path
    if warehouse.exists():
        con = duckdb.connect(str(warehouse), read_only=True)
        try:
            tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
            if "lsoa_reach" in tables:
                return con.execute("SELECT * FROM lsoa_reach").df()
        finally:
            con.close()
    return pd.DataFrame()


def query_reach(
    dest_type: str,
    cutoff: int,
    region: str,
    urban_rural: str,
    country: str = "england",
) -> dict[str, Any]:
    _ = urban_rural  # LSOA-level reach is not yet split by RUC in the writer
    if country == "netherlands":
        return {
            "available": False,
            "geographies": [],
            "dest_type": dest_type,
            "cutoff": cutoff,
            "median": None,
            "n_areas": 0,
            "histogram": [],
            "ranked": [],
            "note": (
                "15/30/45 destination counts are not in the Netherlands pack. "
                "We do not invent them or copy another country's travel times."
            ),
            "region_name": "Netherlands" if region == "all" else region,
        }
    df = load_reach_frame()
    if df.empty:
        return {
            "available": False,
            "geographies": [],
            "dest_type": dest_type,
            "cutoff": cutoff,
            "median": None,
            "n_areas": 0,
            "histogram": [],
            "ranked": [],
            "note": (
                "45-minute destination counts are not in this pack. "
                "Install Java 17 + r5py and a Geofabrik PBF, then run `uv run aequitas reach`. "
                "We do not invent 15/30/45."
            ),
            "region_name": (
                "Ireland"
                if country == "ireland" and region == "all"
                else ITL1_NAMES.get(region, "England") if region != "all" else "England"
            ),
        }
    payload = summarise_reach(df, dest_type=dest_type, cutoff=cutoff, region=region)
    payload["region_name"] = ITL1_NAMES.get(region, "England") if region != "all" else "England"
    return payload


def geographies_with_reach() -> list[str]:
    df = load_reach_frame()
    if df.empty or "region" not in df.columns:
        return []
    return sorted({str(r) for r in df["region"].dropna().unique()})


def load_bands_frame(cfg: PipelineConfig | None = None, country: str = "england") -> pd.DataFrame:
    from aequitas.analytics.bands import bands_output_path, write_access_bands

    cfg = cfg or PipelineConfig()
    if country == "ireland":
        ie = cfg.processed_dir / "ireland" / "sa_access_bands.parquet"
        if ie.exists():
            return pd.read_parquet(ie)
        from aequitas.ireland.bands import write_ireland_bands

        written = write_ireland_bands(cfg)
        return pd.read_parquet(written) if written is not None and written.exists() else pd.DataFrame()
    if country == "netherlands":
        return pd.DataFrame()
    path = bands_output_path(cfg.processed_dir)
    if path.exists():
        return pd.read_parquet(path)
    written = write_access_bands(cfg)
    if written is not None and written.exists():
        return pd.read_parquet(written)
    return pd.DataFrame()


def query_bands(region: str, urban_rural: str, country: str = "england") -> dict[str, Any]:
    from aequitas.analytics.bands import summarise_bands

    df = load_bands_frame(country=country)
    if df.empty:
        return {
            "empty": True,
            "empty_reason": (
                "Aequitas service bands are not built for the Netherlands in this checkout. "
                "15/30/45 has not been run. We do not copy another country's bands here."
                if country == "netherlands"
                else "Access bands are not built yet — need LSOA demographics."
            ),
            "mode": "service",
            "not_tfl_ptal": True,
            "hansen_available": False,
            "map": {"geography": "region", "data": []},
            "people_by_band_decile": [],
            "band_totals": [],
            "n_areas": 0,
            "people": 0,
            "pct_worst_two": None,
            "narrative": "Access bands are not built yet.",
            "formula": "",
            "geographies_with_times": [],
        }
    payload = summarise_bands(df, region=region, urban_rural=urban_rural)
    if country == "ireland":
        if isinstance(payload.get("map"), dict):
            payload["map"]["geography"] = "ireland_county"
            agg = payload["map"].get("aggregation")
            if isinstance(agg, str):
                payload["map"]["aggregation"] = (
                    agg.replace("ITL1", "County")
                    .replace("LSOAs", "Small Areas")
                    .replace("LAD ", "County ")
                )
        if isinstance(payload.get("map_aggregation"), str):
            payload["map_aggregation"] = (
                payload["map_aggregation"]
                .replace("ITL1", "County")
                .replace("LSOAs", "Small Areas")
                .replace("LAD ", "County ")
            )
        if payload.get("narrative"):
            payload["narrative"] = (
                str(payload["narrative"])
                .replace("LSOAs", "Small Areas")
                .replace("England", "Ireland")
                .replace("official PTAL", "TfL PTAL")
            )
            if "not TfL PTAL" not in payload["narrative"]:
                payload["narrative"] += " Not TfL PTAL."
    return payload
