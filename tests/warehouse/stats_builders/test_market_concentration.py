"""Tests for market_concentration.py — covers c3, bsa2."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.market_concentration import build_market_concentration_stats


def _routes_df():
    # 3 operators in one region: shares 60%, 30%, 10% -> HHI = 3600+900+100 = 4600
    rows = (
        [{"primary_region": "London", "agency_name": "Big Co"}] * 6
        + [{"primary_region": "London", "agency_name": "Mid Co"}] * 3
        + [{"primary_region": "London", "agency_name": "Small Co"}] * 1
    )
    return pd.DataFrame(rows)


def test_c3_computes_hhi_and_top_operator_from_routes():
    stats = build_market_concentration_stats(
        "c3_operator_hhi", routes_df=_routes_df(),
        region_name="London",
    )
    assert stats["hhi"] == pytest.approx(4600.0, abs=0.1)
    assert stats["region_name"] == "London"
    assert stats["top_operator"] == "Big Co"
    assert stats["top_operator_share"] == pytest.approx(60.0, abs=0.1)


def test_bsa2_uses_same_route_based_hhi_as_c3():
    stats = build_market_concentration_stats(
        "bsa2_operator_concentration", routes_df=_routes_df(),
        region_name="London",
    )
    assert stats["hhi"] == pytest.approx(4600.0, abs=0.1)
    assert stats["region_name"] == "London"
    assert stats["top_operator"] == "Big Co"
    assert stats["top_operator_share"] == pytest.approx(60.0, abs=0.1)


def test_empty_inputs_return_empty():
    assert build_market_concentration_stats("c3_operator_hhi", routes_df=pd.DataFrame(), region_name="London") == {}
    assert build_market_concentration_stats("bsa2_operator_concentration", routes_df=pd.DataFrame(), region_name="London") == {}
