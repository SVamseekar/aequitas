"""Write NL duckdb from already-processed buurt tables. Does not rescan stop_times."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.netherlands.network import load_ovapi_network
from aequitas.netherlands.warehouse import build_netherlands_warehouse, netherlands_warehouse_path


def main() -> None:
    cfg = PipelineConfig()
    gtfs = cfg.raw_dir / "ovapi" / "gtfs-nl.zip"
    areas_by_mode = {}
    extras_by_mode = {}
    for mode in ("bus", "all"):
        path = cfg.processed_dir / "netherlands" / f"buurt_table_{mode}.parquet"
        areas = pd.read_parquet(path)
        logger.info(
            "{} n={} sunday_desert={} ses={}",
            mode,
            len(areas),
            int(areas["sunday_desert"].sum()),
            int(areas["ses_score"].notna().sum()) if "ses_score" in areas else 0,
        )
        extras = load_ovapi_network(gtfs, mode=mode, include_stops_per_route=False)
        extras["mode"] = mode
        extras["vintage"] = (
            "OVapi gtfs-nl.zip + calendar_dates.txt, CBS SES-WOA 86092NED (2023), Kerncijfers 85984NED (2024)."
        )
        areas_by_mode[mode] = areas
        extras_by_mode[mode] = extras
    dest = netherlands_warehouse_path(cfg.project_root)
    tmp = dest.with_suffix(".duckdb.tmp")
    if tmp.exists():
        tmp.unlink()
    build_netherlands_warehouse(
        areas_by_mode,
        dest,
        extras_by_mode=extras_by_mode,
        vintages={"gtfs": extras_by_mode["bus"]["vintage"], "join_rate": "0.743"},
    )
    logger.info("wrote {}", dest)


if __name__ == "__main__":
    main()
