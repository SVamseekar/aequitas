"""Service quality processing — headways, SQI, evening/Sunday flags.

Ported from Phase 0 notebook 04b. Streams stop_times.txt (5.8GB) in chunks.

Algorithm:
1. Stream stop_times.txt → per (stop_id, day_type) departure lists
2. Compute headway statistics per stop
3. Join stops → LSOAs (from NaPTAN spatial join output)
4. Aggregate to LSOA level
5. Compute composite SQI (5 weighted components, 0-100)
6. Flag evening isolation and Sunday deserts
"""

from pathlib import Path
from zipfile import ZipFile

import geopandas as gpd
import numpy as np
import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.ingestion.boundaries import load_lsoa_boundaries
from aequitas.ingestion.imd import load_imd
from aequitas.ingestion.naptan import load_naptan
from aequitas.processing.spatial import assign_stops_to_lsoa

# Time band thresholds (minutes from midnight)
_AM_PEAK_START = 7 * 60       # 07:00
_AM_PEAK_END = 9 * 60 + 30    # 09:30
_INTERPEAK_END = 16 * 60      # 16:00
_PM_PEAK_END = 19 * 60        # 19:00
_EVENING_THRESHOLD = 21 * 60  # 21:00 — last service before this = evening isolated
_NIGHT_THRESHOLD = 22 * 60    # 22:00 — last service before this = night isolated


def _parse_gtfs_time(time_str: str) -> int:
    """Convert GTFS HH:MM:SS to minutes from midnight. Handles >24:00."""
    try:
        h, m, _ = time_str.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return -1


def _time_band(minutes: int) -> str:
    """Classify departure time into service band."""
    if minutes < 0:
        return "unknown"
    if minutes < _AM_PEAK_START:
        return "early"
    if minutes < _AM_PEAK_END:
        return "am_peak"
    if minutes < _INTERPEAK_END:
        return "interpeak"
    if minutes < _PM_PEAK_END:
        return "pm_peak"
    return "evening"


def _compute_headway_stats(departures: list[int]) -> dict:
    """Compute headway statistics from a list of departure times (minutes from midnight)."""
    deps = sorted(set(departures))
    n = len(deps)
    if n == 0:
        return {
            "n_trips": 0, "mean_headway_min": None, "median_headway_min": None,
            "max_headway_min": None, "cov_headway": None,
            "first_dep": None, "last_dep": None, "span_min": None,
            "peak_interpeak_ratio": None,
            "n_am_peak": 0, "n_interpeak": 0, "n_pm_peak": 0, "n_evening": 0,
        }

    headways = np.diff(deps) if n > 1 else np.array([])
    bands = [_time_band(d) for d in deps]
    span = deps[-1] - deps[0] if n > 1 else 0

    # Peak/interpeak ratio
    n_am = sum(1 for b in bands if b == "am_peak")
    n_inter = sum(1 for b in bands if b == "interpeak")
    n_pm = sum(1 for b in bands if b == "pm_peak")
    n_eve = sum(1 for b in bands if b == "evening")
    # interpeak headway vs peak headway ratio (higher = worse evenings vs peaks)
    peak_interpeak = (n_am + n_pm) / max(n_inter, 1) if n_inter > 0 else None

    return {
        "n_trips": n,
        "mean_headway_min": float(np.mean(headways)) if len(headways) > 0 else None,
        "median_headway_min": float(np.median(headways)) if len(headways) > 0 else None,
        "max_headway_min": float(np.max(headways)) if len(headways) > 0 else None,
        "cov_headway": float(np.std(headways) / np.mean(headways)) if len(headways) > 0 and np.mean(headways) > 0 else None,
        "first_dep": deps[0],
        "last_dep": deps[-1],
        "span_min": span,
        "peak_interpeak_ratio": peak_interpeak,
        "n_am_peak": n_am,
        "n_interpeak": n_inter,
        "n_pm_peak": n_pm,
        "n_evening": n_eve,
    }


def _stream_stop_times(
    zip_path: Path,
    trips_df: pd.DataFrame,
    chunk_size: int = 1_000_000,
) -> pd.DataFrame:
    """Stream stop_times.txt → per (stop_id, day_type) departure statistics.

    Day type is derived from calendar.txt service_id patterns (weekday/saturday/sunday).
    Simplified approach: classify by trip's calendar pattern.
    """
    # Build trip → day_type mapping from calendar
    with ZipFile(zip_path) as zf:
        with zf.open("calendar.txt") as f:
            calendar = pd.read_csv(f)

    # Determine day type for each service_id
    def classify_service(row: pd.Series) -> str:
        if row.get("sunday", 0) == 1 and all(row.get(d, 0) == 0 for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]):
            return "sunday"
        if row.get("saturday", 0) == 1 and all(row.get(d, 0) == 0 for d in ["monday", "tuesday", "wednesday", "thursday", "friday"]):
            return "saturday"
        if any(row.get(d, 0) == 1 for d in ["monday", "tuesday", "wednesday", "thursday", "friday"]):
            return "weekday"
        return "other"

    service_day_type = calendar.apply(classify_service, axis=1)
    service_to_day: dict[str, str] = dict(zip(calendar["service_id"].astype(str), service_day_type))

    # Trip → day_type lookup (vectorised — iterrows over 1.75M rows is too slow)
    trip_to_day: dict[str, str] = dict(zip(
        trips_df["trip_id"].astype(str),
        trips_df["service_id"].astype(str).map(service_to_day).fillna("other"),
    ))

    logger.info("Streaming stop_times.txt for headway computation")
    # Accumulate (stop_id, day_type) → list of departure times
    stop_day_departures: dict[tuple[str, str], list[int]] = {}
    typed_trip_ids = set(trip_to_day.keys())

    with ZipFile(zip_path) as zf:
        with zf.open("stop_times.txt") as f:
            reader = pd.read_csv(
                f,
                usecols=["trip_id", "stop_id", "departure_time"],
                chunksize=chunk_size,
                dtype={"trip_id": str, "stop_id": str, "departure_time": str},
            )
            chunk_num = 0
            for chunk in reader:
                chunk_num += 1
                if chunk_num % 20 == 0:
                    logger.info("  stop_times chunk {}, {} pairs so far", chunk_num, len(stop_day_departures))

                # Filter to trips with known day types
                chunk = chunk[chunk["trip_id"].isin(typed_trip_ids)].copy()
                if chunk.empty:
                    continue

                # Parse departure times vectorised (split HH:MM:SS → minutes)
                parts = chunk["departure_time"].str.split(":", expand=True)
                chunk["dep_min"] = pd.to_numeric(parts[0], errors="coerce") * 60 + pd.to_numeric(parts[1], errors="coerce")
                chunk["dep_min"] = chunk["dep_min"].fillna(-1).astype(int)
                chunk = chunk[chunk["dep_min"] >= 0]

                # Map trip → day_type
                chunk["day_type"] = chunk["trip_id"].map(trip_to_day)

                # Accumulate per (stop_id, day_type) group
                for (stop_id, day_type), grp in chunk.groupby(["stop_id", "day_type"]):
                    key = (str(stop_id), str(day_type))
                    dep_list = grp["dep_min"].tolist()
                    if key not in stop_day_departures:
                        stop_day_departures[key] = dep_list
                    else:
                        stop_day_departures[key].extend(dep_list)

    logger.info("Computing headway stats for {} (stop, day_type) pairs", len(stop_day_departures))
    records = []
    for (stop_id, day_type), departures in stop_day_departures.items():
        stats = _compute_headway_stats(departures)
        stats["stop_id"] = stop_id
        stats["day_type"] = day_type
        records.append(stats)

    return pd.DataFrame(records)


def _compute_sqi(lsoa_df: pd.DataFrame) -> pd.Series:
    """Compute composite Service Quality Index (0-100) for each LSOA.

    5 weighted components (from Phase 0 notebook 04b):
    1. Headway score  (40%): score = max(0, 100 - mean_headway/60 * 100)
    2. Span score     (20%): score = min(100, span_min / (18*60) * 100)
    3. Frequency score(20%): score = min(100, total_weekday_departures / 100 * 100)
    4. Evening score  (10%): score = min(100, max(0, (last_dep - 18*60) / (4*60) * 100))
    5. Sunday score   (10%): score = min(100, total_sunday / max(total_weekday, 1) * 200)
    """
    q = lsoa_df.copy()

    q["score_headway"] = np.clip(100 - (q["mean_headway_min"].fillna(60) / 60) * 100, 0, 100)
    q["score_span"] = np.clip(q["span_min"].fillna(0) / (18 * 60) * 100, 0, 100)
    q["score_frequency"] = np.clip(q["total_weekday_departures"].fillna(0) / 100 * 100, 0, 100)

    eve_score = np.clip(
        (q["last_service_min"].fillna(0) - 18 * 60) / (4 * 60) * 100, 0, 100
    )
    q["score_evening"] = eve_score

    sun_ratio = q["total_sunday_departures"].fillna(0) / np.maximum(q["total_weekday_departures"].fillna(1), 1)
    q["score_sunday"] = np.clip(sun_ratio * 200, 0, 100)

    sqi = (
        0.40 * q["score_headway"]
        + 0.20 * q["score_span"]
        + 0.20 * q["score_frequency"]
        + 0.10 * q["score_evening"]
        + 0.10 * q["score_sunday"]
    )
    return sqi.round(2)


def compute_service_quality(cfg: PipelineConfig) -> pd.DataFrame:
    """Compute LSOA-level service quality metrics.

    Returns DataFrame with 33,755 rows (all England LSOAs), columns including:
    sqi, mean_headway_min, evening_isolated, sunday_desert, and more.
    """
    zip_path = cfg.raw_dir / "bods" / "bods_gtfs_all.zip"

    # Load trips
    with ZipFile(zip_path) as zf:
        with zf.open("trips.txt") as f:
            trips_df = pd.read_csv(f, low_memory=False, usecols=["trip_id", "service_id"])

    # Stream stop_times → headways
    stop_headways = _stream_stop_times(zip_path, trips_df, chunk_size=cfg.stop_times_chunk_size)

    # Get stop → LSOA mapping via spatial join
    logger.info("Assigning stops to LSOAs for service quality aggregation")
    naptan = load_naptan(cfg.raw_dir / "naptan" / "Stops.csv")
    lsoa_gdf = load_lsoa_boundaries(cfg.raw_dir / "boundaries")
    stops_with_lsoa = assign_stops_to_lsoa(naptan, lsoa_gdf)[["ATCOCode", "lsoa_code"]].rename(
        columns={"ATCOCode": "stop_id"}
    )

    # Join weekday headways to LSOAs
    wd = stop_headways[stop_headways["day_type"] == "weekday"].copy()
    wd = wd.merge(stops_with_lsoa, on="stop_id", how="left")

    # Sunday trips per stop → LSOA
    sun = stop_headways[stop_headways["day_type"] == "sunday"][["stop_id", "n_trips"]].rename(
        columns={"n_trips": "sunday_trips"}
    )
    wd = wd.merge(sun, on="stop_id", how="left")

    # Aggregate to LSOA level
    lsoa_agg = (
        wd.dropna(subset=["lsoa_code"])
        .groupby("lsoa_code")
        .agg(
            n_stops_with_service=("stop_id", "nunique"),
            mean_headway_min=("mean_headway_min", "mean"),
            median_headway_min=("median_headway_min", "median"),
            cov_headway=("cov_headway", "mean"),
            first_service_min=("first_dep", "min"),
            last_service_min=("last_dep", "max"),
            total_weekday_departures=("n_trips", "sum"),
            total_sunday_departures=("sunday_trips", "sum"),
            n_stops_with_evening=("n_evening", lambda x: (x > 0).sum()),
            span_min=("span_min", "mean"),
        )
        .reset_index()
    )

    # Ensure all 33,755 LSOAs present (zero-fill)
    all_lsoas = pd.DataFrame({"lsoa_code": lsoa_gdf["LSOA21CD"].values})
    lsoa_quality = all_lsoas.merge(lsoa_agg, on="lsoa_code", how="left")

    # Compute SQI
    lsoa_quality["sqi"] = _compute_sqi(lsoa_quality)

    # Evening isolation and Sunday desert flags
    lsoa_quality["evening_isolated"] = (
        lsoa_quality["last_service_min"].isna()
        | (lsoa_quality["last_service_min"] < _EVENING_THRESHOLD)
    )
    lsoa_quality["sunday_desert"] = (
        lsoa_quality["total_sunday_departures"].isna()
        | (lsoa_quality["total_sunday_departures"] == 0)
    )
    lsoa_quality["no_service"] = lsoa_quality["n_stops_with_service"].isna()

    n_eve = int(lsoa_quality["evening_isolated"].sum())
    n_sun = int(lsoa_quality["sunday_desert"].sum())
    mean_sqi = float(lsoa_quality["sqi"].mean())
    logger.info(
        "Service quality: {} LSOAs, mean SQI={:.1f}, evening_isolated={}, sunday_desert={}",
        len(lsoa_quality), mean_sqi, n_eve, n_sun,
    )
    return lsoa_quality.reset_index(drop=True)
