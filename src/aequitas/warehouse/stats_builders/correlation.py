"""Stats builder for correlation.j2 — Pearson correlation between two variables.

Covers: d1_coverage_deprivation, d2_coverage_unemployment, d3_coverage_car,
d4_coverage_elderly, d5_coverage_income, b5_frequency_deprivation,
c5_length_vs_frequency.

Reuses aequitas.intelligence.calculators.calculate_correlation — the Pearson
r/p-value/strength/direction logic already exists and is tested there.
"""

import pandas as pd

from aequitas.intelligence.calculators import calculate_correlation

CORRELATION_CONFIG: dict[str, dict] = {
    "d1_coverage_deprivation": {
        "x_col": "imd_score", "y_col": "trips_per_capita",
        "x_label": "IMD Score", "y_label": "Trips per Capita",
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
    "c5_length_vs_frequency": {
        # stop_count is used as a frequency proxy here: no per-route
        # departure-frequency column exists in any audit parquet, so
        # stops-per-route is the closest available proxy for service
        # frequency along a route.
        "x_col": "length_km", "y_col": "stop_count",
        "x_label": "Route Length (km)", "y_label": "Stops per Route (frequency proxy)",
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
        strength, direction} ready for correlation.j2 rendering, or an
        empty dict ({}) if either configured column is missing from `df`,
        or if fewer than 3 complete-case rows (non-null in both columns)
        remain after dropping missing values.
    """
    cfg = CORRELATION_CONFIG[section_id]
    x_col, y_col = cfg["x_col"], cfg["y_col"]

    if x_col not in df.columns or y_col not in df.columns:
        return {}

    pair = df[[x_col, y_col]].dropna()
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
