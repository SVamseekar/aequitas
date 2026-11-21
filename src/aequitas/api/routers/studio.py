"""Studio jobs: validate a patch, apply walk-to-stop (and r5py when present)."""

from __future__ import annotations

import base64
import binascii
import io
import threading
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import duckdb
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from aequitas.analytics.studio import (
    StudioPatch,
    apply_studio,
    parse_studio_patch,
    parse_upload_text,
    winners_losers_csv,
)
from aequitas.api.deps import get_db

router = APIRouter(prefix="/studio", tags=["studio"])

_JOBS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


class StudioJobRequest(BaseModel):
    country: str
    region: str = "all"
    urban_rural: str = "all"
    ops: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "drawn"
    upload_text: str | None = None
    upload_filename: str = ""
    pack: str = ""


def _stage(job_id: str, stage: str) -> None:
    with _LOCK:
        _JOBS[job_id]["stage"] = stage


def _load_demographics(db: duckdb.DuckDBPyConnection | None) -> pd.DataFrame:
    if db is None:
        return pd.DataFrame()
    tables = {r[0] for r in db.execute("SHOW TABLES").fetchall()}
    if "lsoa_demographics" not in tables:
        return pd.DataFrame()
    return db.execute("SELECT * FROM lsoa_demographics").df()


def _load_centroids(
    db: duckdb.DuckDBPyConnection | None,
    region: str,
    urban_rural: str,
    processed_dir: Path | None,
) -> pd.DataFrame:
    from aequitas.analytics.centroids import (
        ensure_centroids,
        filter_centroids_for_studio,
        load_centroid_points,
    )

    empty = pd.DataFrame(columns=["area", "name", "lat", "lon", "pop", "imd_decile"])
    ie_mode = processed_dir is not None and processed_dir.name == "ireland"
    ie_cents = None
    if processed_dir is not None:
        ie_cents = (
            processed_dir / "sa_centroids.parquet"
            if ie_mode
            else processed_dir / "ireland" / "sa_centroids.parquet"
        )
    if ie_mode:
        pts = pd.read_parquet(ie_cents) if ie_cents is not None and ie_cents.exists() else empty
    else:
        if processed_dir is not None:
            ensure_centroids(processed_dir)
        pts = load_centroid_points(processed_dir)
    if pts.empty and db is not None:
        tables = {r[0] for r in db.execute("SHOW TABLES").fetchall()}
        if "lsoa_centroids" in tables:
            pts = db.execute("SELECT * FROM lsoa_centroids").df()
    demo = _load_demographics(db)
    if demo.empty or pts.empty:
        return empty
    return filter_centroids_for_studio(demo, pts, region=region, urban_rural=urban_rural)


def _load_baseline_stops(
    db: duckdb.DuckDBPyConnection | None,
    centroids: pd.DataFrame,
) -> list[tuple[float, float]]:
    from aequitas.analytics.centroids import bbox_of, filter_stops_to_bbox

    if db is None:
        return []
    tables = {r[0] for r in db.execute("SHOW TABLES").fetchall()}
    stop_table = (
        "stops" if "stops" in tables else "naptan_stops" if "naptan_stops" in tables else None
    )
    if stop_table is None:
        return []
    cols = {r[0] for r in db.execute(f"DESCRIBE {stop_table}").fetchall()}
    lat_c = "latitude" if "latitude" in cols else "stop_lat"
    lon_c = "longitude" if "longitude" in cols else "stop_lon"
    q = (
        f"SELECT {lat_c}, {lon_c} FROM {stop_table} "
        f"WHERE {lat_c} IS NOT NULL AND {lon_c} IS NOT NULL"
    )
    rows = db.execute(q).fetchall()
    stops = [(float(a), float(b)) for a, b in rows]
    return filter_stops_to_bbox(stops, bbox_of(centroids, pad_deg=0.08))


def _other_terms(
    db: duckdb.DuckDBPyConnection | None, region: str, urban_rural: str
) -> dict[str, float | None]:
    if db is None:
        return {}
    try:
        from aequitas.analytics.score import terms_from_section_stats
        from aequitas.api.services.score import load_section_stats

        by_id = load_section_stats(db, region, urban_rural)
        terms, _ = terms_from_section_stats(
            by_id.get("a3_walking_distance"),
            by_id.get("b2_operating_hours"),
            by_id.get("b1_frequency"),
            by_id.get("d1_coverage_deprivation"),
        )
        return terms
    except Exception:
        return {}


def _run_job(job_id: str, patch: StudioPatch) -> None:
    from aequitas.api.deps import _state
    from aequitas.core.config import PipelineConfig

    cfg = PipelineConfig()
    db: duckdb.DuckDBPyConnection | None = None
    try:
        _stage(job_id, "baseline")
        db_path = _state.get("ie_db_path") if patch.country == "ireland" else _state.get("db_path")
        if db_path is not None:
            db = duckdb.connect(str(db_path), read_only=True)
        processed = (
            cfg.processed_dir / "ireland" if patch.country == "ireland" else cfg.processed_dir
        )
        centroids = _load_centroids(db, patch.region, patch.urban_rural, processed)
        baseline = _load_baseline_stops(db, centroids)
        terms = _other_terms(db, patch.region, patch.urban_rural)
        _stage(job_id, "coverage")
        result = apply_studio(
            patch,
            centroids=centroids,
            baseline_stops=baseline,
            processed_dir=processed,
            raw_dir=cfg.raw_dir,
            other_terms=terms,
        )
        _stage(job_id, "results")
        payload = result.to_dict()
        with _LOCK:
            _JOBS[job_id]["status"] = "done"
            _JOBS[job_id]["result"] = payload
            _JOBS[job_id]["finished_at"] = datetime.now(UTC).isoformat()
    except Exception as exc:
        with _LOCK:
            _JOBS[job_id]["status"] = "error"
            _JOBS[job_id]["error"] = str(exc)
            _JOBS[job_id]["finished_at"] = datetime.now(UTC).isoformat()
    finally:
        if db is not None:
            db.close()


@router.post("/parse")
def parse_upload(body: dict[str, Any]) -> dict[str, Any]:
    text = str(body.get("text") or "")
    filename = str(body.get("filename") or "")
    limit = 10 * 1024 * 1024
    try:
        encoded = body.get("archive_base64")
        if encoded is not None:
            if not isinstance(encoded, str) or len(encoded) > 4 * ((limit + 2) // 3):
                raise ValueError("GTFS ZIP must be at most 10 MB.")
            archive = base64.b64decode(encoded, validate=True)
            if len(archive) > limit:
                raise ValueError("GTFS ZIP must be at most 10 MB.")
            with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
                stops = [
                    entry
                    for entry in zipped.infolist()
                    if entry.filename.rsplit("/", 1)[-1] == "stops.txt"
                ]
                if len(stops) != 1:
                    raise ValueError("GTFS ZIP must contain exactly one stops.txt file.")
                if stops[0].file_size > limit:
                    raise ValueError("GTFS stops.txt must be at most 10 MB when extracted.")
                text = zipped.read(stops[0]).decode("utf-8-sig")
                filename = "stops.txt"
        if len(text.encode("utf-8")) > limit:
            raise ValueError("Upload must be at most 10 MB.")
        ops, err = parse_upload_text(text, filename=filename)
        if not err and body.get("country"):
            _, err = parse_studio_patch(
                {
                    "country": body["country"],
                    "region": body.get("region", "all"),
                    "urban_rural": body.get("urban_rural", "all"),
                    "ops": [op.to_dict() for op in ops],
                    "source": "upload",
                }
            )
    except (
        ValueError,
        TypeError,
        AttributeError,
        IndexError,
        UnicodeError,
        binascii.Error,
        zipfile.BadZipFile,
        RuntimeError,
    ) as exc:
        return {"ok": False, "error": str(exc) or "That file could not be read.", "ops": []}
    if err:
        return {"ok": False, "error": err, "ops": []}
    return {"ok": True, "error": None, "ops": [o.to_dict() for o in ops]}


@router.post("/jobs")
def create_job(
    body: StudioJobRequest,
    db: Annotated[duckdb.DuckDBPyConnection | None, Depends(get_db)],
) -> dict[str, Any]:
    if body.country not in {"england", "ireland"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Studio calculations are available for England and Ireland only. "
                "Your country draft can still be saved."
            ),
        )
    from aequitas.api.deps import _state
    from aequitas.warehouse.packs import CURRENT_IDS, resolve_pack, warehouse_for_pack

    requested = resolve_pack(body.country, body.pack) if body.pack else None
    live = _state.get("ie_db_path") if body.country == "ireland" else _state.get("db_path")
    current_date = bool(
        requested
        and requested.get("current")
        and live
        and warehouse_for_pack(body.country, body.pack, live) == Path(live)
    )
    if body.pack.strip().lower() not in CURRENT_IDS and not current_date:
        raise HTTPException(
            status_code=400,
            detail=(
                "Studio calculates against the current warehouse only. "
                "Select the current network before running."
            ),
        )
    raw = body.model_dump()
    extra_ops = []
    if body.upload_text:
        parsed, err = parse_upload_text(body.upload_text, filename=body.upload_filename)
        if err:
            raise HTTPException(status_code=400, detail=err)
        extra_ops = [o.to_dict() for o in parsed]
    raw["ops"] = list(body.ops) + extra_ops
    patch, err = parse_studio_patch(raw)
    if err or patch is None:
        raise HTTPException(status_code=400, detail=err or "Invalid patch.")
    job_id = uuid.uuid4().hex[:12]
    with _LOCK:
        _JOBS[job_id] = {
            "id": job_id,
            "status": "running",
            "created_at": datetime.now(UTC).isoformat(),
            "result": None,
            "error": None,
            "stage": "validated",
            "patch": patch.to_dict(),
        }
    # Return promptly so every job can report its actual worker stages.
    thread = threading.Thread(target=_run_job, args=(job_id, patch), daemon=True)
    thread.start()
    with _LOCK:
        snapshot = dict(_JOBS[job_id])
    return snapshot


@router.get("/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    with _LOCK:
        job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="No studio job with that id.")
    return {
        k: job[k]
        for k in ("id", "status", "stage", "patch", "created_at", "finished_at", "error")
        if k in job
    }


@router.get("/jobs/{job_id}/result")
def job_result(job_id: str) -> dict[str, Any]:
    with _LOCK:
        job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="No studio job with that id.")
    if job["status"] != "done" or not job.get("result"):
        raise HTTPException(status_code=409, detail="Job is not finished yet.")
    return job["result"]


@router.get("/jobs/{job_id}/winners.csv")
def job_csv(job_id: str) -> PlainTextResponse:
    with _LOCK:
        job = _JOBS.get(job_id)
    if not job or not job.get("result"):
        raise HTTPException(status_code=404, detail="No finished studio result to export.")
    from aequitas.analytics.studio import StudioResult

    r = job["result"]
    result = StudioResult(
        ok=r["ok"],
        mode=r["mode"],
        note=r["note"],
        patch=r["patch"],
        score_before=r["score_before"],
        score_after=r["score_after"],
        people_gained=r["people_gained"],
        people_lost=r["people_lost"],
        n_areas=r["n_areas"],
        deciles=r["deciles"],
        areas=r["areas"],
        reach_available=r["reach_available"],
        needs_r5py=r["needs_r5py"],
        narrative=r["narrative"],
    )
    return PlainTextResponse(winners_losers_csv(result), media_type="text/csv")
