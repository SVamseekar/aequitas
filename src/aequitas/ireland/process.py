"""Join TFI stops to Republic Small Areas; 400 m, evening, Sunday, SQI analogue."""

from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.ireland.constants import (
    COUNTY_NAME_BY_SLUG,
    EVENING_START_MIN,
    URBAN_DENSITY_PER_KM2,
    in_ireland_bbox,
    in_northern_ireland,
    slug_county,
)

# Same 400 m walk as England.
WALK_M = 400.0
# ITM / Irish Transverse Mercator
ITM = "EPSG:2157"


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def clip_republic_stops(stops: pd.DataFrame) -> pd.DataFrame:
    """Drop NI / out-of-bbox stops. Requires stop_lat, stop_lon."""
    lat = pd.to_numeric(stops["stop_lat"], errors="coerce")
    lon = pd.to_numeric(stops["stop_lon"], errors="coerce")
    keep = []
    for la, lo in zip(lat.tolist(), lon.tolist(), strict=True):
        if la is None or lo is None or (isinstance(la, float) and math.isnan(la)):
            keep.append(False)
            continue
        la_f, lo_f = float(la), float(lo)
        if in_northern_ireland(la_f, lo_f):
            keep.append(False)
            continue
        keep.append(in_ireland_bbox(la_f, lo_f))
    out = stops.loc[np.asarray(keep)].copy()
    out["stop_lat"] = pd.to_numeric(out["stop_lat"], errors="coerce")
    out["stop_lon"] = pd.to_numeric(out["stop_lon"], errors="coerce")
    logger.info("Republic stops: {} / {} (NI / out-of-bbox dropped)", len(out), len(stops))
    return out


def load_tfi_stops(gtfs_zip: Path) -> pd.DataFrame:
    with ZipFile(gtfs_zip) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith("stops.txt"))
        df = pd.read_csv(BytesIO(zf.read(name)))
    need = {"stop_id", "stop_lat", "stop_lon"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"TFI stops.txt missing {missing}")
    if "stop_name" not in df.columns:
        df["stop_name"] = df["stop_id"].astype(str)
    return clip_republic_stops(df)


def load_tfi_stop_times_sample(gtfs_zip: Path, *, max_rows: int | None = None) -> pd.DataFrame:
    """Per-stop weekday / evening / Sunday departure counts from TFI stop_times.

    Aggregates in chunks so the 300+ MB stop_times.txt is never fully in RAM.
    """
    with ZipFile(gtfs_zip) as zf:
        names = {Path(n).name.lower(): n for n in zf.namelist()}
        trips = pd.read_csv(
            BytesIO(zf.read(names["trips.txt"])),
            dtype=str,
            usecols=lambda c: c in {"trip_id", "service_id", "route_id"},
        )
        cal = None
        if "calendar.txt" in names:
            cal = pd.read_csv(BytesIO(zf.read(names["calendar.txt"])), dtype=str)
        trip_cal = trips[["trip_id", "service_id"]].copy()
        if cal is not None and "service_id" in cal.columns:
            for col in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
                if col in cal.columns:
                    cal[col] = pd.to_numeric(cal[col], errors="coerce").fillna(0).astype(int)
            trip_cal = trip_cal.merge(cal, on="service_id", how="left")
        else:
            trip_cal["monday"] = 1
            trip_cal["sunday"] = 0
        weekday_svc = (
            trip_cal.get("monday", 0).fillna(0).astype(float)
            + trip_cal.get("tuesday", 0).fillna(0).astype(float)
            + trip_cal.get("wednesday", 0).fillna(0).astype(float)
            + trip_cal.get("thursday", 0).fillna(0).astype(float)
            + trip_cal.get("friday", 0).fillna(0).astype(float)
        ) > 0
        flags = pd.DataFrame(
            {
                "trip_id": trip_cal["trip_id"].astype(str),
                "is_weekday": weekday_svc.astype(int),
                "is_sunday": trip_cal.get("sunday", 0).fillna(0).astype(float).gt(0).astype(int),
            }
        )
        flag_map = flags.drop_duplicates("trip_id").set_index("trip_id")

        acc: dict[str, list[int]] = {}
        read = 0
        with zf.open(names["stop_times.txt"]) as fh:
            for chunk in pd.read_csv(
                fh,
                dtype=str,
                usecols=lambda c: c in {"trip_id", "stop_id", "departure_time"},
                chunksize=400_000,
            ):
                chunk["trip_id"] = chunk["trip_id"].astype(str)
                chunk["stop_id"] = chunk["stop_id"].astype(str)
                chunk = chunk.join(flag_map, on="trip_id")
                chunk["is_weekday"] = chunk["is_weekday"].fillna(0).astype(int)
                chunk["is_sunday"] = chunk["is_sunday"].fillna(0).astype(int)
                mins = chunk["departure_time"].map(_hhmmss_to_min)
                eve = pd.to_numeric(mins, errors="coerce").ge(EVENING_START_MIN).fillna(False).astype(int)
                g = chunk.assign(evening=eve).groupby("stop_id", sort=False)[
                    ["is_weekday", "evening", "is_sunday"]
                ].sum()
                for sid, row in g.iterrows():
                    cur = acc.get(sid)
                    if cur is None:
                        acc[sid] = [int(row["is_weekday"]), int(row["evening"]), int(row["is_sunday"])]
                    else:
                        cur[0] += int(row["is_weekday"])
                        cur[1] += int(row["evening"])
                        cur[2] += int(row["is_sunday"])
                read += len(chunk)
                if max_rows is not None and read >= max_rows:
                    break
                logger.info("TFI stop_times aggregated {:,} rows / {} stops", read, len(acc))

    out = pd.DataFrame(
        [(k, v[0], v[1], v[2]) for k, v in acc.items()],
        columns=["stop_id", "weekday", "evening", "sunday"],
    )
    logger.info("TFI per-stop service rows: {}", len(out))
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


def load_pobal_hp(path: Path) -> pd.DataFrame:
    """Load HP 2022. Accept SA or ED rows. Never rename to IMD."""
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    cols = {c.lower().strip(): c for c in df.columns}

    def pick(*cands: str) -> str | None:
        for c in cands:
            if c in cols:
                return cols[c]
        for key, orig in cols.items():
            if any(c in key for c in cands):
                return orig
        return None

    sa_col = pick("sa_guid_2022", "sa_pub2022", "sa_code", "sa2022", "small_area")
    ed_col = pick("ed_id_str", "ed_id", "ed_code", "csoed", "electoral")
    hp_col = pick(
        "index22_ed_std_rel_wt",
        "std_rel_wt",
        "hp2022",
        "relative_index",
        "hp_rel",
        "index2022",
        "hp_index",
    )
    if hp_col is None:
        # Prefer a column whose name looks like the relative index, not the 1–5 category.
        named = [
            c
            for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c])
            and any(k in str(c).lower() for k in ("rel", "index", "hp"))
            and "cat" not in str(c).lower()
            and "lab" not in str(c).lower()
        ]
        hp_col = named[0] if named else None
    if hp_col is None:
        raise ValueError(f"Pobal CSV has no HP index column: {list(df.columns)}")
    out = pd.DataFrame()
    out["hp_relative"] = pd.to_numeric(df[hp_col], errors="coerce")
    if sa_col:
        out["sa_code"] = df[sa_col].astype(str)
    else:
        out["sa_code"] = (df[ed_col].astype(str) if ed_col else df.index.astype(str))
    if ed_col:
        # CSO ED_ID_STR is 6 digits; CKAN has 5-digit and slash-joined merged EDs.
        exploded = []
        for i, raw in enumerate(df[ed_col].astype(str)):
            parts = [p.strip() for p in raw.replace(";", "/").split("/") if p.strip()]
            if not parts:
                parts = [raw.strip()]
            for p in parts:
                digits = "".join(ch for ch in p if ch.isdigit())
                code = digits.zfill(6) if digits else p.strip()
                exploded.append((i, code))
        if exploded:
            idx, codes = zip(*exploded)
            out = out.iloc[list(idx)].copy()
            out["ed_code"] = list(codes)
        else:
            out["ed_code"] = df[ed_col].astype(str)
    name_col = pick("ed_name", "sa_name", "name")
    if name_col:
        out["name"] = df[name_col].astype(str)
    county_col = pick("county", "countyname", "localauthority")
    if county_col:
        out["county_raw"] = df[county_col].astype(str)
        out["region"] = out["county_raw"].map(slug_county)
    # HP relative: higher = more affluent (Pobal convention). Decile 1 = most deprived.
    valid = out["hp_relative"].dropna()
    if valid.empty:
        out["hp_decile"] = pd.NA
    else:
        # invert so decile 1 = most disadvantaged (same orientation as IMD decile)
        ranks = out["hp_relative"].rank(method="average", ascending=True)
        out["hp_decile"] = pd.qcut(ranks, 10, labels=False, duplicates="drop") + 1
    return out.dropna(subset=["hp_relative"])


def _itm_xy(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Irish Transverse Mercator metres (or a local metres approx if pyproj missing)."""
    try:
        from pyproj import Transformer

        t = Transformer.from_crs("EPSG:4326", ITM, always_xy=True)
        x, y = t.transform(lon, lat)
        return np.column_stack([np.asarray(x), np.asarray(y)])
    except Exception:  # noqa: BLE001
        # ~111.32 km per degree; lon scaled by cos(mean lat)
        mean_lat = float(np.nanmean(lat)) if len(lat) else 53.4
        kx = 111_320.0 * math.cos(math.radians(mean_lat))
        return np.column_stack([np.asarray(lon) * kx, np.asarray(lat) * 110_540.0])


def join_sa_stops(
    areas: pd.DataFrame,
    stops: pd.DataFrame,
    *,
    walk_m: float = WALK_M,
) -> pd.DataFrame:
    """Each SA: stop_count within walk_m of its centroid (cKDTree in metres)."""
    if "lat" not in areas.columns or "lon" not in areas.columns:
        raise ValueError("areas need lat/lon centroids")
    out = areas.copy()
    if stops.empty:
        out["stop_count"] = 0
        out["nearest_stop_m"] = np.nan
        out["within_400m"] = False
        return out
    sa_xy = _itm_xy(out["lat"].astype(float).to_numpy(), out["lon"].astype(float).to_numpy())
    st_xy = _itm_xy(
        stops["stop_lat"].astype(float).to_numpy(),
        stops["stop_lon"].astype(float).to_numpy(),
    )
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


def assign_urban_rural(areas: pd.DataFrame) -> pd.DataFrame:
    """Density rule. Labelled in metadata — not England RUC."""
    out = areas.copy()
    if "area_km2" in out.columns and out["area_km2"].notna().any():
        dens = out["population"].astype(float) / out["area_km2"].replace(0, np.nan)
        out["urban_rural"] = np.where(dens >= URBAN_DENSITY_PER_KM2, "urban", "rural")
    else:
        # No area: treat as urban if pop ≥ national median (documented fallback).
        med = float(out["population"].median()) if len(out) else 0
        out["urban_rural"] = np.where(out["population"].astype(float) >= med, "urban", "rural")
        out.attrs["urban_rural_rule"] = "population-median fallback (no SA area)"
    return out


def attach_service_flags(
    areas: pd.DataFrame,
    stop_times: pd.DataFrame | None,
    stops: pd.DataFrame,
) -> pd.DataFrame:
    """Evening / Sunday / weekday trips using stop_times joined via nearest stop."""
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
    if {"weekday", "evening", "sunday"}.issubset(st.columns) and "departure_min" not in st.columns:
        per_stop = (
            st.groupby("stop_id", as_index=False)[["weekday", "evening", "sunday"]].sum()
        )
    else:
        weekday = (st.get("monday", 0).fillna(0).astype(float) > 0) | (
            st.get("tuesday", 0).fillna(0).astype(float) > 0
        )
        sunday = st.get("sunday", 0).fillna(0).astype(float) > 0
        eve = pd.to_numeric(st["departure_min"], errors="coerce") >= EVENING_START_MIN
        per_stop = pd.DataFrame(
            {
                "stop_id": st["stop_id"],
                "weekday": weekday.astype(int),
                "sunday": sunday.astype(int),
                "evening": eve.fillna(False).astype(int),
            }
        ).groupby("stop_id", as_index=False).sum()

    stop_xy = stops[["stop_id", "stop_lat", "stop_lon"]].copy()
    stop_xy["stop_id"] = stop_xy["stop_id"].astype(str)
    per_stop = per_stop.merge(stop_xy, on="stop_id", how="left")
    per_stop = per_stop.dropna(subset=["stop_lat", "stop_lon"])
    if per_stop.empty:
        out["weekday_trips"] = 0
        out["evening_trips"] = 0
        out["sunday_trips"] = 0
    else:
        sa_xy = _itm_xy(out["lat"].astype(float).to_numpy(), out["lon"].astype(float).to_numpy())
        st_xy = _itm_xy(
            per_stop["stop_lat"].astype(float).to_numpy(),
            per_stop["stop_lon"].astype(float).to_numpy(),
        )
        from scipy.spatial import cKDTree

        tree = cKDTree(st_xy)
        neigh = tree.query_ball_point(sa_xy, r=WALK_M)
        wd = per_stop["weekday"].to_numpy()
        ev = per_stop["evening"].to_numpy()
        su = per_stop["sunday"].to_numpy()
        w_trips = [int(wd[ix].sum()) if ix else 0 for ix in neigh]
        e_trips = [int(ev[ix].sum()) if ix else 0 for ix in neigh]
        s_trips = [int(su[ix].sum()) if ix else 0 for ix in neigh]
        out["weekday_trips"] = w_trips
        out["evening_trips"] = e_trips
        out["sunday_trips"] = s_trips
    out["no_service"] = out["weekday_trips"].eq(0)
    out["evening_isolated"] = out["evening_trips"].eq(0)
    out["sunday_desert"] = out["sunday_trips"].eq(0)
    # SQI analogue 0–100: log1p weekday trips, scaled to the pack max.
    mx = max(float(out["weekday_trips"].max()), 1.0)
    out["sqi"] = (np.log1p(out["weekday_trips"].astype(float)) / math.log1p(mx) * 100.0).clip(0, 100)
    return out


def hp_decile_from_relative(series: pd.Series) -> pd.Series:
    ranks = series.rank(method="average", ascending=True)
    return pd.qcut(ranks, 10, labels=False, duplicates="drop") + 1


def build_ireland_areas(
    *,
    areas: pd.DataFrame,
    stops: pd.DataFrame,
    stop_times: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Fixture-friendly builder: 400 m + bands inputs + HP decile + county."""
    need = {"sa_code", "lat", "lon", "population"}
    missing = need - set(areas.columns)
    if missing:
        raise ValueError(f"areas missing {missing}")
    joined = join_sa_stops(areas, stops)
    joined = attach_service_flags(joined, stop_times, stops)
    if "hp_relative" in joined.columns and "hp_decile" not in joined.columns:
        joined["hp_decile"] = hp_decile_from_relative(joined["hp_relative"])
    if "hp_decile" not in joined.columns:
        joined["hp_decile"] = 5
        joined["hp_relative"] = 0.0
    if "region" not in joined.columns:
        joined["region"] = "dublin"
    if "name" not in joined.columns:
        joined["name"] = joined["sa_code"].astype(str)
    joined = assign_urban_rural(joined)
    joined["trips_per_capita"] = joined["weekday_trips"].astype(float) / joined["population"].replace(0, np.nan)
    joined["trips_per_capita"] = joined["trips_per_capita"].fillna(0.0)
    joined["stops_per_1k"] = joined["stop_count"].astype(float) / joined["population"].replace(0, np.nan) * 1000.0
    joined["stops_per_1k"] = joined["stops_per_1k"].replace([np.inf, -np.inf], 0).fillna(0.0)
    joined["imd_decile"] = joined["hp_decile"]  # warehouse reuse only — UI says HP
    joined["imd_score"] = joined["hp_relative"]
    joined["lsoa_code"] = joined["sa_code"]
    joined["sfca_score_norm"] = np.where(joined["within_400m"], 1.0, 0.0)
    return joined


def write_processed(areas: pd.DataFrame, processed_dir: Path) -> dict[str, Path]:
    """Write Ireland parquets (does not touch England processed files)."""
    ie = processed_dir / "ireland"
    ie.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    demo = ie / "sa_table.parquet"
    areas.to_parquet(demo, index=False)
    paths["sa_table"] = demo
    cents = ie / "sa_centroids.parquet"
    areas[["sa_code", "lat", "lon", "population", "hp_decile", "region", "name"]].rename(
        columns={"sa_code": "area", "population": "pop", "hp_decile": "imd_decile"}
    ).to_parquet(cents, index=False)
    paths["centroids"] = cents
    # Also the path Studio looks at for Ireland
    (processed_dir / "ireland").mkdir(exist_ok=True)
    return paths
