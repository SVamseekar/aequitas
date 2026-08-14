"""Sanity validation — entity counts and join rates, not a locked Gini."""

from __future__ import annotations

from typing import Any

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.core.constants import LSOA_COUNT_ENGLAND, POPULATION_ENGLAND
from aequitas.validation.gates import (
    check_entity_counts,
    check_lsoa_count,
    check_match_rates,
    check_population_total,
)


def _first(cfg: PipelineConfig, name: str):
    for folder in (cfg.processed_dir, cfg.audit_dir):
        path = folder / name
        if path.exists():
            return path
    return None


def validate_sanity(cfg: PipelineConfig) -> dict[str, Any]:
    """LSOA/population/join-rate sanity. Refresh is allowed to change Gini."""
    checks: list[dict[str, Any]] = []

    master_path = _first(cfg, "master_lsoa_table.parquet")
    if master_path is None:
        checks.append(
            {
                "name": "master_lsoa_present",
                "status": "FAIL",
                "expected": True,
                "actual": False,
                "tolerance": "exists",
            }
        )
        return {
            "checks": checks,
            "n_pass": 0,
            "n_fail": 1,
            "n_warn": 0,
            "all_pass": False,
        }

    master = pd.read_parquet(master_path)
    lsoa_n = len(master)
    pop_col = "population" if "population" in master.columns else None
    population = int(master[pop_col].sum()) if pop_col else 0

    lsoa_ok = check_lsoa_count(lsoa_n)
    checks.append(
        {
            "name": "lsoa_count",
            "status": "PASS" if lsoa_ok else "FAIL",
            "expected": LSOA_COUNT_ENGLAND,
            "actual": lsoa_n,
            "tolerance": "exact",
        }
    )

    pop_ok = check_population_total(population)
    checks.append(
        {
            "name": "population_total",
            "status": "PASS" if pop_ok else "FAIL",
            "expected": POPULATION_ENGLAND,
            "actual": population,
            "tolerance": "±100",
        }
    )

    naptan_path = _first(cfg, "naptan_stops.parquet")
    routes_path = _first(cfg, "bods_routes.parquet")
    if naptan_path is not None and routes_path is not None:
        stops_n = len(pd.read_parquet(naptan_path))
        routes_n = len(pd.read_parquet(routes_path))
        entity_ok = check_entity_counts(stops_n, routes_n)
        checks.append(
            {
                "name": "entity_counts",
                "status": "PASS" if entity_ok else "WARN",
                "expected": "stops/routes within ±10% of last snapshot",
                "actual": f"stops={stops_n} routes={routes_n}",
                "tolerance": "±10%",
            }
        )

    if "lsoa_code" in master.columns or "lsoa_cd" in master.columns:
        key = "lsoa_code" if "lsoa_code" in master.columns else "lsoa_cd"
        join_rate = float(master[key].notna().mean())
        join_ok = check_match_rates(join_rate)
        checks.append(
            {
                "name": "lsoa_key_present",
                "status": "PASS" if join_ok else "FAIL",
                "expected": ">=0.999",
                "actual": join_rate,
                "tolerance": "join",
            }
        )

    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    n_fail = sum(1 for c in checks if c["status"] == "FAIL")
    n_warn = sum(1 for c in checks if c["status"] == "WARN")
    logger.info(f"Sanity validation: {n_pass} pass, {n_fail} fail, {n_warn} warn")
    return {
        "checks": checks,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "n_warn": n_warn,
        "all_pass": n_fail == 0,
    }
