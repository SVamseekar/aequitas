"""r5py 15 / 30 / 45 minute destination counts (jobs, GP, school).

Counts destinations reachable within each cutoff from an LSOA centroid.
Not Hansen. Not a live query — write Parquet, then warehouse/API read it.

Full England can take many hours. Writer is resumable by ITL1 (`region`).
If Java / r5py / PBF / GTFS are missing, the CLI explains how to install
and writes nothing (never random percentages).
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
from loguru import logger

DEST_TYPES = ("jobs", "gp", "school")
# School first: smallest point set, so the first chunk is the timing canary.
DEST_RUN_ORDER = ("school", "gp", "jobs")
CUTOFFS_MIN = (15, 30, 45)
BUFFER_KM = 40.0
CHUNK_ORIGINS = 20
KM_PER_DEG_LAT = 111.32
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
    "r5py needs Java 21 (class file 65). Java 17 cannot load it. "
    "Install: brew install openjdk@21 && uv pip install r5py, "
    "then set JAVA_HOME to that JDK. "
    "Place a Geofabrik England PBF under data/raw/osm/ and BODS GTFS under data/raw/bods/."
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
    country: str = "england"
    buffer_km: float = BUFFER_KM
    chunk_size: int = CHUNK_ORIGINS


def departure_from_gtfs(gtfs: Path) -> datetime | None:
    """08:00 UTC on feed_info feed_start_date. None if the zip does not say."""
    import csv
    import io
    import zipfile

    if not zipfile.is_zipfile(gtfs):
        return None
    with zipfile.ZipFile(gtfs) as zf:
        names = [n for n in zf.namelist() if n.endswith("feed_info.txt")]
        if not names:
            return None
        text = zf.read(names[0]).decode("utf-8")
    row = next(csv.DictReader(io.StringIO(text)), None)
    raw = (row or {}).get("feed_start_date", "").strip()
    if len(raw) != 8 or not raw.isdigit():
        return None
    return datetime(int(raw[:4]), int(raw[4:6]), int(raw[6:8]), 8, 0, tzinfo=timezone.utc)


def count_within_cutoffs(minutes: pd.Series) -> dict[str, int]:
    """Count non-null travel times under 15 / 30 / 45 minutes. No negatives."""
    valid = pd.to_numeric(minutes, errors="coerce")
    valid = valid[valid.notna() & (valid >= 0)]
    return {
        "t_15": int((valid <= 15).sum()),
        "t_30": int((valid <= 30).sum()),
        "t_45": int((valid <= 45).sum()),
    }


def _minutes_from_travel_time(raw: pd.Series) -> pd.Series:
    if pd.api.types.is_timedelta64_dtype(raw):
        return raw.dt.total_seconds() / 60.0
    return pd.to_numeric(raw, errors="coerce")


def counts_from_travel_times(matrix: pd.DataFrame, origin_ids: list[str]) -> pd.DataFrame:
    """Reduce one chunk's OD pairs to t_15 / t_30 / t_45. Unreachable origins stay 0."""
    if matrix.empty or "travel_time" not in matrix.columns:
        minutes = pd.Series(dtype=float)
        from_id = pd.Series(dtype=str)
    else:
        minutes = _minutes_from_travel_time(matrix["travel_time"])
        from_id = matrix["from_id"].astype(str)
    ok = minutes.notna() & (minutes >= 0) & (minutes <= 45)
    slim = pd.DataFrame({"origin_id": from_id.loc[ok].values, "minutes": minutes.loc[ok].values})
    grouped = {str(key): grp for key, grp in slim.groupby("origin_id")["minutes"]}
    rows = [
        {"lsoa": str(oid), **count_within_cutoffs(grouped.get(str(oid), pd.Series(dtype=float)))}
        for oid in origin_ids
    ]
    return pd.DataFrame(rows)


def clip_destinations(
    destinations: pd.DataFrame,
    origins: pd.DataFrame,
    buffer_km: float,
) -> pd.DataFrame:
    """Keep destinations inside the origin bbox plus buffer_km. Inclusive edges stay."""
    national = len(destinations)
    if destinations.empty or origins.empty:
        logger.info("dest clip buffer_km={} national={} kept=0", buffer_km, national)
        return destinations.iloc[0:0].copy()
    lat = pd.to_numeric(origins["lat"], errors="coerce")
    lon = pd.to_numeric(origins["lon"], errors="coerce")
    lat_min, lat_max = float(lat.min()), float(lat.max())
    lon_min, lon_max = float(lon.min()), float(lon.max())
    mid = (lat_min + lat_max) / 2.0
    lat_pad = buffer_km / KM_PER_DEG_LAT
    lon_scale = max(math.cos(math.radians(mid)), 0.2)
    lon_pad = buffer_km / (KM_PER_DEG_LAT * lon_scale)
    south, north = lat_min - lat_pad, lat_max + lat_pad
    west, east = lon_min - lon_pad, lon_max + lon_pad
    dlat = pd.to_numeric(destinations["lat"], errors="coerce")
    dlon = pd.to_numeric(destinations["lon"], errors="coerce")
    keep = dlat.between(south, north) & dlon.between(west, east)
    clipped = destinations.loc[keep].copy()
    logger.info(
        "dest clip buffer_km={} national={} kept={} bbox=({:.4f},{:.4f},{:.4f},{:.4f})",
        buffer_km,
        national,
        len(clipped),
        south,
        west,
        north,
        east,
    )
    return clipped


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


def reach_output_path(processed_dir: Path, country: str = "england") -> Path:
    """England keeps the historical reach/ folder. Other countries stay keyed."""
    if country and country != "england":
        return processed_dir / country / "access_times.parquet"
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


def _points_for_r5(frame: pd.DataFrame, id_column: str) -> pd.DataFrame:
    """GeoDataFrame with an id column. r5py 1.1 routes on point geometry."""
    import geopandas as gpd

    out = frame.copy()
    if "id" not in out.columns and id_column in out.columns:
        out = out.rename(columns={id_column: "id"})
    if "geometry" not in out.columns:
        out = gpd.GeoDataFrame(
            out,
            geometry=gpd.points_from_xy(out["lon"], out["lat"]),
            crs="EPSG:4326",
        )
    return out


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
        def destination_counts(
            self,
            origins: pd.DataFrame,
            destinations: pd.DataFrame,
            departure: datetime,
        ) -> pd.DataFrame:
            """One matrix for this chunk, then counts only. Pairs are discarded."""
            orig = _points_for_r5(origins, "lsoa")
            dest = _points_for_r5(destinations, "dest_id")
            tt = r5py.TravelTimeMatrix(
                network,
                origins=orig,
                destinations=dest,
                departure=departure.replace(tzinfo=None),
                transport_modes=[
                    r5py.TransportMode.TRANSIT,
                    r5py.TransportMode.WALK,
                ],
                max_time=timedelta(minutes=45),
            )
            counts = counts_from_travel_times(tt, orig["id"].astype(str).tolist())
            del tt
            return counts

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


def _england_origins_from_centroids(processed_dir: Path) -> Path | None:
    """Centroids plus the warehouse region name. No invented coordinates."""
    centroids = processed_dir / "lsoa_centroids.parquet"
    if not centroids.exists():
        logger.warning("Reach skipped. Missing master_lsoa_table.parquet and lsoa_centroids.parquet")
        return None
    warehouse = processed_dir.parent / "aequitas.duckdb"
    if not warehouse.exists():
        logger.warning(
            "Reach skipped. Centroids have no ITL1 column and {} is missing.",
            warehouse.name,
        )
        return None
    import duckdb

    origins = pd.read_parquet(centroids)
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        demo = con.execute("SELECT lsoa_cd AS lsoa, region FROM lsoa_demographics").df()
    finally:
        con.close()
    if "lsoa_code" in origins.columns and "lsoa" not in origins.columns:
        origins = origins.rename(columns={"lsoa_code": "lsoa"})
    origins["lsoa"] = origins["lsoa"].astype(str)
    demo["lsoa"] = demo["lsoa"].astype(str)
    merged = origins.merge(demo, on="lsoa", how="left")
    out = processed_dir / "reach" / "_origins_england.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(out, index=False)
    logger.info("Reach origins from centroids + warehouse region ({})", len(merged))
    return out


def _done_lsoas(path: Path, dest_type: str) -> set[str]:
    if not path.exists():
        return set()
    frame = pd.read_parquet(path, columns=["lsoa", "dest_type"])
    hit = frame[frame["dest_type"].astype(str) == dest_type]
    return set(hit["lsoa"].astype(str))


def _reach_complete(path: Path, origin_ids: set[str], dest_types: tuple[str, ...] | list[str]) -> bool:
    if not path.exists() or not origin_ids:
        return False
    frame = pd.read_parquet(path, columns=["lsoa", "dest_type"])
    for dest in dest_types:
        have = set(frame.loc[frame["dest_type"].astype(str) == dest, "lsoa"].astype(str))
        if not origin_ids <= have:
            return False
    return True


def _counts_for_origins(
    origins: pd.DataFrame,
    destinations: pd.DataFrame,
    engine: TravelTimeEngine,
    *,
    dest_type: str,
    region: str | None,
    departure: datetime | None,
) -> pd.DataFrame:
    counter = getattr(engine, "destination_counts", None)
    if counter is not None:
        if departure is None:
            raise RuntimeError("Reach departure is missing. Not inventing a service day.")
        counts = counter(origins, destinations, departure)
        counts["dest_type"] = dest_type
        counts["region"] = region
        return counts
    return write_reach_from_engine(
        origins,
        destinations,
        engine,
        dest_type=dest_type,
        region=region,
        departure=departure,
    )


def checkpoint_reach(out: Path, incoming: pd.DataFrame, *, region: str | None) -> None:
    """Merge this chunk onto the parquet and replace the file. A kill keeps earlier chunks."""
    if incoming.empty:
        return
    existing = pd.read_parquet(out) if out.exists() else None
    merged = merge_reach_frames(existing, incoming)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / f"{out.name}.tmp"
    merged.to_parquet(tmp, index=False)
    os.replace(tmp, out)
    meta = {
        "written_at": datetime.now(timezone.utc).isoformat(),
        "region": region,
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


def write_reach(
    cfg: ReachConfig,
    engine: TravelTimeEngine | None = None,
    departure: datetime | None = None,
) -> Path | None:
    """Write country-keyed access-time parquet. Returns path or None if skipped."""
    from aequitas.analytics.destinations import load_destination_frames

    out = reach_output_path(cfg.processed_dir, country=cfg.country)
    out.parent.mkdir(parents=True, exist_ok=True)
    pbf = _find_pbf(cfg.raw_dir)
    gtfs = _find_gtfs(cfg.raw_dir)

    if engine is None:
        missing: list[str] = []
        if pbf is None:
            missing.append("OSM PBF (data/raw/osm/*.pbf)")
        if gtfs is None:
            missing.append("BODS GTFS (data/raw/bods/*.zip)")
        if missing:
            logger.warning(
                "Reach skipped. Missing: {}. Download Geofabrik England "
                "(https://download.geofabrik.de/europe/united-kingdom/england.html) "
                "into data/raw/osm/ (gitignored). {}",
                "; ".join(missing),
                JAVA_HINT,
            )
            return None
        try:
            engine = try_build_r5_engine(pbf, gtfs)
        except RuntimeError as exc:
            logger.warning("Reach skipped. Missing router: {}", exc)
            return None
        if departure is None:
            departure = departure_from_gtfs(gtfs)
            if departure is None:
                logger.warning(
                    "Reach skipped. {} has no feed_start_date. Not inventing a service day.",
                    gtfs.name,
                )
                return None
            logger.info("Reach departure from GTFS feed_start_date {}", departure.date())

    origins_path = cfg.processed_dir / "master_lsoa_table.parquet"
    if cfg.country == "ireland":
        origins_path = cfg.processed_dir / "ireland" / "sa_table.parquet"
        if not origins_path.exists():
            origins_path = cfg.processed_dir / "master_lsoa_table.parquet"
    elif cfg.country == "netherlands":
        alt = cfg.processed_dir / "netherlands" / "buurt_table.parquet"
        if alt.exists():
            origins_path = alt
    elif cfg.country == "france":
        alt = cfg.processed_dir / "france" / "iris_table.parquet"
        if alt.exists():
            origins_path = alt
    if not origins_path.exists() and cfg.country == "england":
        origins_path = _england_origins_from_centroids(cfg.processed_dir)
    if origins_path is None or not origins_path.exists():
        logger.warning("No origin table — cannot compute reach")
        return None

    origins = pd.read_parquet(origins_path)
    if "lsoa_cd" in origins.columns and "lsoa" not in origins.columns:
        origins = origins.rename(columns={"lsoa_cd": "lsoa"})
    if "lsoa_code" in origins.columns and "lsoa" not in origins.columns:
        origins = origins.rename(columns={"lsoa_code": "lsoa"})
    if "lsoa" not in origins.columns:
        for cand in ("sa", "sa_code", "buurt", "buurt_code", "iris", "code_iris", "area_id"):
            if cand in origins.columns:
                origins = origins.rename(columns={cand: "lsoa"})
                break
    if cfg.region and cfg.region != "all":
        before = len(origins)
        if "region_code" in origins.columns:
            origins = origins[origins["region_code"] == cfg.region]
        elif "rgn22cd" in origins.columns:
            origins = origins[origins["rgn22cd"] == cfg.region]
        elif "region" in origins.columns:
            name = ITL1_NAMES.get(cfg.region, cfg.region)
            origins = origins[origins["region"].isin([cfg.region, name])]
        else:
            logger.warning(
                "Reach skipped. Missing region column, so {} would cover every origin. Not writing.",
                cfg.region,
            )
            return None
        logger.info("Reach batch region={} rows={} (from {})", cfg.region, len(origins), before)
        if origins.empty:
            logger.warning("Reach skipped. No origins for region {}.", cfg.region)
            return None

    dest_frames = load_destination_frames(cfg.processed_dir, cfg.country, dest_types=cfg.dest_types)

    if not dest_frames:
        logger.warning(
            "No destination Parquets for {} (processed/{}/destinations_{{jobs,gp,school}}.parquet). "
            "Do not copy another country's points.",
            cfg.country,
            cfg.country if cfg.country != "england" else "england or processed/",
        )
        return out if out.exists() else None

    origin_ids = set(origins["lsoa"].astype(str))
    if (
        not cfg.force
        and cache_is_fresh(out, [p for p in (pbf, gtfs) if p])
        and _reach_complete(out, origin_ids, tuple(dest_frames))
    ):
        logger.info("Reach cache complete — skip (use --force to recompute)")
        return out

    ordered = [d for d in DEST_RUN_ORDER if d in dest_frames]
    ordered += [d for d in dest_frames if d not in ordered]
    # The bbox clip is for the router. Fixture engines ignore coordinates.
    route_clip = hasattr(engine, "destination_counts")
    clipped: dict[str, pd.DataFrame] = {}
    for dest in ordered:
        if route_clip:
            clipped[dest] = clip_destinations(dest_frames[dest], origins, cfg.buffer_km)
        else:
            clipped[dest] = dest_frames[dest]
        if clipped[dest].empty:
            logger.warning("Reach dest_type={} kept 0 destinations after clip. Not writing zeros.", dest)

    chunk = max(int(cfg.chunk_size), 1)
    canary = False
    school_n = len(clipped.get("school", ()))
    jobs_n = len(clipped.get("jobs", ()))
    for dest in ordered:
        dest_df = clipped[dest]
        if dest_df.empty:
            continue
        done = set() if cfg.force else _done_lsoas(out, dest)
        pending = origins[~origins["lsoa"].astype(str).isin(done)].reset_index(drop=True)
        logger.info(
            "Reach dest_type={} pending={} skipped={} dests={}",
            dest,
            len(pending),
            len(done),
            len(dest_df),
        )
        start = 0
        while start < len(pending):
            part = pending.iloc[start : start + chunk]
            t0 = time.perf_counter()
            incoming = _counts_for_origins(
                part,
                dest_df,
                engine,
                dest_type=dest,
                region=cfg.region,
                departure=departure,
            )
            elapsed = time.perf_counter() - t0
            sec = elapsed / max(len(part), 1)
            logger.info(
                "reach chunk dest={} origins={}–{} seconds={:.1f} sec_per_origin={:.2f}",
                dest,
                start + 1,
                start + len(part),
                elapsed,
                sec,
            )
            issues = validate_reach_frame(incoming, expected_lsoas=len(part))
            for issue in issues:
                logger.warning("Reach validation: {}", issue)
            checkpoint_reach(out, incoming, region=cfg.region)
            start += len(part)
            if dest == "school" and not canary and jobs_n and school_n:
                canary = True
                projected = sec * (jobs_n / school_n) * len(origins)
                logger.info(
                    "jobs projection {:.1f} h at this rate (buffer_km={} chunk={})",
                    projected / 3600,
                    cfg.buffer_km,
                    chunk,
                )
                if projected > 8 * 3600 and chunk < 100:
                    chunk = 100
                    logger.warning("Widened chunk to 100 origins. max_time stays 45.")
    if not out.exists():
        logger.warning("Reach wrote nothing for region={}", cfg.region)
        return None
    logger.info("Wrote {}", out)
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
