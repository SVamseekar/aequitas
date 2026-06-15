"""Stats builder for route_frequency_ranking.j2 — b4_route_frequency.

Top-5/bottom-5 INDIVIDUAL ROUTES by daily trip count (n_trips_per_day, from
the route_trip_frequency intermediate — see
processing/route_trip_frequency.py). This is deliberately route-grain, not
region-grain (b1_frequency already covers region-level service_quality_index
averages — see ranking.py).

Filterable by region (route_trip_frequency.primary_region) and urban/rural
(route_urban_rural.urban_rural_classification, joined on route_id).
"""

import pandas as pd

_TOP_N = 5


def _route_record(row: pd.Series) -> dict:
    return {
        "route_short_name": str(row["route_short_name"]),
        "agency_name": str(row["agency_name"]),
        "n_trips_per_day": int(row["n_trips_per_day"]),
        "primary_region": str(row["primary_region"]),
    }


def build_route_frequency_stats(
    route_trip_frequency_df: pd.DataFrame,
    route_urban_rural_df: pd.DataFrame,
    region: str,
    region_name: str,
    urban_rural: str,
) -> dict:
    """Build top/bottom-5 route frequency stats for b4_route_frequency.

    Args:
        route_trip_frequency_df: route_id, n_trips_per_day, route_short_name,
            agency_name, primary_region (national, unfiltered).
        route_urban_rural_df: route_id, urban_rural_classification,
            primary_region — used only when urban_rural != "all".
        region: Active region filter ("all" or an ONS region code).
        region_name: Resolved ONS region name (or "England" for "all").
        urban_rural: Active area-type filter ("all"/"urban"/"rural").

    Returns:
        Dict with top_routes, bottom_routes (lists of
        {route_short_name, agency_name, n_trips_per_day, primary_region}),
        n_routes, scope_label, and unit. Returns {} if no routes remain
        after filtering or required columns are missing.
    """
    required = {"route_id", "n_trips_per_day", "route_short_name", "agency_name", "primary_region"}
    if route_trip_frequency_df.empty or not required.issubset(route_trip_frequency_df.columns):
        return {}

    # BODS GTFS bulk data includes ~2.4k Wales/Scotland routes with no
    # England-region match in route_geometries (primary_region is NaN) —
    # exclude them from all scopes, since this report is England-only.
    routes = route_trip_frequency_df.dropna(subset=["n_trips_per_day", "primary_region"])

    if region != "all":
        routes = routes[routes["primary_region"] == region_name]

    if urban_rural != "all" and not route_urban_rural_df.empty:
        classified = route_urban_rural_df[
            route_urban_rural_df["urban_rural_classification"] == urban_rural
        ]["route_id"]
        routes = routes[routes["route_id"].isin(classified)]

    if routes.empty:
        return {}

    sorted_routes = routes.sort_values("n_trips_per_day", ascending=False)
    top_routes = [_route_record(row) for _, row in sorted_routes.head(_TOP_N).iterrows()]

    # When fewer than 2*_TOP_N routes are in scope, head(_TOP_N) and a naive
    # tail(_TOP_N) would overlap — the same route would appear as both
    # "busiest" and "least busy". Exclude rows already in top_routes.
    remaining = sorted_routes.iloc[_TOP_N:]
    bottom_routes = [
        _route_record(row)
        for _, row in remaining.tail(_TOP_N).sort_values("n_trips_per_day").iterrows()
    ]

    scope_label = region_name
    if urban_rural != "all":
        scope_label = f"{region_name} ({urban_rural})"

    return {
        "top_routes": top_routes,
        "bottom_routes": bottom_routes,
        "n_routes": int(len(routes)),
        "scope_label": scope_label,
        "unit": "trips/day",
    }
