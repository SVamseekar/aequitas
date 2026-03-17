"""Tests for chart_data builder — produces typed JSON payloads for frontend."""

import numpy as np
import pandas as pd
import pytest
from aequitas.intelligence.chart_data_builder import (
    build_horizontal_bar,
    build_scatter_regression,
    build_lorenz_curve,
    build_stacked_bar,
    build_grouped_bar,
    build_box_violin,
    build_choropleth,
    build_heatmap,
    build_shap_bar,
    build_scatter_clusters,
)


def test_horizontal_bar_structure():
    data = pd.DataFrame({
        "label": ["North East", "South East", "London"],
        "value": [12.1, 31.4, 25.0],
    })
    result = build_horizontal_bar(
        data=data, title="Route density", x_label="Routes per 100k",
        y_label="Region", national_avg=22.8,
    )
    assert result["type"] == "horizontal_bar"
    assert len(result["data"]) == 3
    assert result["data"][0]["rank"] == 1  # sorted descending
    assert result["national_avg"] == 22.8


def test_horizontal_bar_sorted():
    data = pd.DataFrame({"label": ["A", "B", "C"], "value": [10, 30, 20]})
    result = build_horizontal_bar(data=data, title="T", x_label="X", y_label="Y")
    values = [d["value"] for d in result["data"]]
    assert values == sorted(values, reverse=True)


def test_scatter_regression_samples():
    np.random.seed(42)
    n = 5000
    x = np.random.randn(n)
    y = 2 * x + np.random.randn(n)
    df = pd.DataFrame({"x": x, "y": y, "id": [f"E{i:08d}" for i in range(n)]})
    result = build_scatter_regression(
        df, x_col="x", y_col="y", id_col="id",
        title="Test", x_label="X", y_label="Y", max_points=2000,
    )
    assert result["type"] == "scatter_regression"
    assert len(result["data"]) <= 2000
    assert result["sample_size"] == n
    assert result["r"] is not None
    assert "regression_line" in result


def test_lorenz_curve():
    values = pd.Series([1.0, 2.0, 3.0, 4.0, 10.0])
    weights = pd.Series([100, 100, 100, 100, 100])
    result = build_lorenz_curve(
        values=values, weights=weights, title="Equity",
        reference_gini=0.36, reference_label="UK Income",
    )
    assert result["type"] == "lorenz_curve"
    assert 0 <= result["gini"] <= 1
    assert result["curve_points"][0]["cum_pop"] == 0.0
    assert result["curve_points"][-1]["cum_pop"] == pytest.approx(1.0, abs=0.01)


def test_stacked_bar():
    result = build_stacked_bar(
        categories=["NE", "SE"],
        series=[
            {"name": "Covered", "values": [80.0, 90.0]},
            {"name": "Not covered", "values": [20.0, 10.0]},
        ],
        title="Coverage",
    )
    assert result["type"] == "stacked_bar"
    assert len(result["categories"]) == 2
    assert len(result["series"]) == 2


def test_grouped_bar():
    result = build_grouped_bar(
        categories=["NE", "SE"],
        series=[
            {"name": "Urban", "values": [4.2, 5.1]},
            {"name": "Rural", "values": [1.3, 1.8]},
        ],
        title="Urban vs Rural",
    )
    assert result["type"] == "grouped_bar"


def test_box_violin():
    groups = {
        "North East": pd.Series([10, 20, 30, 40, 50, 60, 70]),
        "South East": pd.Series([15, 25, 35, 45, 55, 65, 75]),
    }
    result = build_box_violin(groups=groups, title="Route lengths", unit="km")
    assert result["type"] == "box_violin"
    assert len(result["groups"]) == 2
    assert "q1" in result["groups"][0]
    assert "median" in result["groups"][0]


def test_choropleth():
    data = pd.DataFrame({
        "area_code": ["E06000001", "E06000002"],
        "area_name": ["Hartlepool", "Middlesbrough"],
        "value": [12.3, 8.7],
    })
    result = build_choropleth(
        data=data, title="Deserts", geography="lad",
        metric="pct_no_service", colour_scale="RdYlGn",
    )
    assert result["type"] == "choropleth"
    assert len(result["data"]) == 2


def test_heatmap():
    result = build_heatmap(
        x_labels=["1", "2", "3"],
        y_labels=["Urban", "Rural"],
        values=[[60, 55, 50], [40, 35, 30]],
        title="SQI by decile",
        colour_scale="Viridis",
    )
    assert result["type"] == "heatmap"
    assert len(result["values"]) == 2
    assert len(result["values"][0]) == 3


def test_shap_bar():
    features = pd.DataFrame({
        "feature": ["nocar_pct", "imd_score", "elderly_pct"],
        "importance": [0.142, 0.098, 0.067],
    })
    result = build_shap_bar(features=features, title="SHAP", model_r2=0.472)
    assert result["type"] == "shap_bar"
    assert result["model_r2"] == 0.472
    assert len(result["features"]) == 3
    # Should be sorted by importance descending
    importances = [f["importance"] for f in result["features"]]
    assert importances == sorted(importances, reverse=True)


def test_scatter_clusters():
    data = pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [0.5, 1.5, 2.5, 3.5],
        "cluster": [0, 0, 1, 1],
        "id": ["E01", "E02", "E03", "E04"],
    })
    cluster_labels = {0: "Urban", 1: "Rural"}
    result = build_scatter_clusters(
        data=data, cluster_labels=cluster_labels,
        title="Clusters", x_label="PC1", y_label="PC2", max_points=2000,
    )
    assert result["type"] == "scatter_clusters"
    assert len(result["clusters"]) == 2
    assert len(result["data"]) == 4
