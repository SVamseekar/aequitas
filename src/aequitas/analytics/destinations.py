"""Country-keyed jobs / GP / school destination points.

England may still read the legacy flat `processed/destinations_{type}.parquet`.
Ireland, the Netherlands, and France only read
`processed/{country}/destinations_{type}.parquet`. They never fall through
to an England file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
from loguru import logger

DEST_TYPES = ("jobs", "gp", "school")
COUNTRIES = ("england", "ireland", "netherlands", "france")
REQUIRED_COLUMNS = ("dest_id", "dest_type", "lat", "lon")
OPTIONAL_COLUMNS = ("name", "area_id", "weight", "source")


def destination_path(processed_dir: Path, country: str, dest_type: str) -> Path:
    """Canonical country-keyed parquet path."""
    if country not in COUNTRIES:
        raise ValueError(f"country must be one of {COUNTRIES}")
    if dest_type not in DEST_TYPES:
        raise ValueError(f"dest_type must be one of {DEST_TYPES}")
    return processed_dir / country / f"destinations_{dest_type}.parquet"


def legacy_england_path(processed_dir: Path, dest_type: str) -> Path:
    return processed_dir / f"destinations_{dest_type}.parquet"


def resolve_destination_path(processed_dir: Path, country: str, dest_type: str) -> Path | None:
    """Existing dest parquet for *that country only*. Never another country's file."""
    keyed = destination_path(processed_dir, country, dest_type)
    if keyed.exists():
        return keyed
    if country == "england":
        legacy = legacy_england_path(processed_dir, dest_type)
        if legacy.exists():
            return legacy
    return None


def load_destination_frames(
    processed_dir: Path,
    country: str,
    dest_types: Iterable[str] = DEST_TYPES,
) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for dest in dest_types:
        path = resolve_destination_path(processed_dir, country, dest)
        if path is None:
            continue
        frames[dest] = pd.read_parquet(path)
        logger.info("Loaded {} {} destinations from {}", country, dest, path)
    return frames


def validate_destination_frame(df: pd.DataFrame, *, country: str) -> list[str]:
    """Schema checks. IE/NL/FR must not require LSOA columns."""
    _ = country
    issues: list[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        issues.append(f"missing columns: {missing}")
        return issues
    lat = pd.to_numeric(df["lat"], errors="coerce")
    lon = pd.to_numeric(df["lon"], errors="coerce")
    if lat.isna().all() or lon.isna().all():
        issues.append("lat/lon are all null")
    bad_dest = set(df["dest_type"].astype(str).unique()) - set(DEST_TYPES)
    if bad_dest:
        issues.append(f"unknown dest_type: {sorted(bad_dest)}")
    if df["dest_id"].astype(str).eq("").any():
        issues.append("empty dest_id")
    return issues


def write_destination_frame(
    df: pd.DataFrame,
    processed_dir: Path,
    country: str,
    dest_type: str,
) -> Path:
    if dest_type not in DEST_TYPES:
        raise ValueError(f"dest_type must be one of {DEST_TYPES}")
    work = df.copy()
    if "dest_type" not in work.columns:
        work["dest_type"] = dest_type
    work = work[work["dest_type"].astype(str) == dest_type]
    issues = validate_destination_frame(work, country=country)
    if issues:
        raise ValueError(f"{country}/{dest_type} destination frame invalid: {issues}")
    cols = [c for c in (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS) if c in work.columns]
    path = destination_path(processed_dir, country, dest_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    work[cols].to_parquet(path, index=False)
    logger.info("Wrote {} {} rows to {}", country, len(work), path)
    return path


def destinations_inventory(processed_dir: Path, country: str) -> dict:
    """What dest files exist for this country — never another country's counts."""
    types: dict[str, dict] = {}
    for dest in DEST_TYPES:
        path = resolve_destination_path(processed_dir, country, dest)
        if path is None:
            types[dest] = {"available": False, "rows": 0, "path": None}
            continue
        df = pd.read_parquet(path)
        types[dest] = {
            "available": True,
            "rows": int(len(df)),
            "path": str(path),
            "source": str(df["source"].iloc[0]) if "source" in df.columns and len(df) else None,
        }
    dist = processed_dir / country / "official_distances.parquet"
    official = None
    if dist.exists():
        ddf = pd.read_parquet(dist)
        official = {"available": True, "rows": int(len(ddf)), "path": str(dist), "columns": list(ddf.columns)}
    facility = {}
    for dest in DEST_TYPES:
        fpath = processed_dir / country / f"facility_400m_{dest}.parquet"
        if not fpath.exists():
            continue
        fdf = pd.read_parquet(fpath)
        n = int(len(fdf))
        n_in = int((fdf["n_within"] > 0).sum()) if "n_within" in fdf.columns else 0
        pop = pd.to_numeric(fdf["population"], errors="coerce") if "population" in fdf.columns else None
        people_share = None
        if pop is not None and float(pop.sum()) > 0:
            people_share = float(pop[fdf["n_within"] > 0].sum() / pop.sum())
        note = None
        if dest == "jobs" and n > 0 and n_in == n:
            note = (
                "Jobs file is an area-centroid employment proxy, so every centroid is "
                "within 400 m of itself. Not a workplace point file."
            )
        facility[dest] = {
            "available": True,
            "n_areas": n,
            "n_within_400m": n_in,
            "people_share": people_share,
            "path": str(fpath),
            "note": note,
        }
    return {
        "country": country,
        "destinations": types,
        "official_distances": official,
        "facility_400m": facility,
        "note": (
            None
            if any(v["available"] for v in types.values()) or official
            else f"No official {country} destination extract on disk. We do not copy another country's points."
        ),
    }


COUNTRY_METRIC_CRS = {
    "england": "EPSG:27700",
    "ireland": "EPSG:2157",
    "netherlands": "EPSG:28992",
    "france": "EPSG:2154",
}


def facility_400m(
    areas: pd.DataFrame,
    dests: pd.DataFrame,
    *,
    country: str,
    dest_type: str,
) -> dict:
    """Share of people whose area centroid is within 400 m of an official dest."""
    from pyproj import Transformer
    from scipy.spatial import cKDTree

    if dest_type not in DEST_TYPES:
        raise ValueError(f"dest_type must be one of {DEST_TYPES}")
    crs = COUNTRY_METRIC_CRS.get(country)
    if crs is None:
        raise ValueError(f"no metric CRS for {country}")
    need = {"area_id", "lat", "lon"}
    if need - set(areas.columns):
        raise ValueError("areas need area_id, lat, lon")
    if {"lat", "lon"} - set(dests.columns):
        raise ValueError("dests need lat, lon")
    work = areas.dropna(subset=["lat", "lon"]).copy()
    pts = dests.dropna(subset=["lat", "lon"])
    transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    ax, ay = transformer.transform(work["lon"].to_numpy(), work["lat"].to_numpy())
    dx, dy = transformer.transform(pts["lon"].to_numpy(), pts["lat"].to_numpy())
    tree = cKDTree(list(zip(dx, dy, strict=True))) if len(pts) else None
    counts = []
    for x, y in zip(ax, ay, strict=True):
        if tree is None:
            counts.append(0)
        else:
            counts.append(int(len(tree.query_ball_point((x, y), r=400.0))))
    work = work.assign(n_within=counts)
    pop = pd.to_numeric(work["population"], errors="coerce") if "population" in work.columns else pd.Series([1.0] * len(work))
    pop = pop.fillna(0)
    n_in = int((work["n_within"] > 0).sum())
    people_share = float(pop[work["n_within"] > 0].sum() / pop.sum()) if float(pop.sum()) > 0 else None
    return {
        "dest_type": dest_type,
        "country": country,
        "n_areas": int(len(work)),
        "n_within_400m": n_in,
        "people_share": people_share,
        "frame": work[["area_id", "lat", "lon", "n_within"]].assign(
            dest_type=dest_type,
            population=pop.to_numpy(),
        ),
    }


def write_facility_400m(
    processed_dir: Path,
    country: str,
    dest_type: str,
    areas: pd.DataFrame,
    dests: pd.DataFrame,
) -> Path:
    summary = facility_400m(areas, dests, country=country, dest_type=dest_type)
    path = processed_dir / country / f"facility_400m_{dest_type}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    summary["frame"].to_parquet(path, index=False)
    logger.info(
        "Wrote {} {} 400 m facility rows ({}/{} areas) → {}",
        country,
        dest_type,
        summary["n_within_400m"],
        summary["n_areas"],
        path,
    )
    return path


def compute_country_facility_400m(processed_dir: Path, country: str) -> dict[str, Path]:
    """Build 400 m exhibits from that country's dests + area table only."""
    written: dict[str, Path] = {}
    areas = _load_country_areas(processed_dir, country)
    if areas is None or areas.empty:
        logger.warning("No area centroids for {} — skip 400 m facility", country)
        return written
    dests = load_destination_frames(processed_dir, country)
    for dest_type, dest_df in dests.items():
        written[dest_type] = write_facility_400m(processed_dir, country, dest_type, areas, dest_df)
    return written


def _load_country_areas(processed_dir: Path, country: str) -> pd.DataFrame | None:
    if country == "england":
        cents = processed_dir / "lsoa_centroids.parquet"
        if not cents.exists():
            return None
        df = pd.read_parquet(cents)
        id_col = "lsoa_code" if "lsoa_code" in df.columns else "lsoa"
        out = df.rename(columns={id_col: "area_id"})
        jobs = processed_dir / "england" / "destinations_jobs.parquet"
        audit = processed_dir.parent / "audit" / "lsoa_employment_proxy.parquet"
        pop_src = audit if audit.exists() else None
        if pop_src is not None:
            pop = pd.read_parquet(pop_src)
            pcol = next((c for c in ("lsoa_cd", "lsoa_code", "lsoa") if c in pop.columns), None)
            if pcol and "population" in pop.columns:
                out = out.merge(pop[[pcol, "population"]], left_on="area_id", right_on=pcol, how="left")
        if "population" not in out.columns:
            out["population"] = 1.0
        return out[["area_id", "lat", "lon", "population"]]
    table = {
        "ireland": processed_dir / "ireland" / "sa_table.parquet",
        "netherlands": processed_dir / "netherlands" / "buurt_table.parquet",
        "france": processed_dir / "france" / "iris_table.parquet",
    }.get(country)
    if table is None or not table.exists():
        return None
    df = pd.read_parquet(table)
    id_col = next((c for c in ("sa_code", "buurt_code", "iris_code", "area_id") if c in df.columns), None)
    if id_col is None:
        return None
    out = df.rename(columns={id_col: "area_id"})
    if "population" not in out.columns:
        out["population"] = 1.0
    return out[["area_id", "lat", "lon", "population"]]
