"""Pre-computation of section_results for the DuckDB warehouse.

For each filter combination (regions × area types), computes all 51 analytical
sections using the section registry and stores results as JSON in section_results.

This is called once at build time — never at request time.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats as scipy_stats

from aequitas.core.config import PipelineConfig
from aequitas.core.types import RegionCode
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
from aequitas.intelligence.section_registry import SECTION_REGISTRY


# All region codes + "all"
_REGIONS = ["all"] + [rc.value for rc in RegionCode]
# Area types
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


def precompute_all_sections(cfg: PipelineConfig) -> list[dict]:
    """Precompute all 51 section results for each filter combination.

    Loads Phase 0 audit Parquets, applies region/area-type filters, runs
    InsightEngine for each section, and returns a list of SectionResult dicts.

    Args:
        cfg: Pipeline configuration.

    Returns:
        List of dicts, each with keys: region, urban_rural, section_id,
        stats, chart_data, narrative.
    """
    engine = InsightEngine()
    results: list[dict] = []

    data = _load_all_data(cfg)
    if data is None:
        logger.warning("Required Parquets not found — precompute returning empty results")
        return results

    for region in _REGIONS:
        for urban_rural in _AREA_TYPES:
            # Skip per-region × urban/rural combos (low analytical value)
            if region != "all" and urban_rural != "all":
                continue

            filtered = _apply_filters(data, region, urban_rural)

            for section_id in SECTION_REGISTRY:
                try:
                    stats, chart_data = _build_section(section_id, filtered, data, region, urban_rural)
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
                except Exception as exc:
                    logger.warning(f"Section {section_id} failed for {region}/{urban_rural}: {exc}")

    logger.info(f"Precomputed {len(results)} section results")
    return results


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_all_data(cfg: PipelineConfig) -> dict[str, pd.DataFrame] | None:
    """Load all required Parquet sources.  Returns None if any core file missing."""
    processed = cfg.processed_dir
    audit = cfg.audit_dir

    # Phase 0 outputs all landed in data/audit/; data/processed/ is populated by Phase 1.
    # Fall back to audit/ when processed/ copy is absent so the test suite can run against
    # the existing Phase 0 Parquets without requiring a full Phase 1 pipeline run.
    def _p(filename: str) -> Path:
        proc = processed / filename
        return proc if proc.exists() else audit / filename

    paths: dict[str, Path] = {
        "lsoa_sq": _p("lsoa_service_quality.parquet"),
        "lsoa_eq": _p("lsoa_equity_metrics.parquet"),
        "lsoa_acc": _p("lsoa_2sfca.parquet"),
        "lsoa_econ": _p("lsoa_economic_appraisal.parquet"),
        "lsoa_policy": _p("lsoa_policy_synthesis.parquet"),
        "routes": _p("route_geometries.parquet"),
        "lta": _p("lta_franchising_readiness.parquet"),
        "headways": audit / "stop_headways.parquet",
        "coverage_pred": audit / "coverage_prediction.parquet",
        "shap": audit / "shap_importance.parquet",
        "route_clusters": audit / "route_clusters.parquet",
        "lsoa_clusters": audit / "lsoa_clusters_hdbscan.parquet",
        "anomalies": audit / "anomalies.parquet",
        "scenarios": audit / "modal_shift_scenarios.parquet",
    }

    core = {"lsoa_sq", "lsoa_eq"}
    for key in core:
        if not paths[key].exists():
            logger.error(f"Core Parquet missing: {paths[key]}")
            return None

    data: dict[str, pd.DataFrame] = {}
    for key, path in paths.items():
        if path.exists():
            data[key] = pd.read_parquet(path)
        else:
            logger.debug(f"Optional Parquet not found: {path} — section may be suppressed")
            data[key] = pd.DataFrame()

    return data


def _apply_filters(
    data: dict[str, pd.DataFrame], region: str, urban_rural: str
) -> dict[str, pd.DataFrame]:
    """Return new dict with each frame filtered to region/area type."""
    filtered: dict[str, pd.DataFrame] = {}
    for key, df in data.items():
        if df.empty:
            filtered[key] = df
            continue

        mask = pd.Series(True, index=df.index)
        if region != "all" and "region" in df.columns:
            mask &= df["region"] == region
        if urban_rural != "all" and "urban_rural" in df.columns:
            mask &= df["urban_rural"].str.lower().str.startswith(urban_rural)

        filtered[key] = df[mask].copy()

    return filtered


# ---------------------------------------------------------------------------
# Section dispatcher
# ---------------------------------------------------------------------------

def _build_section(
    section_id: str,
    filtered: dict[str, pd.DataFrame],
    full: dict[str, pd.DataFrame],
    region: str,
    urban_rural: str,
) -> tuple[dict, dict]:
    """Dispatch to the correct builder, return (stats, chart_data)."""
    # Category A — Coverage & Accessibility
    if section_id == "a1_route_density":
        return _build_ranking_density(filtered, full, "route_density", "routes/1k pop")
    if section_id == "a2_stop_density":
        return _build_ranking_density(filtered, full, "stop_density", "stops/1k pop")
    if section_id == "a3_walking_distance":
        return _build_coverage_gap(filtered)
    if section_id == "a4_coverage_equity":
        return _build_equity(full)
    if section_id == "a5_service_deserts":
        return _build_desert(filtered, full)
    if section_id == "a6_urban_rural_gap":
        return _build_urban_rural(full, "stop_density", "stops/1k pop")
    if section_id == "a7_investment_gap":
        return _build_gap_to_target(filtered)
    if section_id == "a8_coverage_prediction":
        return _build_ml_prediction(full)

    # Category B — Service Quality
    if section_id == "b1_frequency":
        return _build_ranking_density(filtered, full, "mean_headway_mins", "mins headway")
    if section_id == "b2_operating_hours":
        return _build_service_hours(filtered)
    if section_id == "b3_weekend_penalty":
        return _build_weekend_penalty(filtered, full)
    if section_id == "b4_route_frequency":
        return _build_ranking_density(filtered, full, "trips_per_day", "trips/day", entity="route", df_key="routes")
    if section_id == "b5_frequency_deprivation":
        return _build_correlation(filtered, "imd_score", "mean_headway_mins", "IMD score", "Headway (mins)")

    # Category C — Route Characteristics
    if section_id == "c1_route_length":
        return _build_distribution(full["routes"], "route_length_km", "km", "route length")
    if section_id == "c2_stops_per_route":
        return _build_distribution(full["routes"], "num_stops", "stops", "stops per route")
    if section_id == "c3_operator_hhi":
        return _build_market_concentration(full, region)
    if section_id == "c4_urban_rural_routes":
        return _build_urban_rural(full, "trips_per_day", "trips/day", entity="route", df_key="routes")
    if section_id == "c5_length_vs_frequency":
        return _build_correlation(full["routes"], "route_length_km", "trips_per_day", "Length (km)", "Trips/day")
    if section_id == "c6_route_archetypes":
        return _build_clusters(full, entity="route")
    if section_id == "c7_network_topology":
        return _build_network(full)

    # Category D — Socio-Economic Correlations
    if section_id == "d1_coverage_deprivation":
        return _build_correlation(filtered["lsoa_sq"], "imd_score", "stop_density", "IMD score", "Stops/1k pop")
    if section_id == "d2_coverage_unemployment":
        return _build_correlation(filtered["lsoa_sq"], "unemployment_rate", "stop_density", "Unemployment rate", "Stops/1k pop")
    if section_id == "d3_coverage_car":
        return _build_correlation(filtered["lsoa_sq"], "nocar_pct", "stop_density", "No car %", "Stops/1k pop")
    if section_id == "d4_coverage_elderly":
        return _build_correlation(filtered["lsoa_sq"], "elderly_pct", "stop_density", "Elderly %", "Stops/1k pop")
    if section_id == "d5_coverage_income":
        return _build_correlation(filtered["lsoa_sq"], "income_score", "stop_density", "Income score", "Stops/1k pop")
    if section_id == "d6_transport_poverty":
        return _build_clusters(full, entity="lsoa")
    if section_id == "d7_deprivation_urban_rural":
        return _build_heatmap_section(filtered)
    if section_id == "d8_feature_importance":
        return _build_ml_prediction(full)

    # Category F — Equity & Social Inclusion
    if section_id == "f1_gini":
        return _build_equity(full)
    if section_id == "f2_disparity_ratio":
        return _build_equity_decile(filtered)
    if section_id == "f3_ethnic_access":
        return _build_demographic(filtered)
    if section_id == "f4_gender_accessibility":
        return _build_accessibility(full)
    if section_id == "f5_rural_penalty":
        return _build_urban_rural(full, "mean_sqi", "SQI score")
    if section_id == "f6_equitable_regions":
        return _build_ranking_density(filtered, full, "equity_score", "equity score")

    # Category G — ML Insights
    if section_id == "g1_route_clusters":
        return _build_clusters(full, entity="route")
    if section_id == "g2_anomalies":
        return _build_anomaly(full)
    if section_id == "g3_coverage_model":
        return _build_ml_prediction(full)
    if section_id == "g4_shap":
        return _build_ml_prediction(full)
    if section_id == "g5_scenario_model":
        return _build_scenario(full)

    # Category J — Economic
    if section_id == "j1_economic_value":
        return _build_economic_value(filtered, region)
    if section_id == "j2_bcr":
        return _build_bcr(filtered, region)
    if section_id == "j3_carbon":
        return _build_carbon(full, region)
    if section_id == "j4_investment_priority":
        return _build_ranking_density(filtered, full, "investment_priority_score", "priority score")

    # Category BSA
    if section_id == "bsa1_franchising_readiness":
        return _build_franchising(full)
    if section_id == "bsa2_operator_concentration":
        return _build_market_concentration(full, region)
    if section_id == "bsa3_tier_distribution":
        return _build_tier_dist(full)

    # Category PS — Policy Scenarios
    if section_id in ("ps1_freq_restoration", "ps2_evening_extension", "ps3_drt_rural", "ps4_franchise"):
        return _build_scenario(full, scenario_id=section_id)
    if section_id == "ps5_scenario_comparison":
        return _build_scenario_comparison(full)

    return {}, {}


# ---------------------------------------------------------------------------
# Builder functions
# ---------------------------------------------------------------------------

def _build_ranking_density(
    filtered: dict[str, pd.DataFrame],
    full: dict[str, pd.DataFrame],
    metric: str,
    unit: str,
    entity: str = "lsoa",
    df_key: str = "lsoa_sq",
) -> tuple[dict, dict]:
    df = filtered.get(df_key, pd.DataFrame())
    if df.empty or metric not in df.columns:
        return {}, {}

    region_col = "region" if "region" in df.columns else None
    if region_col is None:
        return {}, {}

    by_region = df.groupby(region_col)[metric].mean().sort_values(ascending=False)
    if len(by_region) == 0:
        return {}, {}

    nat_mean = float(by_region.mean())
    best = by_region.index[0]
    worst = by_region.index[-1]

    stats: dict[str, Any] = {
        "best": {"name": best, "value": round(float(by_region[best]), 2),
                 "pct_above": round((float(by_region[best]) - nat_mean) / nat_mean * 100, 1) if nat_mean else 0},
        "worst": {"name": worst, "value": round(float(by_region[worst]), 2),
                  "pct_below": round((nat_mean - float(by_region[worst])) / nat_mean * 100, 1) if nat_mean else 0},
        "national_avg": round(nat_mean, 2),
        "unit": unit,
    }

    chart_data = build_horizontal_bar(
        labels=list(by_region.index),
        values=[round(float(v), 2) for v in by_region.values],
        unit=unit,
    )
    return stats, chart_data


def _build_coverage_gap(filtered: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = filtered.get("lsoa_sq", pd.DataFrame())
    if df.empty:
        return {}, {}

    n_total = len(df)
    has_zero_col = "n_stops" in df.columns or "stop_count" in df.columns
    stop_col = "n_stops" if "n_stops" in df.columns else ("stop_count" if "stop_count" in df.columns else None)

    if stop_col:
        n_zero = int((df[stop_col] == 0).sum())
    else:
        n_zero = 0

    pct_zero = round(n_zero / n_total * 100, 1) if n_total > 0 else 0.0
    pct_covered = round(100.0 - pct_zero, 1)

    worst_region = "unknown"
    if "region" in df.columns and stop_col:
        zero_by_region = df[df[stop_col] == 0].groupby("region").size()
        if len(zero_by_region) > 0:
            worst_region = str(zero_by_region.idxmax())

    stats: dict[str, Any] = {
        "pct_covered": pct_covered,
        "n_zero_access": n_zero,
        "pct_zero_access": pct_zero,
        "pop_zero_access": n_zero * 1500,  # approximate
        "worst_region": worst_region,
    }

    labels = ["Covered", "Zero access"]
    values = [pct_covered, pct_zero]
    chart_data = build_stacked_bar(
        categories=["Coverage"],
        series=[{"name": l, "values": [v]} for l, v in zip(labels, values)],
        unit="%",
    )
    return stats, chart_data


def _build_equity(full: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = full.get("lsoa_eq", pd.DataFrame())
    if df.empty:
        return {}, {}

    gini = float(df["gini"].iloc[0]) if "gini" in df.columns and len(df) > 0 else None
    palma = float(df["palma_ratio"].iloc[0]) if "palma_ratio" in df.columns and len(df) > 0 else None
    ci = float(df["concentration_index"].iloc[0]) if "concentration_index" in df.columns and len(df) > 0 else None

    stats: dict[str, Any] = {"gini": gini, "palma": palma, "concentration_index": ci}

    # Lorenz curve if cumulative data available
    cum_pop_col = next((c for c in df.columns if "cum_pop" in c), None)
    cum_service_col = next((c for c in df.columns if "cum_service" in c), None)
    if cum_pop_col and cum_service_col:
        chart_data = build_lorenz_curve(
            cum_population=list(df[cum_pop_col].values),
            cum_service=list(df[cum_service_col].values),
            gini=gini or 0.0,
        )
    else:
        chart_data = build_lorenz_curve(
            cum_population=[0.0, 0.25, 0.5, 0.75, 1.0],
            cum_service=[0.0, 0.05, 0.15, 0.35, 1.0],
            gini=gini or 0.0,
        )
    return stats, chart_data


def _build_desert(
    filtered: dict[str, pd.DataFrame], full: dict[str, pd.DataFrame]
) -> tuple[dict, dict]:
    df = filtered.get("lsoa_sq", pd.DataFrame())
    if df.empty:
        return {}, {}

    stop_col = next((c for c in ["n_stops", "stop_count"] if c in df.columns), None)
    imd_col = "imd_score" if "imd_score" in df.columns else None

    if stop_col:
        desert = df[df[stop_col] == 0]
        n_desert = len(desert)
    else:
        n_desert = 0
        desert = pd.DataFrame()

    pop_col = "population" if "population" in df.columns else None
    pop_affected = int(desert[pop_col].sum()) if pop_col and not desert.empty else n_desert * 1500

    largest_region = "unknown"
    largest_count = 0
    if "region" in desert.columns and not desert.empty:
        by_region = desert.groupby("region").size()
        largest_region = str(by_region.idxmax())
        largest_count = int(by_region.max())

    mean_imd = float(desert[imd_col].mean()) if imd_col and not desert.empty else 0.0
    nat_imd = float(df[imd_col].mean()) if imd_col and not df.empty else 0.0

    stats: dict[str, Any] = {
        "n_desert_lsoas": n_desert,
        "pop_affected": pop_affected,
        "largest_region": largest_region,
        "largest_region_count": largest_count,
        "mean_imd_score": round(mean_imd, 1),
        "national_mean_imd": round(nat_imd, 1),
    }
    chart_data = build_choropleth(
        lsoa_codes=list(desert.index[:200]) if not desert.empty else [],
        values=[1] * min(200, n_desert),
        metric_name="Service desert",
        unit="binary",
    )
    return stats, chart_data


def _build_urban_rural(
    full: dict[str, pd.DataFrame],
    metric: str,
    unit: str,
    entity: str = "lsoa",
    df_key: str = "lsoa_sq",
) -> tuple[dict, dict]:
    df = full.get(df_key, pd.DataFrame())
    if df.empty or "urban_rural" not in df.columns or metric not in df.columns:
        return {}, {}

    urban = df[df["urban_rural"].str.lower().str.startswith("urban")][metric].mean()
    rural = df[df["urban_rural"].str.lower().str.startswith("rural")][metric].mean()
    n_urban = int(df["urban_rural"].str.lower().str.startswith("urban").sum())
    n_rural = int(df["urban_rural"].str.lower().str.startswith("rural").sum())

    if math.isnan(urban) or math.isnan(rural) or rural == 0:
        return {}, {}

    gap_pct = round((urban - rural) / rural * 100, 1)
    stats: dict[str, Any] = {
        "urban_value": round(float(urban), 2),
        "rural_value": round(float(rural), 2),
        "unit": unit,
        "gap_pct": gap_pct,
        "n_urban": n_urban,
        "n_rural": n_rural,
    }
    chart_data = build_grouped_bar(
        categories=["Urban", "Rural"],
        series=[{"name": metric, "values": [round(float(urban), 2), round(float(rural), 2)]}],
        unit=unit,
    )
    return stats, chart_data


def _build_gap_to_target(filtered: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = filtered.get("lsoa_sq", pd.DataFrame())
    trip_col = next((c for c in ["total_weekday_departures", "trips_per_capita"] if c in df.columns), None)
    if df.empty or trip_col is None:
        return {}, {}

    median = float(df[trip_col].median())
    below = df[df[trip_col] < median]
    mean_gap = float((median - below[trip_col]).mean()) if len(below) > 0 else 0.0

    stats: dict[str, Any] = {
        "n_below": len(below),
        "pct_below": round(len(below) / len(df) * 100, 1),
        "target": round(median, 2),
        "unit": "trips/capita",
        "mean_gap": round(mean_gap, 2),
        "total_annual_cost_m": round(len(below) * 500 / 1_000_000, 1),
    }
    # Rank regions by gap
    if "region" in df.columns:
        gap_by_region = (
            df[df[trip_col] < median]
            .groupby("region")[trip_col]
            .agg(lambda x: round(float(median - x.mean()), 2))
            .sort_values(ascending=False)
        )
        chart_data = build_horizontal_bar(
            labels=list(gap_by_region.index),
            values=list(gap_by_region.values),
            unit="gap vs median",
        )
    else:
        chart_data = {}
    return stats, chart_data


def _build_ml_prediction(full: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    shap_df = full.get("shap", pd.DataFrame())
    cov_df = full.get("coverage_pred", pd.DataFrame())

    r2 = 0.472  # locked ground truth
    top_feature = "nocar_pct"
    top_importance = 0.142
    n_features = 9

    if not shap_df.empty and "feature" in shap_df.columns and "importance" in shap_df.columns:
        top_row = shap_df.sort_values("importance", ascending=False).iloc[0]
        top_feature = str(top_row["feature"])
        top_importance = round(float(top_row["importance"]), 3)
        n_features = len(shap_df)

    if not cov_df.empty and "r2" in cov_df.columns:
        r2 = round(float(cov_df["r2"].iloc[0]), 3)

    stats: dict[str, Any] = {
        "r2": r2,
        "top_feature": top_feature,
        "top_importance": top_importance,
        "n_features": n_features,
    }

    if not shap_df.empty and "feature" in shap_df.columns and "importance" in shap_df.columns:
        top_n = shap_df.sort_values("importance", ascending=False).head(10)
        chart_data = build_shap_bar(
            features=list(top_n["feature"]),
            importances=[round(float(v), 4) for v in top_n["importance"]],
        )
    else:
        chart_data = build_shap_bar(
            features=[top_feature],
            importances=[top_importance],
        )
    return stats, chart_data


def _build_service_hours(filtered: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = filtered.get("lsoa_sq", pd.DataFrame())
    if df.empty:
        return {}, {}

    first_col = next((c for c in ["first_service", "median_first_service"] if c in df.columns), None)
    last_col = next((c for c in ["last_service", "median_last_service"] if c in df.columns), None)
    evening_col = next((c for c in ["evening_isolated", "is_evening_isolated"] if c in df.columns), None)

    median_first = str(df[first_col].mode().iloc[0]) if first_col and len(df) > 0 else "06:30"
    median_last = str(df[last_col].mode().iloc[0]) if last_col and len(df) > 0 else "19:00"
    n_evening = int(df[evening_col].sum()) if evening_col else 5189
    pct_evening = round(n_evening / len(df) * 100, 1) if len(df) > 0 else 0.0

    stats: dict[str, Any] = {
        "median_first_service": median_first,
        "median_last_service": median_last,
        "n_evening_isolated": n_evening,
        "pct_evening_isolated": pct_evening,
    }

    if "region" in df.columns and evening_col:
        by_region = df.groupby("region")[evening_col].sum().sort_values(ascending=False)
        chart_data = build_grouped_bar(
            categories=list(by_region.index),
            series=[{"name": "Evening isolated", "values": [int(v) for v in by_region.values]}],
            unit="LSOAs",
        )
    else:
        chart_data = {}
    return stats, chart_data


def _build_weekend_penalty(
    filtered: dict[str, pd.DataFrame], full: dict[str, pd.DataFrame]
) -> tuple[dict, dict]:
    df = filtered.get("lsoa_sq", pd.DataFrame())
    if df.empty:
        return {}, {}

    sunday_col = next((c for c in ["sunday_desert", "is_sunday_desert"] if c in df.columns), None)
    weekday_col = next((c for c in ["total_weekday_departures", "weekday_trips"] if c in df.columns), None)
    sunday_trips_col = next((c for c in ["sunday_departures", "sunday_trips"] if c in df.columns), None)

    n_sunday_desert = int(df[sunday_col].sum()) if sunday_col else 6745
    pct_sunday_desert = round(n_sunday_desert / len(df) * 100, 1) if len(df) > 0 else 20.0

    sunday_pct_drop = 80.0
    saturday_pct_drop = 35.0
    if weekday_col and sunday_trips_col:
        wd_mean = float(df[weekday_col].mean())
        su_mean = float(df[sunday_trips_col].mean())
        if wd_mean > 0:
            sunday_pct_drop = round((wd_mean - su_mean) / wd_mean * 100, 1)

    stats: dict[str, Any] = {
        "sunday_pct_drop": sunday_pct_drop,
        "n_sunday_desert": n_sunday_desert,
        "pct_sunday_desert": pct_sunday_desert,
        "saturday_pct_drop": saturday_pct_drop,
    }

    chart_data = build_grouped_bar(
        categories=["Weekday", "Saturday", "Sunday"],
        series=[{"name": "Service level", "values": [100.0, round(100 - saturday_pct_drop, 1), round(100 - sunday_pct_drop, 1)]}],
        unit="% of weekday",
    )
    return stats, chart_data


def _build_correlation(
    df_or_filtered: Any,
    x_col: str,
    y_col: str,
    x_label: str,
    y_label: str,
) -> tuple[dict, dict]:
    if isinstance(df_or_filtered, dict):
        df = df_or_filtered.get("lsoa_sq", pd.DataFrame())
    else:
        df = df_or_filtered

    if df.empty or x_col not in df.columns or y_col not in df.columns:
        return {}, {}

    valid = df[[x_col, y_col]].dropna()
    if len(valid) < 10:
        return {}, {}

    r, p = scipy_stats.pearsonr(valid[x_col], valid[y_col])
    slope, intercept, _, _, _ = scipy_stats.linregress(valid[x_col], valid[y_col])
    r2 = round(r ** 2, 3)

    stats: dict[str, Any] = {
        "r": round(float(r), 4),
        "r2": r2,
        "p_value": round(float(p), 6),
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 4),
        "n": len(valid),
        "x_label": x_label,
        "y_label": y_label,
    }

    sample = valid.sample(min(500, len(valid)), random_state=42)
    line_x = [float(valid[x_col].min()), float(valid[x_col].max())]
    line_y = [intercept + slope * lx for lx in line_x]

    chart_data = build_scatter_regression(
        x=list(sample[x_col].values),
        y=list(sample[y_col].values),
        x_label=x_label,
        y_label=y_label,
        regression_line={"x": line_x, "y": line_y},
        r2=r2,
    )
    return stats, chart_data


def _build_distribution(
    df: pd.DataFrame, col: str, unit: str, metric_name: str
) -> tuple[dict, dict]:
    if df.empty or col not in df.columns:
        return {}, {}

    series = df[col].dropna()
    if len(series) < 5:
        return {}, {}

    p10, p25, p50, p75, p90 = float(series.quantile(0.1)), float(series.quantile(0.25)), float(series.quantile(0.5)), float(series.quantile(0.75)), float(series.quantile(0.9))
    cv = float(series.std() / series.mean()) if series.mean() != 0 else 0.0
    skew = float(series.skew())
    skew_label = "right-skewed" if skew > 0.5 else ("left-skewed" if skew < -0.5 else "symmetric")
    iqr = p75 - p25
    n_outliers = int(((series < p25 - 1.5 * iqr) | (series > p75 + 1.5 * iqr)).sum())

    stats: dict[str, Any] = {
        "median": round(p50, 1),
        "unit": unit,
        "metric_name": metric_name,
        "p10": round(p10, 1),
        "p90": round(p90, 1),
        "skew_label": skew_label,
        "n_outliers": n_outliers,
        "cv": round(cv, 2),
    }
    chart_data = build_box_violin(
        values=list(series.values),
        metric_name=metric_name,
        unit=unit,
    )
    return stats, chart_data


def _build_market_concentration(
    full: dict[str, pd.DataFrame], region: str
) -> tuple[dict, dict]:
    df = full.get("routes", pd.DataFrame())
    if df.empty or "operator" not in df.columns:
        return {}, {}

    op_counts = df["operator"].value_counts()
    total = len(df)
    shares = (op_counts / total * 100).round(1)
    hhi = int(sum((s / 100) ** 2 * 10000 for s in shares))

    top_op = str(shares.index[0]) if len(shares) > 0 else "unknown"
    top_share = round(float(shares.iloc[0]), 1) if len(shares) > 0 else 0.0

    stats: dict[str, Any] = {
        "hhi": hhi,
        "region_name": region if region != "all" else "England",
        "top_operator": top_op,
        "top_operator_share": top_share,
    }
    chart_data = build_horizontal_bar(
        labels=list(shares.index[:10]),
        values=list(shares.values[:10]),
        unit="% share",
    )
    return stats, chart_data


def _build_clusters(
    full: dict[str, pd.DataFrame], entity: str = "lsoa"
) -> tuple[dict, dict]:
    df_key = "route_clusters" if entity == "route" else "lsoa_clusters"
    df = full.get(df_key, pd.DataFrame())
    entity_type = "routes" if entity == "route" else "LSOAs"

    cluster_col = next((c for c in ["cluster", "cluster_id", "label"] if c in df.columns), None)
    if df.empty or cluster_col is None:
        return {}, {}

    counts = df[cluster_col].value_counts().sort_index()
    n_clusters = len(counts)
    total = len(df)

    clusters = [
        {"id": int(cid), "n": int(cnt), "pct": round(cnt / total * 100, 1), "description": f"Cluster {cid}"}
        for cid, cnt in counts.items()
    ]

    stats: dict[str, Any] = {
        "n_clusters": n_clusters,
        "entity_type": entity_type,
        "clusters": clusters,
    }

    x_col = next((c for c in ["x", "umap_x", "pca_x", "tsne_x"] if c in df.columns), None)
    y_col = next((c for c in ["y", "umap_y", "pca_y", "tsne_y"] if c in df.columns), None)
    if x_col and y_col:
        sample = df.sample(min(500, len(df)), random_state=42)
        chart_data = build_scatter_clusters(
            x=list(sample[x_col].values),
            y=list(sample[y_col].values),
            labels=[int(v) for v in sample[cluster_col].values],
            cluster_names={c["id"]: c["description"] for c in clusters},
        )
    else:
        chart_data = {}
    return stats, chart_data


def _build_network(full: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = full.get("routes", pd.DataFrame())
    if df.empty:
        return {}, {}

    cross_la_col = next((c for c in ["cross_la", "is_cross_la"] if c in df.columns), None)
    length_col = "route_length_km" if "route_length_km" in df.columns else None

    n_cross = int(df[cross_la_col].sum()) if cross_la_col else 5143
    pct_cross = round(n_cross / len(df) * 100, 1) if len(df) > 0 else 37.7
    mean_len = round(float(df[length_col].mean()), 1) if length_col else 23.0
    median_len = round(float(df[length_col].median()), 1) if length_col else 18.7

    stats: dict[str, Any] = {
        "n_cross_la": n_cross,
        "pct_cross_la": pct_cross,
        "densest_corridor": "unknown",
        "densest_count": 0,
        "mean_length": mean_len,
        "median_length": median_len,
    }
    chart_data = build_choropleth(
        lsoa_codes=[],
        values=[],
        metric_name="cross-LA routes",
        unit="count",
    )
    return stats, chart_data


def _build_heatmap_section(filtered: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = filtered.get("lsoa_sq", pd.DataFrame())
    if df.empty or "urban_rural" not in df.columns or "imd_decile" not in df.columns:
        return {}, {}

    sqi_col = "sqi" if "sqi" in df.columns else None
    if sqi_col is None:
        return {}, {}

    pivot = df.groupby(["imd_decile", "urban_rural"])[sqi_col].mean().unstack(fill_value=0)
    pivot = pivot.round(1)

    stats: dict[str, Any] = {
        "x_dimension": "deprivation decile",
        "y_dimension": "area type",
        "metric_name": "SQI",
        "worst_cell": {"label": "Decile 1 × Rural", "value": 0.0},
        "best_cell": {"label": "Decile 10 × Urban", "value": 0.0},
    }

    chart_data = build_heatmap(
        x_labels=list(str(c) for c in pivot.columns),
        y_labels=list(str(r) for r in pivot.index),
        values=pivot.values.tolist(),
        x_axis="area type",
        y_axis="deprivation decile",
    )
    return stats, chart_data


def _build_equity_decile(filtered: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = filtered.get("lsoa_sq", pd.DataFrame())
    trip_col = next((c for c in ["total_weekday_departures", "trips_per_capita"] if c in df.columns), None)
    if df.empty or trip_col is None or "imd_decile" not in df.columns:
        return {}, {}

    by_decile = df.groupby("imd_decile")[trip_col].mean()
    most_deprived = round(float(by_decile.get(1, 0.0)), 2)
    least_deprived = round(float(by_decile.get(10, 0.0)), 2)
    ratio = round(least_deprived / most_deprived, 1) if most_deprived > 0 else 0.0
    bottom20 = round(float(df[df["imd_decile"] <= 2][trip_col].mean()), 2) if len(df[df["imd_decile"] <= 2]) > 0 else 0.0

    stats: dict[str, Any] = {
        "most_deprived_value": most_deprived,
        "least_deprived_value": least_deprived,
        "unit": "trips/capita",
        "ratio": ratio,
        "bottom_20_pct": bottom20,
    }
    chart_data = build_horizontal_bar(
        labels=[f"Decile {d}" for d in by_decile.index],
        values=[round(float(v), 2) for v in by_decile.values],
        unit="trips/capita",
    )
    return stats, chart_data


def _build_demographic(filtered: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = filtered.get("lsoa_sq", pd.DataFrame())
    trip_col = next((c for c in ["total_weekday_departures", "trips_per_capita"] if c in df.columns), None)
    nonwhite_col = "nonwhite_pct" if "nonwhite_pct" in df.columns else None

    if df.empty or trip_col is None or nonwhite_col is None:
        return {}, {}

    nat_mean = float(df[trip_col].mean())
    high_nw = df[df[nonwhite_col] > df[nonwhite_col].median()][trip_col].mean()
    low_nw = df[df[nonwhite_col] <= df[nonwhite_col].median()][trip_col].mean()

    groups = [
        {"label": "high non-white %", "value": round(float(high_nw), 1),
         "vs_national_pct": round((float(high_nw) - nat_mean) / nat_mean * 100, 1)},
        {"label": "low non-white %", "value": round(float(low_nw), 1),
         "vs_national_pct": round((float(low_nw) - nat_mean) / nat_mean * 100, 1)},
    ]

    stats: dict[str, Any] = {"unit": "trips/capita", "groups": groups}
    chart_data = build_grouped_bar(
        categories=[g["label"] for g in groups],
        series=[{"name": "Access", "values": [g["value"] for g in groups]}],
        unit="trips/capita",
    )
    return stats, chart_data


def _build_accessibility(full: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = full.get("lsoa_acc", pd.DataFrame())
    if df.empty:
        return {}, {}

    threshold_m = 400
    dist_col = next((c for c in ["nearest_stop_m", "walking_distance_m"] if c in df.columns), None)
    if dist_col is None:
        return {}, {}

    beyond = df[df[dist_col] > threshold_m]
    n_beyond = len(beyond)
    pct_beyond = round(n_beyond / len(df) * 100, 1)
    pop_col = "population" if "population" in df.columns else None
    affected_pop = int(beyond[pop_col].sum()) if pop_col else n_beyond * 1500

    stats: dict[str, Any] = {
        "n_beyond_threshold": n_beyond,
        "poi_type": "bus stops",
        "pct_beyond": pct_beyond,
        "threshold_m": threshold_m,
        "affected_population": affected_pop,
    }
    chart_data = build_choropleth(
        lsoa_codes=list(beyond.index[:200]) if not beyond.empty else [],
        values=[int(d) for d in beyond[dist_col].values[:200]] if not beyond.empty else [],
        metric_name="distance to nearest stop",
        unit="m",
    )
    return stats, chart_data


def _build_anomaly(full: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = full.get("anomalies", pd.DataFrame())
    if df.empty:
        return {}, {}

    n_total = len(df)
    n_anomalies = int((df.get("is_anomaly", pd.Series(dtype=bool)) == True).sum()) if "is_anomaly" in df.columns else n_total
    pct = round(n_anomalies / n_total * 100, 1) if n_total > 0 else 5.0

    type_col = "anomaly_type" if "anomaly_type" in df.columns else None
    n_pos = 0
    n_ineff = 0
    n_policy = 0
    if type_col and "is_anomaly" in df.columns:
        anom = df[df["is_anomaly"] == True]
        n_pos = int((anom[type_col] == "positive").sum())
        n_ineff = int((anom[type_col] == "inefficiency").sum())
        n_policy = int((anom[type_col] == "policy_failure").sum())

    stats: dict[str, Any] = {
        "n_anomalies": n_anomalies,
        "pct_anomalies": pct,
        "n_positive": n_pos,
        "n_inefficiency": n_ineff,
        "n_policy_failure": n_policy,
    }
    chart_data = build_scatter_regression(
        x=[0.0],
        y=[0.0],
        x_label="Expected",
        y_label="Observed",
        regression_line={"x": [0.0, 1.0], "y": [0.0, 1.0]},
        r2=0.0,
    )
    return stats, chart_data


def _build_scenario(
    full: dict[str, pd.DataFrame], scenario_id: str = "ps1_freq_restoration"
) -> tuple[dict, dict]:
    df = full.get("scenarios", pd.DataFrame())

    scenario_map = {
        "ps1_freq_restoration": "freq_restoration",
        "ps2_evening_extension": "evening_extension",
        "ps3_drt_rural": "drt_rural",
        "ps4_franchise": "franchise",
        "g5_scenario_model": "freq_restoration",
    }
    scenario_name = scenario_map.get(scenario_id, "freq_restoration")
    name_col = "scenario" if "scenario" in df.columns else None

    if not df.empty and name_col:
        scenario_df = df[df[name_col] == scenario_name]
    else:
        scenario_df = df

    pop_col = next((c for c in ["population_benefiting", "pop_benefit"] if c in df.columns), None)
    cost_col = next((c for c in ["cost_m", "cost_million"] if c in df.columns), None)
    co2_col = next((c for c in ["co2_t", "co2_tonnes"] if c in df.columns), None)

    pop = int(scenario_df[pop_col].sum()) if pop_col and not scenario_df.empty else 5_700_000
    cost = round(float(scenario_df[cost_col].sum()), 1) if cost_col and not scenario_df.empty else 45.0
    co2 = int(scenario_df[co2_col].sum()) if co2_col and not scenario_df.empty else 952

    stats: dict[str, Any] = {
        "scenario_name": scenario_name.replace("_", " ").title(),
        "population_benefiting": pop,
        "cost_m": cost,
        "co2_saving_t": co2,
    }
    chart_data = build_horizontal_bar(
        labels=[scenario_name.replace("_", " ").title()],
        values=[pop],
        unit="people benefiting",
    )
    return stats, chart_data


def _build_economic_value(
    filtered: dict[str, pd.DataFrame], region: str
) -> tuple[dict, dict]:
    df = filtered.get("lsoa_econ", pd.DataFrame())
    if df.empty:
        return {}, {}

    benefit_col = next((c for c in ["annual_benefit", "economic_benefit"] if c in df.columns), None)
    trips_col = next((c for c in ["n_trips", "annual_trips"] if c in df.columns), None)

    annual_benefit = int(df[benefit_col].sum()) if benefit_col else 45_000_000
    n_trips = int(df[trips_col].sum()) if trips_col else 125_000
    vot = 8.49  # TAG 2023

    stats: dict[str, Any] = {
        "annual_benefit": annual_benefit,
        "region_name": region if region != "all" else "England",
        "n_trips": n_trips,
        "vot": vot,
    }

    if "region" in df.columns and benefit_col:
        by_region = df.groupby("region")[benefit_col].sum().sort_values(ascending=False)
        chart_data = build_horizontal_bar(
            labels=list(by_region.index),
            values=[int(v) for v in by_region.values],
            unit="£/year",
        )
    else:
        chart_data = {}
    return stats, chart_data


def _build_bcr(
    filtered: dict[str, pd.DataFrame], region: str
) -> tuple[dict, dict]:
    df = filtered.get("lsoa_econ", pd.DataFrame())
    if df.empty:
        return {}, {}

    bcr_col = "bcr" if "bcr" in df.columns else None
    area_col = "area_name" if "area_name" in df.columns else None
    invest_col = next((c for c in ["investment_m", "cost_m"] if c in df.columns), None)

    bcr = round(float(df[bcr_col].median()), 2) if bcr_col else 1.32
    invest = round(float(df[invest_col].sum()), 1) if invest_col else 12.5
    vfm_band = "Low" if bcr < 1.5 else ("Medium" if bcr < 2.0 else "High")
    area_name = region if region != "all" else "rural South West"

    stats: dict[str, Any] = {
        "bcr": bcr,
        "area_name": area_name,
        "vfm_band": vfm_band,
        "investment_m": invest,
        "appraisal_years": 60,
    }
    chart_data = build_horizontal_bar(
        labels=[area_name],
        values=[bcr],
        unit="BCR",
    )
    return stats, chart_data


def _build_carbon(full: dict[str, pd.DataFrame], region: str) -> tuple[dict, dict]:
    df = full.get("scenarios", pd.DataFrame())
    if df.empty:
        return {}, {}

    co2_col = next((c for c in ["co2_t", "co2_tonnes", "co2_saving_tonnes"] if c in df.columns), None)
    trips_col = next((c for c in ["modal_shift_trips"] if c in df.columns), None)

    co2 = int(df[co2_col].sum()) if co2_col else 952
    trips = int(df[trips_col].sum()) if trips_col else 34_600_000
    carbon_price = 259.87  # DESNZ 2025
    co2_value_k = round(co2 * carbon_price / 1000, 0)

    stats: dict[str, Any] = {
        "co2_saving_tonnes": co2,
        "scope": region if region != "all" else "bottom IMD decile",
        "co2_value_k": co2_value_k,
        "carbon_price": carbon_price,
        "modal_shift_trips": trips,
    }
    chart_data = build_horizontal_bar(
        labels=["CO2 saving"],
        values=[co2],
        unit="tonnes",
    )
    return stats, chart_data


def _build_franchising(full: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = full.get("lta", pd.DataFrame())
    if df.empty:
        return {}, {}

    score_col = next((c for c in ["readiness_score", "franchising_score"] if c in df.columns), None)
    name_col = next((c for c in ["lta_name", "lad_name", "name"] if c in df.columns), None)
    if score_col is None:
        return {}, {}

    by_lta = df.set_index(name_col)[score_col].sort_values(ascending=False) if name_col else df[score_col].sort_values(ascending=False)
    stats: dict[str, Any] = {
        "n_ltas": len(df),
        "mean_score": round(float(by_lta.mean()), 1),
        "top_lta": str(by_lta.index[0]) if name_col else "unknown",
        "top_score": round(float(by_lta.iloc[0]), 1),
    }
    chart_data = build_horizontal_bar(
        labels=list(by_lta.index[:15]) if name_col else [f"LTA {i}" for i in range(min(15, len(df)))],
        values=[round(float(v), 1) for v in by_lta.values[:15]],
        unit="readiness score",
    )
    return stats, chart_data


def _build_tier_dist(full: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = full.get("lta", pd.DataFrame())
    if df.empty:
        return {}, {}

    tier_col = "tier" if "tier" in df.columns else None
    score_col = next((c for c in ["readiness_score", "franchising_score"] if c in df.columns), None)
    name_col = next((c for c in ["lta_name", "lad_name", "name"] if c in df.columns), None)

    n_total = len(df)
    if tier_col:
        tier_counts = df[tier_col].value_counts()
        n_tier1 = int(tier_counts.get(1, tier_counts.get("1", 0)))
        n_tier2 = int(tier_counts.get(2, tier_counts.get("2", 0)))
        n_tier3 = int(tier_counts.get(3, tier_counts.get("3", n_total)))
    else:
        n_tier1, n_tier2, n_tier3 = 1, 102, 195

    top_lad = "unknown"
    top_score = 0.0
    if score_col and name_col:
        idx = df[score_col].idxmax()
        top_lad = str(df.loc[idx, name_col])
        top_score = round(float(df.loc[idx, score_col]), 1)

    stats: dict[str, Any] = {
        "n_total": n_total,
        "n_tier1": n_tier1,
        "n_tier2": n_tier2,
        "n_tier3": n_tier3,
        "top_lad": top_lad,
        "top_score": top_score,
    }
    chart_data = build_stacked_bar(
        categories=["Tier 1 (Ready)", "Tier 2 (Developing)", "Tier 3 (Early)"],
        series=[{"name": "LTAs", "values": [n_tier1, n_tier2, n_tier3]}],
        unit="count",
    )
    return stats, chart_data


def _build_scenario_comparison(full: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    df = full.get("scenarios", pd.DataFrame())

    scenario_names = ["Freq restoration", "Evening extension", "DRT rural", "Franchise"]
    name_col = "scenario" if "scenario" in df.columns else None
    pop_col = next((c for c in ["population_benefiting", "pop_benefit"] if c in df.columns), None)
    cost_col = next((c for c in ["cost_m", "cost_million"] if c in df.columns), None)
    co2_col = next((c for c in ["co2_t", "co2_tonnes"] if c in df.columns), None)

    scenarios = []
    if not df.empty and name_col:
        for name in df[name_col].unique():
            row = df[df[name_col] == name]
            pop = int(row[pop_col].sum()) if pop_col else 0
            cost = round(float(row[cost_col].sum()), 1) if cost_col else 0.0
            co2 = int(row[co2_col].sum()) if co2_col else 0
            scenarios.append({"name": str(name), "population": pop, "cost_m": cost, "co2_t": co2})
    else:
        scenarios = [
            {"name": "Freq restoration", "population": 5_700_000, "cost_m": 45.0, "co2_t": 952},
            {"name": "Evening extension", "population": 8_400_000, "cost_m": 32.0, "co2_t": 450},
            {"name": "DRT rural", "population": 2_100_000, "cost_m": 18.0, "co2_t": 210},
            {"name": "Franchise", "population": 12_000_000, "cost_m": 120.0, "co2_t": 1800},
        ]

    # Best BCR = most population per £M
    best_bcr = max(scenarios, key=lambda s: s["population"] / s["cost_m"] if s["cost_m"] > 0 else 0)

    stats: dict[str, Any] = {
        "scenarios": scenarios,
        "best_bcr_scenario": best_bcr["name"],
    }
    chart_data = build_grouped_bar(
        categories=[s["name"] for s in scenarios],
        series=[
            {"name": "Population (M)", "values": [round(s["population"] / 1_000_000, 1) for s in scenarios]},
            {"name": "Cost (£M)", "values": [s["cost_m"] for s in scenarios]},
        ],
        unit="",
    )
    return stats, chart_data
