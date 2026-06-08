"""Tests for ml_prediction.py — covers a8, d8, g3, g4."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.ml_prediction import build_ml_prediction_stats


def _shap_df():
    return pd.DataFrame({
        "feature": ["imd_score", "unemployment_rate", "nocar_pct", "elderly_pct",
                    "disability_pct", "income_score", "nonwhite_pct", "stops_per_1k", "urban_enc"],
        "mean_abs_shap": [0.00547, 0.00211, 0.08302, 0.00653, 0.01606, 0.00684, 0.03029, 0.06281, 0.0],
    })


@pytest.mark.parametrize("section_id", [
    "a8_coverage_prediction", "d8_feature_importance", "g3_coverage_model", "g4_shap",
])
def test_all_four_sections_produce_identical_national_stats(section_id):
    stats = build_ml_prediction_stats(section_id, shap_df=_shap_df(), r2=0.4719)
    assert stats["r2"] == pytest.approx(0.4719)
    assert stats["top_feature"] == "nocar_pct"
    assert stats["top_importance"] == pytest.approx(0.083, abs=0.001)
    assert stats["n_features"] == 9


def test_empty_shap_df_returns_empty():
    stats = build_ml_prediction_stats("g4_shap", shap_df=pd.DataFrame(), r2=0.4719)
    assert stats == {}


def test_missing_r2_returns_empty():
    stats = build_ml_prediction_stats("g4_shap", shap_df=_shap_df(), r2=None)
    assert stats == {}
