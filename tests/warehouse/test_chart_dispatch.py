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
        route_urban_rural_df=pd.DataFrame(),
        route_trip_frequency_df=pd.DataFrame(),
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

_CORR_DF = pd.DataFrame(
    {
        "lsoa_cd": [f"E0100000{i}" for i in range(8)],
        "imd_score": [10, 20, 30, 40, 50, 60, 70, 80],
        "stops_per_1k": [5.0, 4.0, 6.0, 3.0, 7.0, 2.0, 8.0, 1.0],
        "trips_per_capita": [5, 4, 6, 3, 7, 2, 8, 1],
        "service_quality_index": [60, 55, 65, 50, 70, 45, 75, 40],
        "unemployment_rate": [3, 4, 5, 6, 7, 8, 9, 10],
        "nocar_pct": [10, 15, 20, 25, 30, 35, 40, 45],
        "elderly_pct": [12, 14, 16, 18, 20, 22, 24, 26],
        "income_score": [1, 2, 3, 4, 5, 6, 7, 8],
        "nonwhite_pct": [5, 10, 15, 20, 25, 30, 35, 40],
    }
)


@pytest.mark.parametrize(
    "section_id",
    [
        "b5_frequency_deprivation",
        "d1_coverage_deprivation",
        "d2_coverage_unemployment",
        "d3_coverage_car",
        "d4_coverage_elderly",
        "d5_coverage_income",
        "f3_ethnic_access",
    ],
)
def test_correlation_scatter_sections(section_id: str) -> None:
    sources = _empty_sources(correlation_df=_CORR_DF)
    stats = {"r": 0.5, "p_value": 0.01, "n": 8}
    chart = build_chart_data(
        section_id=section_id,
        stats=stats,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_CORR_DF["lsoa_cd"],
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
        section_id="d1_coverage_deprivation",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_CORR_DF["lsoa_cd"],
    )
    assert chart == {}


def test_correlation_scatter_too_few_rows_returns_empty() -> None:
    small_df = _CORR_DF.head(2)
    sources = _empty_sources(correlation_df=small_df)
    chart = build_chart_data(
        section_id="d1_coverage_deprivation",
        stats={"r": 0.5, "p_value": 0.5, "n": 2},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=small_df["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# c5_length_vs_frequency
# ---------------------------------------------------------------------------

_ROUTES_DF = pd.DataFrame(
    {
        "route_id": [f"R{i}" for i in range(6)],
        "primary_region": ["London"] * 3 + ["North West"] * 3,
        "length_km": [10.0, 20.0, 15.0, 5.0, 8.0, 12.0],
        "stop_count": [5, 10, 8, 3, 4, 6],
        "cross_la_int": [0, 1, 0, 0, 1, 0],
    }
)


def test_c5_length_vs_frequency() -> None:
    sources = _empty_sources(route_geometries_df=_ROUTES_DF)
    stats = {"r": 0.5, "p_value": 0.1, "n": 6}
    chart = build_chart_data(
        section_id="c5_length_vs_frequency",
        stats=stats,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "scatter_regression"
    assert len(chart["data"]) == 6


def test_c5_length_vs_frequency_region_filter() -> None:
    sources = _empty_sources(route_geometries_df=_ROUTES_DF)
    stats = {"r": 0.5, "p_value": 0.1, "n": 3}
    chart = build_chart_data(
        section_id="c5_length_vs_frequency",
        stats=stats,
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert len(chart["data"]) == 3


# ---------------------------------------------------------------------------
# g2_anomalies
# ---------------------------------------------------------------------------

_ANOMALIES_DF = pd.DataFrame(
    {
        "lsoa_cd": [f"E0200000{i}" for i in range(5)],
        "imd_score": [10, 20, 30, 40, 50],
        "service_quality_index": [60, 50, 40, 30, 20],
        "anomaly_type": (
            ["positive_deprived_well_served"] * 2 + ["inefficiency_affluent_poor_served"] * 3
        ),
        "both_anomaly": [True, False, True, False, False],
    }
)


def test_g2_anomalies() -> None:
    sources = _empty_sources(anomalies_df=_ANOMALIES_DF)
    stats = {
        "n_anomalies": 2,
        "pct_anomalies": 40.0,
        "n_positive": 2,
        "n_inefficiency": 3,
        "n_policy_failure": 0,
    }
    chart = build_chart_data(
        section_id="g2_anomalies",
        stats=stats,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_ANOMALIES_DF["lsoa_cd"],
    )
    assert chart["type"] == "scatter_regression"
    assert len(chart["data"]) == 5


def test_g2_anomalies_empty_stats() -> None:
    sources = _empty_sources(anomalies_df=_ANOMALIES_DF)
    chart = build_chart_data(
        section_id="g2_anomalies",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_ANOMALIES_DF["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# lorenz_curve — f1_gini, a4_coverage_equity
# ---------------------------------------------------------------------------

_EQUITY_DF = pd.DataFrame(
    {
        "lsoa_cd": [f"E0300000{i}" for i in range(10)],
        "trips_per_capita": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "population": [1000] * 10,
        "imd_decile": [1, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "v_imd": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05],
    }
)


@pytest.mark.parametrize("section_id", ["f1_gini", "a4_coverage_equity"])
def test_lorenz_curve_sections(section_id: str) -> None:
    sources = _empty_sources(equity_df=_EQUITY_DF)
    stats = {"gini": 0.5, "palma": 2.0, "concentration_index": 0.1, "n_lsoas": 10}
    chart = build_chart_data(
        section_id=section_id,
        stats=stats,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_EQUITY_DF["lsoa_cd"],
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
        section_id="f1_gini",
        stats=stats,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=one_decile_df["lsoa_cd"],
    )
    assert chart == {}


def test_lorenz_curve_empty_stats_returns_empty() -> None:
    sources = _empty_sources(equity_df=_EQUITY_DF)
    chart = build_chart_data(
        section_id="f1_gini",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_EQUITY_DF["lsoa_cd"],
    )
    assert chart == {}


@pytest.mark.parametrize("section_id", ["f1_gini", "a4_coverage_equity"])
def test_lorenz_curve_insufficient_data_stats_returns_empty(section_id: str) -> None:
    sources = _empty_sources(equity_df=_EQUITY_DF)
    chart = build_chart_data(
        section_id=section_id,
        stats={"insufficient_data": True, "n_lsoas": 5},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_EQUITY_DF["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# shap_bar — a8_coverage_prediction, d8_feature_importance, g4_shap
# ---------------------------------------------------------------------------

_SHAP_DF = pd.DataFrame(
    {
        "feature": ["nocar_pct", "imd_score", "elderly_pct"],
        "mean_abs_shap": [0.3, 0.2, 0.1],
    }
)


@pytest.mark.parametrize(
    "section_id",
    ["a8_coverage_prediction", "d8_feature_importance", "g4_shap"],
)
def test_shap_bar_sections(section_id: str) -> None:
    sources = _empty_sources(shap_df=_SHAP_DF, rf_r2=0.472)
    stats = {"r2": 0.472, "top_feature": "nocar_pct", "top_importance": 0.3, "n_features": 3}
    chart = build_chart_data(
        section_id=section_id,
        stats=stats,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "shap_bar" == SECTION_REGISTRY[section_id].chart_type
    assert chart["title"] == SECTION_REGISTRY[section_id].title
    assert "features" in chart
    assert chart["model_r2"] == 0.472


def test_shap_bar_empty_stats_returns_empty() -> None:
    sources = _empty_sources(shap_df=_SHAP_DF, rf_r2=0.472)
    chart = build_chart_data(
        section_id="g4_shap",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# scatter_clusters — c6_route_archetypes, g1_route_clusters, d6_transport_poverty
# ---------------------------------------------------------------------------

_ROUTE_CLUSTERS_DF = pd.DataFrame(
    {
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
    }
)

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
        section_id=section_id,
        stats=_ROUTE_CLUSTER_STATS,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "scatter_clusters" == SECTION_REGISTRY[section_id].chart_type
    assert chart["title"] == SECTION_REGISTRY[section_id].title
    # noise rows (cluster == -1) excluded
    assert all(p["cluster"] != -1 for p in chart["data"])
    assert len(chart["data"]) == 6
    cluster_ids = {c["id"] for c in chart["clusters"]}
    assert cluster_ids == {0, 1}
    # A10 regression guard: legend must carry real descriptions, not
    # placeholder "undefined" labels, and must not include the -1 noise
    # cluster.
    assert -1 not in cluster_ids
    for c in chart["clusters"]:
        assert c["label"]
        assert "undefined" not in c["label"].lower()


def test_route_cluster_scatter_empty_stats_returns_empty() -> None:
    sources = _empty_sources(route_clusters_df=_ROUTE_CLUSTERS_DF)
    chart = build_chart_data(
        section_id="g1_route_clusters",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


def test_route_cluster_scatter_empty_df_returns_empty() -> None:
    sources = _empty_sources(route_clusters_df=pd.DataFrame())
    chart = build_chart_data(
        section_id="g1_route_clusters",
        stats=_ROUTE_CLUSTER_STATS,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


_LSOA_CLUSTERS_DF = pd.DataFrame(
    {
        "lsoa_cd": [f"E0300000{i}" for i in range(10)],
        "hdbscan_label": [0, 0, 1, 1, -1, 0, 1, 0, 1, -1],
        "hdbscan_archetype": [
            "Elderly Rural",
            "Elderly Rural",
            "Diverse Urban",
            "Diverse Urban",
            "Noise",
            "Elderly Rural",
            "Diverse Urban",
            "Elderly Rural",
            "Diverse Urban",
            "Noise",
        ],
        "gmm_label": [0] * 10,
        "gmm_max_prob": [0.9] * 10,
        "gmm_prob_0": [0.9] * 10,
        "gmm_prob_1": [0.05] * 10,
        "gmm_prob_2": [0.03] * 10,
        "gmm_prob_3": [0.02] * 10,
    }
)

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
        section_id="d6_transport_poverty",
        stats=_LSOA_CLUSTER_STATS,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_LSOA_CLUSTERS_DF["lsoa_cd"],
    )
    expected_type = SECTION_REGISTRY["d6_transport_poverty"].chart_type
    assert chart["type"] == "scatter_clusters" == expected_type
    assert chart["title"] == SECTION_REGISTRY["d6_transport_poverty"].title
    assert all(p["cluster"] != -1 for p in chart["data"])
    assert len(chart["data"]) == 8


def test_d6_transport_poverty_empty_stats_returns_empty() -> None:
    sources = _empty_sources(lsoa_clusters_df=_LSOA_CLUSTERS_DF, equity_df=_EQUITY_DF)
    chart = build_chart_data(
        section_id="d6_transport_poverty",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_LSOA_CLUSTERS_DF["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# box_violin — c1_route_length, c2_stops_per_route
# ---------------------------------------------------------------------------


def _distribution_stats(unit: str) -> dict:
    return {
        "mean": 11.0,
        "median": 11.0,
        "std": 1.0,
        "cv": 0.1,
        "iqr": 2.0,
        "p10": 5.0,
        "p90": 20.0,
        "n_outliers": 0,
        "metric_name": "x",
        "unit": unit,
        "skew_label": "symmetric",
    }


@pytest.mark.parametrize(
    "section_id,unit",
    [("c1_route_length", "km"), ("c2_stops_per_route", "stops")],
)
def test_box_violin_sections(section_id: str, unit: str) -> None:
    sources = _empty_sources(route_geometries_df=_ROUTES_DF)
    stats = _distribution_stats(unit)
    chart = build_chart_data(
        section_id=section_id,
        stats=stats,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
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
        section_id="c1_route_length",
        stats=stats,
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    labels = {g["label"] for g in chart["groups"]}
    assert labels == {"London"}


def test_box_violin_filtered_by_urban_rural() -> None:
    """c1/c2 box_violin groups should reflect the urban/rural filter (mirrors A6 stats test)."""
    route_ur = pd.DataFrame(
        {
            "route_id": ["R0", "R1", "R2", "R3", "R4", "R5"],
            "urban_rural_classification": [
                "urban",
                "urban",
                "rural",
                "rural",
                "mixed",
                "mixed",
            ],
        }
    )
    sources = _empty_sources(route_geometries_df=_ROUTES_DF, route_urban_rural_df=route_ur)
    stats = _distribution_stats("km")

    def _ranges(urban_rural: str) -> set[tuple[float, float]]:
        chart = build_chart_data(
            section_id="c1_route_length",
            stats=stats,
            region="all",
            region_name="England",
            urban_rural=urban_rural,
            filtered=pd.DataFrame(),
            region_df=pd.DataFrame(),
            sources=sources,
            lsoa_cds=pd.Series(dtype=str),
        )
        return {(g["min"], g["max"]) for g in chart["groups"]}

    ranges_all = _ranges("all")
    ranges_urban = _ranges("urban")
    ranges_rural = _ranges("rural")

    # "all" includes every route's length_km (R0-R5: 5.0-20.0), grouped by region.
    assert ranges_all == {(10.0, 20.0), (5.0, 12.0)}
    # "urban" keeps only R0/R1 (10.0, 20.0), both London; "mixed" R4/R5 excluded.
    assert ranges_urban == {(10.0, 20.0)}
    # "rural" keeps only R2 (London, 15.0) and R3 (North West, 5.0); R4/R5 excluded.
    assert ranges_rural == {(15.0, 15.0), (5.0, 5.0)}
    assert ranges_urban != ranges_all
    assert ranges_rural != ranges_all
    assert ranges_urban != ranges_rural


def test_box_violin_empty_routes_returns_empty() -> None:
    sources = _empty_sources(route_geometries_df=pd.DataFrame())
    stats = _distribution_stats("km")
    chart = build_chart_data(
        section_id="c1_route_length",
        stats=stats,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# heatmap — d7_deprivation_urban_rural
# ---------------------------------------------------------------------------

_REGION_DF = pd.DataFrame(
    {
        "lsoa_cd": [f"E0400000{i}" for i in range(8)],
        "urban_rural": ["Urban"] * 4 + ["Rural"] * 4,
        "imd_decile": [1, 2, 3, 4, 1, 2, 3, 4],
        "trips_per_capita": [10, 8, 6, 4, 5, 4, 3, 2],
        "service_quality_index": [70, 60, 50, 40, 50, 40, 30, 20],
    }
)


def test_d7_heatmap() -> None:
    sources = _empty_sources()
    stats = {
        "x_dimension": "IMD decile",
        "y_dimension": "urban/rural classification",
        "metric_name": "service quality index",
        "worst_cell": {"label": "Decile 4, Rural", "value": 20.0},
        "best_cell": {"label": "Decile 1, Urban", "value": 70.0},
    }
    chart = build_chart_data(
        section_id="d7_deprivation_urban_rural",
        stats=stats,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=_REGION_DF,
        region_df=_REGION_DF,
        sources=sources,
        lsoa_cds=_REGION_DF["lsoa_cd"],
    )
    assert chart["type"] == "heatmap" == SECTION_REGISTRY["d7_deprivation_urban_rural"].chart_type
    assert chart["title"] == SECTION_REGISTRY["d7_deprivation_urban_rural"].title
    assert "x_labels" in chart
    assert "y_labels" in chart
    assert "values" in chart
    assert set(chart["y_labels"]) == {"Urban", "Rural"}

    # values must be derived from service_quality_index (70/60/50/40 Urban,
    # 50/40/30/20 Rural), not trips_per_capita (10/8/6/4 and 5/4/3/2) — the two
    # metrics produce visibly different pivot tables.
    flat_values = [v for row in chart["values"] for v in row]
    assert set(flat_values) == {70.0, 60.0, 50.0, 40.0, 30.0, 20.0}
    assert 10.0 not in flat_values
    assert 8.0 not in flat_values


def test_d7_heatmap_empty_stats_returns_empty() -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="d7_deprivation_urban_rural",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=_REGION_DF,
        region_df=_REGION_DF,
        sources=sources,
        lsoa_cds=_REGION_DF["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# default fallback
# ---------------------------------------------------------------------------


def test_unhandled_section_returns_empty() -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="g3_coverage_model",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


def test_a3_walking_distance_returns_empty() -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="a3_walking_distance",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


def test_g5_scenario_model_returns_kpi_tiles() -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="g5_scenario_model",
        stats={
            "scenario": {
                "population_affected": 1,
                "estimated_annual_cost_m": 1,
                "co2_saving_t_yr": 1,
            }
        },
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "kpi_tiles" == SECTION_REGISTRY["g5_scenario_model"].chart_type
    assert chart["title"] == SECTION_REGISTRY["g5_scenario_model"].title
    assert len(chart["tiles"]) == 3


# ---------------------------------------------------------------------------
# horizontal_bar — ranking-derived (a1, a2, b1, f6, j4, bsa1)
# ---------------------------------------------------------------------------

_RANKING_DF = pd.DataFrame(
    {
        "primary_region": [
            "London",
            "South East",
            "North West",
            "London",
            "South East",
            "North West",
        ],
        "region": ["London", "South East", "North West", "London", "South East", "North West"],
        "route_count": [10, 20, 30, 12, 22, 28],
        "stops_per_1k": [5.0, 4.0, 3.0, 5.5, 4.5, 3.5],
        "service_quality_index": [70, 60, 50, 72, 62, 52],
        "trips_per_capita": [8, 6, 4, 9, 7, 5],
        "vulnerability_index": [0.2, 0.5, 0.8, 0.25, 0.55, 0.85],
        "investment_gap_annual_cost": [100, 200, 300, 110, 210, 310],
        "franchising_readiness": [80, 60, 40, 82, 62, 42],
    }
)


@pytest.mark.parametrize(
    "section_id",
    [
        "a1_route_density",
        "a2_stop_density",
        "b1_frequency",
        "f6_equitable_regions",
        "j4_investment_priority",
        "bsa1_franchising_readiness",
    ],
)
def test_ranking_horizontal_bar_sections(section_id: str) -> None:
    sources = _empty_sources(ranking_df=_RANKING_DF)
    chart = build_chart_data(
        section_id=section_id,
        stats={"best": {}, "worst": {}},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "horizontal_bar" == SECTION_REGISTRY[section_id].chart_type
    assert chart["title"] == SECTION_REGISTRY[section_id].title
    assert "data" in chart
    assert len(chart["data"]) >= 2


@pytest.mark.parametrize(
    "section_id",
    [
        "a1_route_density",
        "a2_stop_density",
        "b1_frequency",
        "f6_equitable_regions",
        "j4_investment_priority",
        "bsa1_franchising_readiness",
    ],
)
def test_ranking_horizontal_bar_region_not_all_returns_kpi_tiles(section_id: str) -> None:
    sources = _empty_sources(ranking_df=_RANKING_DF)
    stats = {
        "region_name": "London",
        "value": 12.3,
        "national_avg": 10.0,
        "vs_national_pct": 23.0,
        "unit": "routes/km²",
    }
    chart = build_chart_data(
        section_id=section_id,
        stats=stats,
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "kpi_tiles"
    assert chart["title"] == SECTION_REGISTRY[section_id].title
    assert len(chart["tiles"]) == 3


@pytest.mark.parametrize(
    "section_id",
    [
        "a1_route_density",
        "j4_investment_priority",
    ],
)
def test_ranking_horizontal_bar_region_not_all_empty_stats_returns_empty(section_id: str) -> None:
    sources = _empty_sources(ranking_df=_RANKING_DF)
    chart = build_chart_data(
        section_id=section_id,
        stats={"region_name": "London"},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# horizontal_bar — b4_route_frequency (own builder, route-grain)
# ---------------------------------------------------------------------------


def test_b4_route_frequency_chart_combines_top_and_bottom() -> None:
    stats = {
        "top_routes": [
            {"route_short_name": "A1", "agency_name": "First Bristol", "n_trips_per_day": 100, "primary_region": "South West"},
            {"route_short_name": "2", "agency_name": "First Portsmouth", "n_trips_per_day": 80, "primary_region": "South East"},
        ],
        "bottom_routes": [
            {"route_short_name": "Z9", "agency_name": "Tiny Bus Co", "n_trips_per_day": 1, "primary_region": "North East"},
            {"route_short_name": "Y8", "agency_name": "Tiny Bus Co", "n_trips_per_day": 2, "primary_region": "North East"},
        ],
        "n_routes": 100,
        "scope_label": "England",
        "unit": "trips/day",
    }
    chart = build_chart_data(
        section_id="b4_route_frequency",
        stats=stats,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=_empty_sources(),
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "horizontal_bar" == SECTION_REGISTRY["b4_route_frequency"].chart_type
    assert chart["title"] == SECTION_REGISTRY["b4_route_frequency"].title
    assert len(chart["data"]) == 4
    assert chart["data"][0]["label"] == "A1 (First Bristol)"
    assert chart["data"][0]["value"] == 100


def test_b4_route_frequency_chart_empty_stats_returns_empty() -> None:
    chart = build_chart_data(
        section_id="b4_route_frequency",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=_empty_sources(),
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


def test_ranking_horizontal_bar_empty_ranking_df_returns_empty() -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="a1_route_density",
        stats={"best": {}, "worst": {}},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# kpi_tiles — scenario-derived (ps1-ps4, g5)
# ---------------------------------------------------------------------------

_SCENARIO_STATS = {
    "scenario": {
        "name": "Frequency Restoration",
        "scope": "England",
        "population_affected": 5_000_000,
        "annual_additional_trips": 1000,
        "estimated_annual_cost_m": 50.0,
        "co2_saving_t_yr": 1200.0,
        "confidence": "medium",
    }
}


@pytest.mark.parametrize(
    "section_id",
    [
        "ps1_freq_restoration",
        "ps2_evening_extension",
        "ps3_drt_rural",
        "ps4_franchise",
        "g5_scenario_model",
    ],
)
def test_scenario_kpi_tile_sections(section_id: str) -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id=section_id,
        stats=_SCENARIO_STATS,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "kpi_tiles" == SECTION_REGISTRY[section_id].chart_type
    assert chart["title"] == SECTION_REGISTRY[section_id].title
    assert len(chart["tiles"]) == 3
    labels = {tile["label"] for tile in chart["tiles"]}
    assert labels == {"Population affected", "Annual cost", "CO₂ saved"}
    population_tile = next(t for t in chart["tiles"] if t["label"] == "Population affected")
    assert population_tile["value"] == 5_000_000
    assert population_tile["unit"] == "people"


def test_scenario_kpi_tiles_empty_stats_returns_empty() -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="ps1_freq_restoration",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# a7_investment_gap
# ---------------------------------------------------------------------------

_POLICY_DF_A7 = pd.DataFrame(
    {
        "lsoa_cd": [f"E0100000{i}" for i in range(6)],
        "region": ["London", "London", "South East", "South East", "North West", "North West"],
        "trips_per_capita": [2.0, 3.0, 8.0, 9.0, 1.0, 1.5],
    }
)


def test_a7_investment_gap() -> None:
    sources = _empty_sources(policy_df=_POLICY_DF_A7, national_median_trips_per_capita=5.0)
    chart = build_chart_data(
        section_id="a7_investment_gap",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "horizontal_bar" == SECTION_REGISTRY["a7_investment_gap"].chart_type
    assert chart["title"] == SECTION_REGISTRY["a7_investment_gap"].title
    labels = {item["label"] for item in chart["data"]}
    assert "South East" not in labels  # all rows above national median, no gap
    assert "London" in labels
    assert "North West" in labels


def test_a7_investment_gap_region_not_all_returns_empty() -> None:
    sources = _empty_sources(policy_df=_POLICY_DF_A7, national_median_trips_per_capita=5.0)
    chart = build_chart_data(
        section_id="a7_investment_gap",
        stats={},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# c3_operator_hhi
# ---------------------------------------------------------------------------

_ROUTES_C3 = pd.DataFrame(
    {
        "route_id": [f"R{i}" for i in range(8)],
        "primary_region": ["London"] * 4 + ["South East"] * 4,
        "agency_name": ["Op A", "Op A", "Op B", "Op C", "Op A", "Op B", "Op C", "Op D"],
    }
)


def test_c3_operator_hhi() -> None:
    sources = _empty_sources(route_geometries_df=_ROUTES_C3)
    chart = build_chart_data(
        section_id="c3_operator_hhi",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "horizontal_bar" == SECTION_REGISTRY["c3_operator_hhi"].chart_type
    assert len(chart["data"]) == 2


def test_c3_operator_hhi_region_not_all_returns_kpi_tiles() -> None:
    sources = _empty_sources(route_geometries_df=_ROUTES_C3)
    stats = {
        "hhi": 2500.0,
        "region_name": "London",
        "top_operator": "Op A",
        "top_operator_share": 50.0,
    }
    chart = build_chart_data(
        section_id="c3_operator_hhi",
        stats=stats,
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "kpi_tiles"
    assert chart["title"] == SECTION_REGISTRY["c3_operator_hhi"].title
    assert len(chart["tiles"]) == 2
    for tile in chart["tiles"]:
        assert isinstance(tile["value"], (int, float))
    assert chart["tiles"][0]["label"] == "HHI"
    assert chart["tiles"][0]["value"] == 2500.0
    assert "Op A" in chart["tiles"][1]["label"]
    assert chart["tiles"][1]["value"] == 50.0


def test_c3_operator_hhi_region_not_all_empty_stats_returns_empty() -> None:
    sources = _empty_sources(route_geometries_df=_ROUTES_C3)
    chart = build_chart_data(
        section_id="c3_operator_hhi",
        stats={},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


def test_c3_operator_hhi_missing_columns_returns_empty() -> None:
    sources = _empty_sources(route_geometries_df=pd.DataFrame({"route_id": ["R1"]}))
    chart = build_chart_data(
        section_id="c3_operator_hhi",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# f2_disparity_ratio
# ---------------------------------------------------------------------------

_EQUITY_DF_F2 = pd.DataFrame(
    {
        "lsoa_cd": [f"E0100000{i}" for i in range(8)],
        "imd_decile": [1, 1, 2, 2, 3, 3, 4, 4],
        "trips_per_capita": [10, 12, 8, 7, 6, 5, 4, 3],
    }
)


def test_f2_disparity_ratio() -> None:
    sources = _empty_sources(equity_df=_EQUITY_DF_F2)
    chart = build_chart_data(
        section_id="f2_disparity_ratio",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_EQUITY_DF_F2["lsoa_cd"],
    )
    assert chart["type"] == "horizontal_bar" == SECTION_REGISTRY["f2_disparity_ratio"].chart_type
    labels = {item["label"] for item in chart["data"]}
    assert "Decile 1" in labels


def test_f2_disparity_ratio_empty_stats_returns_empty() -> None:
    sources = _empty_sources(equity_df=_EQUITY_DF_F2)
    chart = build_chart_data(
        section_id="f2_disparity_ratio",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_EQUITY_DF_F2["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# j1_economic_value, j2_bcr, j3_carbon
# ---------------------------------------------------------------------------

_APPRAISAL_DF = pd.DataFrame(
    {
        "lsoa_cd": [f"E0100000{i}" for i in range(6)],
        "region": ["London", "London", "South East", "South East", "North West", "North West"],
        "annual_time_benefit": [1e6, 2e6, 3e6, 4e6, 5e6, 6e6],
        "pv_benefits": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
        "pv_costs": [5.0, 5.0, 10.0, 10.0, 100.0, 100.0],
        "modal_shift_co2_net_saving_kg": [1000, 2000, 3000, 4000, 5000, 6000],
    }
)


@pytest.mark.parametrize(
    "section_id,x_label",
    [
        ("j1_economic_value", "Annual benefit (£m)"),
        ("j2_bcr", "BCR"),
        ("j3_carbon", "Net CO₂ saved (t/yr)"),
    ],
)
def test_appraisal_horizontal_bar_sections(section_id: str, x_label: str) -> None:
    sources = _empty_sources(appraisal_df=_APPRAISAL_DF)
    chart = build_chart_data(
        section_id=section_id,
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_APPRAISAL_DF["lsoa_cd"],
    )
    assert chart["type"] == "horizontal_bar" == SECTION_REGISTRY[section_id].chart_type
    assert chart["x_label"] == x_label
    assert len(chart["data"]) == 3


@pytest.mark.parametrize("section_id", ["j2_bcr"])
def test_appraisal_horizontal_bar_region_not_all_returns_empty(section_id: str) -> None:
    sources = _empty_sources(appraisal_df=_APPRAISAL_DF)
    chart = build_chart_data(
        section_id=section_id,
        stats={},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_APPRAISAL_DF["lsoa_cd"],
    )
    assert chart == {}


def test_j1_economic_value_region_not_all_returns_kpi_tiles() -> None:
    sources = _empty_sources(appraisal_df=_APPRAISAL_DF)
    stats = {
        "region_name": "London",
        "annual_benefit": 3_000_000.0,
        "n_trips": 50_000.0,
        "vot": 12.34,
    }
    chart = build_chart_data(
        section_id="j1_economic_value",
        stats=stats,
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_APPRAISAL_DF["lsoa_cd"],
    )
    assert chart["type"] == "kpi_tiles"
    assert chart["title"] == SECTION_REGISTRY["j1_economic_value"].title
    assert len(chart["tiles"]) == 3


def test_j1_economic_value_region_not_all_empty_stats_returns_empty() -> None:
    sources = _empty_sources(appraisal_df=_APPRAISAL_DF)
    chart = build_chart_data(
        section_id="j1_economic_value",
        stats={},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_APPRAISAL_DF["lsoa_cd"],
    )
    assert chart == {}


def test_j3_carbon_region_not_all_returns_kpi_tiles() -> None:
    sources = _empty_sources(appraisal_df=_APPRAISAL_DF)
    stats = {
        "co2_saving_tonnes": 31.2,
        "co2_value_k": 5.4,
        "scope": "London",
        "carbon_price": 0.173,
        "modal_shift_trips": 1234.0,
    }
    chart = build_chart_data(
        section_id="j3_carbon",
        stats=stats,
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_APPRAISAL_DF["lsoa_cd"],
    )
    assert chart["type"] == "kpi_tiles"
    assert chart["title"] == SECTION_REGISTRY["j3_carbon"].title
    assert len(chart["tiles"]) == 3


def test_j3_carbon_region_not_all_empty_stats_returns_empty() -> None:
    sources = _empty_sources(appraisal_df=_APPRAISAL_DF)
    chart = build_chart_data(
        section_id="j3_carbon",
        stats={},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_APPRAISAL_DF["lsoa_cd"],
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# bsa2_operator_concentration
# ---------------------------------------------------------------------------

_LTA_DF_BSA2 = pd.DataFrame(
    {
        "lad_cd": ["E001", "E002", "E003", "E004"],
        "lad_nm": ["A", "B", "C", "D"],
        "region": ["London", "London", "South East", "South East"],
        "region_hhi": [2000, 2200, 1500, 1600],
        "mean_trips_per_cap": [8.0, 9.0, 4.0, 5.0],
        "sunday_desert_rate": [0.1, 0.2, 0.3, 0.4],
        "readiness_tier": pd.Categorical(
            ["Tier 1 — High", "Tier 2 — Medium", "Tier 3 — Low", "Tier 1 — High"],
            categories=["Tier 1 — High", "Tier 2 — Medium", "Tier 3 — Low"],
        ),
    }
)


def test_bsa2_operator_concentration() -> None:
    sources = _empty_sources(lta_df=_LTA_DF_BSA2)
    chart = build_chart_data(
        section_id="bsa2_operator_concentration",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert (
        chart["type"]
        == "horizontal_bar"
        == SECTION_REGISTRY["bsa2_operator_concentration"].chart_type
    )
    assert len(chart["data"]) == 2


def test_bsa2_operator_concentration_region_not_all_returns_empty() -> None:
    sources = _empty_sources(lta_df=_LTA_DF_BSA2)
    chart = build_chart_data(
        section_id="bsa2_operator_concentration",
        stats={},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# a6_urban_rural_gap, f5_rural_penalty
# ---------------------------------------------------------------------------

_REGION_DF_A6 = pd.DataFrame(
    {
        "lsoa_cd": [f"E0100000{i}" for i in range(8)],
        "region": ["London"] * 4 + ["South East"] * 4,
        "urban_rural": ["Urban", "Urban", "Rural", "Rural"] * 2,
        "trips_per_capita": [10, 12, 4, 5, 8, 9, 3, 4],
        "service_quality_index": [70, 75, 40, 45, 65, 68, 35, 38],
    }
)


@pytest.mark.parametrize("section_id", ["a6_urban_rural_gap", "f5_rural_penalty"])
def test_urban_rural_gap_grouped_bar(section_id: str) -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id=section_id,
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=_REGION_DF_A6,
        region_df=_REGION_DF_A6,
        sources=sources,
        lsoa_cds=_REGION_DF_A6["lsoa_cd"],
    )
    assert chart["type"] == "grouped_bar" == SECTION_REGISTRY[section_id].chart_type
    assert chart["categories"] == ["London", "South East"]
    series_names = {s["name"] for s in chart["series"]}
    assert series_names == {"Urban", "Rural"}


@pytest.mark.parametrize("section_id", ["a6_urban_rural_gap", "f5_rural_penalty"])
def test_urban_rural_gap_missing_columns_returns_empty(section_id: str) -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id=section_id,
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# ps5_scenario_comparison
# ---------------------------------------------------------------------------

_PS5_STATS = {
    "scenarios": [
        {"name": "A", "population": 5_000_000, "cost_m": 50.0, "co2_t": 1200.0},
        {"name": "B", "population": 2_000_000, "cost_m": 20.0, "co2_t": 500.0},
    ],
    "best_bcr_scenario": "A",
}


def test_ps5_scenario_comparison() -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="ps5_scenario_comparison",
        stats=_PS5_STATS,
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "table" == SECTION_REGISTRY["ps5_scenario_comparison"].chart_type
    assert chart["columns"] == [
        "Scenario", "Population affected", "Cost £m/yr", "CO2 t/yr", "Cost/beneficiary (£)",
    ]
    # Sorted by population descending: A (5M) before B (2M)
    assert [row["Scenario"] for row in chart["data"]] == ["A", "B"]
    row_a = chart["data"][0]
    assert row_a["Population affected"] == 5_000_000
    assert row_a["Cost £m/yr"] == 50.0
    assert row_a["CO2 t/yr"] == 1200.0
    assert row_a["Cost/beneficiary (£)"] == round(50.0 * 1e6 / 5_000_000, 2)


def test_ps5_scenario_comparison_empty_stats_returns_empty() -> None:
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="ps5_scenario_comparison",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# b2_operating_hours, b3_weekend_penalty
# ---------------------------------------------------------------------------

_FILTERED_B2 = pd.DataFrame(
    {
        "lsoa_cd": [f"E0100000{i}" for i in range(8)],
        "region": ["London"] * 4 + ["South East"] * 4,
    }
)

_SQ_DF_B2 = pd.DataFrame(
    {
        "lsoa_cd": [f"E0100000{i}" for i in range(8)],
        "first_service_min": [330, 340, 350, 360, 300, 310, 320, 330],
        "last_service_min": [1380, 1390, 1400, 1410, 1350, 1360, 1370, 1380],
        "total_weekday_departures": [100, 110, 120, 130, 80, 90, 100, 110],
        "total_sunday_departures": [20, 22, 24, 26, 10, 12, 14, 16],
    }
)


def test_b2_operating_hours() -> None:
    sources = _empty_sources(service_quality_df=_SQ_DF_B2)
    chart = build_chart_data(
        section_id="b2_operating_hours",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=_FILTERED_B2,
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_SQ_DF_B2["lsoa_cd"],
    )
    assert chart["type"] == "grouped_bar" == SECTION_REGISTRY["b2_operating_hours"].chart_type
    assert chart["categories"] == ["London", "South East"]
    series_names = {s["name"] for s in chart["series"]}
    assert series_names == {"First service (min)", "Last service (min)"}


def test_b2_operating_hours_region_not_all_returns_empty() -> None:
    sources = _empty_sources(service_quality_df=_SQ_DF_B2)
    chart = build_chart_data(
        section_id="b2_operating_hours",
        stats={},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=_FILTERED_B2,
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_SQ_DF_B2["lsoa_cd"],
    )
    assert chart == {}


def test_b3_weekend_penalty() -> None:
    sources = _empty_sources(service_quality_df=_SQ_DF_B2)
    chart = build_chart_data(
        section_id="b3_weekend_penalty",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=_FILTERED_B2,
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=_SQ_DF_B2["lsoa_cd"],
    )
    assert chart["type"] == "grouped_bar" == SECTION_REGISTRY["b3_weekend_penalty"].chart_type
    series_names = {s["name"] for s in chart["series"]}
    assert series_names == {"Weekday departures", "Sunday departures"}


def test_b3_weekend_penalty_missing_columns_returns_empty() -> None:
    sources = _empty_sources(service_quality_df=pd.DataFrame({"lsoa_cd": ["E01000000"]}))
    chart = build_chart_data(
        section_id="b3_weekend_penalty",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=_FILTERED_B2,
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(["E01000000"]),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# bsa3_tier_distribution
# ---------------------------------------------------------------------------


def test_bsa3_tier_distribution() -> None:
    sources = _empty_sources(lta_df=_LTA_DF_BSA2)
    chart = build_chart_data(
        section_id="bsa3_tier_distribution",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "stacked_bar" == SECTION_REGISTRY["bsa3_tier_distribution"].chart_type
    assert chart["categories"] == ["London", "South East"]


def test_bsa3_tier_distribution_region_filtered() -> None:
    sources = _empty_sources(lta_df=_LTA_DF_BSA2)
    chart = build_chart_data(
        section_id="bsa3_tier_distribution",
        stats={"some": "stats"},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "stacked_bar"
    assert chart["categories"] == ["London"]


def test_bsa3_tier_distribution_missing_columns_returns_empty() -> None:
    sources = _empty_sources(lta_df=pd.DataFrame({"region": ["London"]}))
    chart = build_chart_data(
        section_id="bsa3_tier_distribution",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# a5_service_deserts (choropleth)
# ---------------------------------------------------------------------------


def test_choropleth_section_a5() -> None:
    sources = _empty_sources(lta_df=_LTA_DF_BSA2)
    chart = build_chart_data(
        section_id="a5_service_deserts",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "choropleth" == SECTION_REGISTRY["a5_service_deserts"].chart_type
    assert chart["title"] == SECTION_REGISTRY["a5_service_deserts"].title


def test_choropleth_section_a5_region_filtered() -> None:
    sources = _empty_sources(lta_df=_LTA_DF_BSA2)
    chart = build_chart_data(
        section_id="a5_service_deserts",
        stats={"some": "stats"},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "choropleth"


def test_choropleth_section_a5_missing_columns_returns_empty() -> None:
    sources = _empty_sources(lta_df=pd.DataFrame({"region": ["London"]}))
    chart = build_chart_data(
        section_id="a5_service_deserts",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# c7_network_topology (horizontal bar of regions by cross-LA route count)
# ---------------------------------------------------------------------------

_NETWORK_TOPOLOGY_ROUTES_DF = pd.DataFrame(
    {
        "route_id": [f"R{i}" for i in range(8)],
        "primary_region": (
            ["South East"] * 3 + ["London"] * 2 + ["North West"] * 2 + ["South East"]
        ),
        "length_km": [10.0, 20.0, 15.0, 5.0, 8.0, 12.0, 30.0, 25.0],
        "cross_la": [True, True, True, True, False, True, False, True],
    }
)


def test_c7_network_topology_horizontal_bar_all_region() -> None:
    sources = _empty_sources(route_geometries_df=_NETWORK_TOPOLOGY_ROUTES_DF)
    chart = build_chart_data(
        section_id="c7_network_topology",
        stats={"some": "stats"},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart["type"] == "horizontal_bar" == SECTION_REGISTRY["c7_network_topology"].chart_type
    assert chart["title"] == SECTION_REGISTRY["c7_network_topology"].title
    # South East: R0,R1,R2,R7 all cross_la=True -> 4; London: only R3 -> 1; NW: only R5 -> 1
    labels = {row["label"]: row["value"] for row in chart["data"]}
    assert labels["South East"] == 4.0
    assert labels["London"] == 1.0
    assert labels["North West"] == 1.0
    assert chart["data"][0]["rank"] == 1
    assert "national_avg" in chart


def test_c7_network_topology_region_filtered_returns_empty() -> None:
    sources = _empty_sources(route_geometries_df=_NETWORK_TOPOLOGY_ROUTES_DF)
    chart = build_chart_data(
        section_id="c7_network_topology",
        stats={"some": "stats"},
        region="E12000007",
        region_name="London",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


def test_c7_network_topology_missing_columns_returns_empty() -> None:
    sources = _empty_sources(route_geometries_df=pd.DataFrame({"route_id": ["R0"]}))
    chart = build_chart_data(
        section_id="c7_network_topology",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


def test_c7_network_topology_no_cross_la_routes_returns_empty() -> None:
    df = _NETWORK_TOPOLOGY_ROUTES_DF.copy()
    df["cross_la"] = False
    sources = _empty_sources(route_geometries_df=df)
    chart = build_chart_data(
        section_id="c7_network_topology",
        stats={},
        region="all",
        region_name="England",
        urban_rural="all",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


# ---------------------------------------------------------------------------
# A17: insufficient_data sentinel guards for a5/a6/a7/f5
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("section_id", ["a6_urban_rural_gap", "f5_rural_penalty"])
def test_urban_rural_gap_chart_insufficient_data_returns_empty(section_id: str) -> None:
    """A17: insufficient_data stats (e.g. London has 0 Rural LSOAs) suppress the chart."""
    sources = _empty_sources()
    chart = build_chart_data(
        section_id=section_id,
        stats={"insufficient_data": True, "n_lsoas": 4969, "n_urban": 4969, "n_rural": 0},
        region="E12000007",
        region_name="London",
        urban_rural="rural",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


def test_investment_gap_chart_insufficient_data_returns_empty() -> None:
    """A17: insufficient_data stats suppress the a7 investment-gap chart."""
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="a7_investment_gap",
        stats={"insufficient_data": True, "n_lsoas": 0},
        region="E12000007",
        region_name="London",
        urban_rural="rural",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}


def test_service_deserts_choropleth_insufficient_data_returns_empty() -> None:
    """A17: insufficient_data stats suppress the a5 service-deserts choropleth."""
    sources = _empty_sources()
    chart = build_chart_data(
        section_id="a5_service_deserts",
        stats={"insufficient_data": True, "n_lsoas": 0},
        region="E12000007",
        region_name="London",
        urban_rural="rural",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )
    assert chart == {}
