"""Stats builders for equity.j2 and equity_decile.j2.

Covers: f1_gini, a4_coverage_equity (identical computation — same underlying
Gini/Palma/CI analysis surfaced under two policy-dimension categories),
f2_disparity_ratio.

Fixes ISSUES.md §2.3: equity_summary.json's regional_equity dict has only one
key ("Unknown") — it cannot supply real per-region breakdowns. Instead, Gini,
Palma, and Concentration Index are computed LIVE from the filtered
lsoa_equity_metrics slice, so every region/area-type combination produces its
own real, traceable distribution statistics rather than one national figure
repeated 30 times.
"""

import numpy as np
import pandas as pd

_MIN_DISTINCT_DECILES = 2
_MIN_LSOAS_FOR_GINI = 30


def _population_weighted_gini(values: pd.Series, weights: pd.Series) -> float:
    """Population-weighted Gini coefficient via the Lorenz-curve trapezoid method."""
    order = np.argsort(values.to_numpy())
    v = values.to_numpy()[order]
    w = weights.to_numpy()[order]

    cum_w = np.cumsum(w)
    cum_vw = np.cumsum(v * w)
    total_w = cum_w[-1]
    total_vw = cum_vw[-1]
    if total_w == 0 or total_vw == 0:
        return 0.0

    lorenz_x = np.concatenate([[0.0], cum_w / total_w])
    lorenz_y = np.concatenate([[0.0], cum_vw / total_vw])

    area_under_lorenz = np.trapezoid(lorenz_y, lorenz_x) if hasattr(np, "trapezoid") else np.trapz(lorenz_y, lorenz_x)
    return float(1 - 2 * area_under_lorenz)


def _palma_ratio(df: pd.DataFrame, value_col: str) -> float:
    """Top-10%-share / bottom-40%-share, by population-weighted value."""
    ranked = df.sort_values(value_col)
    total = float((ranked[value_col] * ranked["population"]).sum())
    if total == 0:
        return 0.0

    cum_pop = ranked["population"].cumsum()
    total_pop = cum_pop.iloc[-1]
    bottom_mask = cum_pop <= total_pop * 0.4
    top_mask = cum_pop > total_pop * 0.9

    bottom_share = float((ranked.loc[bottom_mask, value_col] * ranked.loc[bottom_mask, "population"]).sum()) / total
    top_share = float((ranked.loc[top_mask, value_col] * ranked.loc[top_mask, "population"]).sum()) / total
    if bottom_share == 0:
        return 0.0
    return top_share / bottom_share


def _concentration_index(df: pd.DataFrame, value_col: str) -> float:
    """Erreygers-style concentration index: 2/mean * population-weighted covariance(rank, value)."""
    ranked = df.sort_values("imd_decile")
    cum_pop = ranked["population"].cumsum()
    total_pop = float(cum_pop.iloc[-1])
    if total_pop == 0:
        return 0.0
    fractional_rank = (cum_pop - ranked["population"] / 2) / total_pop

    mean_value = float((ranked[value_col] * ranked["population"]).sum() / total_pop)
    if mean_value == 0:
        return 0.0

    weighted_cov = float(
        ((ranked[value_col] - mean_value) * (fractional_rank - 0.5) * ranked["population"]).sum() / total_pop
    )
    return float(2 * weighted_cov / mean_value)


def _build_distribution(equity_df: pd.DataFrame) -> dict:
    if equity_df.empty or equity_df["imd_decile"].nunique() < _MIN_DISTINCT_DECILES:
        return {}

    n_lsoas = int(len(equity_df))
    if n_lsoas < _MIN_LSOAS_FOR_GINI:
        return {"insufficient_data": True, "n_lsoas": n_lsoas}

    return {
        "gini": round(_population_weighted_gini(equity_df["trips_per_capita"], equity_df["population"]), 4),
        "palma": round(_palma_ratio(equity_df, "trips_per_capita"), 2),
        "concentration_index": round(_concentration_index(equity_df, "trips_per_capita"), 4),
        "n_lsoas": n_lsoas,
    }


def _build_disparity_ratio(equity_df: pd.DataFrame) -> dict:
    if equity_df.empty or equity_df["imd_decile"].nunique() < _MIN_DISTINCT_DECILES:
        return {}

    by_decile = equity_df.groupby("imd_decile")["trips_per_capita"].mean()
    most_deprived_value = float(by_decile.loc[by_decile.index.min()])
    least_deprived_value = float(by_decile.loc[by_decile.index.max()])

    bottom_20 = equity_df[equity_df["imd_decile"] <= 2]
    total_trips = float((equity_df["trips_per_capita"] * equity_df["population"]).sum())
    bottom_20_trips = float((bottom_20["trips_per_capita"] * bottom_20["population"]).sum())
    bottom_20_pct = (bottom_20_trips / total_trips * 100) if total_trips > 0 else 0.0

    # If the most-deprived decile has zero baseline service, the ratio is
    # mathematically undefined (division by zero) — surface a sentinel
    # rather than a misleading 0 or raising.
    ratio: float | None = (
        round(least_deprived_value / most_deprived_value, 2) if most_deprived_value > 0 else None
    )

    return {
        "most_deprived_value": round(most_deprived_value, 2),
        "least_deprived_value": round(least_deprived_value, 2),
        "ratio": ratio,
        "ratio_undefined": ratio is None,
        "bottom_20_pct": round(bottom_20_pct, 1),
        "unit": "trips per capita",
    }


def build_equity_stats(section_id: str, equity_df: pd.DataFrame) -> dict:
    """Build stats for f1_gini, a4_coverage_equity, or f2_disparity_ratio.

    Args:
        section_id: One of "f1_gini", "a4_coverage_equity", "f2_disparity_ratio".
        equity_df: lsoa_equity_metrics rows filtered to the active region/
            area-type combo. Must retain lsoa_cd, imd_decile, trips_per_capita,
            population columns.

    Returns:
        Dict matching equity.j2's contract (f1/a4) or equity_decile.j2's
        contract (f2), or {} when the filtered slice is empty or spans fewer
        than 2 distinct IMD deciles (distribution statistics undefined).

        f1/a4 dicts include "insufficient_data": True (with only "n_lsoas")
        instead of gini/palma/concentration_index when the slice has fewer
        than _MIN_LSOAS_FOR_GINI LSOAs — small samples produce out-of-[0,1]
        Gini artifacts.

        f2 dicts include "ratio": None and "ratio_undefined": True when the
        most-deprived decile's mean trips-per-capita is zero (division by
        zero would otherwise be masked as a misleading 0).
    """
    if section_id in ("f1_gini", "a4_coverage_equity"):
        return _build_distribution(equity_df)
    if section_id == "f2_disparity_ratio":
        return _build_disparity_ratio(equity_df)
    return {}
