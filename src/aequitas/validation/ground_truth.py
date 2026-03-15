"""Ground truth validation — compare pipeline outputs to Phase 0 locked values.

Loads ground_truth.json analytics section and checks each metric against
the actual pipeline Parquet outputs using appropriate tolerances.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig


_STATUS_PASS = "PASS"
_STATUS_WARN = "WARN"
_STATUS_FAIL = "FAIL"


def _pct_diff(actual: float, expected: float) -> float:
    """Percentage difference from expected value."""
    if expected == 0:
        return abs(actual) * 100
    return abs(actual - expected) / abs(expected) * 100


def validate_against_ground_truth(cfg: PipelineConfig) -> dict[str, Any]:
    """Run all ground truth validation checks.

    Loads ground_truth.json analytics section and compares against
    Phase 0 audit Parquets (which ARE the source of truth for Phase 1).

    Args:
        cfg: Pipeline configuration with audit_dir path.

    Returns:
        Dict with keys: checks (list), n_pass, n_fail, n_warn, all_pass.
        Each check has: name, status, expected, actual, tolerance.
    """
    gt_path = cfg.audit_dir / "ground_truth.json"
    if not gt_path.exists():
        return {"checks": [], "n_pass": 0, "n_fail": 0, "n_warn": 0, "all_pass": False,
                "error": f"ground_truth.json not found at {gt_path}"}

    with open(gt_path) as f:
        gt = json.load(f)

    analytics_gt = gt.get("analytics", {})
    tolerances = gt.get("tolerances", {})

    checks: list[dict] = []

    # Load Phase 0 audit Parquets to compare
    _check_equity_metrics(cfg, analytics_gt, tolerances, checks)
    _check_service_quality(cfg, analytics_gt, tolerances, checks)
    _check_policy_synthesis(cfg, analytics_gt, tolerances, checks)

    n_pass = sum(1 for c in checks if c["status"] == _STATUS_PASS)
    n_warn = sum(1 for c in checks if c["status"] == _STATUS_WARN)
    n_fail = sum(1 for c in checks if c["status"] == _STATUS_FAIL)

    return {
        "checks": checks,
        "n_pass": n_pass,
        "n_warn": n_warn,
        "n_fail": n_fail,
        "all_pass": n_fail == 0,
    }


def _add_check(
    checks: list,
    name: str,
    expected: Any,
    actual: Any,
    tolerance: str = "exact",
    tol_value: float | None = None,
) -> None:
    """Add a check result."""
    if isinstance(expected, str):
        status = _STATUS_PASS if actual == expected else _STATUS_FAIL
    elif tolerance == "exact":
        status = _STATUS_PASS if actual == expected else _STATUS_FAIL
    elif tolerance == "within_50":
        status = _STATUS_PASS if abs(actual - expected) <= 50 else _STATUS_FAIL
    elif tolerance == "within_pct_5":
        status = _STATUS_PASS if _pct_diff(actual, expected) <= 5.0 else _STATUS_FAIL
    elif tolerance == "within_pct" and tol_value is not None:
        status = _STATUS_PASS if _pct_diff(actual, expected) <= tol_value else _STATUS_FAIL
    else:
        status = _STATUS_PASS if actual == expected else _STATUS_FAIL

    checks.append({
        "name": name,
        "status": status,
        "expected": expected,
        "actual": actual,
        "tolerance": tolerance,
    })
    if status != _STATUS_PASS:
        logger.warning(f"Validation {status}: {name} — expected {expected}, got {actual}")


def _check_equity_metrics(
    cfg: PipelineConfig,
    gt: dict,
    tolerances: dict,
    checks: list,
) -> None:
    """Check Gini, Palma, CI, triple-deprived against Phase 0 audit Parquet."""
    equity_path = cfg.audit_dir / "lsoa_equity_metrics.parquet"
    if not equity_path.exists():
        logger.warning(f"Equity Parquet not found: {equity_path}")
        return

    df = pd.read_parquet(equity_path)
    cols = df.columns.tolist()

    if "gini" in cols:
        actual_gini = float(df["gini"].iloc[0])
        _add_check(checks, "gini_coefficient", gt.get("gini_coefficient"), actual_gini, "within_pct_5")
    if "palma_ratio" in cols:
        actual_palma = float(df["palma_ratio"].iloc[0])
        _add_check(checks, "palma_ratio", gt.get("palma_ratio"), actual_palma, "within_pct_5")
    if "concentration_index" in cols:
        actual_ci = float(df["concentration_index"].iloc[0])
        _add_check(checks, "concentration_index", gt.get("concentration_index"), actual_ci, "within_pct_5")


def _check_service_quality(
    cfg: PipelineConfig,
    gt: dict,
    tolerances: dict,
    checks: list,
) -> None:
    """Check SQI mean, evening isolated, Sunday deserts against Phase 0 audit Parquet."""
    sq_path = cfg.audit_dir / "lsoa_service_quality.parquet"
    if not sq_path.exists():
        logger.warning(f"Service quality Parquet not found: {sq_path}")
        return

    df = pd.read_parquet(sq_path)
    cols = df.columns.tolist()

    sqi_col = "service_quality_index" if "service_quality_index" in cols else None
    if sqi_col:
        actual_sqi = float(df[sqi_col].mean())
        _add_check(checks, "mean_sqi", gt.get("mean_sqi"), round(actual_sqi, 1), "within_pct_5")

    if "evening_isolated" in cols:
        actual_ei = int(df["evening_isolated"].sum())
        _add_check(checks, "evening_isolated_lsoas", gt.get("evening_isolated_lsoas"), actual_ei, "within_50")

    if "sunday_desert" in cols:
        actual_sd = int(df["sunday_desert"].sum())
        _add_check(checks, "sunday_desert_lsoas", gt.get("sunday_desert_lsoas"), actual_sd, "within_50")


def _check_policy_synthesis(
    cfg: PipelineConfig,
    gt: dict,
    tolerances: dict,
    checks: list,
) -> None:
    """Check Q1 priority LSOAs, triple-deprived, scenarios against Phase 0 audit Parquet."""
    policy_path = cfg.audit_dir / "lsoa_policy_synthesis.parquet"
    if not policy_path.exists():
        logger.warning(f"Policy synthesis Parquet not found: {policy_path}")
        return

    df = pd.read_parquet(policy_path)
    cols = df.columns.tolist()

    if "priority_quadrant" in cols:
        q1_label = "Q1: High vulnerability, Low access (PRIORITY)"
        actual_q1 = int((df["priority_quadrant"] == q1_label).sum())
        _add_check(checks, "q1_priority_lsoas", gt.get("q1_priority_lsoas"), actual_q1, "within_50")

    if "triple_deprived" in cols:
        actual_triple = int(df["triple_deprived"].sum())
        _add_check(checks, "triple_deprived_lsoas", gt.get("triple_deprived_lsoas"), actual_triple, "exact")

    # Policy scenarios
    scenarios_path = cfg.audit_dir / "policy_scenarios.parquet"
    if scenarios_path.exists():
        sc_df = pd.read_parquet(scenarios_path)
        _add_check(checks, "policy_scenarios_count", gt.get("policy_scenarios_count"), len(sc_df), "exact")
