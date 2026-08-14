"""Join OVapi stops to CBS buurten; 400 m; evening; Sunday; SES-WOA; stedelijkheid."""

from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.netherlands.constants import (
    ALL_PT_ROUTE_TYPES,
    BUS_ROUTE_TYPES,
    EVENING_START_MIN,
    NL_BBOX,
    RDNEW,
    URBAN_STEDELIJKHEID_MAX,
    in_nl_bbox,
    slug_province,
)

WALK_M = 400.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def clip_nl_stops(stops: pd.DataFrame) -> pd.DataFrame:
    """Drop BE/DE / out-of-bbox stops. Requires stop_lat, stop_lon."""
    lat = pd.to_numeric(stops["stop_lat"], errors="coerce")
    lon = pd.to_numeric(stops["stop_lon"], errors="coerce")
    keep = []
    for la, lo in zip(lat.tolist(), lon.tolist(), strict=True):
        if la is None or lo is None or (isinstance(la, float) and math.isnan(la)):
            keep.append(False)
            continue
        keep.append(in_nl_bbox(float(la), float(lo)))
    out = stops.loc[np.asarray(keep)].copy()
    out["stop_lat"] = pd.to_numeric(out["stop_lat"], errors="coerce")
    out["stop_lon"] = pd.to_numeric(out["stop_lon"], errors="coerce")
    logger.info("NL stops: {} / {} (BE/DE / out-of-bbox dropped)", len(out), len(stops))
    return out


def _route_types(gtfs_zip: Path) -> pd.DataFrame:
    with ZipFile(gtfs_zip) as zf:
        names = {Path(n).name.lower(): n for n in zf.namelist()}
        routes = pd.read_csv(BytesIO(zf.read(names["routes.txt"])), dtype=str)
    routes["route_type"] = pd.to_numeric(routes.get("route_type"), errors="coerce")
    return routes


def load_ovapi_stops(gtfs_zip: Path, *, mode: str = "bus") -> pd.DataFrame:
    """Stops used by `mode` (`bus` or `all`) inside the Netherlands bbox."""
    with ZipFile(gtfs_zip) as zf:
        names = {Path(n).name.lower(): n for n in zf.namelist()}
        stops = pd.read_csv(BytesIO(zf.read(names["stops.txt"])))
        trips = pd.read_csv(
            BytesIO(zf.read(names["trips.txt"])),
            dtype=str,
            usecols=lambda c: c in {"trip_id", "route_id"},
        )
        routes = pd.read_csv(BytesIO(zf.read(names["routes.txt"])), dtype=str)
    need = {"stop_id", "stop_lat", "stop_lon"}
    missing = need - set(stops.columns)
    if missing:
        raise ValueError(f"OVapi stops.txt missing {missing}")
    allowed = BUS_ROUTE_TYPES if mode == "bus" else ALL_PT_ROUTE_TYPES
    routes["route_type"] = pd.to_numeric(routes.get("route_type"), errors="coerce")
    keep_routes = set(routes.loc[routes["route_type"].isin(allowed), "route_id"].astype(str))
    trip_ids = set(trips.loc[trips["route_id"].astype(str).isin(keep_routes), "trip_id"].astype(str))
    # stop_times can be huge — stream just stop_id + trip_id
    used: set[str] = set()
    with ZipFile(gtfs_zip) as zf:
        names = {Path(n).name.lower(): n for n in zf.namelist()}
        with zf.open(names["stop_times.txt"]) as fh:
            for chunk in pd.read_csv(
                fh, dtype=str, usecols=lambda c: c in {"trip_id", "stop_id"}, chunksize=500_000
            ):
                hit = chunk["trip_id"].astype(str).isin(trip_ids)
                used.update(chunk.loc[hit, "stop_id"].astype(str))
    stops["stop_id"] = stops["stop_id"].astype(str)
    stops = stops[stops["stop_id"].isin(used)]
    return clip_nl_stops(stops)


def load_ovapi_stop_times(gtfs_zip: Path, *, mode: str = "bus") -> pd.DataFrame:
    cache = gtfs_zip.parent / f"stop_service_{mode}.parquet"
    if cache.exists() and cache.stat().st_mtime >= gtfs_zip.stat().st_mtime:
        logger.info("Using cached OVapi stop service {}", cache.name)
        return pd.read_parquet(cache)
    with ZipFile(gtfs_zip) as zf:
        names = {Path(n).name.lower(): n for n in zf.namelist()}
        trips = pd.read_csv(
            BytesIO(zf.read(names["trips.txt"])),
            dtype=str,
            usecols=lambda c: c in {"trip_id", "service_id", "route_id"},
        )
        routes = pd.read_csv(BytesIO(zf.read(names["routes.txt"])), dtype=str)
        cal = None
        cal_dates = None
        if "calendar.txt" in names:
            cal = pd.read_csv(BytesIO(zf.read(names["calendar.txt"])), dtype=str)
        if "calendar_dates.txt" in names:
            cal_dates = pd.read_csv(
                BytesIO(zf.read(names["calendar_dates.txt"])),
                dtype=str,
                usecols=lambda c: c in {"service_id", "date", "exception_type"},
            )
    allowed = BUS_ROUTE_TYPES if mode == "bus" else ALL_PT_ROUTE_TYPES
    routes["route_type"] = pd.to_numeric(routes.get("route_type"), errors="coerce")
    keep_routes = set(routes.loc[routes["route_type"].isin(allowed), "route_id"].astype(str))
    trips = trips[trips["route_id"].astype(str).isin(keep_routes)]
    trip_cal = trips[["trip_id", "service_id"]].copy()
    if cal is not None and "service_id" in cal.columns:
        for col in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            if col in cal.columns:
                cal[col] = pd.to_numeric(cal[col], errors="coerce").fillna(0).astype(int)
        trip_cal = trip_cal.merge(cal, on="service_id", how="left")
    if cal_dates is not None and not cal_dates.empty:
        # OVapi publishes calendar_dates only (no calendar.txt). exception_type 1 = service added.
        cd = cal_dates.copy()
        cd["exception_type"] = pd.to_numeric(cd["exception_type"], errors="coerce").fillna(1).astype(int)
        cd = cd[cd["exception_type"] == 1]
        cd["date"] = pd.to_datetime(cd["date"], format="%Y%m%d", errors="coerce")
        cd = cd.dropna(subset=["date"])
        cd["dow"] = cd["date"].dt.dayofweek
        by_svc = cd.groupby(cd["service_id"].astype(str))["dow"].agg(
            monday=lambda s: int((s == 0).any()),
            tuesday=lambda s: int((s == 1).any()),
            wednesday=lambda s: int((s == 2).any()),
            thursday=lambda s: int((s == 3).any()),
            friday=lambda s: int((s == 4).any()),
            saturday=lambda s: int((s == 5).any()),
            sunday=lambda s: int((s == 6).any()),
        )
        trip_cal["service_id"] = trip_cal["service_id"].astype(str)
        trip_cal = trip_cal.merge(by_svc, left_on="service_id", right_index=True, how="left", suffixes=("", "_cd"))
        for col in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            alt = f"{col}_cd"
            if alt in trip_cal.columns:
                base = pd.to_numeric(trip_cal[col], errors="coerce").fillna(0) if col in trip_cal.columns else 0
                trip_cal[col] = (base + pd.to_numeric(trip_cal[alt], errors="coerce").fillna(0)).clip(0, 1).astype(int)
                trip_cal.drop(columns=[alt], inplace=True)
    if "sunday" not in trip_cal.columns:
        trip_cal["sunday"] = 0
    if "monday" not in trip_cal.columns:
        trip_cal["monday"] = 1
    def _day(name: str) -> pd.Series:
        if name in trip_cal.columns:
            return pd.to_numeric(trip_cal[name], errors="coerce").fillna(0)
        return pd.Series(0, index=trip_cal.index)

    weekday_svc = (_day("monday") + _day("tuesday") + _day("wednesday") + _day("thursday") + _day("friday")) > 0
    flags = pd.DataFrame(
        {
            "trip_id": trip_cal["trip_id"].astype(str),
            "is_weekday": weekday_svc.astype(int),
            "is_sunday": _day("sunday").gt(0).astype(int),
        }
    )
    flag_map = flags.drop_duplicates("trip_id").set_index("trip_id")
    acc: dict[str, list[int]] = {}
    read = 0
    with ZipFile(gtfs_zip) as zf:
        names = {Path(n).name.lower(): n for n in zf.namelist()}
        with zf.open(names["stop_times.txt"]) as fh:
            for chunk in pd.read_csv(
                fh,
                dtype=str,
                usecols=lambda c: c in {"trip_id", "stop_id", "departure_time"},
                chunksize=400_000,
            ):
                chunk["trip_id"] = chunk["trip_id"].astype(str)
                chunk = chunk.join(flag_map, on="trip_id")
                if "is_weekday" not in chunk.columns:
                    continue
                chunk = chunk.dropna(subset=["is_weekday"])
                mins = chunk["departure_time"].map(_hhmmss_to_min)
                eve = pd.to_numeric(mins, errors="coerce").ge(EVENING_START_MIN).fillna(False).astype(int)
                g = chunk.assign(evening=eve).groupby("stop_id", sort=False)[
                    ["is_weekday", "evening", "is_sunday"]
                ].sum()
                for sid, row in g.iterrows():
                    cur = acc.get(str(sid))
                    if cur is None:
                        acc[str(sid)] = [int(row["is_weekday"]), int(row["evening"]), int(row["is_sunday"])]
                    else:
                        cur[0] += int(row["is_weekday"])
                        cur[1] += int(row["evening"])
                        cur[2] += int(row["is_sunday"])
                read += len(chunk)
                logger.info("OVapi stop_times ({}) aggregated {:,} rows / {} stops", mode, read, len(acc))
    out = pd.DataFrame(
        [(k, v[0], v[1], v[2]) for k, v in acc.items()],
        columns=["stop_id", "weekday", "evening", "sunday"],
    )
    logger.info("OVapi per-stop service rows ({}): {}", mode, len(out))
    try:
        out.to_parquet(cache, index=False)
    except Exception:  # noqa: BLE001
        pass
    return out


def _hhmmss_to_min(value: object) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    parts = text.split(":")
    if len(parts) < 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
        return h * 60 + m
    except ValueError:
        return None


def _rd_xy(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    try:
        from pyproj import Transformer

        t = Transformer.from_crs("EPSG:4326", RDNEW, always_xy=True)
        x, y = t.transform(lon, lat)
        return np.column_stack([np.asarray(x), np.asarray(y)])
    except Exception:  # noqa: BLE001
        mean_lat = float(np.nanmean(lat)) if len(lat) else 52.1
        kx = 111_320.0 * math.cos(math.radians(mean_lat))
        return np.column_stack([np.asarray(lon) * kx, np.asarray(lat) * 110_540.0])


def join_buurt_stops(areas: pd.DataFrame, stops: pd.DataFrame, *, walk_m: float = WALK_M) -> pd.DataFrame:
    out = areas.copy()
    if stops.empty:
        out["stop_count"] = 0
        out["nearest_stop_m"] = np.nan
        out["within_400m"] = False
        return out
    sa_xy = _rd_xy(out["lat"].astype(float).to_numpy(), out["lon"].astype(float).to_numpy())
    st_xy = _rd_xy(stops["stop_lat"].astype(float).to_numpy(), stops["stop_lon"].astype(float).to_numpy())
    valid = np.isfinite(st_xy).all(axis=1)
    st_xy = st_xy[valid]
    from scipy.spatial import cKDTree

    tree = cKDTree(st_xy)
    counts = tree.query_ball_point(sa_xy, r=walk_m, return_length=True)
    dist, _ = tree.query(sa_xy, k=1)
    out["stop_count"] = np.asarray(counts, dtype=int)
    out["nearest_stop_m"] = np.asarray(dist, dtype=float)
    out["within_400m"] = out["stop_count"] > 0
    return out


def attach_service_flags(
    areas: pd.DataFrame,
    stop_times: pd.DataFrame | None,
    stops: pd.DataFrame,
) -> pd.DataFrame:
    out = areas.copy()
    if stop_times is None or stop_times.empty or stops.empty:
        out["weekday_trips"] = 0
        out["evening_trips"] = 0
        out["sunday_trips"] = 0
        out["evening_isolated"] = True
        out["sunday_desert"] = True
        out["no_service"] = True
        out["sqi"] = 0.0
        return out
    st = stop_times.copy()
    st["stop_id"] = st["stop_id"].astype(str)
    per_stop = st.groupby("stop_id", as_index=False)[["weekday", "evening", "sunday"]].sum()
    stop_xy = stops[["stop_id", "stop_lat", "stop_lon"]].copy()
    stop_xy["stop_id"] = stop_xy["stop_id"].astype(str)
    per_stop = per_stop.merge(stop_xy, on="stop_id", how="left").dropna(subset=["stop_lat", "stop_lon"])
    if per_stop.empty:
        out["weekday_trips"] = 0
        out["evening_trips"] = 0
        out["sunday_trips"] = 0
    else:
        sa_xy = _rd_xy(out["lat"].astype(float).to_numpy(), out["lon"].astype(float).to_numpy())
        st_xy = _rd_xy(per_stop["stop_lat"].astype(float).to_numpy(), per_stop["stop_lon"].astype(float).to_numpy())
        from scipy.spatial import cKDTree

        tree = cKDTree(st_xy)
        neigh = tree.query_ball_point(sa_xy, r=WALK_M)
        wd = per_stop["weekday"].to_numpy()
        ev = per_stop["evening"].to_numpy()
        su = per_stop["sunday"].to_numpy()
        out["weekday_trips"] = [int(wd[ix].sum()) if ix else 0 for ix in neigh]
        out["evening_trips"] = [int(ev[ix].sum()) if ix else 0 for ix in neigh]
        out["sunday_trips"] = [int(su[ix].sum()) if ix else 0 for ix in neigh]
    out["no_service"] = out["weekday_trips"].eq(0)
    out["evening_isolated"] = out["evening_trips"].eq(0)
    out["sunday_desert"] = out["sunday_trips"].eq(0)
    mx = max(float(out["weekday_trips"].max()), 1.0)
    out["sqi"] = (np.log1p(out["weekday_trips"].astype(float)) / math.log1p(mx) * 100.0).clip(0, 100)
    return out


def assign_stedelijkheid(areas: pd.DataFrame) -> pd.DataFrame:
    out = areas.copy()
    sted = pd.to_numeric(out.get("stedelijkheid"), errors="coerce")
    out["urban_rural"] = np.where(sted.le(URBAN_STEDELIJKHEID_MAX), "urban", "rural")
    out.loc[sted.isna(), "urban_rural"] = "rural"
    return out


def ses_decile_from_score(series: pd.Series) -> pd.Series:
    """Higher SES-WOA = more advantaged. Decile 1 = lowest SES. Null SES stays null."""
    out = pd.Series(np.nan, index=series.index, dtype="float")
    valid = pd.to_numeric(series, errors="coerce").notna()
    if int(valid.sum()) < 10:
        return out
    ranks = series.loc[valid].rank(method="average", ascending=True)
    out.loc[valid] = pd.qcut(ranks, 10, labels=False, duplicates="drop") + 1
    return out


def build_nl_areas(
    *,
    areas: pd.DataFrame,
    stops: pd.DataFrame,
    stop_times: pd.DataFrame | None = None,
) -> pd.DataFrame:
    need = {"buurt_code", "lat", "lon", "population"}
    missing = need - set(areas.columns)
    if missing:
        raise ValueError(f"areas missing {missing}")
    joined = join_buurt_stops(areas, stops)
    joined = attach_service_flags(joined, stop_times, stops)
    if "ses_score" in joined.columns:
        joined["ses_decile"] = ses_decile_from_score(joined["ses_score"])
    else:
        joined["ses_decile"] = np.nan
        joined["ses_score"] = np.nan
    if "region" not in joined.columns:
        joined["region"] = "utrecht"
    if "name" not in joined.columns:
        joined["name"] = joined["buurt_code"].astype(str)
    joined = assign_stedelijkheid(joined)
    joined["trips_per_capita"] = joined["weekday_trips"].astype(float) / joined["population"].replace(0, np.nan)
    joined["trips_per_capita"] = joined["trips_per_capita"].fillna(0.0)
    joined["stops_per_1k"] = joined["stop_count"].astype(float) / joined["population"].replace(0, np.nan) * 1000.0
    joined["stops_per_1k"] = joined["stops_per_1k"].replace([np.inf, -np.inf], 0).fillna(0.0)
    # warehouse reuse only — UI says SES-WOA
    joined["imd_decile"] = joined["ses_decile"]
    joined["imd_score"] = joined["ses_score"]
    joined["hp_decile"] = joined["ses_decile"]
    joined["hp_relative"] = joined["ses_score"]
    joined["lsoa_code"] = joined["buurt_code"]
    joined["sa_code"] = joined["buurt_code"]
    joined["sfca_score_norm"] = np.where(joined["within_400m"], 1.0, 0.0)
    return joined


def write_processed(areas: pd.DataFrame, processed_dir: Path, *, mode: str) -> dict[str, Path]:
    nl = processed_dir / "netherlands"
    nl.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    demo = nl / f"buurt_table_{mode}.parquet"
    areas.to_parquet(demo, index=False)
    paths["buurt_table"] = demo
    if mode == "bus":
        areas.to_parquet(nl / "buurt_table.parquet", index=False)
        cents = nl / "buurt_centroids.parquet"
        areas[["buurt_code", "lat", "lon", "population", "ses_decile", "region", "name"]].rename(
            columns={"buurt_code": "area", "population": "pop", "ses_decile": "imd_decile"}
        ).to_parquet(cents, index=False)
        paths["centroids"] = cents
    return paths
