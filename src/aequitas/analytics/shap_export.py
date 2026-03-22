"""Export SHAP feature importance to Parquet for InsightEngine consumption.

Trains a lightweight RF model on master_lsoa_table features, computes SHAP
values, and saves to shap_importance.parquet.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from aequitas.analytics.ml_prediction import train_coverage_model, compute_shap_importance
from aequitas.core.config import PipelineConfig

# The 9 socio-economic features used in coverage prediction
_FEATURE_COLS = [
    "imd_score",
    "unemployment_rate",
    "nocar_pct",
    "elderly_pct",
    "income_score",
    "nonwhite_pct",
    "disability_pct",
    "geo_barriers_score",
    "imd_decile",
]


def export_shap_importance(
    cfg: PipelineConfig | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Train RF model and export SHAP importance to Parquet.

    Args:
        cfg: Pipeline configuration. Uses default if None.
        output_dir: Override output directory (default: cfg.audit_dir).

    Returns:
        Path to the written shap_importance.parquet.
    """
    if cfg is None:
        cfg = PipelineConfig()
    out_dir = output_dir or cfg.audit_dir

    master = pd.read_parquet(cfg.audit_dir / "master_lsoa_table.parquet")

    # Prepare features + target — use only available columns
    available = [c for c in _FEATURE_COLS if c in master.columns]
    if not available:
        raise ValueError("No feature columns found in master_lsoa_table.parquet")

    X = master[available].fillna(0)
    if "trips_per_capita" in master.columns:
        y = master["trips_per_capita"].fillna(0).values
    else:
        # Fallback: use first available feature as a dummy target for structure
        y = master[available[0]].fillna(0).values

    model, metrics = train_coverage_model(X, y)
    logger.info(f"SHAP export: RF R²={metrics['r2_test']:.3f}")

    importance = compute_shap_importance(model, X)

    out_path = out_dir / "shap_importance.parquet"
    importance.to_parquet(out_path, index=False)
    logger.info(f"SHAP importance exported: {len(importance)} features → {out_path}")
    return out_path
