"""Tests for chart_dispatch.build_chart_data — the 19 sections in Task 1."""

import pandas as pd
import pytest

from aequitas.intelligence.section_registry import SECTION_REGISTRY
from aequitas.warehouse.chart_dispatch import build_chart_data
from aequitas.warehouse.precompute import _Sources


def _empty_sources(**overrides: object) -> _Sources:
    base = dict(
        policy_df=pd.DataFrame(),
        equity_df=pd.DataFrame(),
        equity_summary={},
        route_geometries_df=pd.DataFrame(),
        route_clusters_df=pd.DataFrame(),
        lsoa_clusters_df=pd.DataFrame(),
        shap_df=pd.DataFrame(),
        anomalies_df=pd.DataFrame(),
        lta_df=pd.DataFrame(),
        policy_scenarios_df=pd.DataFrame(),
        service_levels_df=pd.DataFrame(),
        service_quality_df=pd.DataFrame(),
        appraisal_df=pd.DataFrame(),
        national_median_trips_per_capita=0.0,
        ranking_df=pd.DataFrame(),
        correlation_df=pd.DataFrame(),
        rf_r2=None,
    )
    base.update(overrides)
    return _Sources(**base)


# ---------------------------------------------------------------------------
# scatter_regression — correlation-based sections (b5, d1-d5)
# ---------------------------------------------------------------------------

_CORR_DF = pd.DataFrame({
    "lsoa_cd": [f"E0100000{i}" for i in range(8)],
    "imd_score": [10, 20, 30, 40, 50, 60, 70, 80],
    "trips_per_capita": [5, 4, 6, 3, 7, 2, 8, 1],
    "service_quality_index": [60, 55, 65, 50, 70, 45, 75, 40],
    "unemployment_rate": [3, 4, 5, 6, 7, 8, 9, 10],
    "nocar_pct": [10, 15, 20, 25, 30, 35, 40, 45],
    "elderly_pct": [12, 14, 16, 18, 20, 22, 24, 26],
    "income_score": [1, 2, 3, 4, 5, 6, 7, 8],
})


@pytest.mark.parametrize("section_id", [
    "b5_frequency_deprivation",
    "d1_coverage_deprivation",
    "d2_coverage_unemployment",
    "d3_coverage_car",
    "d4_coverage_elderly",
    "d5_coverage_income",
])
def test_correlation_scatter_sections(section_id: str) -> None:
    sources = _empty_sources(correlation_df=_CORR_DF)
    stats = {"r": 0.5, "p_value": 0.01, "n": 8}
    chart = build_chart_data(
        section_id=section_id, stats=stats, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=_CORR_DF["lsoa_cd"],
    )
    assert chart["type"] == "scatter_regression" == SECTION_REGISTRY[section_id].chart_type
    assert chart["title"] == SECTION_REGISTRY[section_id].title
    assert "data" in chart
    assert "regression_line" in chart
    assert "r" in chart
    assert len(chart["data"]) == 8


def test_correlation_scatter_empty_stats_returns_empty() -> None:
    sources = _empty_sources(correlation_df=_CORR_DF)
    chart = build_chart_data(
        section_id="d1_coverage_deprivation", stats={}, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=_CORR_DF["lsoa_cd"],
    )
    assert chart == {}


def test_correlation_scatter_too_few_rows_returns_empty() -> None:
    small_df = _CORR_DF.head(2)
    sources = _empty_sources(correlation_df=small_df)
    chart = build_chart_data(
        section_id="d1_coverage_deprivation", stats={"r": 0.5, "p_value": 0.5, "n": 2},
        region="all", region_name="England", urban_rural="all",
        filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=small_df["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# c5_length_vs_frequency
# ---------------------------------------------------------------------------

_ROUTES_DF = pd.DataFrame({
    "route_id": [f"R{i}" for i in range(6)],
    "primary_region": ["London"] * 3 + ["North West"] * 3,
    "length_km": [10.0, 20.0, 15.0, 5.0, 8.0, 12.0],
    "stop_count": [5, 10, 8, 3, 4, 6],
    "cross_la_int": [0, 1, 0, 0, 1, 0],
})


def test_c5_length_vs_frequency() -> None:
    sources = _empty_sources(route_geometries_df=_ROUTES_DF)
    stats = {"r": 0.5, "p_value": 0.1, "n": 6}
    chart = build_chart_data(
        section_id="c5_length_vs_frequency", stats=stats, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "scatter_regression"
    assert len(chart["data"]) == 6


def test_c5_length_vs_frequency_region_filter() -> None:
    sources = _empty_sources(route_geometries_df=_ROUTES_DF)
    stats = {"r": 0.5, "p_value": 0.1, "n": 3}
    chart = build_chart_data(
        section_id="c5_length_vs_frequency", stats=stats, region="E12000007", region_name="London",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    assert len(chart["data"]) == 3


# ---------------------------------------------------------------------------
# g2_anomalies
# ---------------------------------------------------------------------------

_ANOMALIES_DF = pd.DataFrame({
    "lsoa_cd": [f"E0200000{i}" for i in range(5)],
    "imd_score": [10, 20, 30, 40, 50],
    "service_quality_index": [60, 50, 40, 30, 20],
    "anomaly_type": (
        ["positive_deprived_well_served"] * 2 + ["inefficiency_affluent_poor_served"] * 3
    ),
    "both_anomaly": [True, False, True, False, False],
})


def test_g2_anomalies() -> None:
    sources = _empty_sources(anomalies_df=_ANOMALIES_DF)
    stats = {
        "n_anomalies": 2, "pct_anomalies": 40.0,
        "n_positive": 2, "n_inefficiency": 3, "n_policy_failure": 0,
    }
    chart = build_chart_data(
        section_id="g2_anomalies", stats=stats, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=_ANOMALIES_DF["lsoa_cd"],
    )
    assert chart["type"] == "scatter_regression"
    assert len(chart["data"]) == 5


def test_g2_anomalies_empty_stats() -> None:
    sources = _empty_sources(anomalies_df=_ANOMALIES_DF)
    chart = build_chart_data(
        section_id="g2_anomalies", stats={}, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=_ANOMALIES_DF["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# lorenz_curve — f1_gini, a4_coverage_equity
# ---------------------------------------------------------------------------

_EQUITY_DF = pd.DataFrame({
    "lsoa_cd": [f"E0300000{i}" for i in range(10)],
    "trips_per_capita": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "population": [1000] * 10,
    "imd_decile": [1, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    "v_imd": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05],
})


@pytest.mark.parametrize("section_id", ["f1_gini", "a4_coverage_equity"])
def test_lorenz_curve_sections(section_id: str) -> None:
    sources = _empty_sources(equity_df=_EQUITY_DF)
    stats = {"gini": 0.5, "palma": 2.0, "concentration_index": 0.1, "n_lsoas": 10}
    chart = build_chart_data(
        section_id=section_id, stats=stats, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=_EQUITY_DF["lsoa_cd"],
    )
    assert chart["type"] == "lorenz_curve" == SECTION_REGISTRY[section_id].chart_type
    assert chart["title"] == SECTION_REGISTRY[section_id].title
    assert "curve_points" in chart
    assert "gini" in chart


def test_lorenz_curve_one_decile_returns_empty() -> None:
    one_decile_df = _EQUITY_DF.copy()
    one_decile_df["imd_decile"] = 1
    sources = _empty_sources(equity_df=one_decile_df)
    stats = {"gini": 0.5, "palma": 2.0, "concentration_index": 0.1, "n_lsoas": 10}
    chart = build_chart_data(
        section_id="f1_gini", stats=stats,
        region="all", region_name="England", urban_rural="all",
        filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=one_decile_df["lsoa_cd"],
    )
    assert chart == {}


def test_lorenz_curve_empty_stats_returns_empty() -> None:
    sources = _empty_sources(equity_df=_EQUITY_DF)
    chart = build_chart_data(
        section_id="f1_gini", stats={}, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=_EQUITY_DF["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# shap_bar — a8_coverage_prediction, d8_feature_importance, g4_shap
# ---------------------------------------------------------------------------

_SHAP_DF = pd.DataFrame({
    "feature": ["nocar_pct", "imd_score", "elderly_pct"],
    "mean_abs_shap": [0.3, 0.2, 0.1],
})


@pytest.mark.parametrize(
    "section_id", ["a8_coverage_prediction", "d8_feature_importance", "g4_shap"],
)
def test_shap_bar_sections(section_id: str) -> None:
    sources = _empty_sources(shap_df=_SHAP_DF, rf_r2=0.472)
    stats = {"r2": 0.472, "top_feature": "nocar_pct", "top_importance": 0.3, "n_features": 3}
    chart = build_chart_data(
        section_id=section_id, stats=stats, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "shap_bar" == SECTION_REGISTRY[section_id].chart_type
    assert chart["title"] == SECTION_REGISTRY[section_id].title
    assert "features" in chart
    assert chart["model_r2"] == 0.472


def test_shap_bar_empty_stats_returns_empty() -> None:
    sources = _empty_sources(shap_df=_SHAP_DF, rf_r2=0.472)
    chart = build_chart_data(
        section_id="g4_shap", stats={}, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# scatter_clusters — c6_route_archetypes, g1_route_clusters, d6_transport_poverty
# ---------------------------------------------------------------------------

_ROUTE_CLUSTERS_DF = pd.DataFrame({
    "route_id": [f"R{i}" for i in range(8)],
    "agency_id": ["A1"] * 8,
    "primary_region": ["London"] * 4 + ["North West"] * 4,
    "cluster": [0, 0, 1, 1, -1, 0, 1, -1],
    "length_km": [10, 12, 30, 32, 5, 11, 31, 6],
    "stop_count": [5, 6, 15, 16, 2, 5, 16, 3],
    "n_las": [1, 1, 2, 2, 1, 1, 2, 1],
    "n_shapes": [1, 1, 1, 1, 1, 1, 1, 1],
    "length_cat_enc": [0, 0, 1, 1, 0, 0, 1, 0],
    "cross_la_int": [0, 0, 1, 1, 0, 0, 1, 0],
})

_ROUTE_CLUSTER_STATS = {
    "n_clusters": 2,
    "entity_type": "routes",
    "clusters": [
        {"id": 0, "n": 4, "pct": 50.0, "description": "Short local routes"},
        {"id": 1, "n": 3, "pct": 37.5, "description": "Long-distance routes"},
    ],
}


@pytest.mark.parametrize("section_id", ["c6_route_archetypes", "g1_route_clusters"])
def test_route_cluster_scatter_sections(section_id: str) -> None:
    sources = _empty_sources(route_clusters_df=_ROUTE_CLUSTERS_DF)
    chart = build_chart_data(
        section_id=section_id, stats=_ROUTE_CLUSTER_STATS, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "scatter_clusters" == SECTION_REGISTRY[section_id].chart_type
    assert chart["title"] == SECTION_REGISTRY[section_id].title
    # noise rows (cluster == -1) excluded
    assert all(p["cluster"] != -1 for p in chart["data"])
    assert len(chart["data"]) == 6
    cluster_ids = {c["id"] for c in chart["clusters"]}
    assert cluster_ids == {0, 1}


def test_route_cluster_scatter_empty_stats_returns_empty() -> None:
    sources = _empty_sources(route_clusters_df=_ROUTE_CLUSTERS_DF)
    chart = build_chart_data(
        section_id="g1_route_clusters", stats={}, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


def test_route_cluster_scatter_empty_df_returns_empty() -> None:
    sources = _empty_sources(route_clusters_df=pd.DataFrame())
    chart = build_chart_data(
        section_id="g1_route_clusters", stats=_ROUTE_CLUSTER_STATS,
        region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


_LSOA_CLUSTERS_DF = pd.DataFrame({
    "lsoa_cd": [f"E0300000{i}" for i in range(10)],
    "hdbscan_label": [0, 0, 1, 1, -1, 0, 1, 0, 1, -1],
    "hdbscan_archetype": [
        "Elderly Rural", "Elderly Rural", "Diverse Urban", "Diverse Urban", "Noise",
        "Elderly Rural", "Diverse Urban", "Elderly Rural", "Diverse Urban", "Noise",
    ],
    "gmm_label": [0] * 10,
    "gmm_max_prob": [0.9] * 10,
    "gmm_prob_0": [0.9] * 10,
    "gmm_prob_1": [0.05] * 10,
    "gmm_prob_2": [0.03] * 10,
    "gmm_prob_3": [0.02] * 10,
})

_LSOA_CLUSTER_STATS = {
    "n_clusters": 2,
    "entity_type": "LSOAs",
    "clusters": [
        {"id": "Elderly Rural", "n": 4, "pct": 40.0, "description": "Elderly Rural"},
        {"id": "Diverse Urban", "n": 4, "pct": 40.0, "description": "Diverse Urban"},
    ],
}


def test_d6_transport_poverty() -> None:
    sources = _empty_sources(lsoa_clusters_df=_LSOA_CLUSTERS_DF, equity_df=_EQUITY_DF)
    chart = build_chart_data(
        section_id="d6_transport_poverty", stats=_LSOA_CLUSTER_STATS,
        region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=_LSOA_CLUSTERS_DF["lsoa_cd"],
    )
    expected_type = SECTION_REGISTRY["d6_transport_poverty"].chart_type
    assert chart["type"] == "scatter_clusters" == expected_type
    assert chart["title"] == SECTION_REGISTRY["d6_transport_poverty"].title
    assert all(p["cluster"] != -1 for p in chart["data"])
    assert len(chart["data"]) == 8


def test_d6_transport_poverty_empty_stats_returns_empty() -> None:
    sources = _empty_sources(lsoa_clusters_df=_LSOA_CLUSTERS_DF, equity_df=_EQUITY_DF)
    chart = build_chart_data(
        section_id="d6_transport_poverty", stats={}, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=_LSOA_CLUSTERS_DF["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# box_violin — c1_route_length, c2_stops_per_route
# ---------------------------------------------------------------------------

def _distribution_stats(unit: str) -> dict:
    return {
        "mean": 11.0, "median": 11.0, "std": 1.0, "cv": 0.1, "iqr": 2.0,
        "p10": 5.0, "p90": 20.0, "n_outliers": 0,
        "metric_name": "x", "unit": unit, "skew_label": "symmetric",
    }


@pytest.mark.parametrize(
    "section_id,unit", [("c1_route_length", "km"), ("c2_stops_per_route", "stops")],
)
def test_box_violin_sections(section_id: str, unit: str) -> None:
    sources = _empty_sources(route_geometries_df=_ROUTES_DF)
    stats = _distribution_stats(unit)
    chart = build_chart_data(
        section_id=section_id, stats=stats, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "box_violin" == SECTION_REGISTRY[section_id].chart_type
    assert chart["title"] == SECTION_REGISTRY[section_id].title
    assert chart["unit"] == unit
    assert "groups" in chart
    # region == "all" -> grouped by primary_region
    labels = {g["label"] for g in chart["groups"]}
    assert labels == {"London", "North West"}


def test_box_violin_region_filtered() -> None:
    sources = _empty_sources(route_geometries_df=_ROUTES_DF)
    stats = _distribution_stats("km")
    chart = build_chart_data(
        section_id="c1_route_length", stats=stats, region="E12000007", region_name="London",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    labels = {g["label"] for g in chart["groups"]}
    assert labels == {"London"}


def test_box_violin_empty_routes_returns_empty() -> None:
    sources = _empty_sources(route_geometries_df=pd.DataFrame())
    stats = _distribution_stats("km")
    chart = build_chart_data(
        section_id="c1_route_length", stats=stats, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# heatmap — d7_deprivation_urban_rural
# ---------------------------------------------------------------------------

_REGION_DF = pd.DataFrame({
    "lsoa_cd": [f"E0400000{i}" for i in range(8)],
    "urban_rural": ["Urban"] * 4 + ["Rural"] * 4,
    "imd_decile": [1, 2, 3, 4, 1, 2, 3, 4],
    "trips_per_capita": [10, 8, 6, 4, 5, 4, 3, 2],
    "service_quality_index": [70, 60, 50, 40, 50, 40, 30, 20],
})


def test_d7_heatmap() -> None:
    sources = _empty_sources()
    stats = {
        "x_dimension": "IMD decile", "y_dimension": "urban/rural classification",
        "metric_name": "service quality index",
        "worst_cell": {"label": "Decile 4, Rural", "value": 20.0},
        "best_cell": {"label": "Decile 1, Urban", "value": 70.0},
    }
    chart = build_chart_data(
        section_id="d7_deprivation_urban_rural", stats=stats, region="all", region_name="England",
        urban_rural="all", filtered=_REGION_DF, region_df=_REGION_DF,
        sources=sources, lsoa_cds=_REGION_DF["lsoa_cd"],
    )
    assert chart["type"] == "heatmap" == SECTION_REGISTRY["d7_deprivation_urban_rural"].chart_type
    assert chart["title"] == SECTION_REGISTRY["d7_deprivation_urban_rural"].title
    assert "x_labels" in chart
    assert "y_labels" in chart
    assert "values" in chart
    assert set(chart["y_labels"]) == {"Urban", "Rural"}


def test_d7_heatmap_empty_stats_returns_empty() -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="d7_deprivation_urban_rural", stats={}, region="all", region_name="England",
        urban_rural="all", filtered=_REGION_DF, region_df=_REGION_DF,
        sources=sources, lsoa_cds=_REGION_DF["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# default fallback
# ---------------------------------------------------------------------------

def test_unhandled_section_returns_empty() -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="a1_route_density", stats={"some": "stats"}, region="all", region_name="England",
        urban_rural="all", filtered=pd.DataFrame(), region_df=pd.DataFrame(),
        sources=sources, lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}
