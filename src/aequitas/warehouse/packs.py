"""Dated warehouse snapshots (Wave 6).

Layout (one model, documented in CURRENT_STATE):

    data/packs/manifest.json
    data/packs/{country}/{YYYY-MM-DD}/metrics.json
    data/packs/{country}/{YYYY-MM-DD}/warehouse.duckdb   # optional copy; current may point at live path

Census / IMD / HP stay frozen in each checkout. Only the network (BODS / TFI)
is allowed to time-travel when refresh writes a new pack.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

MANIFEST_NAME = "manifest.json"
CURRENT_IDS = frozenset({"", "current", "latest"})


def packs_root(project_root: Path | None = None) -> Path:
    env = os.environ.get("AEQUITAS_PACKS_DIR")
    if env:
        return Path(env)
    root = project_root or Path(os.environ.get("AEQUITAS_PROJECT_ROOT", "."))
    return root / "data" / "packs"


def manifest_path(root: Path | None = None) -> Path:
    return packs_root(root) / MANIFEST_NAME


def load_manifest(root: Path | None = None) -> dict[str, Any]:
    path = manifest_path(root)
    if not path.exists():
        return {"england": [], "ireland": [], "netherlands": [], "france": [], "updated_at": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"england": [], "ireland": [], "netherlands": [], "france": [], "updated_at": None}
    data.setdefault("england", [])
    data.setdefault("ireland", [])
    data.setdefault("netherlands", [])
    data.setdefault("france", [])
    return data


def save_manifest(data: dict[str, Any], root: Path | None = None) -> Path:
    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def list_packs(country: str, root: Path | None = None) -> list[dict[str, Any]]:
    key = (country or "england").strip().lower()
    rows = list(load_manifest(root).get(key) or [])
    rows.sort(key=lambda r: str(r.get("as_of") or r.get("pack_id") or ""))
    return rows


def current_pack(country: str, root: Path | None = None) -> dict[str, Any] | None:
    rows = list_packs(country, root)
    for row in reversed(rows):
        if row.get("current"):
            return row
    return rows[-1] if rows else None


def resolve_pack(country: str, pack_id: str | None, root: Path | None = None) -> dict[str, Any] | None:
    """Return the pack record, or None if a specific id was requested and missing."""
    key = (pack_id or "").strip()
    rows = list_packs(country, root)
    if not key or key.lower() in CURRENT_IDS:
        return current_pack(country, root)
    for row in rows:
        if row.get("pack_id") == key or row.get("as_of") == key:
            return row
    return None


def warehouse_for_pack(country: str, pack_id: str | None, live_path: Path | None) -> Path | None:
    """Resolve a DuckDB path. Unknown pack id → None (caller 404s)."""
    key = (pack_id or "").strip()
    rec = resolve_pack(country, key or None)
    if key and key.lower() not in CURRENT_IDS and rec is None:
        return None
    if rec and rec.get("warehouse"):
        p = Path(str(rec["warehouse"]))
        if p.exists():
            return p
        dated = packs_root() / country / str(rec.get("pack_id")) / "warehouse.duckdb"
        if dated.exists():
            return dated
    if live_path and Path(live_path).exists() and (not key or key.lower() in CURRENT_IDS):
        return Path(live_path)
    return live_path if live_path and Path(live_path).exists() else None


def extract_metrics(db_path: Path, *, region: str = "all", urban_rural: str = "all") -> dict[str, Any]:
    import duckdb

    from aequitas.api.services.score import score_for_filter

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        scored = score_for_filter(conn, region, urban_rural)
        a3 = {}
        b2 = {}
        b1 = {}
        try:
            rows = conn.execute(
                """
                SELECT section_id, stats FROM section_results
                WHERE region = ? AND urban_rural = ?
                  AND section_id IN ('a3_walking_distance', 'b2_operating_hours', 'b1_frequency')
                """,
                [region, urban_rural],
            ).fetchall()
            parsed: dict[str, Any] = {}
            for sid, stats in rows:
                if isinstance(stats, str):
                    parsed[sid] = json.loads(stats)
                elif isinstance(stats, dict):
                    parsed[sid] = stats
            a3 = parsed.get("a3_walking_distance") or {}
            b2 = parsed.get("b2_operating_hours") or {}
            b1 = parsed.get("b1_frequency") or {}
        except Exception:
            pass
        pct_400 = a3.get("pct_covered")
        evening = b2.get("pct_evening_isolated")
        mean_sqi = b1.get("value") if isinstance(b1.get("value"), (int, float)) else b1.get("national_avg")
        n_areas = scored.n_areas
        if n_areas is None:
            n_areas = a3.get("n_lsoas") or a3.get("n_sas")
        return {
            "score": None if scored.score is None else round(float(scored.score), 1),
            "pct_400m": None if not isinstance(pct_400, (int, float)) else round(float(pct_400), 2),
            "evening_isolated_pct": None
            if not isinstance(evening, (int, float))
            else round(float(evening), 2),
            "mean_sqi": None if not isinstance(mean_sqi, (int, float)) else round(float(mean_sqi), 2),
            "n_areas": int(n_areas) if isinstance(n_areas, (int, float)) else None,
        }
    finally:
        conn.close()


def write_metrics_file(dest_dir: Path, metrics: dict[str, Any]) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / "metrics.json"
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return path


def register_pack(
    country: str,
    pack_id: str,
    *,
    warehouse: Path | None,
    metrics: dict[str, Any],
    current: bool = False,
    copy_db: bool = False,
    root: Path | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Write metrics.json (and optionally a DuckDB copy) and update the manifest."""
    country = country.strip().lower()
    dest = packs_root(root) / country / pack_id
    dest.mkdir(parents=True, exist_ok=True)
    payload = {
        "pack_id": pack_id,
        "as_of": pack_id,
        "country": country,
        "score": metrics.get("score"),
        "pct_400m": metrics.get("pct_400m"),
        "evening_isolated_pct": metrics.get("evening_isolated_pct"),
        "mean_sqi": metrics.get("mean_sqi"),
        "n_areas": metrics.get("n_areas"),
        "note": note,
        **{k: v for k, v in metrics.items() if k not in {"score", "pct_400m", "n_areas"}},
    }
    write_metrics_file(dest, payload)
    wh_path: Path | None = None
    if copy_db and warehouse is not None and warehouse.exists():
        wh_path = dest / "warehouse.duckdb"
        if warehouse.resolve() != wh_path.resolve():
            shutil.copy2(warehouse, wh_path)
            logger.info("Copied warehouse → {}", wh_path)
    elif warehouse is not None:
        wh_path = warehouse

    rec = {
        "pack_id": pack_id,
        "as_of": pack_id,
        "current": current,
        "score": payload.get("score"),
        "pct_400m": payload.get("pct_400m"),
        "evening_isolated_pct": payload.get("evening_isolated_pct"),
        "mean_sqi": payload.get("mean_sqi"),
        "n_areas": payload.get("n_areas"),
        "warehouse": str(wh_path) if wh_path else None,
        "metrics": str(dest / "metrics.json"),
        "note": note,
    }
    man = load_manifest(root)
    rows = [r for r in (man.get(country) or []) if r.get("pack_id") != pack_id]
    if current:
        for r in rows:
            r["current"] = False
    rows.append(rec)
    man[country] = rows
    save_manifest(man, root)
    return rec


def ensure_current_registered(
    country: str,
    live_path: Path,
    *,
    pack_id: str | None = None,
    root: Path | None = None,
) -> dict[str, Any] | None:
    """Register the live warehouse as pack 0 if the country has no packs yet."""
    if not live_path.exists():
        return None
    existing = list_packs(country, root)
    if existing:
        return current_pack(country, root)
    stamp = pack_id
    if not stamp:
        try:
            import duckdb

            conn = duckdb.connect(str(live_path), read_only=True)
            try:
                row = conn.execute(
                    "SELECT value FROM metadata WHERE key IN ('built_at', 'as_of') LIMIT 1"
                ).fetchone()
                if row and row[0]:
                    stamp = str(row[0])[:10]
            except Exception:
                stamp = None
            finally:
                conn.close()
        except Exception:
            stamp = None
    if not stamp or len(stamp) < 8:
        stamp = datetime.fromtimestamp(live_path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    metrics = extract_metrics(live_path)
    note = "Registered live checkout as first network date (Census/IMD/HP frozen)."
    return register_pack(
        country,
        stamp,
        warehouse=live_path,
        metrics=metrics,
        current=True,
        copy_db=False,
        root=root,
        note=note,
    )


def snapshot_after_refresh(
    country: str,
    pack_id: str,
    live_path: Path,
    *,
    root: Path | None = None,
    copy_db: bool = True,
) -> dict[str, Any]:
    metrics = extract_metrics(live_path)
    return register_pack(
        country,
        pack_id,
        warehouse=live_path,
        metrics=metrics,
        current=True,
        copy_db=copy_db,
        root=root,
        note="Network refresh; Census / IMD / HP / centroids unchanged.",
    )
