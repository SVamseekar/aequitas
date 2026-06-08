"""Stats builder for urban_rural_gap.j2 — urban vs rural comparisons.

Covers: a6_urban_rural_gap (coverage gap via trips_per_capita),
f5_rural_penalty (accessibility penalty via service_quality_index),
c4_urban_rural_routes (stub — no route-geometry x urban/rural join exists).

Fixes ISSUES.md §4.2: both sides are ALWAYS computed from the region-filtered
but area-type-UNfiltered dataframe, never from a frame already collapsed to
one area type. This guarantees non-zero n on both sides for all 30 combos.
"""

import pandas as pd

_METRIC_BY_SECTION: dict[str, tuple[str, str]] = {
    "a6_urban_rural_gap": ("trips_per_capita", "trips per capita"),
    "f5_rural_penalty": ("service_quality_index", "service quality index"),
}


def build_urban_rural_gap_stats(
    section_id: str,
    region_df: pd.DataFrame,
    urban_rural: str,
) -> dict:
    """Build stats for a6_urban_rural_gap, f5_rural_penalty, or c4 (stub).

    Args:
        section_id: One of "a6_urban_rural_gap", "f5_rural_penalty",
            "c4_urban_rural_routes".
        region_df: lsoa_policy_synthesis rows filtered by region ONLY — must
            retain both "Urban" and "Rural" rows regardless of the active
            urban_rural filter (§4.2 invariant).
        urban_rural: The active area-type filter ("all"/"urban"/"rural") —
            unused for value computation (both sides always computed), kept
            for signature symmetry with other builders and potential future
            narrative framing.

    Returns:
        Dict matching urban_rural_gap.j2's contract, or {} when source data
        is empty, urban_value is zero (divide-by-zero guard), or the section
        is stubbed.
    """
    if section_id == "c4_urban_rural_routes":
        # STUB (ISSUES.md §8.4): comparing route geometry by urban/rural
        # classification requires a route_geometries x LSOA-urban-rural
        # spatial join that does not exist in any precomputed table.
        return {}

    metric = _METRIC_BY_SECTION.get(section_id)
    if metric is None or region_df.empty or "urban_rural" not in region_df.columns:
        return {}

    column, unit = metric
    urban = region_df[region_df["urban_rural"] == "Urban"]
    rural = region_df[region_df["urban_rural"] == "Rural"]
    if urban.empty or rural.empty:
        return {}

    urban_value = float(urban[column].mean())
    rural_value = float(rural[column].mean())
    if urban_value == 0:
        return {}

    return {
        "urban_value": round(urban_value, 2),
        "rural_value": round(rural_value, 2),
        "gap_pct": (urban_value - rural_value) / urban_value * 100,
        "n_urban": int(len(urban)),
        "n_rural": int(len(rural)),
        "unit": unit,
    }
