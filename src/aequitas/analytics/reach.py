"""r5py 15 / 30 / 45 minute destination counts (jobs, GP, school).

Counts destinations reachable within each cutoff from an LSOA centroid.
Not Hansen. Not a live query — write Parquet, then warehouse/API read it.

Full England can take many hours. Writer is resumable by ITL1 (`region`).
If Java / r5py / PBF / GTFS are missing, the CLI explains how to install
and writes nothing (never random percentages).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
from loguru import logger

DEST_TYPES = ("jobs", "gp", "school")
CUTOFFS_MIN = (15, 30, 45)
OUTPUT_NAME = "lsoa_access_times.parquet"
META_NAME = "lsoa_access_times.meta.json"

ITL1_NAMES: dict[str, str] = {
    "E12000001": "North East",
    "E12000002": "North West",
    "E12000003": "Yorkshire and The Humber",
    "E12000004": "East Midlands",
    "E12000005": "West Midlands",
    "E12000006": "East of England",
    "E12000007": "London",
    "E12000008": "South East",
    "E12000009": "South West",
}

JAVA_HINT = (
    "r5py needs a JDK (this machine documented Java 17). "
    "Install: brew install openjdk@17 && uv pip install r5py. "
    "Place a Geofabrik England/GB PBF under data/raw/osm/ and BODS GTFS under data/raw/bods/."
)


class TravelTimeEngine(Protocol):
    """Minutes from each origin to each destination. None = unreachable."""

    def travel_minutes(
        self,
        origins: pd.DataFrame,
        destinations: pd.DataFrame,
        departure: datetime,
    ) -> pd.DataFrame: ...


@dataclass
class ReachConfig:
    processed_dir: Path
    raw_dir: Path
    region: str | None = None
    dest_types: tuple[str, ...] = DEST_TYPES
    force: bool = False


def count_within_cutoffs(minutes: pd.Series) -> dict[str, int]:
    """Count non-null travel times under 15 / 30 / 45 minutes. No negatives."""
    valid = pd.to_numeric(minutes, errors="coerce")
    valid = valid[valid.notna() & (valid >= 0)]
    return {
        "t_15": int((valid <= 15).sum()),
        "t_30": int((valid <= 30).sum()),
        "t_45": int((valid <= 45).sum()),
    }


def validate_reach_frame(df: pd.DataFrame, expected_lsoas: int | None = None) -> list[str]:
    """Sanity checks — not a Gini lock."""
    issues: list[str] = []
    required = {"lsoa", "dest_type", "t_15", "t_30", "t_45"}
    missing = required - set(df.columns)
    if missing:
        issues.append(f"missing columns: {sorted(missing)}")
        return issues
    if (df[["t_15", "t_30", "t_45"]] < 0).any().any():
        issues.append("negative destination counts")
    if not (df["t_15"] <= df["t_30"]).all() or not (df["t_30"] <= df["t_45"]).all():
        issues.append("cutoffs not nested (t_15 ≤ t_30 ≤ t_45)")
    if expected_lsoas is not None:
        n = df["lsoa"].nunique()
        if n < expected_lsoas * 0.5:
            issues.append(f"join/coverage low: {n} LSOAs vs expected {expected_lsoas}")
    bad_dest = set(df["dest_type"].unique()) - set(DEST_TYPES)
    if bad_dest:
        issues.append(f"unknown dest_type: {sorted(bad_dest)}")
    return issues


def reach_output_path(processed_dir: Path) -> Path:
    return processed_dir / "reach" / OUTPUT_NAME


def cache_is_fresh(out: Path, inputs: list[Path]) -> bool:
    if not out.exists():
        return False
    out_mtime = out.stat().st_mtime
    existing = [p for p in inputs if p.exists()]
    if not existing:
        return True
    return all(p.stat().st_mtime <= out_mtime for p in existing)


def _find_pbf(raw_dir: Path) -> Path | None:
    osm = raw_dir / "osm"
    candidates = []
    if osm.exists():
        candidates.extend(sorted(osm.glob("*.pbf")))
    candidates.extend(sorted(raw_dir.glob("**/*.osm.pbf")))
    return candidates[0] if candidates else None


def _find_gtfs(raw_dir: Path) -> Path | None:
    bods = raw_dir / "bods" / "bods_gtfs_all.zip"
    if bods.exists():
        return bods
    zips = list((raw_dir / "bods").glob("*.zip")) if (raw_dir / "bods").exists() else []
    return zips[0] if zips else None


def write_reach_from_engine(
    origins: pd.DataFrame,
    destinations: pd.DataFrame,
    engine: TravelTimeEngine,
    *,
    dest_type: str,
    region: str | None,
    departure: datetime | None = None,
) -> pd.DataFrame:
    """Compute counts for one destination set using any travel-time engine."""
    if dest_type not in DEST_TYPES:
        raise ValueError(f"dest_type must be one of {DEST_TYPES}")
    if origins.empty or destinations.empty:
        return pd.DataFrame(columns=["lsoa", "dest_type", "t_15", "t_30", "t_45", "region"])

    dep = departure or datetime(2024, 6, 11, 8, 0, tzinfo=timezone.utc)
    matrix = engine.travel_minutes(origins, destinations, dep)
    # Expect columns: origin_id, dest_id, minutes
    rows = []
    for lsoa, grp in matrix.groupby("origin_id"):
        counts = count_within_cutoffs(grp["minutes"])
        rows.append(
            {
                "lsoa": str(lsoa),
                "dest_type": dest_type,
                **counts,
                "region": region,
            }
        )
    return pd.DataFrame(rows)


class StaticMinuteEngine:
    """Test/fixture engine: origin×dest minutes supplied as a DataFrame."""

    def __init__(self, matrix: pd.DataFrame) -> None:
        self.matrix = matrix

    def travel_minutes(
        self,
        origins: pd.DataFrame,
        destinations: pd.DataFrame,
        departure: datetime,
    ) -> pd.DataFrame:
        _ = destinations, departure
        keep = set(origins["lsoa"].astype(str))
        out = self.matrix.copy()
        out["origin_id"] = out["origin_id"].astype(str)
        return out[out["origin_id"].isin(keep)]


def try_build_r5_engine(pbf: Path, gtfs: Path) -> TravelTimeEngine:
    """Build a real r5py TransportNetwork wrapper. Raises with JAVA_HINT on failure."""
    try:
        import r5py  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(f"r5py is not installed. {JAVA_HINT}") from exc

    try:
        network = r5py.TransportNetwork(str(pbf), [str(gtfs)])
    except Exception as exc:  # Java missing, corrupt PBF, etc.
        raise RuntimeError(f"Could not open R5 network. {JAVA_HINT} Detail: {exc}") from exc

    class R5Engine:
        def travel_minutes(
            self,
            origins: pd.DataFrame,
            destinations: pd.DataFrame,
            departure: datetime,
        ) -> pd.DataFrame:
            orig = origins.copy()
            dest = destinations.copy()
            if "id" not in orig.columns:
                orig = orig.rename(columns={"lsoa": "id"})
            if "id" not in dest.columns:
                dest = dest.rename(columns={"dest_id": "id"})
            computer = r5py.TravelTimeMatrixComputer(
                network,
                origins=orig,
                destinations=dest,
                departure=departure.replace(tzinfo=None),
                transport_modes=[
                    r5py.TransportMode.TRANSIT,
                    r5py.TransportMode.WALK,
                ],
            )
            tt = computer.compute_travel_times()
            tt = tt.rename(
                columns={
                    "from_id": "origin_id",
                    "to_id": "dest_id",
                    "travel_time": "minutes",
                }
            )
            return tt[["origin_id", "dest_id", "minutes"]]

    return R5Engine()


def merge_reach_frames(existing: pd.DataFrame | None, incoming: pd.DataFrame) -> pd.DataFrame:
    if existing is None or existing.empty:
        return incoming
    if incoming.empty:
        return existing
    key = ["lsoa", "dest_type"]
    keep = existing.merge(incoming[key], on=key, how="left", indicator=True)
    keep = keep[keep["_merge"] == "left_only"].drop(columns="_merge")
    return pd.concat([keep, incoming], ignore_index=True)


def write_reach(cfg: ReachConfig, engine: TravelTimeEngine | None = None) -> Path | None:
    """Write processed/reach/lsoa_access_times.parquet. Returns path or None if skipped."""
    out = reach_output_path(cfg.processed_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    pbf = _find_pbf(cfg.raw_dir)
    gtfs = _find_gtfs(cfg.raw_dir)

    if engine is None:
        if not cfg.force and cache_is_fresh(out, [p for p in (pbf, gtfs) if p]):
            logger.info("Reach cache newer than GTFS+PBF — skip (use --force to recompute)")
            return out
        if pbf is None or gtfs is None:
            logger.warning(
                "No OSM PBF or BODS GTFS found. Download Geofabrik England "
                "(https://download.geofabrik.de/europe/united-kingdom/england.html) "
                "into data/raw/osm/ (gitignored). {}",
                JAVA_HINT,
            )
            return out if out.exists() else None
        engine = try_build_r5_engine(pbf, gtfs)

    origins_path = cfg.processed_dir / "master_lsoa_table.parquet"
    if not origins_path.exists():
        logger.warning("No master LSOA table — cannot compute reach")
        return None

    origins = pd.read_parquet(origins_path)
    if "lsoa_cd" in origins.columns and "lsoa" not in origins.columns:
        origins = origins.rename(columns={"lsoa_cd": "lsoa"})
    if cfg.region and cfg.region != "all" and "region_code" in origins.columns:
        origins = origins[origins["region_code"] == cfg.region]
        logger.info("Reach batch region={} rows={}", cfg.region, len(origins))
    elif cfg.region and cfg.region != "all" and "rgn22cd" in origins.columns:
        origins = origins[origins["rgn22cd"] == cfg.region]

    dest_frames: dict[str, pd.DataFrame] = {}
    for dest in cfg.dest_types:
        cand = cfg.processed_dir / f"destinations_{dest}.parquet"
        if cand.exists():
            dest_frames[dest] = pd.read_parquet(cand)

    if not dest_frames:
        logger.warning(
            "No destination Parquets (processed/destinations_{{jobs,gp,school}}.parquet). "
            "Writer is ready; place BRES / NHS ODS / GIAS points first."
        )
        return out if out.exists() else None

    existing = pd.read_parquet(out) if out.exists() else None
    frames = []
    for dest, dest_df in dest_frames.items():
        logger.info("Reach dest_type={} origins={} dests={}", dest, len(origins), len(dest_df))
        frames.append(
            write_reach_from_engine(
                origins,
                dest_df,
                engine,
                dest_type=dest,
                region=cfg.region,
            )
        )
    incoming = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    issues = validate_reach_frame(incoming, expected_lsoas=origins["lsoa"].nunique() if not origins.empty else None)
    for issue in issues:
        logger.warning("Reach validation: {}", issue)

    merged = merge_reach_frames(existing, incoming)
    merged.to_parquet(out, index=False)
    meta = {
        "written_at": datetime.now(timezone.utc).isoformat(),
        "region": cfg.region,
        "rows": int(len(merged)),
        "lsoas": int(merged["lsoa"].nunique()) if not merged.empty else 0,
        "dest_types": sorted(merged["dest_type"].unique().tolist()) if not merged.empty else [],
        "geographies": sorted(
            {str(r) for r in merged["region"].dropna().unique()} if "region" in merged.columns else []
        ),
        "unit": "count of destinations reachable within cutoff (not Hansen)",
        "cutoffs_min": list(CUTOFFS_MIN),
    }
    (out.parent / META_NAME).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Wrote {} ({} rows)", out, len(merged))
    return out


def summarise_reach(
    df: pd.DataFrame,
    *,
    dest_type: str = "jobs",
    cutoff: int = 45,
    region: str | None = None,
) -> dict[str, Any]:
    """Filter-level exhibit payload: median count + histogram bins."""
    col = {15: "t_15", 30: "t_30", 45: "t_45"}.get(cutoff)
    if col is None:
        raise ValueError("cutoff must be 15, 30, or 45")
    work = df[df["dest_type"] == dest_type].copy()
    if region and region != "all" and "region" in work.columns:
        work = work[work["region"] == region]
    available = sorted(
        {str(r) for r in df["region"].dropna().unique()} if "region" in df.columns else []
    )
    if work.empty:
        return {
            "available": False,
            "geographies": available,
            "dest_type": dest_type,
            "cutoff": cutoff,
            "median": None,
            "n_areas": 0,
            "histogram": [],
            "ranked": [],
            "note": (
                f"{cutoff}-minute {dest_type} not precomputed"
                + (f" for {ITL1_NAMES.get(region or '', region)}" if region and region != "all" else "")
                + " in this pack. Run `uv run aequitas reach` after placing PBF + GTFS."
            ),
        }
    values = work[col].astype(float)
    hist_bins = [0, 10, 50, 100, 250, 500, 1000, 10_000]
    cats = pd.cut(values, bins=hist_bins, include_lowest=True)
    histogram = [
        {"bin": str(idx), "n": int(n)}
        for idx, n in cats.value_counts().sort_index().items()
    ]
    ranked = (
        work.nlargest(12, col)[["lsoa", col]]
        .rename(columns={col: "value"})
        .to_dict(orient="records")
    )
    return {
        "available": True,
        "geographies": available,
        "dest_type": dest_type,
        "cutoff": cutoff,
        "median": float(values.median()),
        "n_areas": int(len(work)),
        "histogram": histogram,
        "ranked": ranked,
        "note": None,
        "unit": "destinations reachable",
    }
