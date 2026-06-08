"""Stats builder for ml_clusters.j2 — HDBSCAN cluster profile summaries.

Covers: g1_route_clusters, c6_route_archetypes (both from route_clusters.parquet,
differing only in narrative framing), d6_transport_poverty (from
lsoa_clusters_hdbscan.parquet, using its pre-computed hdbscan_archetype labels).
"""

import pandas as pd

_ROUTE_ENTITY_TYPES = {
    "g1_route_clusters": "routes",
    "c6_route_archetypes": "route archetypes",
}


def _describe_route_cluster(cluster_id: int, mean_length: float, mean_stops: float, mean_cross_la: float) -> str:
    """Generate a description from a route cluster's mean feature values.

    Thresholds (short < 15km, long > 35km; cross_la majority > 0.5) are chosen
    to separate the confirmed cluster means (cluster 1: 9.4km/0% cross-LA vs
    cluster 4: 46.8km/100% cross-LA) into clearly distinct narrative bands.
    """
    length_band = "short local" if mean_length < 15 else "long-distance" if mean_length > 35 else "medium-length"
    boundary = "cross-boundary" if mean_cross_la > 0.5 else "within-authority"
    return (
        f"{length_band.capitalize()} {boundary} routes averaging {mean_length:.1f} km "
        f"with {mean_stops:.0f} stops per route"
    )


def _build_route_clusters(section_id: str, df: pd.DataFrame) -> dict:
    required = {"cluster", "length_km", "stop_count", "cross_la_int"}
    if not required.issubset(df.columns):
        return {}

    real = df[df["cluster"] != -1]  # exclude HDBSCAN noise label
    if real.empty:
        return {}

    total = len(real)
    grouped = real.groupby("cluster").agg(
        n=("cluster", "size"),
        mean_length=("length_km", "mean"),
        mean_stops=("stop_count", "mean"),
        mean_cross_la=("cross_la_int", "mean"),
    )

    clusters = []
    for cluster_id, row in grouped.iterrows():
        clusters.append({
            "id": int(cluster_id),
            "n": int(row["n"]),
            "pct": round(float(row["n"]) / total * 100, 1),
            "description": _describe_route_cluster(
                int(cluster_id), float(row["mean_length"]), float(row["mean_stops"]), float(row["mean_cross_la"])
            ),
        })

    return {
        "n_clusters": len(clusters),
        "entity_type": _ROUTE_ENTITY_TYPES[section_id],
        "clusters": sorted(clusters, key=lambda c: -c["n"]),
    }


_ARCHETYPE_DESCRIPTIONS: dict[str, str] = {
    "Noise": "Noise — LSOAs with no clear archetype membership; heterogeneous demographic and service profiles that do not cluster densely with any group",
    "Elderly Rural": "Elderly Rural — LSOAs combining higher elderly populations, rural settlement patterns, and structurally lower service levels",
    "Diverse Urban": "Diverse Urban — LSOAs with higher ethnic diversity, denser urban settlement, and comparatively stronger service provision",
}


def _build_lsoa_archetypes(df: pd.DataFrame) -> dict:
    if "hdbscan_archetype" not in df.columns or df.empty:
        return {}

    counts = df["hdbscan_archetype"].value_counts()
    total = int(counts.sum())
    if total == 0:
        return {}

    clusters = []
    for label, n in counts.items():
        clusters.append({
            "id": label,
            "n": int(n),
            "pct": round(float(n) / total * 100, 1),
            "description": _ARCHETYPE_DESCRIPTIONS.get(label, f"{label} — LSOA archetype identified by HDBSCAN clustering"),
        })

    return {
        "n_clusters": len(clusters),
        "entity_type": "LSOAs",
        "clusters": sorted(clusters, key=lambda c: -c["n"]),
    }


def build_ml_clusters_stats(section_id: str, df: pd.DataFrame) -> dict:
    """Build stats for any ml_clusters.j2-backed section.

    Args:
        section_id: One of g1_route_clusters, c6_route_archetypes, d6_transport_poverty.
        df: For route sections, route_clusters.parquet (unfiltered — routes have
            no region/urban-rural dimension). For d6, lsoa_clusters_hdbscan.parquet
            (callers may pass the unfiltered frame — clustering was computed
            nationally and does not vary by filter, same as SHAP; see ISSUES §4.3).

    Returns:
        Dict with n_clusters, entity_type, clusters list, or {} if the
        required columns/data are absent.
    """
    if df.empty:
        return {}
    if section_id in _ROUTE_ENTITY_TYPES:
        return _build_route_clusters(section_id, df)
    if section_id == "d6_transport_poverty":
        return _build_lsoa_archetypes(df)
    return {}
