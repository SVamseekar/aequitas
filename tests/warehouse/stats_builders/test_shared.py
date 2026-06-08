"""Tests for shared stats-builder helpers."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.shared import build_single_region_stats


def test_build_single_region_stats_shape():
    """Output must match the single_region.j2 contract exactly."""
    by_region = pd.Series({"North East": 1.5, "London": 3.0, "South West": 2.0})
    stats = build_single_region_stats(
        by_region=by_region,
        region_value=1.5,
        region_name="North East",
        unit="trips/capita",
    )
    assert stats["region_name"] == "North East"
    assert stats["value"] == 1.5
    assert stats["unit"] == "trips/capita"
    assert "national_avg" in stats
    assert "vs_national_pct" in stats
    # national_avg = mean(1.5, 3.0, 2.0) = 2.1667
    assert stats["national_avg"] == pytest.approx(2.17, abs=0.01)
    # vs_national_pct = (1.5 - 2.1667) / 2.1667 * 100 = -30.77
    assert stats["vs_national_pct"] == pytest.approx(-30.8, abs=0.1)


def test_build_single_region_stats_has_no_best_worst_keys():
    """Must NOT contain best/worst — engine uses their absence to pick single_region.j2."""
    by_region = pd.Series({"North East": 1.5, "London": 3.0})
    stats = build_single_region_stats(
        by_region=by_region, region_value=1.5, region_name="North East", unit="x"
    )
    assert "best" not in stats
    assert "worst" not in stats
