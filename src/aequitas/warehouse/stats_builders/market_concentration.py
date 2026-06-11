"""Stats builder for market_concentration.j2 — Herfindahl-Hirschman Index.

Covers: c3_operator_hhi (computed from route-level operator market share)
and bsa2_operator_concentration (BSA 2025 framing over the same route-level
HHI). Both sections share the same underlying computation so that region
and urban/rural filters apply identically — see precompute.py's dispatch
for the route filtering (region via primary_region, area type via
route_urban_rural.urban_rural_classification).
"""

import pandas as pd


def _hhi_from_shares(shares_pct: pd.Series) -> float:
    """HHI = sum of squared market shares (in percentage points)."""
    return float((shares_pct ** 2).sum())


def _build_from_routes(routes_df: pd.DataFrame, region_name: str) -> dict:
    if routes_df.empty or "agency_name" not in routes_df.columns:
        return {}

    counts = routes_df["agency_name"].value_counts(dropna=True)
    total = int(counts.sum())
    if total == 0:
        return {}

    shares = counts / total * 100
    hhi = _hhi_from_shares(shares)
    top_operator = str(shares.index[0])
    top_share = float(shares.iloc[0])

    return {
        "hhi": round(hhi, 1),
        "region_name": region_name,
        "top_operator": top_operator,
        "top_operator_share": round(top_share, 1),
    }


def build_market_concentration_stats(
    section_id: str,
    routes_df: pd.DataFrame | None,
    region_name: str,
) -> dict:
    """Build stats for c3_operator_hhi or bsa2_operator_concentration.

    Both sections use the same route-level HHI computation so that region
    and urban/rural filters apply consistently.

    Args:
        section_id: "c3_operator_hhi" or "bsa2_operator_concentration".
        routes_df: route_geometries rows for the active filter scope (region-
            and area-type-filtered, or all routes when scope == "all").
        region_name: Human-readable region/scope label for the template
            header (e.g. "London" or "England" when region == "all").

    Returns:
        Dict matching market_concentration.j2's contract, or {} if the
        relevant source data is empty/missing.
    """
    if section_id in {"c3_operator_hhi", "bsa2_operator_concentration"}:
        return _build_from_routes(routes_df if routes_df is not None else pd.DataFrame(), region_name)
    return {}
