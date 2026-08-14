"""£0 download helpers for OVapi GTFS, CBS SES-WOA, Kerncijfers, Wijk- en Buurtkaart."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
from loguru import logger

from aequitas.ingestion.download import _stream_to
from aequitas.netherlands.constants import (
    KERNCIJFERS_TABLE,
    KERNCIJFERS_TYPED,
    OVAPI_GTFS_URL,
    OVAPI_GTFS_URL_ALT,
    SES_WOA_PERIOD,
    SES_WOA_TABLE,
    SES_WOA_TYPED,
    WIJKBUURT_2024_URL,
    WIJKBUURT_2025_URL,
)

_TIMEOUT = (30, 600)
_PAGE = 10_000


def ovapi_gtfs_path(raw_dir: Path) -> Path | None:
    dest = raw_dir / "ovapi" / "gtfs-nl.zip"
    if dest.exists() and dest.stat().st_size > 1_000_000 and zipfile.is_zipfile(dest):
        return dest
    return None


def download_ovapi_gtfs(raw_dir: Path) -> Path:
    dest_dir = raw_dir / "ovapi"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "gtfs-nl.zip"
    if dest.exists() and dest.stat().st_size > 1_000_000 and zipfile.is_zipfile(dest):
        logger.info("OVapi GTFS already present ({:.1f} MB)", dest.stat().st_size / 1e6)
        return dest
    last: Exception | None = None
    for url in (OVAPI_GTFS_URL, OVAPI_GTFS_URL_ALT):
        try:
            _stream_to(url, dest)
            if dest.stat().st_size < 1_000_000 or not zipfile.is_zipfile(dest):
                raise RuntimeError(f"OVapi zip looks empty: {dest}")
            dest.with_suffix(".zip.url.txt").write_text(url + "\n", encoding="utf-8")
            logger.info("Saved {} from {} ({:.1f} MB)", dest.name, url, dest.stat().st_size / 1e6)
            return dest
        except Exception as exc:  # noqa: BLE001
            last = exc
            logger.warning("OVapi download failed ({}): {}", url, exc)
    raise RuntimeError(f"OVapi GTFS download failed: {last}")


def _odata_pages(url: str, dest_parquet: Path) -> Path:
    dest_parquet.parent.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    skip = 0
    session = requests.Session()
    while True:
        joiner = "&" if "?" in url else "?"
        page_url = f"{url}{joiner}$format=json&$top={_PAGE}&$skip={skip}"
        logger.info("ODataFeed {} skip={}", dest_parquet.name, skip)
        resp = session.get(page_url, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("value") or []
        if not rows:
            break
        frames.append(pd.DataFrame(rows))
        if len(rows) < _PAGE:
            break
        skip += _PAGE
        if skip > 200_000:
            break
    if not frames:
        raise RuntimeError(f"OData returned no rows: {url}")
    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(dest_parquet, index=False)
    dest_parquet.with_suffix(".parquet.url.txt").write_text(url + "\n", encoding="utf-8")
    logger.info("Wrote {} rows → {}", len(out), dest_parquet)
    return dest_parquet


def download_ses_woa(raw_dir: Path) -> Path:
    dest = raw_dir / "netherlands" / f"ses_woa_{SES_WOA_TABLE}_2023.parquet"
    if dest.exists() and dest.stat().st_size > 10_000:
        return dest
    filt = quote(f"Perioden eq '{SES_WOA_PERIOD}'")
    url = f"{SES_WOA_TYPED}?$filter={filt}"
    return _odata_pages(url, dest)


def download_kerncijfers(raw_dir: Path) -> Path:
    dest = raw_dir / "netherlands" / f"kerncijfers_{KERNCIJFERS_TABLE}.parquet"
    if dest.exists() and dest.stat().st_size > 10_000:
        return dest
    return _odata_pages(KERNCIJFERS_TYPED, dest)


def download_wijkbuurtkaart(raw_dir: Path) -> Path:
    dest = raw_dir / "netherlands" / "WijkBuurtkaart_2024_v2.zip"
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    last: Exception | None = None
    for url in (WIJKBUURT_2024_URL, WIJKBUURT_2025_URL):
        try:
            _stream_to(url, dest if "2024" in url else raw_dir / "netherlands" / Path(url).name)
            out = dest if dest.exists() else raw_dir / "netherlands" / Path(url).name
            if out.stat().st_size < 1_000_000:
                raise RuntimeError(f"too small: {out}")
            out.with_suffix(".zip.url.txt").write_text(url + "\n", encoding="utf-8")
            logger.info("Saved {} from {}", out.name, url)
            return out
        except Exception as exc:  # noqa: BLE001
            last = exc
            logger.warning("Wijk- en Buurtkaart failed ({}): {}", url, exc)
    raise RuntimeError(f"Wijk- en Buurtkaart download failed: {last}")


def download_provincie_geojson(raw_dir: Path, public_boundaries: Path | None = None) -> Path | None:
    """PDOK / CBS provincie polygons for SVG fallback (never a GB frame)."""
    dest = raw_dir / "netherlands" / "provincies.geojson"
    urls = (
        "https://cartomap.github.io/nl/wgs84/provincie_2024.geojson",
        "https://cartomap.github.io/nl/wgs84/provincie_2023.geojson",
    )
    if dest.exists() and dest.stat().st_size > 5_000:
        _copy_public(dest, public_boundaries)
        return dest
    last: Exception | None = None
    for url in urls:
        try:
            _stream_to(url, dest)
            if dest.stat().st_size < 5_000:
                raise RuntimeError("too small")
            dest.with_suffix(".geojson.url.txt").write_text(url + "\n", encoding="utf-8")
            _copy_public(dest, public_boundaries)
            return dest
        except Exception as exc:  # noqa: BLE001
            last = exc
            logger.warning("Provincie geojson {}: {}", url, exc)
    logger.warning("Provincie polygons missing: {}", last)
    return dest if dest.exists() else None


def _copy_public(src: Path, public_boundaries: Path | None) -> None:
    if public_boundaries is None:
        return
    public_boundaries.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, public_boundaries)


def write_download_manifest(raw_dir: Path, facts: dict) -> Path:
    dest = raw_dir / "netherlands" / "phase0_counts.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(facts, indent=2), encoding="utf-8")
    return dest
