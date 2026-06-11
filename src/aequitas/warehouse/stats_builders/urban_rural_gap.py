"""Stats builder for urban_rural_gap.j2 — urban vs rural comparisons.

Covers: a6_urban_rural_gap (coverage gap via trips_per_capita),
f5_rural_penalty (accessibility penalty via service_quality_index),
c4_urban_rural_routes (route-level urban/rural mix + cross-LA share, sourced
from the route_urban_rural intermediate — see processing/route_urban_rural.py).

Fixes ISSUES.md §4.2: both sides are ALWAYS computed from the region-filtered
but area-type-UNfiltered dataframe, never from a frame already collapsed to
one area type. This guarantees non-zero n on both sides for all 30 combos.
"""

import pandas as pd

_METRIC_BY_SECTION: dict[str, tuple[str, str]] = {
    "a6_urban_rural_gap": ("trips_per_capita", "trips per capita"),
    "f5_rural_penalty": ("service_quality_index", "service quality index"),
}


def _build_c4_stats(
    region_df: pd.DataFrame,
    urban_rural: str,
    route_urban_rural_df: pd.DataFrame,
    route_geometries_df: pd.DataFrame,
    region_name: str,
    region: str,
) -> dict:
    """Build stats for c4_urban_rural_routes.

    Computes the urban/rural/mixed route-classification split for the active
    region (via route_urban_rural.primary_region), plus n_cross_la/pct_cross_la
    sourced from route_geometries.cross_la (matching c7_network_topology's
    pattern). When urban_rural != "all", the route set is first filtered to
    routes matching that classification before computing cross_la figures.

    Args:
        region_df: Unused directly (kept for signature symmetry / future use).
        urban_rural: Active area-type filter ("all"/"urban"/"rural").
        route_urban_rural_df: route_id -> urban_rural_classification, primary_region.
        route_geometries_df: route_id -> cross_la, primary_region, etc.
        region_name: Resolved ONS region name (or "England" for "all").
        region: Active region filter ("all" or an ONS region code).

    Returns:
        Dict with urban_value/rural_value/gap_pct/n_urban/n_rural/unit (for
        urban_rural_gap.j2's Key Finding block) plus n_cross_la/pct_cross_la,
        or {} when source data is empty.
    """
    if route_urban_rural_df.empty or "urban_rural_classification" not in route_urban_rural_df.columns:
        return {}

    routes = route_urban_rural_df
    if region != "all" and "primary_region" in routes.columns:
        routes = routes[routes["primary_region"] == region_name]
    if routes.empty:
        return {}

    n_total = len(routes)
    n_urban = int((routes["urban_rural_classification"] == "urban").sum())
    n_rural = int((routes["urban_rural_classification"] == "rural").sum())
    n_mixed = int((routes["urban_rural_classification"] == "mixed").sum())

    urban_pct = n_urban / n_total * 100
    rural_pct = n_rural / n_total * 100
    if urban_pct == 0:
        return {}

    stats = {
        "urban_value": round(urban_pct, 1),
        "rural_value": round(rural_pct, 1),
        "gap_pct": (urban_pct - rural_pct) / urban_pct * 100,
        "n_urban": n_urban,
        "n_rural": n_rural,
        "n_mixed": n_mixed,
        "pct_mixed": round(n_mixed / n_total * 100, 1),
        "unit": "% of routes",
        # n_urban/n_rural here count ROUTES, not LSOAs — urban_rural_gap.j2
        # uses entity_label to render the correct noun in the Key Finding.
        "entity_label": "routes",
    }

    # n_cross_la / pct_cross_la from route_geometries, matching
    # _build_network_topology's column/aggregation pattern. When a specific
    # urban_rural view is active, restrict to routes of that classification.
    if not route_geometries_df.empty and "cross_la" in route_geometries_df.columns:
        geo = route_geometries_df
        if region != "all" and "primary_region" in geo.columns:
            geo = geo[geo["primary_region"] == region_name]
        if urban_rural != "all":
            classified_ids = routes[routes["urban_rural_classification"] == urban_rural]["route_id"]
            geo = geo[geo["route_id"].isin(classified_ids)]
        if not geo.empty:
            cross_la = geo[geo["cross_la"]]
            stats["n_cross_la"] = int(len(cross_la))
            stats["pct_cross_la"] = round(len(cross_la) / len(geo) * 100, 1)

    return stats


def build_urban_rural_gap_stats(
    section_id: str,
    region_df: pd.DataFrame,
    urban_rural: str,
    route_urban_rural_df: pd.DataFrame | None = None,
    route_geometries_df: pd.DataFrame | None = None,
    region_name: str = "England",
    region: str = "all",
) -> dict:
    """Build stats for a6_urban_rural_gap, f5_rural_penalty, or c4_urban_rural_routes.

    Args:
        section_id: One of "a6_urban_rural_gap", "f5_rural_penalty",
            "c4_urban_rural_routes".
        region_df: lsoa_policy_synthesis rows filtered by region ONLY — must
            retain both "Urban" and "Rural" rows regardless of the active
            urban_rural filter (§4.2 invariant).
        urban_rural: The active area-type filter ("all"/"urban"/"rural") —
            unused for a6/f5 value computation (both sides always computed),
            but used by c4 to optionally restrict the route set.
        route_urban_rural_df: route_id -> urban_rural_classification,
            primary_region (only required for c4).
        route_geometries_df: route_id -> cross_la, primary_region (only
            required for c4).
        region_name: Resolved ONS region name (only required for c4).
        region: Active region filter (only required for c4).

    Returns:
        Dict matching urban_rural_gap.j2's contract, or {} when source data
        is empty or urban_value is zero (divide-by-zero guard).
    """
    if section_id == "c4_urban_rural_routes":
        return _build_c4_stats(
            region_df,
            urban_rural,
            route_urban_rural_df if route_urban_rural_df is not None else pd.DataFrame(),
            route_geometries_df if route_geometries_df is not None else pd.DataFrame(),
            region_name,
            region,
        )

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
