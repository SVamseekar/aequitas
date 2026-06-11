"""Maps each precomputed section_id to its chart_data payload.

`build_chart_data` is called from `precompute_all_sections` immediately after
`_dispatch` produces `stats` for a section. It re-derives the same filtered
DataFrames `_dispatch` used (or cheap variants of them) and feeds them into
`aequitas.intelligence.chart_data_builder`'s `build_*` functions.

Task 1 covered 19 sections (scatter_regression, lorenz_curve, shap_bar,
scatter_clusters, box_violin, heatmap families). Task 2 adds the
horizontal_bar / grouped_bar / stacked_bar / choropleth families. All other
section_ids return `{}`.
"""

import pandas as pd

from aequitas.intelligence import chart_data_builder
from aequitas.intelligence.section_registry import SECTION_REGISTRY
from aequitas.warehouse.precompute import _filter_by_lsoa, _Sources
from aequitas.warehouse.stats_builders.correlation import CORRELATION_CONFIG
from aequitas.warehouse.stats_builders.equity import _MIN_DISTINCT_DECILES
from aequitas.warehouse.stats_builders.ranking import RANKING_CONFIG

_CORRELATION_SECTIONS = {
    "b5_frequency_deprivation",
    "d1_coverage_deprivation",
    "d2_coverage_unemployment",
    "d3_coverage_car",
    "d4_coverage_elderly",
    "d5_coverage_income",
}

_SCATTER_REGRESSION_SECTIONS = _CORRELATION_SECTIONS | {"c5_length_vs_frequency", "g2_anomalies"}

_LORENZ_SECTIONS = {"f1_gini", "a4_coverage_equity"}

_SHAP_SECTIONS = {"a8_coverage_prediction", "d8_feature_importance", "g4_shap"}

_ROUTE_CLUSTER_SECTIONS = {"c6_route_archetypes", "g1_route_clusters"}

_SCATTER_CLUSTER_SECTIONS = _ROUTE_CLUSTER_SECTIONS | {"d6_transport_poverty"}

_BOX_VIOLIN_SECTIONS = {"c1_route_length", "c2_stops_per_route"}

_RANKING_HORIZONTAL_BAR_SECTIONS = {
    "a1_route_density",
    "a2_stop_density",
    "b1_frequency",
    "f6_equitable_regions",
    "j4_investment_priority",
    "bsa1_franchising_readiness",
}

_SCENARIO_HORIZONTAL_BAR_SECTIONS = {
    "ps1_freq_restoration",
    "ps2_evening_extension",
    "ps3_drt_rural",
    "ps4_franchise",
}


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

    if section_id == "b4_route_frequency":
        return _build_route_frequency_chart(stats)

    if section_id in _RANKING_HORIZONTAL_BAR_SECTIONS:
        if region != "all":
            return {}
        return _chart_horizontal_bar_from_ranking(section_id, sources, region)

    if section_id in _SCENARIO_HORIZONTAL_BAR_SECTIONS:
        return _chart_scenario_horizontal_bar(section_id, stats)

    if section_id == "a7_investment_gap":
        return _build_investment_gap(section_id, region, sources)

    if section_id == "c3_operator_hhi":
        return _build_operator_hhi(section_id, region, sources)

    if section_id == "f2_disparity_ratio":
        return _build_disparity_ratio(section_id, stats, sources, lsoa_cds)

    if section_id == "j1_economic_value":
        return _build_economic_value(section_id, region, sources, lsoa_cds)

    if section_id == "j2_bcr":
        return _build_bcr(section_id, region, sources, lsoa_cds)

    if section_id == "j3_carbon":
        return _build_carbon(section_id, region, sources, lsoa_cds)

    if section_id == "bsa2_operator_concentration":
        return _build_operator_concentration(section_id, region, sources)

    if section_id == "a6_urban_rural_gap":
        return _build_urban_rural_gap_chart(section_id, region_df)

    if section_id == "f5_rural_penalty":
        return _build_urban_rural_gap_chart(section_id, region_df)

    if section_id == "c4_urban_rural_routes":
        return _build_route_urban_rural_chart(sources)

    if section_id == "ps5_scenario_comparison":
        return _build_scenario_comparison(section_id, stats)

    if section_id == "b2_operating_hours":
        return _build_operating_hours(section_id, region, filtered, sources, lsoa_cds)

    if section_id == "b3_weekend_penalty":
        return _build_weekend_penalty(section_id, region, filtered, sources, lsoa_cds)

    if section_id == "bsa3_tier_distribution":
        return _build_tier_distribution_chart(section_id, region, region_name, sources)

    if section_id == "a5_service_deserts":
        return _build_service_deserts_choropleth(section_id, region, region_name, sources)

    if section_id == "c7_network_topology":
        return _build_network_topology_choropleth(section_id, region, region_name, sources)

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
            df=routes,
            x_col=cfg["x_col"],
            y_col=cfg["y_col"],
            id_col="route_id",
            title=title,
            x_label=cfg["x_label"],
            y_label=cfg["y_label"],
        )

    if section_id == "g2_anomalies":
        if not stats:
            return {}
        anomalies_df = _filter_by_lsoa(sources.anomalies_df, lsoa_cds)
        required_cols = {"imd_score", "service_quality_index"}
        if anomalies_df.empty or not required_cols.issubset(anomalies_df.columns):
            return {}
        return chart_data_builder.build_scatter_regression(
            df=anomalies_df,
            x_col="imd_score",
            y_col="service_quality_index",
            id_col="lsoa_cd",
            title=title,
            x_label="IMD Score",
            y_label="Service Quality Index",
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
        df=corr_df,
        x_col=cfg["x_col"],
        y_col=cfg["y_col"],
        id_col="lsoa_cd",
        title=title,
        x_label=cfg["x_label"],
        y_label=cfg["y_label"],
    )


def _build_lorenz_curve(
    section_id: str,
    stats: dict,
    sources: _Sources,
    lsoa_cds: pd.Series,
) -> dict:
    """Lorenz curve chart for f1_gini/a4_coverage_equity; {} if stats empty or <2 deciles."""
    if not stats:
        return {}
    equity_df = _filter_by_lsoa(sources.equity_df, lsoa_cds)
    if equity_df.empty or equity_df["imd_decile"].nunique() < _MIN_DISTINCT_DECILES:
        return {}
    title = SECTION_REGISTRY[section_id].title
    return chart_data_builder.build_lorenz_curve(
        values=equity_df["trips_per_capita"],
        weights=equity_df["population"],
        title=title,
    )


def _build_shap_bar(section_id: str, stats: dict, sources: _Sources) -> dict:
    """SHAP feature-importance bar chart for a8/d8/g4_shap; {} if stats empty."""
    if not stats:
        return {}
    title = SECTION_REGISTRY[section_id].title
    features = sources.shap_df.rename(columns={"mean_abs_shap": "importance"})
    return chart_data_builder.build_shap_bar(
        features=features,
        title=title,
        model_r2=stats.get("r2"),
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
            data=data,
            cluster_labels=cluster_labels,
            title=title,
            x_label="Route Length (km)",
            y_label="Stop Count",
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
        equity_df[["lsoa_cd", "v_imd", "trips_per_capita"]],
        on="lsoa_cd",
        how="inner",
    )
    merged = merged[merged["hdbscan_label"] != -1]
    if merged.empty:
        return {}

    rename_map = {
        "v_imd": "x",
        "trips_per_capita": "y",
        "hdbscan_label": "cluster",
        "lsoa_cd": "id",
    }
    data = merged.rename(columns=rename_map)
    data = data[["x", "y", "cluster", "id"]]

    noise_free = cluster_df[cluster_df["hdbscan_label"] != -1]
    label_pairs = noise_free[["hdbscan_label", "hdbscan_archetype"]].drop_duplicates()
    cluster_labels = dict(label_pairs.itertuples(index=False))

    return chart_data_builder.build_scatter_clusters(
        data=data,
        cluster_labels=cluster_labels,
        title=title,
        x_label="IMD Vulnerability Score",
        y_label="Trips per Capita",
    )


def _build_box_violin(
    section_id: str,
    stats: dict,
    region: str,
    region_name: str,
    sources: _Sources,
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
        x_labels=x_labels,
        y_labels=y_labels,
        values=values,
        title=title,
    )


def _build_route_frequency_chart(stats: dict) -> dict:
    """Horizontal bar of top/bottom routes by n_trips_per_day; {} on guard.

    Combines top_routes and bottom_routes from build_route_frequency_stats
    into a single horizontal bar, labeled "route_short_name (agency_name)".
    """
    if not stats or "top_routes" not in stats or "bottom_routes" not in stats:
        return {}

    top = stats["top_routes"]
    bottom = stats["bottom_routes"]
    seen_labels: set[str] = set()
    rows = []
    for route in top + bottom:
        label = f"{route['route_short_name']} ({route['agency_name']})"
        if label in seen_labels:
            continue
        seen_labels.add(label)
        rows.append({"label": label, "value": route["n_trips_per_day"]})

    if not rows:
        return {}

    data = pd.DataFrame(rows)
    return chart_data_builder.build_horizontal_bar(
        data=data,
        title=SECTION_REGISTRY["b4_route_frequency"].title,
        x_label=stats.get("unit", "trips/day"),
        y_label="Route",
    )


def _chart_horizontal_bar_from_ranking(section_id: str, sources: _Sources, region: str) -> dict:
    """Horizontal bar of region averages for the 7 ranking-derived sections; {} on guard."""
    cfg = RANKING_CONFIG[section_id]
    df = sources.ranking_df
    if df.empty or cfg["group_col"] not in df.columns or cfg["metric"] not in df.columns:
        return {}

    by_region = df.groupby(cfg["group_col"])[cfg["metric"]].mean().dropna()
    if by_region.empty or len(by_region) < 2:
        return {}

    data = pd.DataFrame({"label": by_region.index, "value": by_region.values})
    return chart_data_builder.build_horizontal_bar(
        data=data,
        title=SECTION_REGISTRY[section_id].title,
        x_label=cfg["unit"],
        y_label="Region",
        national_avg=float(by_region.mean()),
    )


def _chart_scenario_horizontal_bar(section_id: str, stats: dict) -> dict:
    """Horizontal bar of population/cost/CO2 for ps1-ps4; {} if stats empty."""
    if not stats or "scenario" not in stats:
        return {}

    scenario = stats["scenario"]
    data = pd.DataFrame(
        {
            "label": ["Population affected (millions)", "Annual cost (£m)", "CO₂ saved (t/yr)"],
            "value": [
                scenario["population_affected"] / 1e6,
                scenario["estimated_annual_cost_m"],
                scenario["co2_saving_t_yr"],
            ],
        }
    )
    return chart_data_builder.build_horizontal_bar(
        data=data,
        title=SECTION_REGISTRY[section_id].title,
        x_label="Value",
        y_label="Metric",
    )


def _build_investment_gap(section_id: str, region: str, sources: _Sources) -> dict:
    """Horizontal bar of regional investment gaps (a7); {} on guard, region=='all' only."""
    if region != "all":
        return {}

    policy_df = sources.policy_df
    if (
        policy_df.empty
        or "region" not in policy_df.columns
        or "trips_per_capita" not in policy_df.columns
    ):
        return {}

    national_median = sources.national_median_trips_per_capita
    below = policy_df[policy_df["trips_per_capita"] < national_median]
    if below.empty:
        return {}

    by_region = below.groupby("region").apply(
        lambda g: (national_median - g["trips_per_capita"]).sum() * 500 / 1e6,
        include_groups=False,
    )
    if by_region.empty:
        return {}

    data = pd.DataFrame({"label": by_region.index, "value": by_region.round(2).values})
    return chart_data_builder.build_horizontal_bar(
        data=data,
        title=SECTION_REGISTRY[section_id].title,
        x_label="Investment gap (£m/yr)",
        y_label="Region",
    )


def _build_operator_hhi(section_id: str, region: str, sources: _Sources) -> dict:
    """Horizontal bar of regional operator HHI (c3); {} on guard, region=='all' only."""
    if region != "all":
        return {}

    routes = sources.route_geometries_df
    if (
        routes.empty
        or "primary_region" not in routes.columns
        or "agency_name" not in routes.columns
    ):
        return {}

    by_region = routes.groupby("primary_region")["agency_name"].apply(
        lambda s: (s.value_counts(normalize=True) * 100).pow(2).sum()
    )
    if len(by_region) < 2:
        return {}

    data = pd.DataFrame({"label": by_region.index, "value": by_region.round(1).values})
    return chart_data_builder.build_horizontal_bar(
        data=data,
        title=SECTION_REGISTRY[section_id].title,
        x_label="HHI",
        y_label="Region",
    )


def _build_disparity_ratio(
    section_id: str, stats: dict, sources: _Sources, lsoa_cds: pd.Series
) -> dict:
    """Horizontal bar of trips per capita by IMD decile (f2); {} if stats empty."""
    if not stats:
        return {}

    equity_df = _filter_by_lsoa(sources.equity_df, lsoa_cds)
    if (
        equity_df.empty
        or "imd_decile" not in equity_df.columns
        or "trips_per_capita" not in equity_df.columns
    ):
        return {}

    by_decile = equity_df.groupby("imd_decile")["trips_per_capita"].mean().reset_index()
    if by_decile.empty:
        return {}

    data = pd.DataFrame(
        {
            "label": "Decile " + by_decile["imd_decile"].astype(str),
            "value": by_decile["trips_per_capita"].round(3),
        }
    )
    return chart_data_builder.build_horizontal_bar(
        data=data,
        title=SECTION_REGISTRY[section_id].title,
        x_label="Trips per capita",
        y_label="IMD Decile",
    )


def _build_economic_value(
    section_id: str, region: str, sources: _Sources, lsoa_cds: pd.Series
) -> dict:
    """Horizontal bar of regional annual time benefit (j1); {} on guard, region=='all' only."""
    if region != "all":
        return {}

    appraisal_df = _filter_by_lsoa(sources.appraisal_df, lsoa_cds)
    if appraisal_df.empty or not {"region", "annual_time_benefit"}.issubset(appraisal_df.columns):
        return {}

    by_region = appraisal_df.groupby("region")["annual_time_benefit"].sum() / 1e6
    if len(by_region) < 2:
        return {}

    data = pd.DataFrame({"label": by_region.index, "value": by_region.round(1).values})
    return chart_data_builder.build_horizontal_bar(
        data=data,
        title=SECTION_REGISTRY[section_id].title,
        x_label="Annual benefit (£m)",
        y_label="Region",
    )


def _build_bcr(section_id: str, region: str, sources: _Sources, lsoa_cds: pd.Series) -> dict:
    """Horizontal bar of regional BCR (j2); {} on guard, region=='all' only."""
    if region != "all":
        return {}

    appraisal_df = _filter_by_lsoa(sources.appraisal_df, lsoa_cds)
    if appraisal_df.empty or not {"region", "pv_benefits", "pv_costs"}.issubset(
        appraisal_df.columns
    ):
        return {}

    by_region = appraisal_df.groupby("region").apply(
        lambda g: g["pv_benefits"].sum() / g["pv_costs"].sum() if g["pv_costs"].sum() else 0.0,
        include_groups=False,
    )
    if len(by_region) < 2:
        return {}

    data = pd.DataFrame({"label": by_region.index, "value": by_region.round(2).values})
    return chart_data_builder.build_horizontal_bar(
        data=data,
        title=SECTION_REGISTRY[section_id].title,
        x_label="BCR",
        y_label="Region",
    )


def _build_carbon(section_id: str, region: str, sources: _Sources, lsoa_cds: pd.Series) -> dict:
    """Horizontal bar of regional net CO2 savings (j3); {} on guard, region=='all' only."""
    if region != "all":
        return {}

    appraisal_df = _filter_by_lsoa(sources.appraisal_df, lsoa_cds)
    if appraisal_df.empty or not {"region", "modal_shift_co2_net_saving_kg"}.issubset(
        appraisal_df.columns
    ):
        return {}

    by_region = appraisal_df.groupby("region")["modal_shift_co2_net_saving_kg"].sum() / 1000
    if len(by_region) < 2:
        return {}

    data = pd.DataFrame({"label": by_region.index, "value": by_region.round(1).values})
    return chart_data_builder.build_horizontal_bar(
        data=data,
        title=SECTION_REGISTRY[section_id].title,
        x_label="Net CO₂ saved (t/yr)",
        y_label="Region",
    )


def _build_operator_concentration(section_id: str, region: str, sources: _Sources) -> dict:
    """Horizontal bar of regional operator HHI from LTA data (bsa2); all-regions only, else {}."""
    if region != "all":
        return {}

    lta = sources.lta_df
    if lta.empty or not {"region", "region_hhi"}.issubset(lta.columns):
        return {}

    by_region = lta.groupby("region")["region_hhi"].mean()
    if len(by_region) < 2:
        return {}

    data = pd.DataFrame({"label": by_region.index, "value": by_region.round(1).values})
    return chart_data_builder.build_horizontal_bar(
        data=data,
        title=SECTION_REGISTRY[section_id].title,
        x_label="HHI",
        y_label="Region",
    )


def _build_route_urban_rural_chart(sources: "_Sources") -> dict:
    """Stacked bar of urban/rural/mixed route share (%) per region (c4); {} on guard.

    Sourced from route_urban_rural.parquet (route_id -> classification,
    primary_region) — see processing/route_urban_rural.py.
    """
    routes = sources.route_urban_rural_df
    required = {"urban_rural_classification", "primary_region"}
    if routes.empty or not required.issubset(routes.columns):
        return {}

    routes = routes.dropna(subset=["primary_region"])
    if routes.empty:
        return {}

    counts = routes.groupby(["primary_region", "urban_rural_classification"]).size().unstack(fill_value=0)
    shares = counts.div(counts.sum(axis=1), axis=0) * 100

    categories = shares.index.tolist()
    series = [
        {"name": label, "values": shares[col].round(1).tolist()}
        for col, label in (("urban", "Urban"), ("rural", "Rural"), ("mixed", "Mixed"))
        if col in shares.columns
    ]
    return chart_data_builder.build_stacked_bar(
        categories=categories,
        series=series,
        title=SECTION_REGISTRY["c4_urban_rural_routes"].title,
    )


def _build_urban_rural_gap_chart(section_id: str, region_df: pd.DataFrame) -> dict:
    """Grouped bar of urban vs rural metric by region (a6/f5); {} on guard."""
    metric = "trips_per_capita" if section_id == "a6_urban_rural_gap" else "service_quality_index"

    if region_df.empty or not {"region", "urban_rural", metric}.issubset(region_df.columns):
        return {}

    pivot = region_df.groupby(["region", "urban_rural"])[metric].mean().unstack(fill_value=0)
    if pivot.empty or "Urban" not in pivot.columns or "Rural" not in pivot.columns:
        return {}

    categories = pivot.index.tolist()
    series = [
        {"name": "Urban", "values": pivot["Urban"].round(3).tolist()},
        {"name": "Rural", "values": pivot["Rural"].round(3).tolist()},
    ]
    return chart_data_builder.build_grouped_bar(
        categories=categories,
        series=series,
        title=SECTION_REGISTRY[section_id].title,
    )


def _build_scenario_comparison(section_id: str, stats: dict) -> dict:
    """Grouped bar comparing population/cost/CO2 across all 4 scenarios (ps5); {} if stats empty."""
    if not stats or "scenarios" not in stats:
        return {}

    scenarios = stats["scenarios"]
    categories = [s["name"] for s in scenarios]
    series = [
        {"name": "Population (millions)", "values": [s["population"] / 1e6 for s in scenarios]},
        {"name": "Cost (£m/yr)", "values": [s["cost_m"] for s in scenarios]},
        {"name": "CO₂ saved (t/yr)", "values": [s["co2_t"] for s in scenarios]},
    ]
    return chart_data_builder.build_grouped_bar(
        categories=categories,
        series=series,
        title=SECTION_REGISTRY[section_id].title,
    )


def _build_operating_hours(
    section_id: str,
    region: str,
    filtered: pd.DataFrame,
    sources: _Sources,
    lsoa_cds: pd.Series,
) -> dict:
    """Grouped bar of median first/last service times by region (b2); all-regions only, else {}."""
    if region != "all":
        return {}

    sq = _filter_by_lsoa(sources.service_quality_df, lsoa_cds)
    if sq.empty or not {"first_service_min", "last_service_min"}.issubset(sq.columns):
        return {}

    if filtered.empty or "region" not in filtered.columns:
        return {}

    joined = sq.merge(filtered[["lsoa_cd", "region"]], on="lsoa_cd", how="inner")
    if joined.empty or "region" not in joined.columns:
        return {}

    by_region = joined.groupby("region")[["first_service_min", "last_service_min"]].median()
    if len(by_region) < 2:
        return {}

    categories = by_region.index.tolist()
    series = [
        {"name": "First service (min)", "values": by_region["first_service_min"].round(1).tolist()},
        {"name": "Last service (min)", "values": by_region["last_service_min"].round(1).tolist()},
    ]
    return chart_data_builder.build_grouped_bar(
        categories=categories,
        series=series,
        title=SECTION_REGISTRY[section_id].title,
    )


def _build_weekend_penalty(
    section_id: str,
    region: str,
    filtered: pd.DataFrame,
    sources: _Sources,
    lsoa_cds: pd.Series,
) -> dict:
    """Grouped bar of mean weekday/Sunday departures by region (b3); all-regions only, else {}."""
    if region != "all":
        return {}

    sq = _filter_by_lsoa(sources.service_quality_df, lsoa_cds)
    if sq.empty or not {"total_weekday_departures", "total_sunday_departures"}.issubset(sq.columns):
        return {}

    if filtered.empty or "region" not in filtered.columns:
        return {}

    joined = sq.merge(filtered[["lsoa_cd", "region"]], on="lsoa_cd", how="inner")
    if joined.empty or "region" not in joined.columns:
        return {}

    by_region = joined.groupby("region")[
        ["total_weekday_departures", "total_sunday_departures"]
    ].mean()
    if len(by_region) < 2:
        return {}

    categories = by_region.index.tolist()
    series = [
        {
            "name": "Weekday departures",
            "values": by_region["total_weekday_departures"].round(1).tolist(),
        },
        {
            "name": "Sunday departures",
            "values": by_region["total_sunday_departures"].round(1).tolist(),
        },
    ]
    return chart_data_builder.build_grouped_bar(
        categories=categories,
        series=series,
        title=SECTION_REGISTRY[section_id].title,
    )


def _build_tier_distribution_chart(
    section_id: str, region: str, region_name: str, sources: _Sources
) -> dict:
    """Stacked bar of franchising readiness tier counts by region (bsa3); {} on guard."""
    lta = sources.lta_df
    if lta.empty or not {"region", "readiness_tier"}.issubset(lta.columns):
        return {}

    if region != "all":
        lta = lta[lta["region"] == region_name]
    if lta.empty:
        return {}

    pivot = lta.groupby(["region", "readiness_tier"], observed=True).size().unstack(fill_value=0)
    if pivot.empty:
        return {}

    categories = pivot.index.tolist()
    series = [{"name": str(tier), "values": pivot[tier].tolist()} for tier in pivot.columns]
    return chart_data_builder.build_stacked_bar(
        categories=categories,
        series=series,
        title=SECTION_REGISTRY[section_id].title,
    )


def _build_service_deserts_choropleth(
    section_id: str, region: str, region_name: str, sources: _Sources
) -> dict:
    """Choropleth of Sunday-desert rate by LAD (a5); {} on guard."""
    lta = sources.lta_df
    required = {"lad_cd", "lad_nm", "sunday_desert_rate", "region"}
    if lta.empty or not required.issubset(lta.columns):
        return {}

    if region != "all":
        lta = lta[lta["region"] == region_name]
        if lta.empty:
            return {}

    data = pd.DataFrame(
        {
            "area_code": lta["lad_cd"],
            "area_name": lta["lad_nm"],
            "value": (lta["sunday_desert_rate"] * 100).round(1),
        }
    )
    return chart_data_builder.build_choropleth(
        data=data,
        geography="lad",
        metric="pct_sunday_desert",
        title=SECTION_REGISTRY[section_id].title,
        colour_scale="RdYlGn",
    )


def _build_network_topology_choropleth(
    section_id: str, region: str, region_name: str, sources: _Sources
) -> dict:
    """Choropleth of mean trips per capita by LAD (c7); {} on guard."""
    lta = sources.lta_df
    required = {"lad_cd", "lad_nm", "mean_trips_per_cap", "region"}
    if lta.empty or not required.issubset(lta.columns):
        return {}

    if region != "all":
        lta = lta[lta["region"] == region_name]
        if lta.empty:
            return {}

    data = pd.DataFrame(
        {
            "area_code": lta["lad_cd"],
            "area_name": lta["lad_nm"],
            "value": lta["mean_trips_per_cap"].round(1),
        }
    )
    return chart_data_builder.build_choropleth(
        data=data,
        geography="lad",
        metric="mean_trips_per_capita",
        title=SECTION_REGISTRY[section_id].title,
        colour_scale="RdYlGn",
    )
