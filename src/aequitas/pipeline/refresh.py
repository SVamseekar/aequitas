"""Unattended network refresh: download → pipeline → swap warehouse.

Leaves Census/IMD/boundaries untouched. Designed for launchd / cron on a laptop.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.ingestion.download import download_bods, download_naptan, require_disk

_LOCK_NAME = ".refresh.lock"
_NETWORK_PARQUETS = (
    "lsoa_service_quality.parquet",
    "route_geometries.parquet",
    "route_urban_rural.parquet",
    "route_trip_frequency.parquet",
    "master_lsoa_table.parquet",
    "naptan_stops.parquet",
    "bods_routes.parquet",
)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _acquire_lock(root: Path) -> Path:
    lock = root / "data" / _LOCK_NAME
    lock.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        age = datetime.now(timezone.utc).timestamp() - lock.stat().st_mtime
        if age < 12 * 3600:
            raise RuntimeError(f"Refresh already running (lock {lock}, {age/3600:.1f}h old)")
        logger.warning("Removing stale refresh lock ({:.1f}h old)", age / 3600)
        lock.unlink()
    lock.write_text(str(os.getpid()), encoding="utf-8")
    return lock


def _promote_network_parquets(cfg: PipelineConfig) -> None:
    """Copy freshly processed network tables into audit so warehouse sees them."""
    cfg.audit_dir.mkdir(parents=True, exist_ok=True)
    for name in _NETWORK_PARQUETS:
        src = cfg.processed_dir / name
        if not src.exists():
            logger.warning("Skip promote — missing {}", name)
            continue
        dest = cfg.audit_dir / name
        shutil.copy2(src, dest)
        logger.info("Promoted {} → audit/", name)


def _write_state(
    cfg: PipelineConfig,
    stamp: str,
    status: str,
    extra: dict | None = None,
    *,
    country: str = "england",
    warehouse: Path | None = None,
) -> None:
    payload = {
        "status": status,
        "stamp": stamp,
        "country": country,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "warehouse": str(warehouse or cfg.warehouse_path),
        **(extra or {}),
    }
    path = _state_path(cfg.project_root, country)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _backup_warehouse(cfg: PipelineConfig) -> Path | None:
    if not cfg.warehouse_path.exists():
        return None
    bak = cfg.warehouse_path.with_suffix(".duckdb.bak")
    shutil.copy2(cfg.warehouse_path, bak)
    logger.info("Backed up warehouse → {}", bak.name)
    return bak


def _restore_warehouse(cfg: PipelineConfig, bak: Path | None) -> None:
    if bak is None or not bak.exists():
        return
    shutil.copy2(bak, cfg.warehouse_path)
    logger.warning("Restored previous warehouse from {}", bak.name)


def _state_path(project_root: Path, country: str = "england") -> Path:
    if country == "ireland":
        return project_root / "data" / "refresh_state_ireland.json"
    return project_root / "data" / "refresh_state.json"


def last_success_age_days(project_root: Path, country: str = "england") -> float | None:
    path = _state_path(project_root, country)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if data.get("status") != "ok" or not data.get("finished_at"):
        return None
    finished = datetime.fromisoformat(data["finished_at"].replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - finished).total_seconds() / 86400


def _run_ireland_refresh(cfg: PipelineConfig, *, skip_download: bool, stamp: str) -> Path:
    from aequitas.ireland.pipeline import run_ireland_pack
    from aequitas.ireland.warehouse import ireland_warehouse_path
    from aequitas.ireland.download import download_tfi_gtfs

    dest = ireland_warehouse_path(cfg.project_root)
    bak = dest.with_suffix(".duckdb.bak") if dest.exists() else None
    if dest.exists():
        shutil.copy2(dest, bak)
        logger.info("Backed up Ireland warehouse → {}", bak.name)
    try:
        if not skip_download:
            download_tfi_gtfs(cfg.raw_dir)
        else:
            logger.info("Skipping TFI download — existing GTFS")
        out = run_ireland_pack(cfg, skip_download=True)
        n = _ireland_sa_count(out)
        if n is not None and not (18_000 <= n <= 20_000):
            raise RuntimeError(f"Ireland sanity failed — n Small Areas = {n} (want ~18,919)")
        return out
    except Exception:
        if bak is not None and bak.exists():
            shutil.copy2(bak, dest)
            logger.warning("Restored previous Ireland warehouse from {}", bak.name)
        raise


def _ireland_sa_count(path: Path) -> int | None:
    import duckdb

    if not path.exists():
        return None
    conn = duckdb.connect(str(path), read_only=True)
    try:
        row = conn.execute("SELECT value FROM metadata WHERE key = 'n_sas'").fetchone()
        if row:
            return int(row[0])
    except Exception:
        return None
    finally:
        conn.close()
    return None


def run_refresh(
    *,
    skip_download: bool = False,
    min_interval_days: int = 25,
    country: str = "england",
) -> int:
    """Download live network files, write a dated pack, swap current. Returns exit code."""
    cfg = PipelineConfig()
    country = (country or "england").strip().lower()
    cfg.force_full_network = True
    os.environ["AEQUITAS_FORCE_FULL_NETWORK"] = "1"

    age = last_success_age_days(cfg.project_root, country)
    if age is not None and age < min_interval_days:
        logger.info("Skipping {} refresh — last success was {:.1f} days ago", country, age)
        return 0

    stamp = _stamp()
    lock = _acquire_lock(cfg.project_root)
    bak: Path | None = None
    try:
        require_disk(cfg.project_root / "data", needed_gb=8.0 if country == "ireland" else 40.0)
        from aequitas.warehouse.packs import snapshot_after_refresh

        if country == "ireland":
            dest = _run_ireland_refresh(cfg, skip_download=skip_download, stamp=stamp)
            snapshot_after_refresh("ireland", stamp, dest, copy_db=True)
            _write_state(cfg, stamp, "ok", country="ireland", warehouse=dest)
            logger.info("Ireland refresh complete for {}", stamp)
            return 0

        if not skip_download:
            download_naptan(cfg.raw_dir, stamp)
            download_bods(cfg.raw_dir, stamp)
        else:
            logger.info("Skipping download — using existing data/raw files")

        bak = _backup_warehouse(cfg)

        from aequitas.pipeline._stages import (
            run_analytics,
            run_ingestion,
            run_intelligence,
            run_processing,
            run_rag_index,
            run_validation,
            run_warehouse,
        )

        for name, fn in (
            ("ingest", run_ingestion),
            ("process", run_processing),
        ):
            logger.info("=== Stage: {} ===", name)
            fn(cfg)

        _promote_network_parquets(cfg)

        for name, fn in (
            ("analytics", run_analytics),
            ("intelligence", run_intelligence),
            ("warehouse", run_warehouse),
            ("validate", run_validation),
            ("rag_index", run_rag_index),
        ):
            logger.info("=== Stage: {} ===", name)
            fn(cfg)

        snapshot_after_refresh("england", stamp, cfg.warehouse_path, copy_db=True)
        _write_state(cfg, stamp, "ok", country="england")
        logger.info("Refresh complete for {}", stamp)
        return 0
    except Exception as exc:
        logger.exception("Refresh failed: {}", exc)
        if country != "ireland":
            _restore_warehouse(cfg, bak)
        _write_state(
            cfg,
            stamp,
            "failed",
            {"error": str(exc)},
            country=country,
        )
        return 1
    finally:
        if lock.exists():
            lock.unlink()


LAUNCH_AGENT_LABEL = "com.aequitas.refresh"


def launch_agent_plist(project_root: Path, uv_bin: str) -> str:
    log_dir = project_root / "data" / "logs"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LAUNCH_AGENT_LABEL}</string>
  <key>WorkingDirectory</key>
  <string>{project_root}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{uv_bin}</string>
    <string>run</string>
    <string>aequitas</string>
    <string>refresh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Day</key>
    <integer>1</integer>
    <key>Hour</key>
    <integer>2</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{log_dir / "refresh.stdout.log"}</string>
  <key>StandardErrorPath</key>
  <string>{log_dir / "refresh.stderr.log"}</string>
  <key>Nice</key>
  <integer>15</integer>
  <key>ProcessType</key>
  <string>Background</string>
</dict>
</plist>
"""


def install_schedule(project_root: Path) -> Path:
    """Install a monthly launchd agent (1st of month, 02:00 local)."""
    uv_bin = shutil.which("uv")
    if not uv_bin:
        raise RuntimeError("uv not found on PATH — cannot install schedule")
    (project_root / "data" / "logs").mkdir(parents=True, exist_ok=True)
    agents = Path.home() / "Library" / "LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    plist = agents / f"{LAUNCH_AGENT_LABEL}.plist"
    plist.write_text(launch_agent_plist(project_root, uv_bin), encoding="utf-8")
    os.system(f'launchctl unload "{plist}" 2>/dev/null')
    rc = os.system(f'launchctl load "{plist}"')
    if rc != 0:
        raise RuntimeError(f"launchctl load failed with code {rc}")
    logger.info("Installed monthly refresh: {}", plist)
    return plist
