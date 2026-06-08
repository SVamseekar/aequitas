"""Stats builder for market_concentration.j2 — Herfindahl-Hirschman Index.

Covers: c3_operator_hhi (computed from route-level operator market share),
bsa2_operator_concentration (uses the pre-computed region_hhi from
lta_franchising_readiness — the BSA franchising-readiness composite already
includes an HHI sub-score, so we reuse it rather than recomputing).
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


def _build_from_lta(lta_df: pd.DataFrame, region_name: str) -> dict:
    if lta_df.empty or "region_hhi" not in lta_df.columns:
        return {}

    mean_hhi = float(lta_df["region_hhi"].mean())
    if pd.isna(mean_hhi):
        return {}

    # No top_operator available from this source — market_concentration.j2
    # gates the operator-detail paragraph behind `{% if top_operator %}`.
    return {
        "hhi": round(mean_hhi, 1),
        "region_name": region_name,
    }


def build_market_concentration_stats(
    section_id: str,
    routes_df: pd.DataFrame | None,
    lta_df: pd.DataFrame | None,
    region_name: str,
) -> dict:
    """Build stats for c3_operator_hhi or bsa2_operator_concentration.

    Args:
        section_id: "c3_operator_hhi" or "bsa2_operator_concentration".
        routes_df: route_geometries rows for the active filter scope (region-
            filtered by primary_region, or all routes when region == "all").
            Required for c3, ignored for bsa2.
        lta_df: lta_franchising_readiness rows for the active filter scope
            (region-filtered, or all LADs when region == "all"). Required for
            bsa2, ignored for c3.
        region_name: Human-readable region/scope label for the template header
            (e.g. "London" or "England" when region == "all").

    Returns:
        Dict matching market_concentration.j2's contract, or {} if the
        relevant source data is empty/missing.
    """
    if section_id == "c3_operator_hhi":
        return _build_from_routes(routes_df if routes_df is not None else pd.DataFrame(), region_name)
    if section_id == "bsa2_operator_concentration":
        return _build_from_lta(lta_df if lta_df is not None else pd.DataFrame(), region_name)
    return {}
