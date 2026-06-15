"""Stats builder for correlation.j2 — Pearson correlation between two variables.

Covers: d1_coverage_deprivation, d2_coverage_unemployment, d3_coverage_car,
d4_coverage_elderly, d5_coverage_income, b5_frequency_deprivation,
c5_length_vs_frequency, f3_ethnic_access, d9a_health_access,
d9b_employment_access, d9c_crime_access, d9d_environment_access,
d9e_barriers_access.

Reuses aequitas.intelligence.calculators.calculate_correlation — the Pearson
r/p-value/strength/direction logic already exists and is tested there.
"""

import pandas as pd

from aequitas.intelligence.calculators import calculate_correlation

CORRELATION_CONFIG: dict[str, dict] = {
    "d1_coverage_deprivation": {
        # stops_per_1k (stop density) matches the locked ground-truth
        # IMD-stop Pearson correlation (ST-001, -0.0644 — see
        # docs/figures-registry.md), not trips_per_capita.
        "x_col": "imd_score", "y_col": "stops_per_1k",
        "x_label": "IMD Score", "y_label": "Bus Stops per 1,000 Population",
    },
    "d2_coverage_unemployment": {
        "x_col": "unemployment_rate", "y_col": "trips_per_capita",
        "x_label": "Unemployment Rate", "y_label": "Trips per Capita",
    },
    "d3_coverage_car": {
        "x_col": "nocar_pct", "y_col": "trips_per_capita",
        "x_label": "Car-Free Household %", "y_label": "Trips per Capita",
    },
    "d4_coverage_elderly": {
        "x_col": "elderly_pct", "y_col": "trips_per_capita",
        "x_label": "Elderly Population %", "y_label": "Trips per Capita",
    },
    "d5_coverage_income": {
        "x_col": "income_score", "y_col": "trips_per_capita",
        "x_label": "Income Score", "y_label": "Trips per Capita",
    },
    "b5_frequency_deprivation": {
        "x_col": "imd_score", "y_col": "service_quality_index",
        "x_label": "IMD Score", "y_label": "Service Quality Index",
    },
    "f3_ethnic_access": {
        # nonwhite_pct is derived in precompute.py::_build_correlation_df from
        # master_lsoa_table's ts021-sourced eth_white/eth_total columns
        # (1 - eth_white / eth_total) * 100. stops_per_1k matches d1's access
        # metric (bus stop density) for cross-section consistency.
        "x_col": "nonwhite_pct", "y_col": "stops_per_1k",
        "x_label": "Non-White Population %", "y_label": "Bus Stops per 1,000 Population",
    },
    "c5_length_vs_frequency": {
        # stop_count is used as a frequency proxy here: no per-route
        # departure-frequency column exists in any audit parquet, so
        # stops-per-route is the closest available proxy for service
        # frequency along a route.
        "x_col": "length_km", "y_col": "stop_count",
        "x_label": "Route Length (km)", "y_label": "Stops per Route (frequency proxy)",
    },
    "d9a_health_access": {
        "x_col": "health_score", "y_col": "trips_per_capita",
        "x_label": "IMD Health & Disability Score", "y_label": "Trips per Capita",
    },
    "d9b_employment_access": {
        "x_col": "employment_score", "y_col": "trips_per_capita",
        "x_label": "IMD Employment Deprivation Score", "y_label": "Trips per Capita",
    },
    "d9c_crime_access": {
        "x_col": "crime_score", "y_col": "service_quality_index",
        "x_label": "IMD Crime Score", "y_label": "Service Quality Index",
    },
    "d9d_environment_access": {
        "x_col": "living_env_score", "y_col": "service_quality_index",
        "x_label": "IMD Living Environment Score", "y_label": "Service Quality Index",
    },
    "d9e_barriers_access": {
        "x_col": "barriers_score", "y_col": "trips_per_capita",
        "x_label": "IMD Barriers to Housing & Services Score", "y_label": "Trips per Capita",
    },
}


def build_correlation_stats(section_id: str, df: pd.DataFrame) -> dict:
    """Build stats for any correlation.j2-backed section.

    Computes a Pearson correlation between the two columns configured for
    `section_id` in CORRELATION_CONFIG, using the shared
    `calculate_correlation` calculator (single source of truth for r,
    p-value, strength, and direction labels).

    Args:
        section_id: One of the keys in CORRELATION_CONFIG. The caller is
            expected to have already filtered/joined `df` so that it
            contains both the configured x_col and y_col for that section.
        df: DataFrame containing at least the configured x_col and y_col.
            For c5_length_vs_frequency, `stop_count` (stops per route) is
            used as a frequency proxy — no per-route departure-frequency
            column exists in any audit parquet.

    Returns:
        A dict with keys {r, p_value, n, n_observations, x_label, y_label,
        strength, direction} ready for correlation.j2 rendering. Returns
        `{"insufficient_data": True, "n_observations": 0}` if either
        configured column is missing from `df`, or if there are zero
        complete-case rows (non-null in both columns) — e.g. London's
        route_geometries rows, which are 100% null for length_km. Returns
        `{}` if there are 1-2 complete-case rows (too few to correlate but
        not a clean "no data" case).
    """
    cfg = CORRELATION_CONFIG[section_id]
    x_col, y_col = cfg["x_col"], cfg["y_col"]

    if x_col not in df.columns or y_col not in df.columns:
        return {"insufficient_data": True, "n_observations": 0}

    pair = df[[x_col, y_col]].dropna()
    if pair.empty:
        return {"insufficient_data": True, "n_observations": 0}
    if len(pair) < 3:
        return {}

    result = calculate_correlation(pair[x_col], pair[y_col])

    return {
        "r": result.r,
        "p_value": result.p_value,
        "n": result.n,
        "n_observations": result.n,
        "x_label": cfg["x_label"],
        "y_label": cfg["y_label"],
        "strength": result.strength,
        "direction": result.direction,
    }
