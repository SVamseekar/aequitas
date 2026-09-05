"""Rebuild only data/aequitas_netherlands.duckdb after Sunday/calendar + 78-filter writers.

Does not touch England or Ireland warehouses.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.netherlands.network import load_ovapi_network
from aequitas.netherlands.pipeline import _load_ses, _norm_buurt
from aequitas.netherlands.process import (
    attach_service_flags,
    load_ovapi_stop_times,
    load_ovapi_stops,
    ses_decile_from_score,
    write_processed,
)
from aequitas.netherlands.warehouse import build_netherlands_warehouse, netherlands_warehouse_path


def main() -> None:
    cfg = PipelineConfig()
    gtfs = cfg.raw_dir / "ovapi" / "gtfs-nl.zip"
    if not gtfs.exists():
        raise FileNotFoundError(gtfs)
    for cache in (gtfs.parent / "stop_service_bus.parquet", gtfs.parent / "stop_service_all.parquet"):
        if cache.exists():
            cache.unlink()
            logger.info("Removed stale {}", cache.name)

    ses_path = cfg.raw_dir / "netherlands" / "ses_woa_86092NED_2023.parquet"
    ses = _load_ses(ses_path) if ses_path.exists() else pd.DataFrame(columns=["buurt_code", "ses_score"])

    areas_by_mode: dict[str, pd.DataFrame] = {}
    extras_by_mode: dict[str, dict] = {}
    stops_by_mode: dict[str, pd.DataFrame] = {}
    for mode in ("bus", "all"):
        table = cfg.processed_dir / "netherlands" / f"buurt_table_{mode}.parquet"
        if not table.exists():
            table = cfg.processed_dir / "netherlands" / "buurt_table.parquet"
        areas = pd.read_parquet(table)
        areas["buurt_code"] = areas["buurt_code"].map(_norm_buurt)
        areas = areas.drop(columns=["ses_score", "ses_decile"], errors="ignore")
        areas = areas.merge(ses, on="buurt_code", how="left")
        areas["ses_decile"] = ses_decile_from_score(areas["ses_score"])
        logger.info("mode={} SES join {:.1%} n={}", mode, float(areas["ses_score"].notna().mean()), len(areas))
        stops = load_ovapi_stops(gtfs, mode=mode)
        stop_times = load_ovapi_stop_times(gtfs, mode=mode)
        areas = attach_service_flags(areas, stop_times, stops)
        logger.info(
            "mode={} sunday_desert={} / {} sunday_trips>0={}",
            mode,
            int(areas["sunday_desert"].sum()),
            len(areas),
            int((areas["sunday_trips"] > 0).sum()),
        )
        write_processed(areas, cfg.processed_dir, mode=mode)
        extras = load_ovapi_network(gtfs, mode=mode)
        extras["mode"] = mode
        extras["vintage"] = (
            "OVapi gtfs-nl.zip + calendar_dates.txt, CBS SES-WOA 86092NED (2023), Kerncijfers 85984NED (2024)."
        )
        areas_by_mode[mode] = areas
        extras_by_mode[mode] = extras
        stops_by_mode[mode] = stops

    dest = netherlands_warehouse_path(cfg.project_root)
    vintages = {
        "gtfs": extras_by_mode["bus"]["vintage"],
        "small_areas": f"CBS buurten n={len(areas_by_mode['bus'])}",
        "join_rate": f"{float(areas_by_mode['bus']['ses_score'].notna().mean()):.4f}",
    }
    build_netherlands_warehouse(
        areas_by_mode,
        dest,
        extras_by_mode=extras_by_mode,
        vintages=vintages,
        stops_by_mode=stops_by_mode,
    )
    logger.info("Wrote {}", dest)


if __name__ == "__main__":
    main()
