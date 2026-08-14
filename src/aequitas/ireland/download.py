"""£0 download helpers for TFI GTFS, Pobal HP 2022, CSO SA / SAPS."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import requests
from loguru import logger

from aequitas.ingestion.download import _stream_to
from aequitas.ireland.constants import (
    CSO_SA_2022_URLS,
    CSO_SAPS_POP_URLS,
    IRELAND_COUNTY_GEOJSON_URLS,
    POBAL_HP_2022_URLS,
    TFI_GTFS_URL,
    slug_county,
)

_TIMEOUT = (30, 600)


def download_tfi_gtfs(raw_dir: Path, stamp: str | None = None) -> Path:
    """Fetch TFI GTFS_All.zip into data/raw/tfi/ (gitignored)."""
    dest_dir = raw_dir / "tfi"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "GTFS_All.zip"
    if dest.exists() and dest.stat().st_size > 1_000_000 and zipfile.is_zipfile(dest):
        logger.info("TFI GTFS already present ({:.1f} MB)", dest.stat().st_size / 1e6)
        return dest
    if stamp:
        snap = raw_dir / "snapshots" / stamp / "tfi"
        snap.mkdir(parents=True, exist_ok=True)
        snap_zip = snap / "GTFS_All.zip"
        _stream_to(TFI_GTFS_URL, snap_zip)
        if dest.exists():
            dest.unlink()
        try:
            dest.symlink_to(snap_zip.resolve())
        except OSError:
            shutil.copy2(snap_zip, dest)
    else:
        _stream_to(TFI_GTFS_URL, dest)
    if dest.stat().st_size < 100_000 or not zipfile.is_zipfile(dest):
        raise RuntimeError(f"TFI GTFS download looks empty: {dest}")
    return dest


def _try_urls(urls: tuple[str, ...], dest: Path, *, min_bytes: int = 200) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for url in urls:
        try:
            _stream_to(url, dest)
            if dest.stat().st_size < min_bytes:
                raise RuntimeError(f"too small ({dest.stat().st_size} B) from {url}")
            logger.info("Saved {} from {}", dest.name, url)
            dest.with_suffix(dest.suffix + ".url.txt").write_text(url + "\n", encoding="utf-8")
            return dest
        except Exception as exc:  # noqa: BLE001
            last = exc
            logger.warning("Download failed ({}): {}", url, exc)
    raise RuntimeError(f"All URLs failed for {dest.name}: {last}")


def download_pobal_hp(raw_dir: Path) -> Path:
    dest = raw_dir / "ireland" / "hp_deprivation_2022.csv"
    if dest.exists() and dest.stat().st_size > 200:
        return dest
    return _try_urls(POBAL_HP_2022_URLS, dest, min_bytes=200)


_SA_FEATURESERVERS = (
    # Tailte Éireann / GeoHive — paginate; a single query of 19k polygons 400s.
    "https://services-eu1.arcgis.com/PxbTDTskGHCe4sv6/arcgis/rest/services/"
    "CSO_Small_Areas_National_Statistical_Boundaries_2022_Generalised_20m/FeatureServer/0",
    "https://services1.arcgis.com/PxbTDTskGHCe4sv6/arcgis/rest/services/"
    "CSO_Small_Areas_National_Statistical_Boundaries_2022_Generalised_20m/FeatureServer/0",
)


def _download_arcgis_paginated(layer_url: str, dest: Path, *, page: int = 2000) -> Path:
    import json

    features: list = []
    offset = 0
    while True:
        q = (
            f"{layer_url}/query?where=1%3D1&outFields=*&f=geojson"
            f"&resultOffset={offset}&resultRecordCount={page}&outSR=4326"
        )
        tmp = dest.with_suffix(f".page{offset}.geojson")
        _stream_to(q, tmp)
        chunk = json.loads(tmp.read_text(encoding="utf-8"))
        tmp.unlink(missing_ok=True)
        if chunk.get("error"):
            raise RuntimeError(chunk["error"])
        batch = chunk.get("features") or []
        features.extend(batch)
        logger.info("SA FeatureServer +{} (total {})", len(batch), len(features))
        if len(batch) < page:
            break
        offset += page
        if offset > 50_000:
            break
    if len(features) < 1000:
        raise RuntimeError(f"FeatureServer returned only {len(features)} SAs")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    return dest


def download_cso_sa_geojson(raw_dir: Path) -> Path | None:
    dest = raw_dir / "ireland" / "sa_2022.geojson"
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    try:
        return _try_urls(CSO_SA_2022_URLS, dest, min_bytes=1_000_000)
    except RuntimeError as exc:
        logger.warning("Packaged SA GeoJSON failed: {}", exc)
    for layer in _SA_FEATURESERVERS:
        try:
            logger.info("Paginating SA FeatureServer {}", layer)
            return _download_arcgis_paginated(layer, dest)
        except Exception as page_exc:  # noqa: BLE001
            logger.warning("SA FeatureServer failed ({}): {}", layer, page_exc)
    logger.warning("CSO SA 2022 GeoJSON not downloaded")
    return None


def download_cso_saps(raw_dir: Path) -> Path | None:
    dest = raw_dir / "ireland" / "saps_2022.csv"
    if dest.exists() and dest.stat().st_size > 200:
        return dest
    try:
        return _try_urls(CSO_SAPS_POP_URLS, dest, min_bytes=200)
    except RuntimeError as exc:
        logger.warning("CSO SAPS not downloaded: {}", exc)
        return None


def tfi_gtfs_path(raw_dir: Path) -> Path | None:
    p = raw_dir / "tfi" / "GTFS_All.zip"
    return p if p.exists() else None


def download_ireland_counties(raw_dir: Path, public_boundaries: Path | None = None) -> Path | None:
    """Fetch official county polygons and write frontend/public/boundaries if given."""
    dest = raw_dir / "ireland" / "counties_2019.geojson"
    try:
        if not (dest.exists() and dest.stat().st_size > 10_000):
            _try_urls(IRELAND_COUNTY_GEOJSON_URLS, dest, min_bytes=10_000)
    except RuntimeError as exc:
        logger.warning("County polygons not downloaded: {}", exc)
        return None
    if public_boundaries is None:
        return dest
    try:
        import json

        raw = json.loads(dest.read_text(encoding="utf-8"))
        features = []
        for feat in raw.get("features") or []:
            props = feat.get("properties") or {}
            keys = {str(k).lower(): k for k in props}
            name = None
            for cand in ("county", "english", "nameenglish", "counties", "name"):
                if cand in keys:
                    name = str(props[keys[cand]])
                    break
            if not name:
                continue
            slug = slug_county(name)
            feat["properties"] = {
                "COUNTY_SLUG": slug,
                "COUNTY": name.replace("County ", "").title(),
                "county": name.replace("County ", "").title(),
            }
            features.append(feat)
        out = {"type": "FeatureCollection", "features": features}
        public_boundaries.parent.mkdir(parents=True, exist_ok=True)
        public_boundaries.write_text(json.dumps(out), encoding="utf-8")
        logger.info("Wrote {} county polygons → {}", len(features), public_boundaries)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not rewrite county geojson: {}", exc)
    return dest
