"""Tests for precompute._dispatch urban/rural route filtering (c1/c2, A6).

Covers _filter_routes_by_urban_rural and its application to
c1_route_length / c2_stops_per_route via the _MISC_SECTIONS dispatch branch.
"""
import pandas as pd
import pytest

from aequitas.warehouse.precompute import _dispatch, _filter_routes_by_urban_rural, _Sources


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


def _routes_df() -> pd.DataFrame:
    return pd.DataFrame({
        "route_id": ["R1", "R2", "R3", "R4", "R5"],
        "primary_region": ["London"] * 5,
        "length_km": [10.0, 12.0, 14.0, 50.0, 100.0],
        "stop_count": [20, 22, 24, 60, 120],
    })


def _route_urban_rural_df() -> pd.DataFrame:
    return pd.DataFrame({
        "route_id": ["R1", "R2", "R3", "R4", "R5"],
        "urban_rural_classification": ["urban", "urban", "urban", "rural", "mixed"],
    })


def _dispatch_kwargs(section_id: str, urban_rural: str, sources: _Sources) -> dict:
    return dict(
        section_id=section_id,
        region="E12000007",
        urban_rural=urban_rural,
        region_name="London",
        filtered=pd.DataFrame(),
        region_df=pd.DataFrame(),
        sources=sources,
        lsoa_cds=pd.Series(dtype=str),
    )


# ---------------------------------------------------------------------------
# _filter_routes_by_urban_rural unit tests
# ---------------------------------------------------------------------------


def test_filter_routes_all_returns_unchanged():
    routes = _routes_df()
    result = _filter_routes_by_urban_rural(routes, _route_urban_rural_df(), "all")
    assert len(result) == 5


def test_filter_routes_urban_excludes_rural_and_mixed():
    routes = _routes_df()
    result = _filter_routes_by_urban_rural(routes, _route_urban_rural_df(), "urban")
    assert set(result["route_id"]) == {"R1", "R2", "R3"}


def test_filter_routes_rural_excludes_urban_and_mixed():
    routes = _routes_df()
    result = _filter_routes_by_urban_rural(routes, _route_urban_rural_df(), "rural")
    assert set(result["route_id"]) == {"R4"}


def test_filter_routes_empty_classification_returns_unchanged():
    routes = _routes_df()
    result = _filter_routes_by_urban_rural(routes, pd.DataFrame(), "urban")
    assert len(result) == 5


# ---------------------------------------------------------------------------
# c1_route_length / c2_stops_per_route dispatch tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("section_id,column", [
    ("c1_route_length", "length_km"),
    ("c2_stops_per_route", "stop_count"),
])
def test_distribution_section_differs_by_urban_rural(section_id: str, column: str):
    sources = _empty_sources(route_geometries_df=_routes_df(), route_urban_rural_df=_route_urban_rural_df())

    stats_all = _dispatch(**_dispatch_kwargs(section_id, "all", sources))
    stats_urban = _dispatch(**_dispatch_kwargs(section_id, "urban", sources))
    stats_rural = _dispatch(**_dispatch_kwargs(section_id, "rural", sources))

    assert stats_all and stats_urban and stats_rural
    # urban subset (R1-R3) excludes the high-value rural/mixed routes (R4, R5)
    assert stats_urban["mean"] != stats_all["mean"]
    assert stats_rural["mean"] != stats_all["mean"]
    assert stats_urban["mean"] != stats_rural["mean"]


def test_distribution_section_mixed_routes_only_in_all():
    sources = _empty_sources(route_geometries_df=_routes_df(), route_urban_rural_df=_route_urban_rural_df())

    stats_all = _dispatch(**_dispatch_kwargs("c1_route_length", "all", sources))
    stats_urban = _dispatch(**_dispatch_kwargs("c1_route_length", "urban", sources))
    stats_rural = _dispatch(**_dispatch_kwargs("c1_route_length", "rural", sources))

    # R5 (mixed, length 100.0) drives the "all" max well above urban/rural-only views.
    assert stats_all["p90"] >= stats_urban["p90"]
    assert stats_all["p90"] >= stats_rural["p90"]


def test_distribution_section_region_filter_still_applies():
    routes = pd.concat([
        _routes_df(),
        pd.DataFrame({
            "route_id": ["R6"],
            "primary_region": ["North West"],
            "length_km": [999.0],
            "stop_count": [999],
        }),
    ], ignore_index=True)
    route_ur = pd.concat([
        _route_urban_rural_df(),
        pd.DataFrame({"route_id": ["R6"], "urban_rural_classification": ["urban"]}),
    ], ignore_index=True)
    sources = _empty_sources(route_geometries_df=routes, route_urban_rural_df=route_ur)

    stats_london = _dispatch(**_dispatch_kwargs("c1_route_length", "all", sources))
    assert stats_london["p90"] < 999.0


def test_distribution_section_empty_after_filter_returns_empty():
    routes = pd.DataFrame({
        "route_id": ["R1"],
        "primary_region": ["London"],
        "length_km": [10.0],
        "stop_count": [20],
    })
    route_ur = pd.DataFrame({"route_id": ["R1"], "urban_rural_classification": ["rural"]})
    sources = _empty_sources(route_geometries_df=routes, route_urban_rural_df=route_ur)

    stats = _dispatch(**_dispatch_kwargs("c1_route_length", "urban", sources))
    assert stats == {}
