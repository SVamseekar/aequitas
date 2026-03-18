"""Pre-computation of section_results for the DuckDB warehouse.

For each filter combination, computes all 51 analytical sections and stores
them with stats, chart_data, and narratives in section_results.

Called once at build time — never at request time.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.core.types import RegionCode
from aequitas.intelligence.calculators import (
    calculate_correlation,
    calculate_gap_to_target,
    describe_distribution,
    rank_regions,
)
from aequitas.intelligence.chart_data_builder import (
    build_box_violin,
    build_choropleth,
    build_grouped_bar,
    build_heatmap,
    build_horizontal_bar,
    build_lorenz_curve,
    build_scatter_clusters,
    build_scatter_regression,
    build_shap_bar,
    build_stacked_bar,
)
from aequitas.intelligence.engine import InsightEngine
from aequitas.intelligence.rules import (
    AccessibilityRule,
    AnomalyRule,
    CarbonRule,
    ClusterRule,
    CorrelationRule,
    DecileRule,
    DemographicRule,
    DesertRule,
    DistributionRule,
    GapToInvestmentRule,
    GiniEquityRule,
    HeatmapRule,
    MLPredictionRule,
    MarketConcentrationRule,
    MinLsoaRule,
    NetworkRule,
    ScenarioComparisonRule,
    TierRule,
    UrbanRuralRule,
)
from aequitas.intelligence.section_registry import SECTION_REGISTRY


# All region codes + "all"
_REGIONS = ["all"] + [rc.value for rc in RegionCode]
_AREA_TYPES = ["all", "urban", "rural"]


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


def _load_parquet_safe(path: Path) -> pd.DataFrame | None:
    """Load a Parquet file, returning None if it doesn't exist."""
    if path.exists():
        return pd.read_parquet(path)
    logger.warning(f"Parquet not found: {path}")
    return None


# ONS code → region name mapping (policy parquets use names, warehouse uses codes)
_REGION_CODE_TO_NAME: dict[str, str] = {
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


def _filter_data(
    df: pd.DataFrame, region: str, urban_rural: str,
) -> pd.DataFrame:
    """Apply region and urban/rural filters to a DataFrame.

    Handles both ONS region codes (E12000007) and region names (London)
    in the data by trying both the code and its name equivalent.
    """
    mask = pd.Series(True, index=df.index)
    if region != "all" and "region" in df.columns:
        region_name = _REGION_CODE_TO_NAME.get(region, region)
        # Match either the ONS code or the region name
        mask &= (df["region"] == region) | (df["region"] == region_name)
    if urban_rural != "all" and "urban_rural" in df.columns:
        mask &= df["urban_rural"].str.lower().str.startswith(urban_rural)
    return df[mask]


def _minutes_to_time(minutes: float) -> str:
    """Convert minutes-from-midnight to HH:MM string."""
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h:02d}:{m:02d}"


def precompute_all_sections(cfg: PipelineConfig) -> list[dict]:
    """Precompute all section results for all filter combinations.

    Loads all required Parquet files, iterates over the 51-section registry,
    applies filters, builds stats + chart_data, renders narratives.

    Args:
        cfg: Pipeline configuration.

    Returns:
        List of dicts with keys: region, urban_rural, section_id, stats,
        chart_data, narrative.
    """
    engine = InsightEngine()
    results: list[dict] = []

    data = _load_all_data(cfg)
    if not data:
        logger.warning("No data loaded — precompute returning empty results")
        return results

    for region in _REGIONS:
        for urban_rural in _AREA_TYPES:
            for section_id in SECTION_REGISTRY:
                try:
                    stats, chart_data = _build_section(
                        section_id, data, region, urban_rural,
                    )
                except Exception as exc:
                    logger.warning(f"Failed to build {section_id} for {region}/{urban_rural}: {exc}")
                    stats, chart_data = {}, {}

                result = engine.generate(
                    section_id=section_id,
                    region=region,
                    urban_rural=urban_rural,
                    stats=stats,
                )
                results.append(
                    SectionResult(
                        region=region,
                        urban_rural=urban_rural,
                        section_id=section_id,
                        stats=stats,
                        chart_data=chart_data,
                        narrative=result["narrative"],
                    ).to_dict()
                )

    logger.info(f"Precomputed {len(results)} section results")
    return results


def _load_all_data(cfg: PipelineConfig) -> dict[str, pd.DataFrame]:
    """Load all Parquet files needed by the 51 sections.

    Falls back to audit/ when processed/ copy is absent so tests can run
    against Phase 0 outputs without a full Phase 1 pipeline run.

    After loading, enriches sparse parquets (accessibility, service_quality,
    clusters, anomalies) with region/population/urban_rural via left-join
    to policy. Also merges socio-economic factors from master_lsoa_table
    into policy so correlation builders (d2-d5, f3) find the columns they need.
    """
    def _p(filename: str) -> Path:
        proc = cfg.processed_dir / filename
        return proc if proc.exists() else cfg.audit_dir / filename

    sources: dict[str, Path] = {
        "policy": _p("lsoa_policy_synthesis.parquet"),
        "equity": _p("lsoa_equity_metrics.parquet"),
        "service_quality": _p("lsoa_service_quality.parquet"),
        "economic": _p("lsoa_economic_appraisal.parquet"),
        "accessibility": _p("lsoa_2sfca.parquet"),
        "routes": _p("route_geometries.parquet"),
        "lta": _p("lta_franchising_readiness.parquet"),
        "scenarios": cfg.audit_dir / "policy_scenarios.parquet",
        "modal_shift": cfg.audit_dir / "modal_shift_scenarios.parquet",
        "anomalies": cfg.audit_dir / "anomalies.parquet",
        "clusters": cfg.audit_dir / "lsoa_clusters_hdbscan.parquet",
        "route_clusters": cfg.audit_dir / "route_clusters.parquet",
        "coverage_pred": cfg.audit_dir / "coverage_prediction.parquet",
    }
    data: dict[str, pd.DataFrame] = {}
    for key, path in sources.items():
        df = _load_parquet_safe(path)
        if df is not None:
            data[key] = df

    # Load master_lsoa_table for socio-economic factors
    master = _load_parquet_safe(_p("master_lsoa_table.parquet"))

    # Normalise LSOA column name: pipeline outputs lsoa_code, audit parquets
    # use lsoa_cd. Canonical name for warehouse/precompute is lsoa_cd.
    for key in list(data.keys()):
        if "lsoa_code" in data[key].columns and "lsoa_cd" not in data[key].columns:
            data[key] = data[key].rename(columns={"lsoa_code": "lsoa_cd"})
    if master is not None and "lsoa_code" in master.columns and "lsoa_cd" not in master.columns:
        master = master.rename(columns={"lsoa_code": "lsoa_cd"})

    # Load SHAP from CSV (no parquet exists — only shap_summary.csv)
    shap_csv = cfg.audit_dir / "shap_summary.csv"
    if shap_csv.exists():
        shap_df = pd.read_csv(shap_csv)
        if "mean_abs_shap" in shap_df.columns:
            shap_df = shap_df.rename(columns={"mean_abs_shap": "importance"})
        data["shap"] = shap_df

    # --- Enrich sparse parquets with region/population/urban_rural ---
    policy_df = data.get("policy")
    if policy_df is not None:
        # Merge socio-economic factors from master into policy
        if master is not None:
            extra_cols = [
                "unemployment_rate", "nocar_pct", "elderly_pct",
                "income_score", "nonwhite_pct", "disability_pct",
            ]
            available = [c for c in extra_cols if c in master.columns and c not in policy_df.columns]
            if available:
                policy_df = policy_df.merge(
                    master[["lsoa_cd"] + available],
                    on="lsoa_cd", how="left",
                )
            data["policy"] = policy_df

        lookup_cols = ["lsoa_cd", "region", "urban_rural", "population"]
        lookup = policy_df[lookup_cols].drop_duplicates(subset=["lsoa_cd"])

        # Enrich accessibility (has LSOA21CD, no region/population/urban_rural)
        if "accessibility" in data:
            acc = data["accessibility"]
            if "LSOA21CD" in acc.columns:
                acc = acc.rename(columns={"LSOA21CD": "lsoa_cd"})
            acc = acc.merge(lookup, on="lsoa_cd", how="left")
            data["accessibility"] = acc

        # Enrich service_quality (has LSOA21CD, no region)
        if "service_quality" in data:
            sq = data["service_quality"]
            if "LSOA21CD" in sq.columns:
                sq = sq.rename(columns={"LSOA21CD": "lsoa_cd"})
            if "region" not in sq.columns:
                sq = sq.merge(lookup[["lsoa_cd", "region"]], on="lsoa_cd", how="left")
            data["service_quality"] = sq

        # Enrich clusters with region/population for D6
        if "clusters" in data:
            cl = data["clusters"]
            if "region" not in cl.columns:
                cl = cl.merge(lookup, on="lsoa_cd", how="left")
                data["clusters"] = cl

        # Enrich anomalies with region
        if "anomalies" in data:
            an = data["anomalies"]
            if "lsoa_cd" in an.columns and "region" not in an.columns:
                an = an.merge(lookup[["lsoa_cd", "region"]], on="lsoa_cd", how="left")
                data["anomalies"] = an

        # Enrich coverage_prediction with region
        if "coverage_pred" in data:
            cp = data["coverage_pred"]
            if "lsoa_cd" in cp.columns and "region" not in cp.columns:
                cp = cp.merge(lookup, on="lsoa_cd", how="left")
                data["coverage_pred"] = cp

        # Enrich economic parquet — region column is "Unknown" for all rows
        # because lsoa_economic_appraisal.parquet was built without ONS region codes.
        # Overwrite region/urban_rural from policy lookup to fix j1/j2/j4.
        if "economic" in data:
            econ = data["economic"]
            if "lsoa_cd" in econ.columns and (
                "region" not in econ.columns
                or econ["region"].eq("Unknown").all()
            ):
                econ = econ.drop(columns=["region", "urban_rural"], errors="ignore")
                econ = econ.merge(
                    lookup[["lsoa_cd", "region", "urban_rural"]],
                    on="lsoa_cd", how="left",
                )
                data["economic"] = econ

    # --- Fix route column names ---
    if "routes" in data:
        r = data["routes"]
        renames: dict[str, str] = {}
        if "length_km" in r.columns and "route_length_km" not in r.columns:
            renames["length_km"] = "route_length_km"
        if "primary_region" in r.columns and "region" not in r.columns:
            renames["primary_region"] = "region"
        if "cross_la" in r.columns and "cross_la_flag" not in r.columns:
            renames["cross_la"] = "cross_la_flag"
        if renames:
            data["routes"] = r.rename(columns=renames)

    return data


def _build_section(
    section_id: str,
    data: dict[str, pd.DataFrame],
    region: str,
    urban_rural: str,
) -> tuple[dict, dict]:
    """Dispatch to the correct builder, return (stats, chart_data)."""
    prefix = section_id.split("_")[0]
    builders: dict[str, Any] = {
        "a1": _build_ranking_density,
        "a2": _build_ranking_density,
        "a3": _build_coverage_gap,
        "a4": _build_equity,
        "a5": _build_desert,
        "a6": _build_urban_rural,
        "a7": _build_gap_to_target,
        "a8": _build_ml_prediction,
        "b1": _build_ranking_density,
        "b2": _build_service_hours,
        "b3": _build_weekend_penalty,
        "b4": _build_ranking_density,
        "b5": _build_correlation,
        "c1": _build_distribution,
        "c2": _build_distribution,
        "c3": _build_market_concentration,
        "c4": _build_urban_rural,
        "c5": _build_correlation,
        "c6": _build_clusters,
        "c7": _build_network,
        "d1": _build_correlation,
        "d2": _build_correlation,
        "d3": _build_correlation,
        "d4": _build_correlation,
        "d5": _build_correlation,
        "d6": _build_clusters,
        "d7": _build_heatmap_section,
        "d8": _build_ml_prediction,
        "f1": _build_equity,
        "f2": _build_equity_decile,
        "f3": _build_demographic,
        "f4": _build_accessibility,
        "f5": _build_urban_rural,
        "f6": _build_ranking_density,
        "g1": _build_clusters,
        "g2": _build_anomaly,
        "g3": _build_ml_prediction,
        "g4": _build_ml_prediction,
        "g5": _build_scenario,
        "j1": _build_economic_value,
        "j2": _build_bcr,
        "j3": _build_carbon,
        "j4": _build_ranking_density,
        "bsa1": _build_franchising,
        "bsa2": _build_market_concentration,
        "bsa3": _build_tier_dist,
        "ps1": _build_scenario,
        "ps2": _build_scenario,
        "ps3": _build_scenario,
        "ps4": _build_scenario,
        "ps5": _build_scenario_comparison,
    }
    builder = builders.get(prefix)
    if builder is None:
        return {}, {}
    return builder(section_id, data, region, urban_rural)


# ---------------------------------------------------------------------------
# Builder functions — each returns (stats_dict, chart_data_dict)
# ---------------------------------------------------------------------------

# Per-section metric and label for ranking charts — avoids all sections
# showing the same trips_per_capita ranking.
_RANKING_METRICS: dict[str, tuple[str, str]] = {
    "a1": ("trips_per_capita", "trips/capita"),
    "a2": ("stop_count", "stops"),
    "b1": ("service_quality_index", "SQI"),
    "b4": ("total_weekday_departures", "departures/day"),
    "f6": ("gini_contribution", "Gini contribution"),
    "j4": ("investment_gap", "investment gap"),
}


def _build_ranking_density(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build ranking by region using the section-appropriate metric."""
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)
    if len(filtered) == 0 or "region" not in filtered.columns:
        return {}, {}

    prefix = section_id.split("_")[0]
    metric, unit = _RANKING_METRICS.get(prefix, ("trips_per_capita", "trips/capita"))
    # Fall back to trips_per_capita if the preferred metric isn't available
    if metric not in filtered.columns:
        metric, unit = "trips_per_capita", "trips/capita"
    if metric not in filtered.columns:
        return {}, {}

    x_label = unit.replace("_", " ").title()

    by_region = filtered.groupby("region")[metric].mean().reset_index()
    by_region.columns = ["label", "value"]

    # Compute national averages from all-England data for pct comparisons
    nat_df = policy.groupby("region")[metric].mean().reset_index()
    nat_avg = float(nat_df[metric].mean()) if len(nat_df) > 0 else float(by_region["value"].mean())

    if len(by_region) < 2:
        # Single-region filter: emit single_region stats for ranking template
        region_name = str(by_region.iloc[0]["label"]) if len(by_region) > 0 else (region if region != "all" else "England")
        region_val = float(by_region.iloc[0]["value"]) if len(by_region) > 0 else 0.0
        vs_nat = round((region_val - nat_avg) / nat_avg * 100, 1) if nat_avg > 0 else 0.0
        stats = {
            "best": {"name": region_name, "value": round(region_val, 2), "pct_above": max(vs_nat, 0)},
            "worst": {"name": region_name, "value": round(region_val, 2), "pct_below": max(-vs_nat, 0)},
            "national_avg": round(nat_avg, 2),
            "unit": unit,
        }
        chart = build_horizontal_bar(
            data=by_region, title=SECTION_REGISTRY[section_id].title,
            x_label=x_label, y_label="Region", national_avg=nat_avg,
        )
        return stats, chart

    best_idx = by_region["value"].idxmax()
    worst_idx = by_region["value"].idxmin()

    stats = {
        "best": {
            "name": str(by_region.loc[best_idx, "label"]),
            "value": round(float(by_region.loc[best_idx, "value"]), 2),
            "pct_above": round((float(by_region.loc[best_idx, "value"]) - nat_avg) / nat_avg * 100, 1),
        },
        "worst": {
            "name": str(by_region.loc[worst_idx, "label"]),
            "value": round(float(by_region.loc[worst_idx, "value"]), 2),
            "pct_below": round((nat_avg - float(by_region.loc[worst_idx, "value"])) / nat_avg * 100, 1),
        },
        "national_avg": round(nat_avg, 2),
        "unit": unit,
    }
    chart = build_horizontal_bar(
        data=by_region, title=SECTION_REGISTRY[section_id].title,
        x_label=x_label, y_label="Region", national_avg=nat_avg,
    )
    return stats, chart


def _build_coverage_gap(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build coverage gap (A3)."""
    acc = data.get("accessibility")
    if acc is None:
        return {}, {}
    filtered = _filter_data(acc, region, urban_rural)
    if not MinLsoaRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    score_col = "sfca_score" if "sfca_score" in filtered.columns else None
    if score_col is None:
        return {}, {}

    n_zero = int((filtered[score_col] == 0).sum())
    pct_covered = round((1 - n_zero / len(filtered)) * 100, 1)
    stats: dict[str, Any] = {
        "pct_covered": pct_covered,
        "n_zero_access": n_zero,
        "pct_zero_access": round(n_zero / len(filtered) * 100, 1),
        "pop_zero_access": int(filtered.loc[filtered[score_col] == 0, "population"].sum()) if "population" in filtered.columns else 0,
    }

    chart: dict = {}
    if "region" in filtered.columns:
        by_region = filtered.groupby("region").apply(
            lambda g: pd.Series({
                "covered": round((g[score_col] > 0).mean() * 100, 1),
                "not_covered": round((g[score_col] == 0).mean() * 100, 1),
            })
        ).reset_index()
        chart = build_stacked_bar(
            categories=by_region["region"].tolist(),
            series=[
                {"name": "Covered", "values": by_region["covered"].tolist()},
                {"name": "Not covered", "values": by_region["not_covered"].tolist()},
            ],
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_equity(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build equity metrics (A4, F1).

    Computes Gini, Palma ratio, and Concentration Index from policy
    trips_per_capita + population (the equity parquet doesn't store these
    as columns — they're scalar outputs of notebook 04c).
    """
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)
    if "trips_per_capita" not in filtered.columns or "population" not in filtered.columns:
        return {}, {}
    if not GiniEquityRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    import numpy as np

    values = filtered["trips_per_capita"].fillna(0).values
    weights = filtered["population"].fillna(1).values

    # Gini coefficient
    sorted_idx = values.argsort()
    sv = values[sorted_idx]
    sw = weights[sorted_idx]
    cum_pop = np.cumsum(sw) / sw.sum()
    weighted_vals = sv * sw
    cum_service = np.cumsum(weighted_vals) / weighted_vals.sum()
    cum_pop = np.concatenate([[0], cum_pop])
    cum_service = np.concatenate([[0], cum_service])
    trapezoid = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    area_under = float(trapezoid(cum_service, cum_pop))
    gini = round(1 - 2 * area_under, 4)

    # Palma ratio — canonical formula from analytics/equity.py:
    # population-weighted mean of top 10% / bottom 40% using cumulative pop fractions
    cum_pop_frac = np.cumsum(sw) / sw.sum()
    bottom_mask = cum_pop_frac <= 0.40
    top_mask = cum_pop_frac > 0.90
    bottom_mean = float(np.average(sv[bottom_mask], weights=sw[bottom_mask])) if bottom_mask.sum() > 0 else 0.0
    top_mean = float(np.average(sv[top_mask], weights=sw[top_mask])) if top_mask.sum() > 0 else 0.0
    palma = round(top_mean / bottom_mean, 3) if bottom_mean > 0 else float("inf")

    # Concentration Index — canonical Wagstaff covariance method from analytics/equity.py
    if "imd_score" in filtered.columns:
        imd_vals = filtered["imd_score"].fillna(0).values
        tpc = filtered["trips_per_capita"].fillna(0).values
        pop = filtered["population"].fillna(1).values
        rank_order = np.argsort(imd_vals)
        pop_by_rank = pop[rank_order]
        total_pop = pop_by_rank.sum()
        frac_rank = (np.cumsum(pop_by_rank) - 0.5 * pop_by_rank) / total_pop
        service_by_rank = tpc[rank_order]
        mean_tpc = float(np.average(service_by_rank, weights=pop_by_rank))
        cov = float(np.average(
            (service_by_rank - mean_tpc) * (frac_rank - 0.5),
            weights=pop_by_rank,
        ))
        ci = round(2 * cov / mean_tpc, 4) if mean_tpc > 0 else 0.0
    else:
        ci = 0.0

    stats: dict[str, Any] = {
        "gini": gini,
        "palma": palma,
        "concentration_index": ci,
    }

    chart = build_lorenz_curve(
        values=filtered["trips_per_capita"].fillna(0),
        weights=filtered["population"].fillna(1),
        title=SECTION_REGISTRY[section_id].title,
    )
    return stats, chart


def _build_desert(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build service desert spotlight (A5)."""
    sq = data.get("service_quality")
    if sq is None:
        return {}, {}
    filtered = _filter_data(sq, region, urban_rural)
    if len(filtered) == 0:
        return {}, {}

    # Use no_service boolean (True = zero service) — total_weekday_departures is never 0
    # because it counts all stops in the LSOA, not just departures from served stops.
    if "no_service" in filtered.columns:
        deserts = filtered[filtered["no_service"] == True]  # noqa: E712
    elif "trips_per_capita" in filtered.columns:
        deserts = filtered[filtered["trips_per_capita"] == 0]
    else:
        return {}, {}

    if not DesertRule().should_fire(n_desert_lsoas=len(deserts)):
        return {}, {}

    stats: dict[str, Any] = {
        "n_desert_lsoas": len(deserts),
        "pop_affected": int(deserts["population"].sum()) if "population" in deserts.columns else 0,
    }
    if "region" in deserts.columns and len(deserts) > 0:
        top_region = deserts["region"].value_counts().idxmax()
        stats["largest_region"] = str(top_region)
        stats["largest_region_count"] = int(deserts["region"].value_counts().max())

    chart: dict = {}
    lta = data.get("lta")
    if lta is not None and "lad_cd" in lta.columns and "sunday_desert_rate" in lta.columns:
        lad_data = lta[["lad_cd", "lad_nm"]].copy()
        lad_data["value"] = (lta["sunday_desert_rate"] * 100).round(1)
        lad_data = lad_data.rename(columns={"lad_cd": "area_code", "lad_nm": "area_name"})
        chart = build_choropleth(
            data=lad_data, title=SECTION_REGISTRY[section_id].title,
            geography="lad", metric="pct_lsoas_no_service", colour_scale="RdYlGn",
        )
    return stats, chart


def _build_urban_rural(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build urban vs rural gap (A6, C4, F5)."""
    policy = data.get("policy")
    if policy is None or "urban_rural" not in policy.columns:
        return {}, {}
    filtered = _filter_data(policy, region, "all")  # always compare both
    metric = "trips_per_capita" if "trips_per_capita" in filtered.columns else None
    if metric is None:
        return {}, {}

    urban = filtered[filtered["urban_rural"].str.lower().str.startswith("urban")]
    rural = filtered[filtered["urban_rural"].str.lower().str.startswith("rural")]
    if not UrbanRuralRule().should_fire(n_urban=len(urban), n_rural=len(rural)):
        return {}, {}

    u_val = float(urban[metric].mean())
    r_val = float(rural[metric].mean())
    gap = round((u_val - r_val) / r_val * 100, 1) if r_val != 0 else 0

    stats: dict[str, Any] = {
        "urban_value": round(u_val, 2),
        "rural_value": round(r_val, 2),
        "unit": "trips/capita",
        "gap_pct": gap,
        "n_urban": len(urban),
        "n_rural": len(rural),
    }

    chart: dict = {}
    if "region" in filtered.columns:
        regions = sorted(filtered["region"].dropna().unique())
        u_vals = [round(float(urban[urban["region"] == r][metric].mean()), 2) if len(urban[urban["region"] == r]) > 0 else 0 for r in regions]
        r_vals = [round(float(rural[rural["region"] == r][metric].mean()), 2) if len(rural[rural["region"] == r]) > 0 else 0 for r in regions]
        chart = build_grouped_bar(
            categories=list(regions),
            series=[{"name": "Urban", "values": u_vals}, {"name": "Rural", "values": r_vals}],
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_gap_to_target(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build gap to target (A7)."""
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)
    if "trips_per_capita" not in filtered.columns or len(filtered) == 0:
        return {}, {}

    median = float(filtered["trips_per_capita"].median())
    below = filtered[filtered["trips_per_capita"] < median]
    if not GapToInvestmentRule().should_fire(n_below_target=len(below)):
        return {}, {}

    stats: dict[str, Any] = {
        "n_below": len(below),
        "pct_below": round(len(below) / len(filtered) * 100, 1),
        "target": round(median, 2),
        "unit": "trips/capita",
        "mean_gap": round(float((median - below["trips_per_capita"]).mean()), 2) if len(below) > 0 else 0.0,
        "total_annual_cost_m": round(float(len(below) * 500 / 1_000_000), 1),
    }

    chart: dict = {}
    if "region" in filtered.columns:
        by_region = filtered.groupby("region").apply(
            lambda g: round(float((median - g.loc[g["trips_per_capita"] < median, "trips_per_capita"]).sum()), 1) if (g["trips_per_capita"] < median).any() else 0
        ).reset_index()
        by_region.columns = ["label", "value"]
        by_region = by_region[by_region["value"] > 0]
        if len(by_region) > 0:
            chart = build_horizontal_bar(
                data=by_region, title=SECTION_REGISTRY[section_id].title,
                x_label="Total gap (trips/capita)", y_label="Region",
            )
    return stats, chart


def _build_ml_prediction(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build ML prediction / SHAP (A8, D8, G3, G4)."""
    shap_df = data.get("shap")
    if shap_df is None or len(shap_df) == 0:
        return {}, {}
    if not MLPredictionRule().should_fire(r2=0.472, n_features=len(shap_df)):
        return {}, {}

    top = shap_df.iloc[0]
    stats: dict[str, Any] = {
        "r2": 0.472,  # locked ground truth
        "top_feature": str(top.get("feature", "")),
        "top_importance": round(float(top.get("mean_abs_shap", top.get("importance", 0))), 3),
        "n_features": len(shap_df),
    }
    feat_df = shap_df.rename(columns={"mean_abs_shap": "importance"}) if "mean_abs_shap" in shap_df.columns else shap_df
    chart: dict = {}
    if "feature" in feat_df.columns and "importance" in feat_df.columns:
        chart = build_shap_bar(features=feat_df, title=SECTION_REGISTRY[section_id].title, model_r2=0.472)
    return stats, chart


def _build_service_hours(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build service hours (B2)."""
    sq = data.get("service_quality")
    if sq is None:
        return {}, {}
    filtered = _filter_data(sq, region, urban_rural)
    if not MinLsoaRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    stats: dict[str, Any] = {}
    if "first_service_min" in filtered.columns:
        stats["median_first_service"] = _minutes_to_time(float(filtered["first_service_min"].median()))
    if "last_service_min" in filtered.columns:
        stats["median_last_service"] = _minutes_to_time(float(filtered["last_service_min"].median()))
    if "evening_isolated" in filtered.columns:
        n_ei = int(filtered["evening_isolated"].sum())
        stats["n_evening_isolated"] = n_ei
        stats["pct_evening_isolated"] = round(n_ei / len(filtered) * 100, 1)

    chart: dict = {}
    if "region" in filtered.columns and "first_service_min" in filtered.columns and "last_service_min" in filtered.columns:
        by_region = filtered.groupby("region").agg(
            first=("first_service_min", "median"), last=("last_service_min", "median")
        ).reset_index()
        chart = build_grouped_bar(
            categories=by_region["region"].tolist(),
            series=[
                {"name": "First service (min)", "values": by_region["first"].round(0).tolist()},
                {"name": "Last service (min)", "values": by_region["last"].round(0).tolist()},
            ],
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_weekend_penalty(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build weekend penalty (B3)."""
    sq = data.get("service_quality")
    if sq is None:
        return {}, {}
    filtered = _filter_data(sq, region, urban_rural)
    if not MinLsoaRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    stats: dict[str, Any] = {}
    if "sunday_desert" in filtered.columns:
        n_sd = int(filtered["sunday_desert"].sum())
        stats["n_sunday_desert"] = n_sd
        stats["pct_sunday_desert"] = round(n_sd / len(filtered) * 100, 1)
    if "total_weekday_departures" in filtered.columns and "total_sunday_departures" in filtered.columns:
        wd = float(filtered["total_weekday_departures"].sum())
        su = float(filtered["total_sunday_departures"].sum())
        stats["sunday_pct_drop"] = round((1 - su / wd) * 100, 1) if wd > 0 else 0

    chart: dict = {}
    if "region" in filtered.columns and "total_weekday_departures" in filtered.columns:
        agg: dict[str, Any] = {"weekday": ("total_weekday_departures", "mean")}
        if "total_sunday_departures" in filtered.columns:
            agg["sunday"] = ("total_sunday_departures", "mean")
        by_region = filtered.groupby("region").agg(**agg).reset_index()
        series = [{"name": "Weekday", "values": by_region["weekday"].round(1).tolist()}]
        if "sunday" in by_region.columns:
            series.append({"name": "Sunday", "values": by_region["sunday"].round(1).tolist()})
        chart = build_grouped_bar(
            categories=by_region["region"].tolist(),
            series=series,
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_correlation(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build correlation section (B5, C5, D1-D5).

    c5 (length vs frequency) uses the routes parquet directly —
    route_length_km and stop_count both exist there. All other sections
    use the policy LSOA parquet.
    """
    prefix = section_id.split("_")[0]

    # c5 uses route-level data, not LSOA policy
    if prefix == "c5":
        return _build_correlation_routes(section_id, data)

    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)

    col_map: dict[str, tuple[str, str, str, str]] = {
        "b5": ("imd_score", "service_quality_index", "IMD Score", "Service Quality Index"),
        "d1": ("imd_score", "trips_per_capita", "IMD Score", "Trips per Capita"),
        "d2": ("unemployment_rate", "trips_per_capita", "Unemployment Rate", "Trips per Capita"),
        "d3": ("nocar_pct", "trips_per_capita", "% No Car", "Trips per Capita"),
        "d4": ("elderly_pct", "trips_per_capita", "% Elderly", "Trips per Capita"),
        "d5": ("income_score", "trips_per_capita", "Income Score", "Trips per Capita"),
    }

    mapping = col_map.get(prefix)
    if mapping is None:
        return {}, {}

    x_col, y_col, x_label, y_label = mapping
    if x_col not in filtered.columns or y_col not in filtered.columns:
        return {}, {}

    corr = calculate_correlation(filtered[x_col], filtered[y_col])
    if not CorrelationRule().should_fire(n=corr.n, p_value=corr.p_value):
        return {}, {}

    stats: dict[str, Any] = {
        "r": corr.r,
        "p_value": corr.p_value,
        "n": corr.n,
        "strength": corr.strength,
        "direction": corr.direction,
        "x_label": x_label,
        "y_label": y_label,
    }

    id_col = "lsoa_code" if "lsoa_code" in filtered.columns else ("lsoa_cd" if "lsoa_cd" in filtered.columns else filtered.columns[0])
    chart = build_scatter_regression(
        df=filtered, x_col=x_col, y_col=y_col, id_col=id_col,
        title=SECTION_REGISTRY[section_id].title, x_label=x_label, y_label=y_label,
    )
    return stats, chart


def _build_correlation_routes(
    section_id: str, data: dict,
) -> tuple[dict, dict]:
    """Build c5 (route length vs stop count) from routes parquet.

    Routes have no region column so this is always national-level —
    the same result is stored for all 30 filter combos.
    """
    routes = data.get("routes")
    if routes is None:
        return {}, {}

    # Normalise column name (routes parquet uses length_km; rename guard already applied)
    x_col = "route_length_km" if "route_length_km" in routes.columns else "length_km"
    y_col = "stop_count"
    if x_col not in routes.columns or y_col not in routes.columns:
        return {}, {}

    # Drop NaN from both columns together to keep series aligned
    aligned = routes[[x_col, y_col]].dropna()
    corr = calculate_correlation(aligned[x_col], aligned[y_col])
    if not CorrelationRule().should_fire(n=corr.n, p_value=corr.p_value):
        return {}, {}

    x_label = "Route Length (km)"
    y_label = "Stops per Route"
    stats: dict[str, Any] = {
        "r": corr.r,
        "p_value": corr.p_value,
        "n": corr.n,
        "strength": corr.strength,
        "direction": corr.direction,
        "x_label": x_label,
        "y_label": y_label,
    }
    id_col = "route_id" if "route_id" in routes.columns else routes.columns[0]
    chart = build_scatter_regression(
        df=routes, x_col=x_col, y_col=y_col, id_col=id_col,
        title=SECTION_REGISTRY[section_id].title, x_label=x_label, y_label=y_label,
    )
    return stats, chart


def _build_distribution(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build distribution section (C1, C2)."""
    routes = data.get("routes")
    if routes is None:
        return {}, {}

    metric_map: dict[str, tuple[str, str, str]] = {
        "c1": ("route_length_km", "Route Length", "km"),
        "c2": ("stop_count", "Stops per Route", "stops"),
    }
    prefix = section_id.split("_")[0]
    mapping = metric_map.get(prefix)
    if mapping is None:
        return {}, {}

    col, name, unit = mapping
    if col not in routes.columns:
        return {}, {}

    values = routes[col].dropna()
    if not DistributionRule().should_fire(n=len(values)):
        return {}, {}

    desc = describe_distribution(values)
    skew = "right-skewed" if desc.mean > desc.median * 1.1 else ("left-skewed" if desc.mean < desc.median * 0.9 else "approximately symmetric")

    stats: dict[str, Any] = {
        "median": desc.median,
        "unit": unit,
        "metric_name": name.lower(),
        "p10": desc.p10,
        "p90": desc.p90,
        "skew_label": skew,
        "n_outliers": desc.outliers,
        "cv": desc.cv,
    }

    chart: dict = {}
    if "region" in routes.columns:
        groups = {r: routes.loc[routes["region"] == r, col].dropna() for r in routes["region"].unique()}
        groups = {k: v for k, v in groups.items() if len(v) > 0}
        if groups:
            chart = build_box_violin(groups=groups, title=SECTION_REGISTRY[section_id].title, unit=unit)
    return stats, chart


def _build_market_concentration(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build market concentration / HHI (C3, BSA2)."""
    lta = data.get("lta")
    if lta is None or "region_hhi" not in lta.columns:
        return {}, {}

    by_region = lta.groupby("region")["region_hhi"].first().reset_index()
    by_region.columns = ["label", "value"]
    if not MarketConcentrationRule().should_fire(n_operators=len(by_region)):
        return {}, {}

    stats: dict[str, Any] = {
        "hhi": round(float(by_region["value"].mean()), 0),
        "region_name": "England" if region == "all" else region,
    }
    chart = build_horizontal_bar(
        data=by_region, title=SECTION_REGISTRY[section_id].title,
        x_label="HHI", y_label="Region",
    )
    return stats, chart


def _build_clusters(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build cluster sections (C6, D6, G1).

    For LSOA clusters (D6): uses the clusters parquet if available; falls back to
    policy (which has hdbscan_archetype and gmm_label from notebooks 04d/02e).
    Prefers HDBSCAN non-noise labels; if < 2 remain after filtering, falls back
    to GMM labels (always 4 components across all LSOAs).
    """
    is_route = section_id.startswith("c6") or section_id.startswith("g1")

    if is_route:
        df = data.get("route_clusters")
        if df is None:
            return {}, {}
        cluster_col = "cluster"
        if cluster_col not in df.columns:
            return {}, {}
        valid = df[df[cluster_col] >= 0]
        unique_labels = sorted(valid[cluster_col].unique())
        entity_type = "routes"
        archetype_col = None
    else:
        # LSOA clusters: prefer dedicated file, fall back to policy.
        # Use explicit None check — DataFrames are truthy-ambiguous.
        _clusters = data.get("clusters")
        df = _clusters if _clusters is not None else data.get("policy")
        if df is None:
            return {}, {}

        filtered = _filter_data(df, region, urban_rural)
        if len(filtered) == 0:
            return {}, {}

        # Try HDBSCAN first (hdbscan_archetype is the label in policy)
        if "hdbscan_archetype" in filtered.columns:
            non_noise = filtered[filtered["hdbscan_archetype"] != "Noise"]
            unique_archetypes = [a for a in non_noise["hdbscan_archetype"].unique() if pd.notna(a)]
            if len(unique_archetypes) >= ClusterRule.MIN_CLUSTERS:
                # Build from hdbscan_archetype strings (no numeric ID)
                clusters_info = []
                for aid in sorted(unique_archetypes):
                    n = int((non_noise["hdbscan_archetype"] == aid).sum())
                    pct = round(n / len(non_noise) * 100, 1)
                    clusters_info.append({"id": aid, "n": n, "pct": pct, "description": str(aid)})
                stats: dict[str, Any] = {
                    "n_clusters": len(unique_archetypes),
                    "entity_type": "LSOAs",
                    "clusters": clusters_info,
                    "noise_pct": round(len(filtered[filtered["hdbscan_archetype"] == "Noise"]) / len(filtered) * 100, 1),
                }
                return stats, {}

        # Fall back to GMM labels (4 components, present on all LSOAs)
        if "gmm_label" in filtered.columns:
            gmm_labels = sorted(filtered["gmm_label"].dropna().unique())
            if not ClusterRule().should_fire(n_clusters=len(gmm_labels)):
                return {}, {}
            clusters_info = []
            for cid in gmm_labels:
                n = int((filtered["gmm_label"] == cid).sum())
                pct = round(n / len(filtered) * 100, 1)
                clusters_info.append({"id": int(cid), "n": n, "pct": pct, "description": f"Cluster {int(cid) + 1}"})
            stats = {
                "n_clusters": len(gmm_labels),
                "entity_type": "LSOAs",
                "clusters": clusters_info,
                "cluster_method": "GMM",
            }
            return stats, {}

        return {}, {}

    if not ClusterRule().should_fire(n_clusters=len(unique_labels)):
        return {}, {}

    entity_type = "routes"
    archetype_col = None
    clusters_info = []
    for cid in unique_labels:
        mask = valid[cluster_col] == cid
        n = int(mask.sum())
        pct = round(n / len(valid) * 100, 1)
        desc = str(df.loc[mask, archetype_col].iloc[0]) if archetype_col and mask.any() else f"Cluster {cid}"
        clusters_info.append({"id": int(cid), "n": n, "pct": pct, "description": desc})

    stats = {
        "n_clusters": len(unique_labels),
        "entity_type": entity_type,
        "clusters": clusters_info,
    }

    chart: dict = {}
    numeric_cols = valid.select_dtypes(include="number").columns.tolist()
    id_col = "route_id" if "route_id" in valid.columns else valid.columns[0]
    if len(numeric_cols) >= 2 and id_col in valid.columns:
        scatter_df = valid[[numeric_cols[0], numeric_cols[1], cluster_col, id_col]].copy()
        scatter_df.columns = ["x", "y", "cluster", "id"]
        cluster_labels = {int(c["id"]): c["description"] for c in clusters_info}
        chart = build_scatter_clusters(
            data=scatter_df, cluster_labels=cluster_labels,
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_network(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build network topology (C7)."""
    routes = data.get("routes")
    if routes is None:
        return {}, {}
    if not NetworkRule().should_fire(n_routes=len(routes)):
        return {}, {}

    cross_col = "cross_la_flag" if "cross_la_flag" in routes.columns else "cross_la"
    n_cross = int(routes[cross_col].astype(bool).sum()) if cross_col in routes.columns else 0
    stats: dict[str, Any] = {
        "n_cross_la": n_cross,
        "pct_cross_la": round(n_cross / len(routes) * 100, 1) if len(routes) > 0 else 0,
        "mean_length": round(float(routes["route_length_km"].mean()), 1) if "route_length_km" in routes.columns else 0,
        "median_length": round(float(routes["route_length_km"].median()), 1) if "route_length_km" in routes.columns else 0,
    }

    chart: dict = {}
    lta = data.get("lta")
    if lta is not None and "lad_cd" in lta.columns and "mean_trips_per_cap" in lta.columns:
        lad_data = lta[["lad_cd", "lad_nm", "mean_trips_per_cap"]].copy()
        lad_data.columns = ["area_code", "area_name", "value"]
        chart = build_choropleth(
            data=lad_data, title=SECTION_REGISTRY[section_id].title,
            geography="lad", metric="cross_la_route_density", colour_scale="Viridis",
        )
    return stats, chart


def _build_heatmap_section(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build heatmap (D7)."""
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, "all")

    if "imd_decile" not in filtered.columns or "urban_rural" not in filtered.columns or "trips_per_capita" not in filtered.columns:
        return {}, {}

    # Drop rows with NaN in groupby columns to avoid NaN-to-int conversion errors
    clean = filtered.dropna(subset=["urban_rural", "imd_decile", "trips_per_capita"])
    if len(clean) == 0:
        return {}, {}

    pivot = clean.groupby(["urban_rural", "imd_decile"])["trips_per_capita"].mean().unstack(fill_value=0)
    cell_counts = clean.groupby(["urban_rural", "imd_decile"]).size().unstack(fill_value=0)
    min_cell = int(cell_counts.min().min())
    # For filtered subsets (single region), scale threshold proportionally —
    # national has ~33k LSOAs; a single region has ~1k–5k so min cell drops ~10×.
    # Use 1 as minimum acceptable cell count for regional sub-filters.
    effective_min = max(1, HeatmapRule.MIN_CELL_N * len(clean) // 33755)
    if min_cell < effective_min:
        return {}, {}

    x_labels = [str(d) for d in sorted(pivot.columns)]
    y_labels = list(pivot.index)
    values = pivot.values.tolist()

    worst_val = float("inf")
    best_val = float("-inf")
    worst_cell: dict = {"label": "", "value": 0}
    best_cell: dict = {"label": "", "value": 0}
    for yi, y_lbl in enumerate(y_labels):
        for xi, x_lbl in enumerate(x_labels):
            v = values[yi][xi]
            if v < worst_val:
                worst_val = v
                worst_cell = {"label": f"Decile {x_lbl} × {y_lbl}", "value": round(v, 1)}
            if v > best_val:
                best_val = v
                best_cell = {"label": f"Decile {x_lbl} × {y_lbl}", "value": round(v, 1)}

    stats: dict[str, Any] = {
        "x_dimension": "deprivation decile",
        "y_dimension": "area type",
        "metric_name": "trips per capita",
        "worst_cell": worst_cell,
        "best_cell": best_cell,
    }
    chart = build_heatmap(
        x_labels=x_labels, y_labels=y_labels, values=values,
        title=SECTION_REGISTRY[section_id].title,
    )
    return stats, chart


def _build_equity_decile(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build equity by IMD decile (F2)."""
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)
    if "imd_decile" not in filtered.columns or "trips_per_capita" not in filtered.columns:
        return {}, {}

    decile_counts = [int((filtered["imd_decile"] == d).sum()) for d in range(1, 11)]
    # Scale minimum per-decile threshold proportionally for regional sub-filters.
    # National: ~3,376 per decile → min 100. Single region (~1/9): ~375 → min ~11.
    scaled_min = max(3, DecileRule.MIN_PER_DECILE * len(filtered) // 33755)
    # All 10 deciles must be present AND each must exceed the scaled threshold.
    if len(decile_counts) != 10 or not all(c >= scaled_min for c in decile_counts):
        return {}, {}

    by_decile = filtered.groupby("imd_decile")["trips_per_capita"].mean()
    most = float(by_decile.get(1, 0))
    least = float(by_decile.get(10, 0))
    ratio = round(least / most, 1) if most > 0 else 0

    stats: dict[str, Any] = {
        "most_deprived_value": round(most, 1),
        "least_deprived_value": round(least, 1),
        "unit": "trips/capita",
        "ratio": ratio,
    }

    decile_df = by_decile.reset_index()
    decile_df.columns = ["label", "value"]
    decile_df["label"] = decile_df["label"].astype(str)
    chart = build_horizontal_bar(
        data=decile_df, title=SECTION_REGISTRY[section_id].title,
        x_label="Trips per capita", y_label="IMD Decile",
    )
    return stats, chart


def _build_demographic(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build demographic breakdown (F3)."""
    policy = data.get("policy")
    if policy is None or "nonwhite_pct" not in policy.columns:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)
    if "trips_per_capita" not in filtered.columns:
        return {}, {}

    median_nw = float(filtered["nonwhite_pct"].median())
    high = filtered[filtered["nonwhite_pct"] >= median_nw]
    low = filtered[filtered["nonwhite_pct"] < median_nw]
    if not DemographicRule().should_fire(group_counts=[len(high), len(low)]):
        return {}, {}

    nat_avg = float(filtered["trips_per_capita"].mean())
    groups = []
    for label, subset in [("high non-white %", high), ("low non-white %", low)]:
        val = float(subset["trips_per_capita"].mean())
        groups.append({
            "label": label,
            "value": round(val, 2),
            "vs_national_pct": round((val - nat_avg) / nat_avg * 100, 1) if nat_avg != 0 else 0,
        })
    stats: dict[str, Any] = {"groups": groups, "unit": "trips/capita"}

    chart = build_grouped_bar(
        categories=[g["label"] for g in groups],
        series=[{"name": "Trips/capita", "values": [g["value"] for g in groups]}],
        title=SECTION_REGISTRY[section_id].title,
    )
    return stats, chart


def _build_accessibility(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build accessibility gap (F4)."""
    acc = data.get("accessibility")
    if acc is None:
        return {}, {}
    filtered = _filter_data(acc, region, urban_rural)
    score_col = "sfca_score" if "sfca_score" in filtered.columns else None
    if score_col is None or len(filtered) == 0:
        return {}, {}

    n_zero = int((filtered[score_col] == 0).sum())
    if not AccessibilityRule().should_fire(n_pois=n_zero):
        return {}, {}

    stats: dict[str, Any] = {
        "n_beyond_threshold": n_zero,
        "poi_type": "LSOAs",
        "pct_beyond": round(n_zero / len(filtered) * 100, 1),
        "threshold_m": 400,
    }

    chart: dict = {}
    if "region" in filtered.columns:
        by_region = filtered[filtered[score_col] == 0].groupby("region").size().reset_index()
        by_region.columns = ["label", "value"]
        chart = build_horizontal_bar(
            data=by_region, title=SECTION_REGISTRY[section_id].title,
            x_label="LSOAs with zero access", y_label="Region",
        )
    return stats, chart


def _build_anomaly(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build anomaly spotlight (G2)."""
    df = data.get("anomalies")
    if df is None:
        return {}, {}

    type_col = "anomaly_type" if "anomaly_type" in df.columns else None
    if type_col is None:
        return {}, {}

    anomalies = df[df[type_col] != "normal"]
    if not AnomalyRule().should_fire(n_anomalies=len(anomalies)):
        return {}, {}

    stats: dict[str, Any] = {
        "n_anomalies": len(anomalies),
        "pct_anomalies": round(len(anomalies) / len(df) * 100, 1),
        "n_positive": int((anomalies[type_col] == "positive_deprived_well_served").sum()),
        "n_inefficiency": int((anomalies[type_col] == "inefficiency_affluent_poor_served").sum()),
        "n_policy_failure": int((anomalies[type_col] == "policy_failure_elderly_no_service").sum()),
    }

    chart: dict = {}
    if "service_quality_index" in df.columns and "imd_score" in df.columns and "lsoa_cd" in df.columns:
        chart = build_scatter_regression(
            df=df, x_col="imd_score", y_col="service_quality_index", id_col="lsoa_cd",
            title=SECTION_REGISTRY[section_id].title,
            x_label="IMD Score", y_label="Service Quality Index",
        )
    return stats, chart


def _build_scenario(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build individual scenario (G5, PS1-PS4)."""
    scenarios = data.get("scenarios")
    if scenarios is None or len(scenarios) == 0:
        return {}, {}

    scenario_map = {"ps1": "A", "ps2": "B", "ps3": "C", "ps4": "D", "g5": "A"}
    prefix = section_id.split("_")[0]
    scenario_letter = scenario_map.get(prefix, "A")

    row = scenarios[scenarios["scenario"] == scenario_letter] if "scenario" in scenarios.columns else pd.DataFrame()
    if len(row) == 0:
        return {}, {}

    r = row.iloc[0]
    pop = int(r.get("population_affected", 0))
    cost = float(r.get("estimated_annual_cost_m", 0))
    co2 = float(r.get("co2_saving_t_yr", 0)) if pd.notna(r.get("co2_saving_t_yr")) else 0

    stats: dict[str, Any] = {
        "scenario": {
            "scenario": str(r.get("scenario", "")),
            "name": str(r.get("name", "")),
            "scope": str(r.get("scope", "")),
            "population_affected": pop,
            "estimated_annual_cost_m": cost,
            "co2_saving_t_yr": int(co2),
            "confidence": str(r.get("confidence", "indicative")),
        }
    }

    bar_data = pd.DataFrame({
        "label": ["Population affected", "Annual cost (£m)", "CO₂ saved (t/yr)"],
        "value": [pop / 1e6, cost, co2],
    })
    chart = build_horizontal_bar(
        data=bar_data, title=SECTION_REGISTRY[section_id].title,
        x_label="Value", y_label="Metric",
    )
    return stats, chart


def _build_economic_value(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build economic value (J1)."""
    econ = data.get("economic")
    if econ is None:
        return {}, {}
    filtered = _filter_data(econ, region, urban_rural)
    if not MinLsoaRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    benefit_col = "annual_total_benefit" if "annual_total_benefit" in filtered.columns else "annual_benefit_gbp"
    trips_col = "annual_additional_trips" if "annual_additional_trips" in filtered.columns else "trips_per_day"

    stats: dict[str, Any] = {
        "annual_benefit": float(filtered[benefit_col].sum()) if benefit_col in filtered.columns else 0,
        "region_name": "England" if region == "all" else region,
        "n_trips": int(filtered[trips_col].sum()) if trips_col in filtered.columns else 0,
        "vot": 8.49,  # TAG v2.03fc, blended commute/other
    }

    chart: dict = {}
    if "region" in filtered.columns and benefit_col in filtered.columns:
        by_region = filtered.groupby("region")[benefit_col].sum().reset_index()
        by_region.columns = ["label", "value"]
        by_region["value"] = (by_region["value"] / 1e6).round(1)
        chart = build_horizontal_bar(
            data=by_region, title=SECTION_REGISTRY[section_id].title,
            x_label="Annual benefit (£m)", y_label="Region",
        )
    return stats, chart


def _build_bcr(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build BCR analysis (J2)."""
    econ = data.get("economic")
    if econ is None:
        return {}, {}
    filtered = _filter_data(econ, region, urban_rural)
    bcr_col = "bcr" if "bcr" in filtered.columns else "bcr_central"
    if bcr_col not in filtered.columns or len(filtered) == 0:
        return {}, {}

    mean_bcr = float(filtered[bcr_col].mean())
    stats: dict[str, Any] = {
        "bcr": round(mean_bcr, 2),
        "area_name": "England" if region == "all" else region,
        "vfm_band": "Very High" if mean_bcr > 4 else ("High" if mean_bcr > 2 else ("Medium" if mean_bcr > 1.5 else ("Low" if mean_bcr > 1 else "Poor"))),
        "investment_m": round(float(filtered["investment_gap_annual_cost"].sum()) / 1e6, 1) if "investment_gap_annual_cost" in filtered.columns else 0,
        "appraisal_years": 60,
    }

    chart: dict = {}
    if "region" in filtered.columns:
        by_region = filtered.groupby("region")[bcr_col].mean().reset_index()
        by_region.columns = ["label", "value"]
        by_region["value"] = by_region["value"].round(2)
        chart = build_horizontal_bar(
            data=by_region, title=SECTION_REGISTRY[section_id].title,
            x_label="BCR", y_label="Region",
        )
    return stats, chart


def _build_carbon(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build carbon reduction (J3)."""
    ms = data.get("modal_shift")
    if ms is None or len(ms) == 0:
        return {}, {}

    el_col = "elasticity_value" if "elasticity_value" in ms.columns else ("elasticity" if "elasticity" in ms.columns else None)
    central = ms[ms[el_col] == 0.55] if el_col in (ms.columns if el_col else []) else ms
    if len(central) == 0:
        central = ms.iloc[[0]]
    r = central.iloc[0]

    co2_saving = float(r.get("net_co2_saving_tonnes_pa", r.get("co2_saved_tonnes", 0)))
    if not CarbonRule().should_fire(co2_saving=co2_saving):
        return {}, {}

    stats: dict[str, Any] = {
        "co2_saving_tonnes": co2_saving,
        "scope": str(r.get("scope", "England")),
        "co2_value_k": round(co2_saving * 259.87 / 1000, 0),
        "carbon_price": 259.87,
        "modal_shift_trips": int(r.get("car_trips_replaced_pa", r.get("modal_shift_trips", 0))),
    }

    chart: dict = {}
    if "scope" in central.columns and "net_co2_saving_tonnes_pa" in central.columns:
        co2_by_scope = central.groupby("scope")["net_co2_saving_tonnes_pa"].first().reset_index()
        co2_by_scope.columns = ["label", "value"]
        chart = build_horizontal_bar(
            data=co2_by_scope, title=SECTION_REGISTRY[section_id].title,
            x_label="Net CO₂ saved (t/yr)", y_label="Scope",
        )
    return stats, chart


def _build_franchising(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build franchising readiness ranking (BSA1)."""
    lta = data.get("lta")
    if lta is None:
        return {}, {}

    score_col = "franchising_readiness" if "franchising_readiness" in lta.columns else None
    if score_col is None or not MinLsoaRule().should_fire(n_lsoas=len(lta)):
        return {}, {}

    sorted_lta = lta.sort_values(score_col, ascending=False)
    best = sorted_lta.iloc[0]
    worst = sorted_lta.iloc[-1]
    nat_avg = float(sorted_lta[score_col].mean())
    name_col = "lad_nm" if "lad_nm" in lta.columns else lta.columns[0]

    stats: dict[str, Any] = {
        "best": {
            "name": str(best[name_col]),
            "value": round(float(best[score_col]), 1),
            "pct_above": round((float(best[score_col]) - nat_avg) / nat_avg * 100, 1),
        },
        "worst": {
            "name": str(worst[name_col]),
            "value": round(float(worst[score_col]), 1),
            "pct_below": round((nat_avg - float(worst[score_col])) / nat_avg * 100, 1),
        },
        "national_avg": round(nat_avg, 1),
        "unit": "readiness score",
    }

    top20 = sorted_lta.head(20)[[name_col, score_col]].copy()
    top20.columns = ["label", "value"]
    chart = build_horizontal_bar(
        data=top20, title=SECTION_REGISTRY[section_id].title,
        x_label="Franchising readiness", y_label="LAD", national_avg=nat_avg,
    )
    return stats, chart


def _build_tier_dist(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build tier distribution (BSA3)."""
    lta = data.get("lta")
    if lta is None or "readiness_tier" not in lta.columns:
        return {}, {}
    if not TierRule().should_fire(n_lads=len(lta)):
        return {}, {}

    tier_nums = lta["readiness_tier"].str.extract(r"Tier (\d)")[0].astype(float)
    tier_counts = tier_nums.value_counts()
    stats: dict[str, Any] = {
        "n_total": len(lta),
        "n_tier1": int(tier_counts.get(1, 0)),
        "n_tier2": int(tier_counts.get(2, 0)),
        "n_tier3": int(tier_counts.get(3, 0)),
    }
    name_col = "lad_nm" if "lad_nm" in lta.columns else lta.columns[0]
    score_col = "franchising_readiness" if "franchising_readiness" in lta.columns else None
    if score_col:
        top = lta.sort_values(score_col, ascending=False).iloc[0]
        stats["top_lad"] = str(top[name_col])
        stats["top_score"] = round(float(top[score_col]), 1)

    chart: dict = {}
    if "region" in lta.columns:
        lta_with_tier = lta.copy()
        lta_with_tier["_tier_num"] = tier_nums
        by_region = lta_with_tier.groupby("region")["_tier_num"].value_counts().unstack(fill_value=0)
        regions = list(by_region.index)
        chart = build_stacked_bar(
            categories=regions,
            series=[
                {"name": "Tier 1 (High)", "values": [int(by_region.loc[r].get(1.0, 0)) for r in regions]},
                {"name": "Tier 2 (Medium)", "values": [int(by_region.loc[r].get(2.0, 0)) for r in regions]},
                {"name": "Tier 3 (Low)", "values": [int(by_region.loc[r].get(3.0, 0)) for r in regions]},
            ],
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_scenario_comparison(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build scenario comparison (PS5)."""
    scenarios = data.get("scenarios")
    if scenarios is None:
        return {}, {}
    if not ScenarioComparisonRule().should_fire(n_scenarios=len(scenarios)):
        return {}, {}

    items = []
    for _, r in scenarios.iterrows():
        items.append({
            "name": str(r.get("name", "")),
            "population": int(r.get("population_affected", 0)),
            "cost_m": round(float(r.get("estimated_annual_cost_m", 0)) if pd.notna(r.get("estimated_annual_cost_m")) else 0, 1),
            "co2_t": int(r.get("co2_saving_t_yr", 0)) if pd.notna(r.get("co2_saving_t_yr")) else 0,
        })

    stats: dict[str, Any] = {
        "scenarios": items,
        "best_bcr_scenario": str(scenarios.iloc[0].get("name", "")) if len(scenarios) > 0 else "",
    }

    names = [i["name"] for i in items]
    chart = build_grouped_bar(
        categories=names,
        series=[
            {"name": "Population (millions)", "values": [round(i["population"] / 1e6, 2) for i in items]},
            {"name": "Cost (£m/yr)", "values": [i["cost_m"] for i in items]},
            {"name": "CO₂ saved (t/yr)", "values": [i["co2_t"] for i in items]},
        ],
        title=SECTION_REGISTRY[section_id].title,
    )
    return stats, chart
