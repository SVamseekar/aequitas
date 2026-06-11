"""Pre-computation of section_results for the DuckDB warehouse.

For each of the 30 filter combinations (10 regions × 3 area types), computes
all 51 registered analytical sections and stores them as JSON in
section_results. This is called once at build time — never at request time.
"""

import json
from dataclasses import dataclass
from typing import Callable

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.core.types import RegionCode
from aequitas.intelligence.engine import InsightEngine
from aequitas.intelligence.section_registry import SECTION_REGISTRY
from aequitas.warehouse.stats_builders.correlation import build_correlation_stats
from aequitas.warehouse.stats_builders.economic import build_economic_stats
from aequitas.warehouse.stats_builders.equity import build_equity_stats
from aequitas.warehouse.stats_builders.market_concentration import build_market_concentration_stats
from aequitas.warehouse.stats_builders.misc import build_misc_stats
from aequitas.warehouse.stats_builders.ml_clusters import build_ml_clusters_stats
from aequitas.warehouse.stats_builders.ml_prediction import build_ml_prediction_stats
from aequitas.warehouse.stats_builders.policy_scenario import build_policy_scenario_stats
from aequitas.warehouse.stats_builders.ranking import build_ranking_stats
from aequitas.warehouse.stats_builders.route_frequency import build_route_frequency_stats
from aequitas.warehouse.stats_builders.urban_rural_gap import build_urban_rural_gap_stats

# Investigation fix: lsoa_policy_synthesis.region holds full ONS region names,
# while RegionCode/_REGIONS hold ONS region CODES. The two never matched —
# this mapping resolves codes to names before filtering.
REGION_NAMES: dict[str, str] = {
    "E12000001": "North East",
    "E12000002": "North West",
    "E12000003": "Yorkshire and The Humber",
    "E12000004": "East Midlands",
    "E12000005": "West Midlands",
    "E12000006": "East of England",
    "E12000007": "London",
    "E12000008": "South East",
    "E12000009": "South West",
}

_REGIONS = ["all"] + [rc.value for rc in RegionCode]
_AREA_TYPES = ["all", "urban", "rural"]

# NOTE: these sets were corrected against the ACTUAL SECTION_REGISTRY contents
# (verified via direct inspection — the registry's real IDs differ from the
# illustrative names used earlier in this plan's module-grouping table).
_RANKING_SECTIONS = {"a1_route_density", "a2_stop_density", "b1_frequency",
                     "f6_equitable_regions", "j4_investment_priority", "bsa1_franchising_readiness"}
_CORRELATION_SECTIONS = {"b5_frequency_deprivation", "c5_length_vs_frequency", "d1_coverage_deprivation",
                         "d2_coverage_unemployment", "d3_coverage_car", "d4_coverage_elderly",
                         "d5_coverage_income"}
_ML_CLUSTER_SECTIONS = {"c6_route_archetypes", "d6_transport_poverty", "g1_route_clusters"}
_ML_PREDICTION_SECTIONS = {"a8_coverage_prediction", "d8_feature_importance", "g3_coverage_model", "g4_shap"}
_MARKET_CONCENTRATION_SECTIONS = {"c3_operator_hhi", "bsa2_operator_concentration"}
_URBAN_RURAL_GAP_SECTIONS = {"a6_urban_rural_gap", "f5_rural_penalty"}
_POLICY_SCENARIO_SECTIONS = {"ps1_freq_restoration", "ps2_evening_extension", "ps3_drt_rural",
                             "ps4_franchise", "g5_scenario_model", "ps5_scenario_comparison"}
_ECONOMIC_SECTIONS = {"j1_economic_value", "j2_bcr", "j3_carbon"}
_EQUITY_SECTIONS = {"f1_gini", "a4_coverage_equity", "f2_disparity_ratio"}
_MISC_SECTIONS = {"a3_walking_distance", "a5_service_deserts", "b2_operating_hours", "b3_weekend_penalty",
                  "c1_route_length", "c2_stops_per_route", "d7_deprivation_urban_rural", "f3_ethnic_access",
                  "f4_gender_accessibility", "g2_anomalies", "bsa3_tier_distribution"}
# c7_network_topology has its own template (network_topology.j2) shared with no
# other section — it gets a small one-off builder inline in _dispatch (Step 3b
# below) rather than its own module, since it is the only section using this contract.
_NETWORK_TOPOLOGY_SECTIONS = {"c7_network_topology"}

# Sections with no viable data source (ISSUES.md §8.2-§8.4) — stubbed pending
# future analytics-stage joins. Documented per-section in their builder module.
_STUB_SECTIONS = {"f3_ethnic_access", "f4_gender_accessibility"}


@dataclass
class SectionResult:
    region: str
    urban_rural: str
    section_id: str
    stats: dict
    chart_data: dict
    narrative: str

    def to_dict(self) -> dict:
        return {
            "region": self.region,
            "urban_rural": self.urban_rural,
            "section_id": self.section_id,
            "stats": self.stats,
            "chart_data": self.chart_data,
            "narrative": self.narrative,
        }


@dataclass
class _Sources:
    """All audit Parquets/JSON loaded once, used across every combo."""

    policy_df: pd.DataFrame
    equity_df: pd.DataFrame
    equity_summary: dict
    route_geometries_df: pd.DataFrame
    route_urban_rural_df: pd.DataFrame
    route_trip_frequency_df: pd.DataFrame
    route_clusters_df: pd.DataFrame
    lsoa_clusters_df: pd.DataFrame
    shap_df: pd.DataFrame
    anomalies_df: pd.DataFrame
    lta_df: pd.DataFrame
    policy_scenarios_df: pd.DataFrame
    service_levels_df: pd.DataFrame
    service_quality_df: pd.DataFrame
    appraisal_df: pd.DataFrame
    national_median_trips_per_capita: float
    ranking_df: pd.DataFrame
    correlation_df: pd.DataFrame
    rf_r2: float | None


def _read_parquet_or_empty(path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def _load_service_quality(path) -> pd.DataFrame:
    """Load lsoa_service_quality, normalising its LSOA21CD column to lsoa_cd.

    This source uses LSOA21CD (the ONS 2021 boundary column name) while every
    other audit table uses lsoa_cd — normalise once at load time so all
    downstream filtering/joining can use a single consistent column name.
    """
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    return df.rename(columns={"LSOA21CD": "lsoa_cd"})


def _build_ranking_df(
    policy_df: pd.DataFrame,
    route_geometries_df: pd.DataFrame,
    service_levels_df: pd.DataFrame,
    lta_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build a per-LSOA frame enriched with the metrics RANKING_CONFIG needs.

    `lsoa_policy_synthesis` lacks route_count, stops_per_1k, franchising_readiness,
    and primary_region — these live in route_geometries / lsoa_service_levels /
    lta_franchising_readiness respectively. RANKING_CONFIG's
    `df.groupby(group_col)[metric].mean()` contract needs every (region,
    metric) pair reachable from a single frame, so region-level aggregates
    are broadcast back onto every LSOA row in that region (mean of a constant
    equals the constant — the regional aggregate is preserved exactly).

    Args:
        policy_df: National lsoa_policy_synthesis frame (one row per LSOA).
        route_geometries_df: Routes with primary_region, used to compute
            route_count per region.
        service_levels_df: lsoa_service_levels with stops_per_1k per LSOA.
        lta_df: lta_franchising_readiness with franchising_readiness per LAD,
            aggregated to a region-level mean and broadcast.

    Returns:
        Copy of policy_df with route_count, primary_region, stops_per_1k,
        and franchising_readiness columns added (NaN where unavailable).
    """
    df = policy_df.copy()
    df["primary_region"] = df["region"]

    if not route_geometries_df.empty and "primary_region" in route_geometries_df.columns:
        route_count_by_region = route_geometries_df.groupby("primary_region").size()
        df["route_count"] = df["primary_region"].map(route_count_by_region)
    else:
        df["route_count"] = pd.NA

    if not service_levels_df.empty and "stops_per_1k" in service_levels_df.columns:
        df = df.merge(service_levels_df[["lsoa_cd", "stops_per_1k"]], on="lsoa_cd", how="left")
    else:
        df["stops_per_1k"] = pd.NA

    if not lta_df.empty and "franchising_readiness" in lta_df.columns and "region" in lta_df.columns:
        readiness_by_region = lta_df.groupby("region")["franchising_readiness"].mean()
        df["franchising_readiness"] = df["region"].map(readiness_by_region)
    else:
        df["franchising_readiness"] = pd.NA

    return df


def _build_correlation_df(policy_df: pd.DataFrame, master_lsoa_path) -> pd.DataFrame:
    """Merge socio-economic factors needed by CORRELATION_CONFIG onto policy_df.

    d2-d5 correlation sections need unemployment_rate, nocar_pct, elderly_pct,
    and income_score — none of which exist in lsoa_policy_synthesis. They live
    in master_lsoa_table (Phase 0's per-LSOA socio-economic factor table),
    joined here on lsoa_cd.
    """
    if not master_lsoa_path.exists():
        return policy_df

    extra_cols = ["lsoa_cd", "unemployment_rate", "nocar_pct", "elderly_pct", "income_score"]
    master_df = pd.read_parquet(master_lsoa_path, columns=extra_cols)
    return policy_df.merge(master_df, on="lsoa_cd", how="left", suffixes=("", "_master"))


def _load_sources(cfg: PipelineConfig) -> _Sources | None:
    audit = cfg.audit_dir
    policy_path = audit / "lsoa_policy_synthesis.parquet"
    equity_path = audit / "lsoa_equity_metrics.parquet"
    if not policy_path.exists() or not equity_path.exists():
        logger.warning("Audit Parquets not found — precompute returning empty results")
        return None

    policy_df = pd.read_parquet(policy_path)

    equity_summary: dict = {}
    summary_path = audit / "equity_summary.json"
    if summary_path.exists():
        equity_summary = json.loads(summary_path.read_text())

    rf_r2: float | None = None
    ground_truth_path = audit / "ground_truth.json"
    if ground_truth_path.exists():
        try:
            ground_truth = json.loads(ground_truth_path.read_text())
            rf_r2 = float(ground_truth["analytics"]["rf_r2_test"])
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(f"Could not read rf_r2_test from ground_truth.json: {exc}")
    else:
        logger.warning(f"ground_truth.json not found at {ground_truth_path}")

    shap_path = audit / "shap_summary.csv"
    shap_df = pd.read_csv(shap_path) if shap_path.exists() else pd.DataFrame()

    # lsoa_economic_appraisal.region is all "Unknown" — recover real
    # region/urban_rural by joining to lsoa_policy_synthesis via lsoa_cd.
    appraisal_raw = _read_parquet_or_empty(audit / "lsoa_economic_appraisal.parquet")
    appraisal_df = pd.DataFrame()
    if not appraisal_raw.empty:
        appraisal_df = appraisal_raw.drop(columns=["region", "urban_rural"], errors="ignore").merge(
            policy_df[["lsoa_cd", "region", "urban_rural"]], on="lsoa_cd", how="inner",
        )

    route_geometries_df = _read_parquet_or_empty(audit / "route_geometries.parquet")
    route_urban_rural_df = _read_parquet_or_empty(audit / "route_urban_rural.parquet")
    route_trip_frequency_df = _read_parquet_or_empty(audit / "route_trip_frequency.parquet")
    lta_df = _read_parquet_or_empty(audit / "lta_franchising_readiness.parquet")
    service_levels_df = _read_parquet_or_empty(audit / "lsoa_service_levels.parquet")

    return _Sources(
        policy_df=policy_df,
        equity_df=pd.read_parquet(equity_path),
        equity_summary=equity_summary,
        route_geometries_df=route_geometries_df,
        route_urban_rural_df=route_urban_rural_df,
        route_trip_frequency_df=route_trip_frequency_df,
        route_clusters_df=_read_parquet_or_empty(audit / "route_clusters.parquet"),
        lsoa_clusters_df=_read_parquet_or_empty(audit / "lsoa_clusters_hdbscan.parquet"),
        shap_df=shap_df,
        anomalies_df=_read_parquet_or_empty(audit / "anomalies.parquet"),
        lta_df=lta_df,
        policy_scenarios_df=_read_parquet_or_empty(audit / "policy_scenarios.parquet"),
        service_levels_df=service_levels_df,
        service_quality_df=_load_service_quality(audit / "lsoa_service_quality.parquet"),
        appraisal_df=appraisal_df,
        national_median_trips_per_capita=float(policy_df["trips_per_capita"].median()),
        ranking_df=_build_ranking_df(policy_df, route_geometries_df, service_levels_df, lta_df),
        correlation_df=_build_correlation_df(policy_df, audit / "master_lsoa_table.parquet"),
        rf_r2=rf_r2,
    )


def _filter_by_lsoa(df: pd.DataFrame, filtered_lsoa_cds: pd.Series) -> pd.DataFrame:
    if df.empty or "lsoa_cd" not in df.columns:
        return df
    return df[df["lsoa_cd"].isin(filtered_lsoa_cds)]


def _filter_by_region_col(df: pd.DataFrame, column: str, value: str) -> pd.DataFrame:
    if df.empty or column not in df.columns or value == "all":
        return df
    return df[df[column] == value]


def precompute_all_sections(cfg: PipelineConfig) -> list[dict]:
    """Precompute all 51 section results for the 30 filter combinations.

    Loads Phase 0 audit Parquets once, applies region/area-type filters per
    combo, dispatches to the appropriate stats builder per section, runs
    InsightEngine, and returns the full list of section results.

    Args:
        cfg: Pipeline configuration.

    Returns:
        List of dicts, each with keys: region, urban_rural, section_id,
        stats, chart_data, narrative. Length is 30 x len(SECTION_REGISTRY).
    """
    from aequitas.warehouse.chart_dispatch import build_chart_data

    sources = _load_sources(cfg)
    if sources is None:
        return []

    engine = InsightEngine()
    results: list[dict] = []

    for region in _REGIONS:
        region_name = "England" if region == "all" else REGION_NAMES[region]
        region_value = "all" if region == "all" else region_name

        for urban_rural in _AREA_TYPES:
            policy_df = sources.policy_df
            region_mask = pd.Series(True, index=policy_df.index)
            if region_value != "all":
                region_mask = policy_df["region"] == region_value

            ur_mask = pd.Series(True, index=policy_df.index)
            if urban_rural != "all":
                ur_mask = policy_df["urban_rural"].str.lower().str.startswith(urban_rural)

            filtered = policy_df[region_mask & ur_mask]
            region_df = policy_df[region_mask]  # region-filtered, area-type UNfiltered (§4.2)
            lsoa_cds = filtered["lsoa_cd"]

            for section_id in SECTION_REGISTRY:
                stats = _dispatch(
                    section_id=section_id,
                    region=region,
                    urban_rural=urban_rural,
                    region_name=region_name,
                    filtered=filtered,
                    region_df=region_df,
                    sources=sources,
                    lsoa_cds=lsoa_cds,
                )
                result = engine.generate(section_id=section_id, region=region, urban_rural=urban_rural, stats=stats)
                chart_data = build_chart_data(
                    section_id=section_id,
                    stats=stats,
                    region=region,
                    region_name=region_name,
                    urban_rural=urban_rural,
                    filtered=filtered,
                    region_df=region_df,
                    sources=sources,
                    lsoa_cds=lsoa_cds,
                )
                results.append(
                    SectionResult(
                        region=region, urban_rural=urban_rural, section_id=section_id,
                        stats=stats, chart_data=chart_data, narrative=result["narrative"],
                    ).to_dict()
                )

    logger.info(f"Precomputed {len(results)} section results")
    return results


def _dispatch(
    section_id: str,
    region: str,
    urban_rural: str,
    region_name: str,
    filtered: pd.DataFrame,
    region_df: pd.DataFrame,
    sources: _Sources,
    lsoa_cds: pd.Series,
) -> dict:
    """Route a section_id to its builder module with the data it needs."""
    if section_id in _STUB_SECTIONS:
        return {}

    if section_id in _RANKING_SECTIONS:
        ranking_filtered = _filter_by_lsoa(sources.ranking_df, filtered["lsoa_cd"])
        return build_ranking_stats(section_id, filtered=ranking_filtered, national_df=sources.ranking_df, region=region, region_name=region_name)

    if section_id in _CORRELATION_SECTIONS:
        if section_id == "c5_length_vs_frequency":
            routes = sources.route_geometries_df
            if region != "all" and "primary_region" in routes.columns:
                routes = routes[routes["primary_region"] == region_name]
            return build_correlation_stats(section_id, df=routes)
        corr_df = _filter_by_lsoa(sources.correlation_df, lsoa_cds)
        return build_correlation_stats(section_id, df=corr_df)

    if section_id in _ML_CLUSTER_SECTIONS:
        if section_id == "d6_transport_poverty":
            cluster_df = _filter_by_lsoa(sources.lsoa_clusters_df, lsoa_cds)
        else:
            cluster_df = sources.route_clusters_df
            if region != "all" and "primary_region" in cluster_df.columns:
                cluster_df = cluster_df[cluster_df["primary_region"] == region_name]
        return build_ml_clusters_stats(section_id, df=cluster_df)

    if section_id in _ML_PREDICTION_SECTIONS:
        return build_ml_prediction_stats(section_id, shap_df=sources.shap_df, r2=sources.rf_r2)

    if section_id in _MARKET_CONCENTRATION_SECTIONS:
        routes = sources.route_geometries_df
        if region != "all" and "primary_region" in routes.columns:
            routes = routes[routes["primary_region"] == region_name]
        lta = sources.lta_df
        if region != "all" and "region" in lta.columns:
            lta = lta[lta["region"] == region_name]
        return build_market_concentration_stats(section_id, routes_df=routes, lta_df=lta, region_name=region_name)

    if section_id == "b4_route_frequency":
        return build_route_frequency_stats(
            route_trip_frequency_df=sources.route_trip_frequency_df,
            route_urban_rural_df=sources.route_urban_rural_df,
            region=region,
            region_name=region_name,
            urban_rural=urban_rural,
        )

    if section_id == "c4_urban_rural_routes":
        return build_urban_rural_gap_stats(
            section_id,
            region_df=region_df,
            urban_rural=urban_rural,
            route_urban_rural_df=sources.route_urban_rural_df,
            route_geometries_df=sources.route_geometries_df,
            region_name=region_name,
            region=region,
        )

    if section_id in _URBAN_RURAL_GAP_SECTIONS:
        return build_urban_rural_gap_stats(section_id, region_df=region_df, urban_rural=urban_rural)

    if section_id in _POLICY_SCENARIO_SECTIONS:
        return build_policy_scenario_stats(section_id, scenarios_df=sources.policy_scenarios_df)

    if section_id in _ECONOMIC_SECTIONS:
        return build_economic_stats(section_id, appraisal_df=_filter_by_lsoa(sources.appraisal_df, lsoa_cds), region_name=region_name)

    if section_id in _EQUITY_SECTIONS:
        return build_equity_stats(section_id, equity_df=_filter_by_lsoa(sources.equity_df, lsoa_cds))

    if section_id in _MISC_SECTIONS:
        return build_misc_stats(
            section_id,
            region=region,
            region_name=region_name,
            urban_rural=urban_rural,
            policy_df=filtered,
            service_levels_df=_filter_by_lsoa(sources.service_levels_df, lsoa_cds),
            service_quality_df=_filter_by_lsoa(sources.service_quality_df, lsoa_cds),
            route_geometries_df=sources.route_geometries_df,
            anomalies_df=_filter_by_lsoa(sources.anomalies_df, lsoa_cds),
            lta_df=_filter_by_region_col(sources.lta_df, "region", region_name) if region != "all" else sources.lta_df,
        )

    if section_id in _NETWORK_TOPOLOGY_SECTIONS:
        return _build_network_topology(sources.route_geometries_df, region, region_name)

    if section_id == "a7_investment_gap":
        return _build_gap_to_target(filtered, sources.national_median_trips_per_capita)

    return {}


def _build_network_topology(routes_df: pd.DataFrame, region: str, region_name: str) -> dict:
    """Stats for c7_network_topology -> network_topology.j2 (the only section using this contract).

    {n_cross_la, pct_cross_la, densest_corridor, densest_count, mean_length, median_length}
    """
    if routes_df.empty or "cross_la" not in routes_df.columns:
        return {}

    df = routes_df
    if region != "all" and "primary_region" in df.columns:
        df = df[df["primary_region"] == region_name]
    if df.empty:
        return {}

    cross_la = df[df["cross_la"]]
    n_total = len(df)
    stats = {
        "n_cross_la": int(len(cross_la)),
        "pct_cross_la": round(len(cross_la) / n_total * 100, 1),
        "mean_length": round(float(df["length_km"].mean()), 1),
        "median_length": round(float(df["length_km"].median()), 1),
    }

    if region == "all" and not cross_la.empty and "primary_region" in cross_la.columns:
        by_region = cross_la.groupby("primary_region").size()
        densest = by_region.idxmax()
        stats["densest_corridor"] = str(densest)
        stats["densest_count"] = int(by_region.loc[densest])

    return stats


def _build_gap_to_target(filtered: pd.DataFrame, national_median: float) -> dict:
    """Gap-to-target stats, fixed to use a fixed national yardstick (§2.5/§8.5).

    The previous implementation computed the median from the FILTERED
    (region-scoped) frame — making every region's "below average" share
    converge to ~50% by construction, since each region was judged against
    its own moving median rather than a comparable national benchmark.
    """
    if filtered.empty or "trips_per_capita" not in filtered.columns:
        return {}

    below = filtered[filtered["trips_per_capita"] < national_median]
    n_below = len(below)
    mean_gap = float((national_median - below["trips_per_capita"]).mean()) if n_below > 0 else 0.0
    # Methodology note in template: £500/LSOA/unit gap/year proxy for route contract cost.
    total_gap = float((national_median - below["trips_per_capita"]).sum()) if n_below > 0 else 0.0
    total_annual_cost_m = round(total_gap * 500 / 1_000_000, 1)

    return {
        "n_below": int(n_below),
        "pct_below": round(n_below / len(filtered) * 100, 1) if len(filtered) > 0 else 0.0,
        "target": round(national_median, 2),
        "target_description": "national median",
        "unit": "trips/capita",
        "mean_gap": round(mean_gap, 2),
        "total_annual_cost_m": total_annual_cost_m,
    }
