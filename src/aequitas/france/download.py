"""£0 download helpers for NAP GTFS, IGN IRIS, F-EDI, INSEE density / recensement."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd
import requests
from loguru import logger

from aequitas.france.constants import (
    FEDI_IRIS_RESOURCE,
    FILOSOFI_IRIS_CANDIDATES,
    IGN_IRIS_WFS,
    IGN_IRIS_WFS_HITS,
    INSEE_DENSITY_XLSX,
    INSEE_IRIS_POP_ZIP,
    NAP_DATASETS_URL,
    iris_text,
)
from aequitas.ingestion.download import _stream_to

_TIMEOUT = (30, 180)
_WFS_PAGE = 1_000
_UA = {"User-Agent": "Aequitas/0.1 (Wave 9 France pack; research)"}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_UA)
    return s


def nap_catalog_path(raw_dir: Path) -> Path:
    return raw_dir / "france" / "nap_gtfs_catalog.json"


def fetch_nap_catalog(raw_dir: Path) -> list[dict]:
    dest = nap_catalog_path(raw_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("NAP catalog {}", NAP_DATASETS_URL)
    resp = _session().get(NAP_DATASETS_URL, timeout=(30, 180))
    dest.with_suffix(".json.http.txt").write_text(
        f"{resp.status_code} {len(resp.content)} {NAP_DATASETS_URL}\n", encoding="utf-8"
    )
    resp.raise_for_status()
    data = resp.json()
    slim: list[dict] = []
    for ds in data:
        for res in ds.get("resources") or []:
            fmt = (res.get("format") or "").lower()
            if fmt != "gtfs":
                continue
            slim.append(
                {
                    "dataset_id": ds.get("id"),
                    "title": ds.get("title"),
                    "resource_id": res.get("id"),
                    "resource_title": res.get("title"),
                    "url": res.get("url") or res.get("original_url"),
                    "filesize": res.get("filesize"),
                    "updated": res.get("updated") or res.get("last_update"),
                    "is_available": res.get("is_available"),
                }
            )
    dest.write_text(json.dumps(slim, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("NAP GTFS resources: {}", len(slim))
    return slim


def download_nap_gtfs(raw_dir: Path, *, limit: int | None = None) -> dict:
    """Download available GTFS zips. Returns merged/skipped counts. Never invents URLs."""
    catalog = fetch_nap_catalog(raw_dir)
    dest_dir = raw_dir / "france" / "nap_gtfs"
    dest_dir.mkdir(parents=True, exist_ok=True)
    log_rows: list[dict] = []
    merged = skipped = 0
    taken = 0
    for rec in catalog:
        if rec.get("is_available") is False:
            skipped += 1
            log_rows.append({**rec, "status": "unavailable"})
            continue
        url = rec.get("url")
        if not url:
            skipped += 1
            log_rows.append({**rec, "status": "no-url"})
            continue
        if limit is not None and taken >= limit:
            skipped += 1
            log_rows.append({**rec, "status": "deferred-limit"})
            continue
        rid = rec.get("resource_id") or rec.get("dataset_id") or taken
        dest = dest_dir / f"{rid}.zip"
        if dest.exists() and dest.stat().st_size > 500 and zipfile.is_zipfile(dest):
            merged += 1
            taken += 1
            log_rows.append({**rec, "status": "cached", "path": str(dest)})
            continue
        try:
            _stream_to(url, dest)
            if dest.stat().st_size < 200 or not zipfile.is_zipfile(dest):
                dest.unlink(missing_ok=True)
                skipped += 1
                log_rows.append({**rec, "status": "not-zip"})
                continue
            merged += 1
            taken += 1
            log_rows.append({**rec, "status": "ok", "bytes": dest.stat().st_size})
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            dest.unlink(missing_ok=True)
            log_rows.append({**rec, "status": f"error:{type(exc).__name__}", "error": str(exc)[:240]})
            logger.warning("NAP skip {} ({})", url, exc)
    summary = {
        "catalog": len(catalog),
        "merged": merged,
        "skipped": skipped,
        "dir": str(dest_dir),
    }
    (raw_dir / "france" / "nap_harvest_log.json").write_text(
        json.dumps({"summary": summary, "rows": log_rows}, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("NAP harvest merged={} skipped={} catalog={}", merged, skipped, len(catalog))
    return summary


def download_fedi_iris(raw_dir: Path) -> Path:
    dest = raw_dir / "france" / "EDI2021_IRIS_FM.xlsx"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100_000:
        return dest
    _stream_to(FEDI_IRIS_RESOURCE, dest)
    dest.with_suffix(".xlsx.url.txt").write_text(FEDI_IRIS_RESOURCE + "\n", encoding="utf-8")
    return dest


def download_insee_density(raw_dir: Path) -> Path | None:
    dest = raw_dir / "france" / "grille_densite_7_niveaux_2024.xlsx"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 10_000:
        return dest
    try:
        _stream_to(INSEE_DENSITY_XLSX, dest)
        dest.with_suffix(".xlsx.url.txt").write_text(INSEE_DENSITY_XLSX + "\n", encoding="utf-8")
        return dest
    except Exception as exc:  # noqa: BLE001
        logger.warning("INSEE density failed: {}", exc)
        dest.with_suffix(".xlsx.fail.txt").write_text(str(exc), encoding="utf-8")
        return dest if dest.exists() else None


def download_insee_iris_pop(raw_dir: Path) -> Path | None:
    dest = raw_dir / "france" / "base-ic-evol-struct-pop-2018_csv.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 10_000:
        return dest
    try:
        _stream_to(INSEE_IRIS_POP_ZIP, dest)
        dest.with_suffix(".zip.url.txt").write_text(INSEE_IRIS_POP_ZIP + "\n", encoding="utf-8")
        return dest
    except Exception as exc:  # noqa: BLE001
        logger.warning("INSEE IRIS pop failed: {}", exc)
        dest.with_suffix(".zip.fail.txt").write_text(str(exc), encoding="utf-8")
        return dest if dest.exists() else None


def download_filosofi_iris(raw_dir: Path) -> Path | None:
    dest_dir = raw_dir / "france"
    dest_dir.mkdir(parents=True, exist_ok=True)
    log = []
    for url in FILOSOFI_IRIS_CANDIDATES:
        dest = dest_dir / Path(url).name
        try:
            _stream_to(url, dest)
            log.append({"url": url, "status": "ok", "bytes": dest.stat().st_size})
            dest.with_suffix(".xlsx.url.txt").write_text(url + "\n", encoding="utf-8")
            (dest_dir / "filosofi_try.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
            return dest
        except Exception as exc:  # noqa: BLE001
            log.append({"url": url, "status": type(exc).__name__, "error": str(exc)[:240]})
            dest.unlink(missing_ok=True)
    (dest_dir / "filosofi_try.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    logger.info("Filosofi IRIS not free at tried URLs — d5 omit unless later file appears")
    return None


def download_iris_wfs(raw_dir: Path) -> Path:
    """Page IGN WFS; persist centroids + codes (not full polygons)."""
    dest = raw_dir / "france" / "iris_centroids.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100_000:
        return dest
    sess = _session()
    hits = sess.get(IGN_IRIS_WFS_HITS, timeout=_TIMEOUT)
    n_matched = None
    try:
        # numberMatched="49386"
        text = hits.text
        if "numberMatched=" in text:
            n_matched = int(text.split("numberMatched=\"")[1].split("\"")[0])
    except Exception:  # noqa: BLE001
        n_matched = None
    logger.info("IGN WFS hits HTTP {} numberMatched={}", hits.status_code, n_matched)
    frames: list[pd.DataFrame] = []
    start = 0
    while True:
        url = f"{IGN_IRIS_WFS}&COUNT={_WFS_PAGE}&STARTINDEX={start}"
        logger.info("WFS IRIS start={}", start)
        resp = sess.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        feats = payload.get("features") or []
        if not feats:
            break
        rows = []
        for f in feats:
            props = f.get("properties") or {}
            geom = f.get("geometry") or {}
            lat = lon = None
            coords = geom.get("coordinates")
            if coords:
                # MultiPolygon — average first ring vertices (cheap centroid)
                ring = coords
                while isinstance(ring, list) and ring and isinstance(ring[0], list) and not isinstance(ring[0][0], (int, float)):
                    ring = ring[0]
                if ring and isinstance(ring[0], (list, tuple)):
                    xs = [p[0] for p in ring if isinstance(p, (list, tuple)) and len(p) >= 2]
                    ys = [p[1] for p in ring if isinstance(p, (list, tuple)) and len(p) >= 2]
                    if xs and ys:
                        lon = float(sum(xs) / len(xs))
                        lat = float(sum(ys) / len(ys))
            rows.append(
                {
                    "iris_code": iris_text(props.get("code_iris")),
                    "com": str(props.get("code_insee") or ""),
                    "name": props.get("nom_iris") or props.get("nom_commune"),
                    "commune_name": props.get("nom_commune"),
                    "type_iris": props.get("type_iris"),
                    "lat": lat,
                    "lon": lon,
                }
            )
        frames.append(pd.DataFrame(rows))
        if len(feats) < _WFS_PAGE:
            break
        start += _WFS_PAGE
        if start > 80_000:
            break
    if not frames:
        raise RuntimeError("IGN WFS returned no IRIS")
    out = pd.concat(frames, ignore_index=True).drop_duplicates("iris_code")
    out.to_parquet(dest, index=False)
    dest.with_suffix(".parquet.url.txt").write_text(
        f"{IGN_IRIS_WFS}\nhits={n_matched} rows={len(out)}\n", encoding="utf-8"
    )
    logger.info("IRIS centroids {} (WFS matched {})", len(out), n_matched)
    return dest


def download_region_geojson(raw_dir: Path, public_boundaries: Path | None = None) -> Path | None:
    dest = raw_dir / "france" / "regions.geojson"
    url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions-version-simplifiee.geojson"
    if dest.exists() and dest.stat().st_size > 2_000:
        _copy_public(dest, public_boundaries)
        return dest
    try:
        _stream_to(url, dest)
        dest.with_suffix(".geojson.url.txt").write_text(url + "\n", encoding="utf-8")
        _copy_public(dest, public_boundaries)
        return dest
    except Exception as exc:  # noqa: BLE001
        logger.warning("Région geojson failed: {}", exc)
        return dest if dest.exists() else None


def _copy_public(src: Path, public_boundaries: Path | None) -> None:
    if public_boundaries is None:
        return
    public_boundaries.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, public_boundaries)


def write_download_manifest(raw_dir: Path, facts: dict) -> Path:
    dest = raw_dir / "france" / "phase0_counts.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(facts, indent=2, default=str), encoding="utf-8")
    return dest
