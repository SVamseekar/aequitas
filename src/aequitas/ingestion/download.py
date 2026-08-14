"""Download live open-data snapshots (NaPTAN + BODS) without a cloud account.

Census, IMD, and LSOA boundaries are official releases and are not re-fetched.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import requests
from loguru import logger

NAPTAN_URL = "https://naptan.api.dft.gov.uk/v1/access-nodes?dataFormat=csv"
# ONS Open Geography: LSOA (Dec 2021) EW population-weighted centroids
ONS_LSOA_PWC_CSV = (
    "https://open-geography-portalx-ons.hub.arcgis.com/api/download/v1/items/"
    "32729e42d05e4e23bc7e43a36aa4ae8b/csv?layers=0"
)
BODS_URLS = (
    "https://data.bus-data.dft.gov.uk/timetable/download/gtfs-file/all/",
    "https://data.bus-data.dft.gov.uk/timetable/download/bulk_archive",
)

_CHUNK = 8 * 1024 * 1024
_TIMEOUT = (30, 600)


def _stream_to(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    logger.info("Downloading {} → {}", url, dest)
    with requests.get(url, stream=True, timeout=_TIMEOUT, allow_redirects=True) as resp:
        resp.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=_CHUNK):
                if chunk:
                    fh.write(chunk)
    tmp.replace(dest)
    logger.info("Saved {} ({:.1f} MB)", dest.name, dest.stat().st_size / 1e6)


def download_naptan(raw_dir: Path, stamp: str) -> Path:
    """Fetch NaPTAN CSV (often wrapped in a zip) and expose Stops.csv for ingest."""
    snap = raw_dir / "snapshots" / stamp / "naptan"
    snap.mkdir(parents=True, exist_ok=True)
    payload = snap / "naptan_download.bin"
    _stream_to(NAPTAN_URL, payload)

    dest_dir = raw_dir / "naptan"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if zipfile.is_zipfile(payload):
        with zipfile.ZipFile(payload) as zf:
            names = zf.namelist()
            stop_name = next(
                (n for n in names if Path(n).name.lower() in {"stops.csv", "naptancsv.csv"}),
                None,
            )
            if stop_name is None:
                raise FileNotFoundError(f"No Stops.csv in NaPTAN zip: {names[:12]}")
            extracted = snap / Path(stop_name).name
            with zf.open(stop_name) as src, extracted.open("wb") as out:
                shutil.copyfileobj(src, out)
            csv_path = extracted
    else:
        csv_path = snap / "Stops.csv"
        shutil.copy2(payload, csv_path)

    for name in ("Stops.csv", "NaPTANcsv.csv"):
        target = dest_dir / name
        if target.exists() or target.is_symlink():
            target.unlink()
        shutil.copy2(csv_path, target)
    return dest_dir / "NaPTANcsv.csv"


def download_bods(raw_dir: Path, stamp: str) -> Path:
    """Fetch the national BODS GTFS bulk zip and point ingest at it."""
    snap = raw_dir / "snapshots" / stamp / "bods"
    snap.mkdir(parents=True, exist_ok=True)
    dest = snap / "bods_gtfs_all.zip"

    last_err: Exception | None = None
    for url in BODS_URLS:
        try:
            _stream_to(url, dest)
            if dest.stat().st_size < 10_000_000:
                raise RuntimeError(f"BODS download too small ({dest.stat().st_size} bytes) from {url}")
            if not zipfile.is_zipfile(dest):
                raise RuntimeError(f"BODS response is not a zip: {url}")
            last_err = None
            break
        except Exception as exc:  # noqa: BLE001 — try next official URL
            last_err = exc
            logger.warning("BODS URL failed ({}): {}", url, exc)
    if last_err is not None:
        raise last_err

    live_dir = raw_dir / "bods"
    live_dir.mkdir(parents=True, exist_ok=True)
    live = live_dir / "bods_gtfs_all.zip"
    if live.exists() or live.is_symlink():
        live.unlink()
    try:
        live.symlink_to(dest.resolve())
    except OSError:
        shutil.copy2(dest, live)
    return live


def free_bytes(path: Path) -> int:
    return shutil.disk_usage(path).free


def require_disk(path: Path, needed_gb: float = 40.0) -> None:
    free_gb = free_bytes(path) / 1e9
    if free_gb < needed_gb:
        raise RuntimeError(
            f"Need {needed_gb:.0f} GB free for a BODS refresh; {path} has {free_gb:.1f} GB"
        )
