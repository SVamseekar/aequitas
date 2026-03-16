"""Service quality processing — headways, SQI, evening/Sunday flags.

Ported from Phase 0 notebook 04b. Two modes:
  1. Fast path: load pre-computed Phase 0 audit Parquets (seconds)
  2. Full path: stream stop_times.txt (5.8GB) from raw GTFS (~90 min)

The fast path is used when data/audit/stop_headways.parquet exists.
The full path is a fallback for fresh data without prior audit results.
"""

from pathlib import Path
from zipfile import ZipFile

import geopandas as gpd
import numpy as np
import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.ingestion.boundaries import load_lsoa_boundaries

# Time band thresholds (minutes from midnight) — matches Phase 0 notebook 04b exactly
_AM_PEAK_START = 7 * 60       # 07:00
_AM_PEAK_END = 9 * 60 + 30    # 09:30
_INTERPEAK_END = 16 * 60      # 16:00
_PM_PEAK_END = 18 * 60 + 30   # 18:30
_EVENING_START = _PM_PEAK_END  # 18:30 — departure at or after this = "evening"
_EVENING_THRESHOLD = 19 * 60  # 19:00 — last service before 19:00 = evening isolated
_NIGHT_THRESHOLD = 22 * 60    # 22:00 — last service before 22:00 = night isolated


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

    first_dep = deps[0]
    last_dep = deps[-1]
    span = last_dep - first_dep

    if n == 1:
        return {
            "n_trips": 1, "mean_headway_min": None, "median_headway_min": None,
            "max_headway_min": None, "cov_headway": None,
            "first_dep": first_dep, "last_dep": last_dep, "span_min": span,
            "peak_interpeak_ratio": None,
            "n_am_peak": 0, "n_interpeak": 0, "n_pm_peak": 0, "n_evening": 0,
        }

    gaps = np.diff(deps, dtype=float)
    mean_h = float(gaps.mean())
    std_h = float(gaps.std())

    n_am = sum(1 for d in deps if _AM_PEAK_START <= d < _AM_PEAK_END)
    n_inter = sum(1 for d in deps if _AM_PEAK_END <= d < _INTERPEAK_END)
    n_pm = sum(1 for d in deps if _INTERPEAK_END <= d < _PM_PEAK_END)
    n_eve = sum(1 for d in deps if d >= _EVENING_START)

    am_tph = n_am / 2.5 if n_am > 0 else 0.0
    inter_tph = n_inter / 6.5 if n_inter > 0 else 0.0
    peak_interpeak = round(am_tph / inter_tph, 2) if inter_tph > 0 else None

    return {
        "n_trips": n,
        "mean_headway_min": round(mean_h, 1),
        "median_headway_min": round(float(np.median(gaps)), 1),
        "max_headway_min": round(float(gaps.max()), 1),
        "cov_headway": round(std_h / mean_h, 3) if mean_h > 0 else None,
        "first_dep": first_dep,
        "last_dep": last_dep,
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

    Day type uses Phase 0 notebook 04b priority ordering: weekday > saturday > sunday.
    A trip that runs Mon-Sun is classified as 'weekday' (not multi-label).
    """
    with ZipFile(zip_path) as zf:
        with zf.open("calendar.txt") as f:
            calendar = pd.read_csv(f)

    cal = calendar.copy()
    cal["service_id"] = cal["service_id"].astype(str)

    is_weekday = cal[["monday", "tuesday", "wednesday", "thursday", "friday"]].any(axis=1)
    is_saturday = cal["saturday"].astype(bool)
    is_sunday = cal["sunday"].astype(bool)

    weekday_sids = set(cal[is_weekday]["service_id"])
    saturday_sids = set(cal[is_saturday]["service_id"])
    sunday_sids = set(cal[is_sunday]["service_id"])

    logger.info(
        "Calendar: {} weekday / {} saturday / {} sunday service_ids",
        len(weekday_sids), len(saturday_sids), len(sunday_sids),
    )

    # Trip → day_type (single-label, priority: weekday > saturday > sunday)
    svc = trips_df["service_id"].astype(str)
    trip_ids = trips_df["trip_id"].astype(str)

    day_type_col = pd.Series("other", index=trips_df.index)
    day_type_col[svc.isin(sunday_sids)] = "sunday"
    day_type_col[svc.isin(saturday_sids)] = "saturday"
    day_type_col[svc.isin(weekday_sids)] = "weekday"

    trip_to_day: dict[str, str] = dict(zip(trip_ids, day_type_col))
    typed_trip_ids = set(k for k, v in trip_to_day.items() if v != "other")

    logger.info("Streaming stop_times.txt for headway computation")
    stop_day_departures: dict[tuple[str, str], list[int]] = {}

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

                chunk = chunk[chunk["trip_id"].isin(typed_trip_ids)].copy()
                if chunk.empty:
                    continue

                parts = chunk["departure_time"].str.split(":", expand=True)
                chunk["dep_min"] = (
                    pd.to_numeric(parts[0], errors="coerce") * 60
                    + pd.to_numeric(parts[1], errors="coerce")
                )
                chunk["dep_min"] = chunk["dep_min"].fillna(-1).astype(int)
                chunk = chunk[chunk["dep_min"] >= 0]
                if chunk.empty:
                    continue

                chunk["day_type"] = chunk["trip_id"].map(trip_to_day)

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


def _build_bods_stop_lsoa(zip_path: Path, lsoa_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Spatial join BODS stops.txt → LSOAs (matches Phase 0 04b methodology)."""
    with ZipFile(zip_path) as zf:
        with zf.open("stops.txt") as f:
            bods_stops = pd.read_csv(f, usecols=["stop_id", "stop_lat", "stop_lon"],
                                     dtype={"stop_id": str})

    bods_stops = bods_stops[
        bods_stops["stop_lat"].between(49.8, 55.9) &
        bods_stops["stop_lon"].between(-6.5, 1.9)
    ].copy()

    stops_gdf = gpd.GeoDataFrame(
        bods_stops[["stop_id"]],
        geometry=gpd.points_from_xy(bods_stops["stop_lon"], bods_stops["stop_lat"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:27700")

    lsoa_27700 = lsoa_gdf.to_crs("EPSG:27700")
    joined = gpd.sjoin(
        stops_gdf[["stop_id", "geometry"]],
        lsoa_27700[["LSOA21CD", "geometry"]],
        how="left",
        predicate="within",
    )[["stop_id", "LSOA21CD"]].drop_duplicates(subset="stop_id")

    matched = joined["LSOA21CD"].notna().sum()
    logger.info("BODS stops → LSOA: {}/{} matched ({:.1f}%)",
                matched, len(stops_gdf), matched / len(stops_gdf) * 100)

    return joined.rename(columns={"LSOA21CD": "lsoa_code"})


def _aggregate_to_lsoa(
    stop_headways: pd.DataFrame,
    stops_with_lsoa: pd.DataFrame,
    lsoa_gdf: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Aggregate stop-level headways → LSOA-level quality metrics + SQI."""
    wd = stop_headways[stop_headways["day_type"] == "weekday"].copy()
    wd = wd.merge(stops_with_lsoa, on="stop_id", how="left")

    sun = (
        stop_headways[stop_headways["day_type"] == "sunday"][["stop_id", "n_trips"]]
        .rename(columns={"n_trips": "sunday_trips"})
    )
    wd = wd.merge(sun, on="stop_id", how="left")
    wd["sunday_trips"] = wd["sunday_trips"].fillna(0)

    lsoa_agg = (
        wd.dropna(subset=["lsoa_code"])
        .groupby("lsoa_code")
        .agg(
            n_stops_with_service=("stop_id", "count"),
            mean_headway_min=("mean_headway_min", "mean"),
            median_headway_min=("median_headway_min", "median"),
            cov_headway=("cov_headway", "mean"),
            first_service_min=("first_dep", "min"),
            last_service_min=("last_dep", "max"),
            total_weekday_departures=("n_trips", "sum"),
            total_sunday_departures=("sunday_trips", "sum"),
            n_stops_with_evening=("n_evening", lambda x: (x > 0).sum()),
            peak_interpeak_ratio=("peak_interpeak_ratio", "median"),
            span_min=("span_min", "mean"),
        )
        .reset_index()
    )

    all_lsoas = pd.DataFrame({"lsoa_code": lsoa_gdf["LSOA21CD"].values})
    lsoa_quality = all_lsoas.merge(lsoa_agg, on="lsoa_code", how="left")

    lsoa_quality["sqi"] = _compute_sqi(lsoa_quality)

    lsoa_quality["evening_isolated"] = (
        lsoa_quality["last_service_min"].isna()
        | (lsoa_quality["last_service_min"] < _EVENING_THRESHOLD)
    )
    lsoa_quality["night_isolated"] = (
        lsoa_quality["last_service_min"].isna()
        | (lsoa_quality["last_service_min"] < _NIGHT_THRESHOLD)
    )
    lsoa_quality["sunday_desert"] = (
        lsoa_quality["total_sunday_departures"].isna()
        | (lsoa_quality["total_sunday_departures"] == 0)
    )
    lsoa_quality["no_service"] = lsoa_quality["n_stops_with_service"].isna()

    return lsoa_quality.reset_index(drop=True)


def _compute_sqi(lsoa_df: pd.DataFrame) -> pd.Series:
    """Compute composite Service Quality Index (0-100) for each LSOA.

    Matches Phase 0 notebook 04b exactly:
    1. Headway score  (40%): 0 for no service; 100 - (mean_headway/60)*100 clipped [0,100]
    2. Span score     (20%): (last_service - first_service) / (18*60) * 100 clipped [0,100]
    3. Frequency score(20%): total_weekday_departures / 100 * 100 clipped [0,100]
    4. Evening score  (10%): 0 for no service; (last_dep - 18*60) / (4*60) * 100 clipped [0,100]
    5. Sunday score   (10%): 0 when no weekday; sunday/weekday * 200 clipped [0,100]
    """
    q = lsoa_df.copy()

    q["score_headway"] = np.where(
        q["mean_headway_min"].notna(),
        (100 - (q["mean_headway_min"] / 60) * 100).clip(0, 100),
        0.0,
    )

    service_span = (
        q["last_service_min"].fillna(0) - q["first_service_min"].fillna(0)
    ).clip(lower=0)
    q["score_span"] = (service_span / (18 * 60) * 100).clip(0, 100)

    q["score_frequency"] = (q["total_weekday_departures"].fillna(0) / 100 * 100).clip(0, 100)

    q["score_evening"] = np.where(
        q["last_service_min"].notna(),
        ((q["last_service_min"] - 18 * 60) / (4 * 60) * 100).clip(0, 100),
        0.0,
    )

    q["score_sunday"] = np.where(
        q["total_weekday_departures"].fillna(0) > 0,
        (q["total_sunday_departures"].fillna(0) / q["total_weekday_departures"].fillna(1) * 200).clip(0, 100),
        0.0,
    )

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

    Fast path: loads Phase 0 audit Parquets (stop_headways.parquet) and
    re-aggregates to LSOA level. Takes seconds, not 90 minutes.

    Full path (fallback): streams raw GTFS stop_times.txt when audit
    Parquets don't exist.

    Returns DataFrame with 33,755 rows (all England LSOAs).
    """
    zip_path = cfg.raw_dir / "bods" / "bods_gtfs_all.zip"
    audit_headways = cfg.audit_dir / "stop_headways.parquet"

    # Fast path: use pre-computed Phase 0 stop headways
    if audit_headways.exists():
        logger.info("Loading pre-computed stop headways from {}", audit_headways)
        stop_headways = pd.read_parquet(audit_headways)
    else:
        logger.info("No audit stop_headways found — streaming from raw GTFS (slow)")
        with ZipFile(zip_path) as zf:
            with zf.open("trips.txt") as f:
                trips_df = pd.read_csv(f, low_memory=False, usecols=["trip_id", "service_id"])
        stop_headways = _stream_stop_times(zip_path, trips_df, chunk_size=cfg.stop_times_chunk_size)

    # Spatial join BODS stops → LSOAs
    logger.info("Assigning stops to LSOAs for service quality aggregation")
    lsoa_gdf = load_lsoa_boundaries(cfg.raw_dir / "boundaries")
    stops_with_lsoa = _build_bods_stop_lsoa(zip_path, lsoa_gdf)

    # Aggregate to LSOA level
    lsoa_quality = _aggregate_to_lsoa(stop_headways, stops_with_lsoa, lsoa_gdf)

    n_eve = int(lsoa_quality["evening_isolated"].sum())
    n_sun = int(lsoa_quality["sunday_desert"].sum())
    mean_sqi = float(lsoa_quality["sqi"].mean())
    logger.info(
        "Service quality: {} LSOAs, mean SQI={:.1f}, evening_isolated={}, sunday_desert={}",
        len(lsoa_quality), mean_sqi, n_eve, n_sun,
    )
    return lsoa_quality
