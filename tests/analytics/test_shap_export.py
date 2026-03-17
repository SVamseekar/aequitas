"""Test SHAP importance export."""

import pandas as pd
import pytest

from aequitas.analytics.shap_export import export_shap_importance
from aequitas.core.config import PipelineConfig


def test_export_shap_produces_parquet(tmp_path):
    """SHAP export creates a Parquet with feature + mean_abs_shap columns."""
    cfg = PipelineConfig()

    # Only run if master_lsoa_table exists (CI may not have it)
    master_path = cfg.audit_dir / "master_lsoa_table.parquet"
    if not master_path.exists():
        pytest.skip("master_lsoa_table.parquet not available")

    out = export_shap_importance(cfg, output_dir=tmp_path)
    assert out.exists()
    df = pd.read_parquet(out)
    assert "feature" in df.columns
    assert "mean_abs_shap" in df.columns
    assert len(df) >= 5  # at least 5 features
    # Should be sorted descending
    assert df["mean_abs_shap"].is_monotonic_decreasing
