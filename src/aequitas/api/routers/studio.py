"""Studio jobs: validate a patch, apply walk-to-stop (and r5py when present)."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

import duckdb
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


def _load_demographics(db: duckdb.DuckDBPyConnection | None):
    import pandas as pd

    if db is None:
        return pd.DataFrame()
    tables = {r[0] for r in db.execute("SHOW TABLES").fetchall()}
    if "lsoa_demographics" not in tables:
        return pd.DataFrame()
    return db.execute("SELECT * FROM lsoa_demographics").df()


def _load_centroids(db: duckdb.DuckDBPyConnection | None, region: str, urban_rural: str, processed_dir):
    import pandas as pd

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
    centroids,
) -> list[tuple[float, float]]:
    from aequitas.analytics.centroids import bbox_of, filter_stops_to_bbox

    if db is None:
        return []
    tables = {r[0] for r in db.execute("SHOW TABLES").fetchall()}
    stop_table = "stops" if "stops" in tables else "naptan_stops" if "naptan_stops" in tables else None
    if stop_table is None:
        return []
    cols = {r[0] for r in db.execute(f"DESCRIBE {stop_table}").fetchall()}
    lat_c = "latitude" if "latitude" in cols else "stop_lat"
    lon_c = "longitude" if "longitude" in cols else "stop_lon"
    q = f"SELECT {lat_c}, {lon_c} FROM {stop_table} WHERE {lat_c} IS NOT NULL AND {lon_c} IS NOT NULL"
    rows = db.execute(q).fetchall()
    stops = [(float(a), float(b)) for a, b in rows]
    return filter_stops_to_bbox(stops, bbox_of(centroids, pad_deg=0.08))


def _other_terms(db: duckdb.DuckDBPyConnection | None, region: str, urban_rural: str) -> dict[str, float | None]:
    if db is None:
        return {}
    try:
        from aequitas.api.services.score import load_section_stats
        from aequitas.analytics.score import terms_from_section_stats

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
    from aequitas.core.config import PipelineConfig
    from aequitas.api.deps import _state

    cfg = PipelineConfig()
    db: duckdb.DuckDBPyConnection | None = None
    try:
        db_path = _state.get("ie_db_path") if patch.country == "ireland" else _state.get("db_path")
        if db_path is not None:
            db = duckdb.connect(str(db_path), read_only=True)
        processed = cfg.processed_dir / "ireland" if patch.country == "ireland" else cfg.processed_dir
        centroids = _load_centroids(db, patch.region, patch.urban_rural, processed)
        baseline = _load_baseline_stops(db, centroids)
        terms = _other_terms(db, patch.region, patch.urban_rural)
        result = apply_studio(
            patch,
            centroids=centroids,
            baseline_stops=baseline,
            processed_dir=cfg.processed_dir,
            raw_dir=cfg.raw_dir,
            other_terms=terms,
        )
        with _LOCK:
            _JOBS[job_id]["status"] = "done"
            _JOBS[job_id]["result"] = result.to_dict()
            _JOBS[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        with _LOCK:
            _JOBS[job_id]["status"] = "error"
            _JOBS[job_id]["error"] = str(exc)
            _JOBS[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
    finally:
        if db is not None:
            db.close()


@router.post("/parse")
def parse_upload(body: dict[str, Any]) -> dict[str, Any]:
    text = str(body.get("text") or "")
    filename = str(body.get("filename") or "")
    ops, err = parse_upload_text(text, filename=filename)
    if err:
        return {"ok": False, "error": err, "ops": []}
    return {"ok": True, "error": None, "ops": [o.to_dict() for o in ops]}


@router.post("/jobs")
def create_job(
    body: StudioJobRequest,
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
) -> dict[str, Any]:
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
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": None,
            "error": None,
        }
    # Tiny fixtures run sync; keep a thread so the UI can poll.
    thread = threading.Thread(target=_run_job, args=(job_id, patch), daemon=True)
    thread.start()
    if len(patch.ops) <= 8:
        thread.join(timeout=45)
    with _LOCK:
        snapshot = dict(_JOBS[job_id])
    return snapshot


@router.get("/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    with _LOCK:
        job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="No studio job with that id.")
    return {k: job[k] for k in ("id", "status", "created_at", "finished_at", "error") if k in job}


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
