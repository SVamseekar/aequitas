"""ONS LSOA (Dec 2021) population-weighted centroids for walk-to-stop.

Vintage matches Census 2021 LSOAs used in the England pack. Coordinates are
not invented: they come from ONS Open Geography, or an on-disk parquet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from aequitas.analytics.studio import ITL1_NAMES

# ONS Open Geography — LSOA (December 2021) EW population-weighted centroids (V4).
ONS_LSOA_PWC_ITEM = "32729e42d05e4e23bc7e43a36aa4ae8b"
ONS_LSOA_PWC_CSV = (
    "https://open-geography-portalx-ons.hub.arcgis.com/api/download/v1/items/"
    f"{ONS_LSOA_PWC_ITEM}/csv?layers=0"
)
ONS_LSOA_PWC_REST = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "LSOA_PopCentroids_EW_2021_V4/FeatureServer/0/query"
)
CENTROID_VINTAGE = "LSOA December 2021 population-weighted centroids (England and Wales)"


def centroids_parquet_path(processed_dir: Path) -> Path:
    return processed_dir / "lsoa_centroids.parquet"


def centroids_meta_path(processed_dir: Path) -> Path:
    return processed_dir / "lsoa_centroids_meta.json"


def _bng_to_wgs84(easting: pd.Series, northing: pd.Series) -> tuple[pd.Series, pd.Series]:
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(easting.to_numpy(), northing.to_numpy())
    return pd.Series(lat, index=easting.index), pd.Series(lon, index=easting.index)


def _normalise_frame(df: pd.DataFrame) -> pd.DataFrame:
    cols = {str(c).strip().lower(): c for c in df.columns}
    code_key = next(
        (cols[k] for k in ("lsoa21cd", "lsoa_code", "lsoa_cd", "lsoa") if k in cols),
        None,
    )
    # Prefer explicit WGS84 names; ONS PWC CSV ships British National Grid as x/y.
    lat_key = next((cols[k] for k in ("lat", "latitude") if k in cols), None)
    lon_key = next((cols[k] for k in ("lon", "long", "longitude", "lng") if k in cols), None)
    x_key = cols.get("x") or cols.get("easting") or cols.get("oseast1m")
    y_key = cols.get("y") or cols.get("northing") or cols.get("osnrth1m")
    if code_key is None:
        raise ValueError(f"Centroid file needs an LSOA code column; got {list(df.columns)}")

    if lat_key and lon_key:
        lat = pd.to_numeric(df[lat_key], errors="coerce")
        lon = pd.to_numeric(df[lon_key], errors="coerce")
        # If "LAT/LONG" are actually easting/northing (typical ONS mix-up), convert.
        if lat.abs().max() > 90 or lon.abs().max() > 180:
            lat, lon = _bng_to_wgs84(lon, lat)
    elif x_key and y_key:
        easting = pd.to_numeric(df[x_key], errors="coerce")
        northing = pd.to_numeric(df[y_key], errors="coerce")
        lat, lon = _bng_to_wgs84(easting, northing)
    else:
        raise ValueError(
            f"Centroid file needs lat/lon or BNG x/y columns; got {list(df.columns)}"
        )

    out = pd.DataFrame({"lsoa_code": df[code_key].astype(str), "lat": lat, "lon": lon})
    out = out.dropna(subset=["lat", "lon"])
    out = out[out["lsoa_code"].str.startswith("E")]
    if out["lat"].abs().max() > 90 or out["lon"].abs().max() > 180:
        raise ValueError("Centroid coordinates are not WGS84 after conversion.")
    return out.drop_duplicates(subset=["lsoa_code"])


def write_centroids_parquet(df: pd.DataFrame, processed_dir: Path, *, source_url: str) -> Path:
    processed_dir.mkdir(parents=True, exist_ok=True)
    path = centroids_parquet_path(processed_dir)
    clean = _normalise_frame(df)
    clean.to_parquet(path, index=False)
    meta = {
        "vintage": CENTROID_VINTAGE,
        "source_url": source_url,
        "n_england": int(len(clean)),
        "columns": ["lsoa_code", "lat", "lon"],
    }
    centroids_meta_path(processed_dir).write_text(json.dumps(meta, indent=2))
    logger.info("Wrote {} LSOA centroids → {}", len(clean), path)
    return path


def download_lsoa_centroids(processed_dir: Path, *, force: bool = False) -> Path:
    """Download ONS PWC CSV (or REST pages) and persist a small parquet."""
    dest = centroids_parquet_path(processed_dir)
    if dest.exists() and not force:
        return dest

    import requests

    processed_dir.mkdir(parents=True, exist_ok=True)
    raw_csv = processed_dir / "lsoa_centroids_ons_pwc_2021.csv"
    try:
        logger.info("Downloading ONS LSOA PWC CSV {}", ONS_LSOA_PWC_CSV)
        with requests.get(ONS_LSOA_PWC_CSV, stream=True, timeout=(30, 180)) as resp:
            resp.raise_for_status()
            with raw_csv.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    if chunk:
                        fh.write(chunk)
        df = pd.read_csv(raw_csv)
        return write_centroids_parquet(df, processed_dir, source_url=ONS_LSOA_PWC_CSV)
    except Exception as exc:  # noqa: BLE001 — fall back to REST paging
        logger.warning("ONS CSV download failed ({}). Trying FeatureServer pages.", exc)

    frames: list[pd.DataFrame] = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "LSOA21CD,LAT,LONG",
            "returnGeometry": "false",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": 2000,
        }
        resp = requests.get(ONS_LSOA_PWC_REST, params=params, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        feats = payload.get("features") or []
        if not feats:
            break
        rows = [f.get("attributes") or {} for f in feats]
        frames.append(pd.DataFrame(rows))
        if not payload.get("exceededTransferLimit"):
            break
        offset += len(feats)
    if not frames:
        raise RuntimeError("ONS FeatureServer returned no LSOA centroids.")
    return write_centroids_parquet(
        pd.concat(frames, ignore_index=True),
        processed_dir,
        source_url=ONS_LSOA_PWC_REST,
    )


def load_centroid_points(processed_dir: Path | None) -> pd.DataFrame:
    if processed_dir is None:
        return pd.DataFrame(columns=["lsoa_code", "lat", "lon"])
    path = centroids_parquet_path(processed_dir)
    if not path.exists():
        return pd.DataFrame(columns=["lsoa_code", "lat", "lon"])
    return _normalise_frame(pd.read_parquet(path))


def region_label(region: str) -> str | None:
    if region in ("", "all", None):
        return None
    return ITL1_NAMES.get(region, region)


def filter_centroids_for_studio(
    demo: pd.DataFrame,
    centroids: pd.DataFrame,
    *,
    region: str,
    urban_rural: str,
) -> pd.DataFrame:
    """Join pack demographics to ONS centroids. Never invents rural or coordinates."""
    if demo.empty or centroids.empty:
        return pd.DataFrame(columns=["area", "name", "lat", "lon", "pop", "imd_decile"])

    d = demo.copy()
    code_col = next(
        (c for c in ("lsoa_cd", "lsoa_code", "lsoa21cd", "lsoa", "sa_code") if c in d.columns),
        None,
    )
    if code_col is None:
        return pd.DataFrame(columns=["area", "name", "lat", "lon", "pop", "imd_decile"])
    name_col = next((c for c in ("lsoa_nm", "lsoa_name", "name") if c in d.columns), None)
    pop_col = next((c for c in ("population", "pop") if c in d.columns), None)
    if pop_col is None:
        return pd.DataFrame(columns=["area", "name", "lat", "lon", "pop", "imd_decile"])

    d["area"] = d[code_col].astype(str)
    d["name"] = d[name_col].astype(str) if name_col else d["area"]
    d["pop"] = pd.to_numeric(d[pop_col], errors="coerce").fillna(0)
    if "imd_decile" in d.columns:
        d["imd_decile"] = pd.to_numeric(d["imd_decile"], errors="coerce").fillna(0).astype(int)
    else:
        d["imd_decile"] = 0

    label = region_label(region)
    if label and "region" in d.columns:
        d = d[d["region"].astype(str) == label]
    if urban_rural not in ("", "all", None) and "urban_rural" in d.columns:
        d = d[d["urban_rural"].astype(str).str.lower() == str(urban_rural).lower()]

    pts = centroids.rename(columns={"lsoa_code": "area"})
    merged = d.merge(pts[["area", "lat", "lon"]], on="area", how="inner")
    return merged[["area", "name", "lat", "lon", "pop", "imd_decile"]].reset_index(drop=True)


def bbox_of(centroids: pd.DataFrame, *, pad_deg: float = 0.02) -> tuple[float, float, float, float] | None:
    if centroids.empty:
        return None
    return (
        float(centroids["lon"].min()) - pad_deg,
        float(centroids["lat"].min()) - pad_deg,
        float(centroids["lon"].max()) + pad_deg,
        float(centroids["lat"].max()) + pad_deg,
    )


def filter_stops_to_bbox(
    stops: list[tuple[float, float]],
    bbox: tuple[float, float, float, float] | None,
) -> list[tuple[float, float]]:
    if not stops or bbox is None:
        return list(stops)
    west, south, east, north = bbox
    return [(lat, lon) for lat, lon in stops if south <= lat <= north and west <= lon <= east]


def ensure_centroids(processed_dir: Path) -> Path | None:
    path = centroids_parquet_path(processed_dir)
    if path.exists():
        return path
    try:
        return download_lsoa_centroids(processed_dir)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not download LSOA centroids: {}", exc)
        return None


def sideload_warehouse_centroids(warehouse_path: Path, processed_dir: Path) -> None:
    """Optional write of lsoa_centroids so a rebuilt warehouse sees the same file."""
    pq = centroids_parquet_path(processed_dir)
    if not pq.exists() or not warehouse_path.exists():
        return
    import duckdb

    try:
        conn = duckdb.connect(str(warehouse_path), read_only=False)
        conn.execute(
            f"CREATE OR REPLACE TABLE lsoa_centroids AS SELECT * FROM read_parquet('{pq}')"
        )
        n = conn.execute("SELECT COUNT(*) FROM lsoa_centroids").fetchone()[0]
        conn.close()
        logger.info("Sideloaded lsoa_centroids ({} rows) into warehouse", n)
    except Exception as exc:  # noqa: BLE001 — apply still reads parquet
        logger.warning("Warehouse sideload skipped: {}", exc)
