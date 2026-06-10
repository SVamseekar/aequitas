"""Maps each precomputed section_id to its chart_data payload.

`build_chart_data` is called from `precompute_all_sections` immediately after
`_dispatch` produces `stats` for a section. It re-derives the same filtered
DataFrames `_dispatch` used (or cheap variants of them) and feeds them into
`aequitas.intelligence.chart_data_builder`'s `build_*` functions.

Only the 19 sections covered by Task 1 of the chart-data-wiring design
(scatter_regression, lorenz_curve, shap_bar, scatter_clusters, box_violin,
heatmap families) are implemented here. All other section_ids return `{}`.
"""

import pandas as pd

from aequitas.intelligence import chart_data_builder
from aequitas.intelligence.section_registry import SECTION_REGISTRY
from aequitas.warehouse.precompute import _filter_by_lsoa, _Sources
from aequitas.warehouse.stats_builders.correlation import CORRELATION_CONFIG
from aequitas.warehouse.stats_builders.equity import _MIN_DISTINCT_DECILES

_CORRELATION_SECTIONS = {
    "b5_frequency_deprivation", "d1_coverage_deprivation", "d2_coverage_unemployment",
    "d3_coverage_car", "d4_coverage_elderly", "d5_coverage_income",
}

_SCATTER_REGRESSION_SECTIONS = _CORRELATION_SECTIONS | {"c5_length_vs_frequency", "g2_anomalies"}

_LORENZ_SECTIONS = {"f1_gini", "a4_coverage_equity"}

_SHAP_SECTIONS = {"a8_coverage_prediction", "d8_feature_importance", "g4_shap"}

_ROUTE_CLUSTER_SECTIONS = {"c6_route_archetypes", "g1_route_clusters"}

_SCATTER_CLUSTER_SECTIONS = _ROUTE_CLUSTER_SECTIONS | {"d6_transport_poverty"}

_BOX_VIOLIN_SECTIONS = {"c1_route_length", "c2_stops_per_route"}


def build_chart_data(
    section_id: str,
    stats: dict,
    region: str,
    region_name: str,
    urban_rural: str,
    filtered: pd.DataFrame,
    region_df: pd.DataFrame,
    sources: _Sources,
    lsoa_cds: pd.Series,
) -> dict:
    """Return chart_data dict for section_id, or {} if not chartable.

    `urban_rural` and `filtered` are accepted for signature parity with
    `precompute.py`'s `_dispatch` and may be used by future section families.
    """
    if section_id in _SCATTER_REGRESSION_SECTIONS:
        return _build_scatter_regression(section_id, stats, region, region_name, sources, lsoa_cds)

    if section_id in _LORENZ_SECTIONS:
        return _build_lorenz_curve(section_id, stats, sources, lsoa_cds)

    if section_id in _SHAP_SECTIONS:
        return _build_shap_bar(section_id, stats, sources)

    if section_id in _SCATTER_CLUSTER_SECTIONS:
        return _build_scatter_clusters(section_id, stats, region, region_name, sources, lsoa_cds)

    if section_id in _BOX_VIOLIN_SECTIONS:
        return _build_box_violin(section_id, stats, region, region_name, sources)

    if section_id == "d7_deprivation_urban_rural":
        return _build_heatmap(section_id, stats, region_df)

    return {}


def _build_scatter_regression(
    section_id: str,
    stats: dict,
    region: str,
    region_name: str,
    sources: _Sources,
    lsoa_cds: pd.Series,
) -> dict:
    """Scatter+regression chart for b5/d1-d5/c5_length_vs_frequency/g2_anomalies; {} on guard."""
    title = SECTION_REGISTRY[section_id].title

    if section_id == "c5_length_vs_frequency":
        routes = sources.route_geometries_df
        if region != "all" and "primary_region" in routes.columns:
            routes = routes[routes["primary_region"] == region_name]
        if routes.empty or "length_km" not in routes.columns or "stop_count" not in routes.columns:
            return {}
        cfg = CORRELATION_CONFIG[section_id]
        return chart_data_builder.build_scatter_regression(
            df=routes, x_col=cfg["x_col"], y_col=cfg["y_col"], id_col="route_id",
            title=title, x_label=cfg["x_label"], y_label=cfg["y_label"],
        )

    if section_id == "g2_anomalies":
        if not stats:
            return {}
        anomalies_df = _filter_by_lsoa(sources.anomalies_df, lsoa_cds)
        required_cols = {"imd_score", "service_quality_index"}
        if anomalies_df.empty or not required_cols.issubset(anomalies_df.columns):
            return {}
        return chart_data_builder.build_scatter_regression(
            df=anomalies_df, x_col="imd_score", y_col="service_quality_index", id_col="lsoa_cd",
            title=title, x_label="IMD Score", y_label="Service Quality Index",
        )

    # _CORRELATION_SECTIONS proper (b5, d1-d5)
    if not stats:
        return {}
    cfg = CORRELATION_CONFIG[section_id]
    corr_df = _filter_by_lsoa(sources.correlation_df, lsoa_cds)
    if cfg["x_col"] not in corr_df.columns or cfg["y_col"] not in corr_df.columns:
        return {}
    if len(corr_df[[cfg["x_col"], cfg["y_col"]]].dropna()) < 3:
        return {}
    return chart_data_builder.build_scatter_regression(
        df=corr_df, x_col=cfg["x_col"], y_col=cfg["y_col"], id_col="lsoa_cd",
        title=title, x_label=cfg["x_label"], y_label=cfg["y_label"],
    )


def _build_lorenz_curve(
    section_id: str, stats: dict, sources: _Sources, lsoa_cds: pd.Series,
) -> dict:
    """Lorenz curve chart for f1_gini/a4_coverage_equity; {} if stats empty or <2 deciles."""
    if not stats:
        return {}
    equity_df = _filter_by_lsoa(sources.equity_df, lsoa_cds)
    if equity_df.empty or equity_df["imd_decile"].nunique() < _MIN_DISTINCT_DECILES:
        return {}
    title = SECTION_REGISTRY[section_id].title
    return chart_data_builder.build_lorenz_curve(
        values=equity_df["trips_per_capita"], weights=equity_df["population"], title=title,
    )


def _build_shap_bar(section_id: str, stats: dict, sources: _Sources) -> dict:
    """SHAP feature-importance bar chart for a8/d8/g4_shap; {} if stats empty."""
    if not stats:
        return {}
    title = SECTION_REGISTRY[section_id].title
    features = sources.shap_df.rename(columns={"mean_abs_shap": "importance"})
    return chart_data_builder.build_shap_bar(
        features=features, title=title, model_r2=stats.get("r2"),
    )


def _build_scatter_clusters(
    section_id: str,
    stats: dict,
    region: str,
    region_name: str,
    sources: _Sources,
    lsoa_cds: pd.Series,
) -> dict:
    """Scatter-clusters chart for c6/g1_route_clusters/d6_transport_poverty; {} on guard."""
    if not stats:
        return {}
    title = SECTION_REGISTRY[section_id].title

    if section_id in _ROUTE_CLUSTER_SECTIONS:
        cluster_df = sources.route_clusters_df
        if region != "all" and "primary_region" in cluster_df.columns:
            cluster_df = cluster_df[cluster_df["primary_region"] == region_name]
        if cluster_df.empty:
            return {}
        data = cluster_df[cluster_df["cluster"] != -1].copy()
        if data.empty:
            return {}
        data = data.rename(
            columns={"length_km": "x", "stop_count": "y", "route_id": "id"},
        )
        data = data[["x", "y", "cluster", "id"]]
        cluster_labels = {c["id"]: c["description"] for c in stats.get("clusters", [])}
        return chart_data_builder.build_scatter_clusters(
            data=data, cluster_labels=cluster_labels, title=title,
            x_label="Route Length (km)", y_label="Stop Count",
        )

    # d6_transport_poverty
    cluster_df = _filter_by_lsoa(sources.lsoa_clusters_df, lsoa_cds)
    if cluster_df.empty:
        return {}
    equity_df = _filter_by_lsoa(sources.equity_df, lsoa_cds)
    equity_required = {"v_imd", "trips_per_capita"}
    if equity_df.empty or not equity_required.issubset(equity_df.columns):
        return {}

    merged = cluster_df.merge(
        equity_df[["lsoa_cd", "v_imd", "trips_per_capita"]], on="lsoa_cd", how="inner",
    )
    merged = merged[merged["hdbscan_label"] != -1]
    if merged.empty:
        return {}

    rename_map = {
        "v_imd": "x", "trips_per_capita": "y", "hdbscan_label": "cluster", "lsoa_cd": "id",
    }
    data = merged.rename(columns=rename_map)
    data = data[["x", "y", "cluster", "id"]]

    noise_free = cluster_df[cluster_df["hdbscan_label"] != -1]
    label_pairs = noise_free[["hdbscan_label", "hdbscan_archetype"]].drop_duplicates()
    cluster_labels = dict(label_pairs.itertuples(index=False))

    return chart_data_builder.build_scatter_clusters(
        data=data, cluster_labels=cluster_labels, title=title,
        x_label="IMD Vulnerability Score", y_label="Trips per Capita",
    )


def _build_box_violin(
    section_id: str, stats: dict, region: str, region_name: str, sources: _Sources,
) -> dict:
    """Box/violin distribution chart for c1_route_length/c2_stops_per_route; {} if no data."""
    routes = sources.route_geometries_df
    if region != "all" and "primary_region" in routes.columns:
        routes = routes[routes["primary_region"] == region_name]
    if routes.empty:
        return {}

    title = SECTION_REGISTRY[section_id].title
    column = "length_km" if section_id == "c1_route_length" else "stop_count"
    unit = "km" if section_id == "c1_route_length" else "stops"

    if column not in routes.columns:
        return {}

    if region == "all" and "primary_region" in routes.columns:
        groups = {r: g[column].dropna() for r, g in routes.groupby("primary_region")}
    else:
        groups = {region_name: routes[column].dropna()}

    groups = {label: values for label, values in groups.items() if not values.empty}
    if not groups:
        return {}

    return chart_data_builder.build_box_violin(groups=groups, title=title, unit=unit)


def _build_heatmap(section_id: str, stats: dict, region_df: pd.DataFrame) -> dict:
    """Heatmap chart for d7_deprivation_urban_rural (SQI by decile/urban-rural); {} on guard."""
    if not stats:
        return {}

    required = {"urban_rural", "imd_decile", "service_quality_index"}
    if region_df.empty or not required.issubset(region_df.columns):
        return {}

    clean = region_df.dropna(subset=list(required))
    if clean.empty:
        return {}

    pivot = (
        clean.groupby(["urban_rural", "imd_decile"])["service_quality_index"]
        .mean()
        .unstack(fill_value=0)
    )
    if pivot.empty:
        return {}

    title = SECTION_REGISTRY[section_id].title
    x_labels = [str(d) for d in sorted(pivot.columns)]
    y_labels = list(pivot.index)
    values = pivot.values.tolist()

    return chart_data_builder.build_heatmap(
        x_labels=x_labels, y_labels=y_labels, values=values, title=title,
    )
