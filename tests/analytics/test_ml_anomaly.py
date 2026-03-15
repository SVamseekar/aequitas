"""Tests for ML anomaly detection."""

import numpy as np
import pandas as pd
import pytest
from aequitas.analytics.ml_anomaly import detect_anomalies


def _make_lsoa_df(n: int = 500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "lsoa_cd": [f"E01{i:06d}" for i in range(n)],
        "imd_decile": rng.integers(1, 11, n),
        "imd_score": rng.uniform(1, 80, n),
        "nocar_pct": rng.uniform(0, 80, n),
        "elderly_pct": rng.uniform(5, 35, n),
        "disability_pct": rng.uniform(3, 25, n),
        "service_quality_index": rng.uniform(0, 100, n),
        "trips_per_capita": rng.uniform(0, 50, n),
    })


def test_anomaly_count():
    df = _make_lsoa_df(500)
    feature_cols = ["imd_score", "nocar_pct", "elderly_pct", "service_quality_index", "trips_per_capita"]
    result = detect_anomalies(df, feature_cols, contamination=0.05)
    n_anomalies = result["iso_anomaly"].sum()
    # contamination=0.05 → expect ~5% = 25 of 500
    assert 15 <= n_anomalies <= 35


def test_both_anomaly_is_intersection():
    df = _make_lsoa_df(500)
    feature_cols = ["imd_score", "nocar_pct", "elderly_pct", "service_quality_index", "trips_per_capita"]
    result = detect_anomalies(df, feature_cols, contamination=0.05)
    expected = result["iso_anomaly"] & result["lof_anomaly"]
    assert (result["both_anomaly"] == expected).all()


def test_anomaly_type_column():
    df = _make_lsoa_df(500)
    feature_cols = ["imd_score", "nocar_pct", "elderly_pct", "service_quality_index", "trips_per_capita"]
    result = detect_anomalies(df, feature_cols, contamination=0.05)
    valid_types = {
        "normal",
        "positive_deprived_well_served",
        "inefficiency_affluent_poor_served",
        "policy_failure_elderly_no_service",
        "other_anomaly",
    }
    assert set(result["anomaly_type"].unique()).issubset(valid_types)


def test_scores_are_floats():
    df = _make_lsoa_df(200)
    feature_cols = ["imd_score", "nocar_pct", "service_quality_index"]
    result = detect_anomalies(df, feature_cols, contamination=0.05)
    assert result["iso_score"].dtype == float
    assert result["lof_score"].dtype == float
