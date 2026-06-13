"""Shared helpers used across multiple stats-builder modules."""

import pandas as pd


def build_single_region_stats(
    by_region: pd.Series,
    region_value: float,
    region_name: str,
    unit: str,
    higher_is_better: bool = True,
) -> dict:
    """Build the stats shape required by single_region.j2.

    Used by ranking-family builders (a1, a2, b1, b4, f6, j4, bsa1) when the
    active filter is a single region rather than "all" — in that context a
    best/worst ranking is meaningless, but a region-vs-national comparison is
    the right narrative (see ISSUES.md §2.4/§8.1).

    Args:
        by_region: Series of metric values indexed by region name, across all
            regions (unfiltered) — used to compute the national average.
        region_value: The metric value for the single selected region.
        region_name: Human-readable region name (e.g. "North East").
        unit: Unit label for the metric (e.g. "trips/capita").
        higher_is_better: Whether a higher metric value is the desirable
            outcome (e.g. SQI) vs a lower one (e.g. vulnerability index).
            Propagated to single_region.j2 so the "ahead of/behind the
            national benchmark" framing matches the metric's direction.

    Returns:
        Dict with keys region_name, value, national_avg, vs_national_pct,
        unit, higher_is_better. Deliberately excludes best/worst so
        InsightEngine selects single_region.j2 instead of ranking.j2.
    """
    national_avg = float(by_region.mean())
    vs_national_pct = (
        round((region_value - national_avg) / national_avg * 100, 1)
        if national_avg != 0
        else 0.0
    )
    return {
        "region_name": region_name,
        "value": round(float(region_value), 2),
        "national_avg": round(national_avg, 2),
        "vs_national_pct": vs_national_pct,
        "unit": unit,
        "higher_is_better": higher_is_better,
    }
