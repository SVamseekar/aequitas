"""Tests for ranking.py — covers a1, a2, b1, b4, f6, j4, bsa1."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.ranking import (
    build_ranking_stats,
    RANKING_CONFIG,
)


def _make_region_df(metric: str, values: dict[str, float], extra_cols: dict | None = None) -> pd.DataFrame:
    rows = []
    for region, val in values.items():
        row = {"region": region, metric: val}
        if extra_cols:
            row.update(extra_cols)
        rows.append(row)
    return pd.DataFrame(rows)


def test_all_regions_shape_has_best_and_worst():
    df = _make_region_df(
        "service_quality_index",
        {"London": 75.0, "North East": 50.0, "South West": 65.0},
    )
    stats = build_ranking_stats(
        section_id="b1_frequency",
        filtered=df,
        national_df=df,
        region="all",
        region_name=None,
    )
    assert stats["best"]["name"] == "London"
    assert stats["best"]["value"] == 75.0
    assert stats["worst"]["name"] == "North East"
    assert stats["worst"]["value"] == 50.0
    assert "national_avg" in stats
    assert stats["unit"] == "SQI points"
    assert "best" in stats and "worst" in stats


def test_lower_is_better_metric_flips_best_worst():
    """f6_equitable_regions: lower vulnerability_index = more equitable = 'best'."""
    df = _make_region_df(
        "vulnerability_index",
        {"London": 0.8, "North East": 0.3, "South West": 0.5},
    )
    stats = build_ranking_stats(
        section_id="f6_equitable_regions",
        filtered=df,
        national_df=df,
        region="all",
        region_name=None,
    )
    assert stats["best"]["name"] == "North East"  # lowest vulnerability = most equitable
    assert stats["worst"]["name"] == "London"


def test_single_region_shape_when_region_filtered():
    df = _make_region_df(
        "service_quality_index",
        {"London": 75.0, "North East": 50.0, "South West": 65.0},
    )
    stats = build_ranking_stats(
        section_id="b1_frequency",
        filtered=df,
        national_df=df,
        region="E12000001",
        region_name="North East",
    )
    assert stats["region_name"] == "North East"
    assert stats["value"] == 50.0
    assert "best" not in stats
    assert "worst" not in stats
    assert "national_avg" in stats


def test_empty_dataframe_returns_empty_stats():
    df = pd.DataFrame(columns=["region", "service_quality_index"])
    stats = build_ranking_stats(section_id="b1_frequency", filtered=df, national_df=df, region="all", region_name=None)
    assert stats == {}


def test_ranking_config_covers_all_seven_sections():
    expected = {
        "a1_route_density",
        "a2_stop_density",
        "b1_frequency",
        "b4_route_frequency",
        "f6_equitable_regions",
        "j4_investment_priority",
        "bsa1_franchising_readiness",
    }
    assert set(RANKING_CONFIG.keys()) == expected
    for sid, cfg in RANKING_CONFIG.items():
        assert "metric" in cfg
        assert "group_col" in cfg
        assert "unit" in cfg
        assert "higher_is_better" in cfg
