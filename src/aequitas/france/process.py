"""Join NAP stops to IRIS; 400 m; evening; Sunday; F-EDI; INSEE density."""

from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.france.constants import (
    ALL_PT_ROUTE_TYPES,
    BUS_ROUTE_TYPES,
    EVENING_START_MIN,
    FR_BBOX,
    LAMBERT93,
    URBAN_DENSITY_MAX,
    in_fr_bbox,
    iris_text,
)

WALK_M = 400.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def clip_fr_stops(stops: pd.DataFrame) -> pd.DataFrame:
    lat = pd.to_numeric(stops["stop_lat"], errors="coerce")
    lon = pd.to_numeric(stops["stop_lon"], errors="coerce")
    keep = []
    for la, lo in zip(lat.tolist(), lon.tolist(), strict=True):
        if la is None or lo is None or (isinstance(la, float) and math.isnan(la)):
            keep.append(False)
            continue
        keep.append(in_fr_bbox(float(la), float(lo)))
    out = stops.loc[np.asarray(keep)].copy()
    out["stop_lat"] = pd.to_numeric(out["stop_lat"], errors="coerce")
    out["stop_lon"] = pd.to_numeric(out["stop_lon"], errors="coerce")
    logger.info("FR stops: {} / {} (DOM / out-of-bbox dropped)", len(out), len(stops))
    return out


def _hhmmss_to_min(value: object) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    parts = text.split(":")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        return None


def _l93_xy(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    try:
        from pyproj import Transformer

        t = Transformer.from_crs("EPSG:4326", LAMBERT93, always_xy=True)
        x, y = t.transform(lon, lat)
        return np.column_stack([np.asarray(x), np.asarray(y)])
    except Exception:  # noqa: BLE001
        mean_lat = float(np.nanmean(lat)) if len(lat) else 46.5
        kx = 111_320.0 * math.cos(math.radians(mean_lat))
        return np.column_stack([np.asarray(lon) * kx, np.asarray(lat) * 110_540.0])


def _service_flags_from_calendar(zf: ZipFile, names: dict[str, str]) -> pd.DataFrame | None:
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
    if cal is None and cal_dates is None:
        return None
    rows = []
    if cal is not None and "service_id" in cal.columns:
        for col in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            if col in cal.columns:
                cal[col] = pd.to_numeric(cal[col], errors="coerce").fillna(0).astype(int)
            else:
                cal[col] = 0
        rows.append(cal[["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]])
    flags = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["service_id"])
    if cal_dates is not None and not cal_dates.empty:
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
        if flags.empty:
            flags = by_svc.reset_index()
        else:
            flags["service_id"] = flags["service_id"].astype(str)
            flags = flags.merge(by_svc, left_on="service_id", right_index=True, how="outer", suffixes=("", "_cd"))
            for col in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
                alt = f"{col}_cd"
                if alt in flags.columns:
                    base = pd.to_numeric(flags[col], errors="coerce").fillna(0) if col in flags.columns else 0
                    flags[col] = (base + pd.to_numeric(flags[alt], errors="coerce").fillna(0)).clip(0, 1).astype(int)
                    flags.drop(columns=[alt], inplace=True)
    return flags


def harvest_one_gtfs(zip_path: Path, prefix: str, *, mode: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Stops + per-stop service for one NAP zip. Calendar may be dates-only."""
    allowed = BUS_ROUTE_TYPES if mode == "bus" else ALL_PT_ROUTE_TYPES
    empty_stops = pd.DataFrame(columns=["stop_id", "stop_lat", "stop_lon"])
    empty_svc = pd.DataFrame(columns=["stop_id", "weekday", "evening", "sunday"])
    meta = {"agencies": [], "n_routes": 0, "prefix": prefix}
    try:
        with ZipFile(zip_path) as zf:
            names = {Path(n).name.lower(): n for n in zf.namelist()}
            if "stops.txt" not in names or "routes.txt" not in names:
                return empty_stops, empty_svc, meta
            stops = pd.read_csv(BytesIO(zf.read(names["stops.txt"])), dtype=str, low_memory=False)
            routes = pd.read_csv(BytesIO(zf.read(names["routes.txt"])), dtype=str)
            if "stop_lat" not in stops.columns or "stop_id" not in stops.columns:
                return empty_stops, empty_svc, meta
            routes["route_type"] = pd.to_numeric(routes.get("route_type"), errors="coerce")
            keep_routes = set(routes.loc[routes["route_type"].isin(allowed), "route_id"].astype(str))
            if not keep_routes:
                return empty_stops, empty_svc, meta
            trips = None
            if "trips.txt" in names:
                trips = pd.read_csv(
                    BytesIO(zf.read(names["trips.txt"])),
                    dtype=str,
                    usecols=lambda c: c in {"trip_id", "route_id", "service_id"},
                )
                trips = trips[trips["route_id"].astype(str).isin(keep_routes)]
            flags = _service_flags_from_calendar(zf, names)
            trip_flags = None
            if trips is not None and flags is not None and not flags.empty and "service_id" in trips.columns:
                trip_flags = trips.merge(flags, on="service_id", how="left")
                for col in ("monday", "tuesday", "wednesday", "thursday", "friday", "sunday"):
                    if col not in trip_flags.columns:
                        trip_flags[col] = np.nan
                wd = (
                    pd.to_numeric(trip_flags["monday"], errors="coerce").fillna(0)
                    + pd.to_numeric(trip_flags["tuesday"], errors="coerce").fillna(0)
                    + pd.to_numeric(trip_flags["wednesday"], errors="coerce").fillna(0)
                    + pd.to_numeric(trip_flags["thursday"], errors="coerce").fillna(0)
                    + pd.to_numeric(trip_flags["friday"], errors="coerce").fillna(0)
                ) > 0
                trip_flags = pd.DataFrame(
                    {
                        "trip_id": trip_flags["trip_id"].astype(str),
                        "is_weekday": wd.astype(int),
                        "is_sunday": pd.to_numeric(trip_flags["sunday"], errors="coerce").fillna(0).gt(0).astype(int),
                    }
                ).drop_duplicates("trip_id")
            used: set[str] = set()
            acc: dict[str, list[int]] = {}
            if "stop_times.txt" in names:
                with zf.open(names["stop_times.txt"]) as fh:
                    keep_trips = set(trips["trip_id"].astype(str)) if trips is not None else None
                    flag_map = (
                        trip_flags.set_index("trip_id") if trip_flags is not None and not trip_flags.empty else None
                    )
                    for chunk in pd.read_csv(
                        fh,
                        dtype=str,
                        usecols=lambda c: c in {"trip_id", "stop_id", "departure_time"},
                        chunksize=400_000,
                    ):
                        chunk["trip_id"] = chunk["trip_id"].astype(str)
                        if keep_trips is not None:
                            chunk = chunk[chunk["trip_id"].isin(keep_trips)]
                        used.update(chunk["stop_id"].astype(str))
                        if flag_map is not None:
                            chunk = chunk.join(flag_map, on="trip_id")
                            if "is_weekday" not in chunk.columns:
                                continue
                            mins = chunk["departure_time"].map(_hhmmss_to_min) if "departure_time" in chunk else None
                            eve = (
                                pd.to_numeric(mins, errors="coerce").ge(EVENING_START_MIN).fillna(False).astype(int)
                                if mins is not None
                                else 0
                            )
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
            stops = stops[stops["stop_id"].astype(str).isin(used)] if used else stops
            stops["stop_id"] = prefix + ":" + stops["stop_id"].astype(str)
            stops = clip_fr_stops(stops)
            svc = pd.DataFrame(
                [(prefix + ":" + k, v[0], v[1], v[2]) for k, v in acc.items()],
                columns=["stop_id", "weekday", "evening", "sunday"],
            )
            if "agency.txt" in names:
                ag = pd.read_csv(BytesIO(zf.read(names["agency.txt"])), dtype=str)
                name_col = "agency_name" if "agency_name" in ag.columns else "agency_id"
                meta["agencies"] = [
                    {"name": str(n), "agency_id": prefix + ":" + str(i), "n_routes": 1}
                    for i, n in zip(ag.get("agency_id", ag.index).astype(str), ag[name_col].astype(str))
                ]
            meta["n_routes"] = int(len(keep_routes))
            return stops, svc, meta
    except Exception as exc:  # noqa: BLE001
        logger.warning("GTFS unreadable {}: {}", zip_path.name, exc)
        return empty_stops, empty_svc, meta


def merge_nap_feeds(gtfs_dir: Path, *, mode: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    zips = sorted(gtfs_dir.glob("*.zip"))
    stop_frames: list[pd.DataFrame] = []
    svc_frames: list[pd.DataFrame] = []
    agencies: list[dict] = []
    n_routes = 0
    for zp in zips:
        prefix = zp.stem
        stops, svc, meta = harvest_one_gtfs(zp, prefix, mode=mode)
        if not stops.empty:
            stop_frames.append(stops)
        if not svc.empty:
            svc_frames.append(svc)
        agencies.extend(meta.get("agencies") or [])
        n_routes += int(meta.get("n_routes") or 0)
    stops = pd.concat(stop_frames, ignore_index=True) if stop_frames else pd.DataFrame(
        columns=["stop_id", "stop_lat", "stop_lon"]
    )
    svc = pd.concat(svc_frames, ignore_index=True) if svc_frames else pd.DataFrame(
        columns=["stop_id", "weekday", "evening", "sunday"]
    )
    # HHI on agency route counts (each feed agency counted once; routes summed later in network.py)
    extras = {"agencies": agencies, "n_routes": n_routes, "n_feeds": len(zips), "mode": mode}
    logger.info("NAP merge {}: {} stops, {} service rows, {} feeds", mode, len(stops), len(svc), len(zips))
    return stops, svc, extras


def join_iris_stops(areas: pd.DataFrame, stops: pd.DataFrame, *, walk_m: float = WALK_M) -> pd.DataFrame:
    out = areas.copy()
    if stops.empty:
        out["stop_count"] = 0
        out["nearest_stop_m"] = np.nan
        out["within_400m"] = False
        return out
    sa_xy = _l93_xy(out["lat"].astype(float).to_numpy(), out["lon"].astype(float).to_numpy())
    st_xy = _l93_xy(stops["stop_lat"].astype(float).to_numpy(), stops["stop_lon"].astype(float).to_numpy())
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
        sa_xy = _l93_xy(out["lat"].astype(float).to_numpy(), out["lon"].astype(float).to_numpy())
        st_xy = _l93_xy(per_stop["stop_lat"].astype(float).to_numpy(), per_stop["stop_lon"].astype(float).to_numpy())
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


def assign_urban_rural(areas: pd.DataFrame) -> pd.DataFrame:
    out = areas.copy()
    dens = pd.to_numeric(out.get("density_level"), errors="coerce")
    out["urban_rural"] = np.where(dens.le(URBAN_DENSITY_MAX), "urban", "rural")
    out.loc[dens.isna(), "urban_rural"] = "rural"
    return out


def fedi_decile_from_score(series: pd.Series) -> pd.Series:
    """Higher EDI = more deprived. Decile 1 = most deprived. Null stays null."""
    out = pd.Series(np.nan, index=series.index, dtype="float")
    valid = pd.to_numeric(series, errors="coerce").notna()
    if int(valid.sum()) < 10:
        return out
    ranks = series.loc[valid].rank(method="average", ascending=False)
    out.loc[valid] = pd.qcut(ranks, 10, labels=False, duplicates="drop") + 1
    return out


def build_fr_areas(
    *,
    areas: pd.DataFrame,
    stops: pd.DataFrame,
    stop_times: pd.DataFrame | None = None,
) -> pd.DataFrame:
    need = {"iris_code", "lat", "lon", "population"}
    missing = need - set(areas.columns)
    if missing:
        raise ValueError(f"areas missing {missing}")
    joined = join_iris_stops(areas, stops)
    joined = attach_service_flags(joined, stop_times, stops)
    if "fedi_score" in joined.columns:
        joined["fedi_decile"] = fedi_decile_from_score(joined["fedi_score"])
    else:
        joined["fedi_decile"] = np.nan
        joined["fedi_score"] = np.nan
    if "region" not in joined.columns:
        joined["region"] = "unknown"
    if "name" not in joined.columns:
        joined["name"] = joined["iris_code"].astype(str)
    joined = assign_urban_rural(joined)
    joined["trips_per_capita"] = joined["weekday_trips"].astype(float) / joined["population"].replace(0, np.nan)
    joined["trips_per_capita"] = joined["trips_per_capita"].fillna(0.0)
    joined["stops_per_1k"] = joined["stop_count"].astype(float) / joined["population"].replace(0, np.nan) * 1000.0
    joined["stops_per_1k"] = joined["stops_per_1k"].replace([np.inf, -np.inf], 0).fillna(0.0)
    # warehouse reuse only — UI says F-EDI
    joined["imd_decile"] = joined["fedi_decile"]
    joined["imd_score"] = joined["fedi_score"]
    joined["hp_decile"] = joined["fedi_decile"]
    joined["hp_relative"] = joined["fedi_score"]
    joined["ses_decile"] = joined["fedi_decile"]
    joined["ses_score"] = joined["fedi_score"]
    joined["lsoa_code"] = joined["iris_code"]
    joined["sa_code"] = joined["iris_code"]
    joined["sfca_score_norm"] = np.where(joined["within_400m"], 1.0, 0.0)
    return joined


def write_processed(areas: pd.DataFrame, processed_dir: Path, *, mode: str) -> dict[str, Path]:
    fr = processed_dir / "france"
    fr.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    demo = fr / f"iris_table_{mode}.parquet"
    areas.to_parquet(demo, index=False)
    paths["iris_table"] = demo
    if mode == "bus":
        areas.to_parquet(fr / "iris_table.parquet", index=False)
        cents = fr / "iris_centroids.parquet"
        areas[["iris_code", "lat", "lon", "population", "fedi_decile", "region", "name"]].rename(
            columns={"iris_code": "area", "population": "pop", "fedi_decile": "imd_decile"}
        ).to_parquet(cents, index=False)
        paths["centroids"] = cents
    return paths
