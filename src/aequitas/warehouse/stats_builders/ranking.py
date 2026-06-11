"""Stats builder for ranking.j2 — best/worst region comparisons.

Covers: a1_route_density, a2_stop_density, b1_frequency,
f6_equitable_regions, j4_investment_priority, bsa1_franchising_readiness.

All six sections share the same template contract — they differ only in
which metric (and source table) is ranked. RANKING_CONFIG is the single
source of truth for that mapping; build_ranking_stats is generic over it.

b4_route_frequency was moved out to its own builder
(stats_builders/route_frequency.py) — it ranks individual ROUTES by daily
trip frequency, not regions, and uses a different template/contract.
"""

import pandas as pd

from aequitas.warehouse.stats_builders.shared import build_single_region_stats

RANKING_CONFIG: dict[str, dict] = {
    "a1_route_density": {
        "metric": "route_count",
        "group_col": "primary_region",
        "unit": "routes",
        "higher_is_better": True,
    },
    "a2_stop_density": {
        "metric": "stops_per_1k",
        "group_col": "region",
        "unit": "stops/1,000 population",
        "higher_is_better": True,
    },
    "b1_frequency": {
        "metric": "service_quality_index",
        "group_col": "region",
        "unit": "SQI points",
        "higher_is_better": True,
    },
    "f6_equitable_regions": {
        "metric": "vulnerability_index",
        "group_col": "region",
        "unit": "vulnerability index",
        "higher_is_better": False,
    },
    "j4_investment_priority": {
        "metric": "investment_gap_annual_cost",
        "group_col": "region",
        "unit": "£/year investment gap",
        "higher_is_better": True,
    },
    "bsa1_franchising_readiness": {
        "metric": "franchising_readiness",
        "group_col": "region",
        "unit": "readiness score (0-100)",
        "higher_is_better": True,
    },
}


def build_ranking_stats(
    section_id: str,
    filtered: pd.DataFrame,
    national_df: pd.DataFrame,
    region: str,
    region_name: str | None,
) -> dict:
    """Build stats for any ranking.j2-backed section.

    Args:
        section_id: One of the keys in RANKING_CONFIG — selects which metric,
            group column, unit, and sort direction to use.
        filtered: The active per-combo scoped frame (matches the dispatch
            call's `filtered=...` argument). Accepted for interface symmetry
            with `precompute.py`'s dispatch (which passes both `filtered` and
            `national_df` to every section builder uniformly), but it is NOT
            used in the ranking computation here — see `national_df` below.
        national_df: The unfiltered, all-regions national frame. This is what
            actually drives the computation: both the all-regions best/worst
            ranking and the single-region "vs national average" comparison are
            grouped from this frame, so that "national average" means the same
            thing — the true national distribution — across all ~30 filter
            combos. Computing it from `filtered` would make the "national"
            average scope-dependent, which is incoherent.
        region: "all" for the all-regions ranking view, or a region code for
            the single-region comparison view.
        region_name: Human-readable region name, required when `region` is not
            "all"; selects which row of `by_region` is the active region.

    Returns:
        For region == "all": dict with keys best, worst, national_avg, unit
        (best/worst each {name, value, pct_above|pct_below}), suitable for
        ranking.j2. For a single region: the build_single_region_stats() shape
        (region_name, value, national_avg, vs_national_pct, unit), which
        deliberately omits best/worst so InsightEngine renders single_region.j2
        instead. Returns {} when there isn't enough data to rank meaningfully.
    """
    cfg = RANKING_CONFIG[section_id]
    metric = cfg["metric"]
    group_col = cfg["group_col"]
    unit = cfg["unit"]
    higher_is_better = cfg["higher_is_better"]

    # Deliberately use national_df (not filtered) — see docstring above.
    df = national_df
    if df.empty or group_col not in df.columns or metric not in df.columns:
        return {}

    by_region = df.groupby(group_col)[metric].mean().dropna()
    if by_region.empty:
        return {}

    if region != "all" and region_name is not None:
        if region_name not in by_region.index:
            return {}
        return build_single_region_stats(
            by_region=by_region,
            region_value=float(by_region[region_name]),
            region_name=region_name,
            unit=unit,
        )

    if len(by_region) < 2:
        return {}

    nat_mean = float(by_region.mean())
    best_name = by_region.idxmax() if higher_is_better else by_region.idxmin()
    worst_name = by_region.idxmin() if higher_is_better else by_region.idxmax()
    best_val = float(by_region[best_name])
    worst_val = float(by_region[worst_name])

    return {
        "best": {
            "name": best_name,
            "value": round(best_val, 2),
            "pct_above": round((best_val - nat_mean) / nat_mean * 100, 1) if nat_mean else 0.0,
        },
        "worst": {
            "name": worst_name,
            "value": round(worst_val, 2),
            "pct_below": round((nat_mean - worst_val) / nat_mean * 100, 1) if nat_mean else 0.0,
        },
        "national_avg": round(nat_mean, 2),
        "unit": unit,
    }
