"""Tests for coverage prediction model."""

import numpy as np
import pandas as pd
from aequitas.analytics.ml_prediction import train_coverage_model, compute_shap_importance


def test_model_trains():
    np.random.seed(42)
    X = pd.DataFrame(np.random.randn(500, 5), columns=[f"f{i}" for i in range(5)])
    y = np.abs(np.random.randn(500))
    model, metrics = train_coverage_model(X, y)
    assert model is not None
    assert "r2_test" in metrics
    assert metrics["r2_test"] > -1  # better than predicting mean


def test_shap_returns_importance():
    np.random.seed(42)
    X = pd.DataFrame(np.random.randn(200, 3), columns=["a", "b", "c"])
    y = np.abs(X["a"]) * 2 + np.abs(np.random.randn(200)) * 0.1  # a is clearly most important
    model, _ = train_coverage_model(X, y)
    importance = compute_shap_importance(model, X)
    assert importance.iloc[0]["feature"] == "a"
