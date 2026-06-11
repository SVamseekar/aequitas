"""Stats builders for the 9 single/dual-section template contracts.

Covers: a3_walking_distance, a5_service_deserts, b2_operating_hours,
b3_weekend_penalty, c1_route_length, c2_stops_per_route,
d7_deprivation_urban_rural, g2_anomalies, bsa3_tier_distribution.
"""

import pandas as pd

from aequitas.intelligence.calculators import describe_distribution

# LSOA-level statistics (coverage %, desert counts) become unstable/misleading
# below this sample size — mirrors equity.py's _MIN_LSOAS_FOR_GINI threshold.
_MIN_LSOAS_FOR_COVERAGE_STATS = 30


def _skew_label(mean: float, median: float, std: float) -> str:
    if std == 0:
        return "approximately symmetric"
    skew = (mean - median) / std
    if skew > 0.2:
        return "right-skewed (positive)"
    if skew < -0.2:
        return "left-skewed (negative)"
    return "approximately symmetric"


def _minutes_to_hhmm(minutes: float) -> str:
    hours, mins = divmod(int(round(minutes)), 60)
    return f"{hours:02d}:{mins:02d}"


def _build_walking_distance(policy_df: pd.DataFrame, region: str) -> dict:
    if policy_df.empty or "sfca_score_norm" not in policy_df.columns:
        return {"insufficient_data": True, "n_lsoas": 0}

    n_lsoas = len(policy_df)
    if n_lsoas < _MIN_LSOAS_FOR_COVERAGE_STATS:
        return {"insufficient_data": True, "n_lsoas": n_lsoas}

    zero_access = policy_df[policy_df["sfca_score_norm"] == 0]
    n_total = len(policy_df)
    n_zero = len(zero_access)

    stats = {
        "pct_covered": (1 - n_zero / n_total) * 100,
        "n_zero_access": int(n_zero),
        "pct_zero_access": n_zero / n_total * 100,
        "pop_zero_access": float(zero_access["population"].sum()),
    }

    if region == "all" and n_zero > 0:
        worst = zero_access.groupby("region").size().idxmax()
        stats["worst_region"] = str(worst)

    return stats


def _build_service_deserts(policy_df: pd.DataFrame, service_levels_df: pd.DataFrame | None, region: str) -> dict:
    if policy_df.empty or service_levels_df is None or service_levels_df.empty:
        return {"insufficient_data": True, "n_lsoas": len(policy_df)}

    n_lsoas = len(policy_df)
    if n_lsoas < _MIN_LSOAS_FOR_COVERAGE_STATS:
        return {"insufficient_data": True, "n_lsoas": n_lsoas}

    joined = policy_df.merge(service_levels_df[["lsoa_cd", "stop_count"]], on="lsoa_cd", how="inner")
    deserts = joined[joined["stop_count"] == 0]
    if deserts.empty:
        return {}

    national_mean_imd = float(policy_df["imd_score"].mean())

    stats = {
        "n_desert_lsoas": int(len(deserts)),
        "pop_affected": float(deserts["population"].sum()),
        "mean_imd_score": round(float(deserts["imd_score"].mean()), 1),
        "national_mean_imd": round(national_mean_imd, 1),
    }

    if region == "all":
        by_region = deserts.groupby("region").size()
        largest = by_region.idxmax()
        stats["largest_region"] = str(largest)
        stats["largest_region_count"] = int(by_region.loc[largest])

    return stats


def _build_operating_hours(service_quality_df: pd.DataFrame | None) -> dict:
    if service_quality_df is None or service_quality_df.empty:
        return {}

    n_total = len(service_quality_df)
    n_evening_isolated = int(service_quality_df["evening_isolated"].sum())

    return {
        "median_first_service": _minutes_to_hhmm(service_quality_df["first_service_min"].median()),
        "median_last_service": _minutes_to_hhmm(service_quality_df["last_service_min"].median()),
        "n_evening_isolated": n_evening_isolated,
        "pct_evening_isolated": n_evening_isolated / n_total * 100,
    }


def _build_weekend_penalty(service_quality_df: pd.DataFrame | None) -> dict:
    """Build sunday/weekend penalty stats from lsoa_service_quality.

    NOTE: lsoa_service_levels.total_weekday_trips/total_saturday_trips/
    total_sunday_trips are zero-filled (see MEMORY.md Critical Data Traps),
    so this builder uses lsoa_service_quality's total_weekday_departures /
    total_sunday_departures and sunday_desert flag instead. No Saturday
    departure figure exists in any audit table — saturday_pct_drop is
    therefore omitted (the template treats it as optional).
    """
    if service_quality_df is None or service_quality_df.empty:
        return {}
    required = {"total_weekday_departures", "total_sunday_departures", "sunday_desert"}
    if not required.issubset(service_quality_df.columns):
        return {}

    weekday = float(service_quality_df["total_weekday_departures"].sum())
    if weekday == 0:
        return {}

    sunday = float(service_quality_df["total_sunday_departures"].sum())
    sunday_deserts = service_quality_df[service_quality_df["sunday_desert"]]

    return {
        "sunday_pct_drop": (1 - sunday / weekday) * 100,
        "n_sunday_desert": int(len(sunday_deserts)),
        "pct_sunday_desert": round(len(sunday_deserts) / len(service_quality_df) * 100, 1),
    }


def _build_distribution_section(route_geometries_df: pd.DataFrame | None, region: str, region_name: str, column: str, metric_name: str, unit: str) -> dict:
    if route_geometries_df is None or route_geometries_df.empty or column not in route_geometries_df.columns:
        return {}

    df = route_geometries_df
    if region != "all" and "primary_region" in df.columns:
        df = df[df["primary_region"] == region_name]
    if df.empty:
        return {}

    summary = describe_distribution(df[column])
    return {
        "mean": summary.mean,
        "median": summary.median,
        "std": summary.std,
        "cv": summary.cv,
        "iqr": summary.iqr,
        "p10": summary.p10,
        "p90": summary.p90,
        "n_outliers": summary.outliers,
        "metric_name": metric_name,
        "unit": unit,
        "skew_label": _skew_label(summary.mean, summary.median, summary.std),
    }


def _build_deprivation_heatmap(policy_df: pd.DataFrame) -> dict:
    if policy_df.empty:
        return {}

    grouped = policy_df.groupby(["imd_decile", "urban_rural"])["service_quality_index"].mean()
    if grouped.empty:
        return {}

    worst_idx = grouped.idxmin()
    best_idx = grouped.idxmax()

    def _cell(idx: tuple) -> dict:
        decile, area_type = idx
        return {"label": f"Decile {decile}, {area_type}", "value": round(float(grouped.loc[idx]), 1)}

    return {
        "x_dimension": "IMD decile",
        "y_dimension": "urban/rural classification",
        "metric_name": "service quality index",
        "worst_cell": _cell(worst_idx),
        "best_cell": _cell(best_idx),
    }


def _build_anomalies(anomalies_df: pd.DataFrame | None) -> dict:
    if anomalies_df is None or anomalies_df.empty:
        return {}

    n_total = len(anomalies_df)
    type_counts = anomalies_df["anomaly_type"].value_counts()

    return {
        "n_anomalies": int(anomalies_df["both_anomaly"].sum()),
        "pct_anomalies": int(anomalies_df["both_anomaly"].sum()) / n_total * 100,
        "n_positive": int(type_counts.get("positive_deprived_well_served", 0)),
        "n_inefficiency": int(type_counts.get("inefficiency_affluent_poor_served", 0)),
        "n_policy_failure": int(type_counts.get("policy_failure_elderly_no_service", 0)),
    }


def _build_tier_distribution(lta_df: pd.DataFrame | None, urban_rural: str) -> dict:
    """Build the bsa3_tier_distribution stats dict.

    Args:
        lta_df: lta_franchising_readiness rows for the active region scope.
        urban_rural: Active area-type filter. lta_franchising_readiness is
            LAD-grain with no urban/rural classification, so the result is
            identical regardless of this value — `is_lad_level_unfiltered`
            tells the template whether to surface that caveat.

    Returns:
        Dict matching tier_distribution.j2's contract, or {} if lta_df is
        missing/empty.
    """
    if lta_df is None or lta_df.empty:
        return {}

    tier_counts = lta_df["readiness_tier"].value_counts()
    return {
        "n_total": int(len(lta_df)),
        "n_tier1": int(tier_counts.get("Tier 1 — High", 0)),
        "n_tier2": int(tier_counts.get("Tier 2 — Medium", 0)),
        "n_tier3": int(tier_counts.get("Tier 3 — Low", 0)),
        "is_lad_level_unfiltered": urban_rural != "all",
    }


def build_misc_stats(
    section_id: str,
    region: str,
    region_name: str,
    urban_rural: str,
    policy_df: pd.DataFrame,
    service_levels_df: pd.DataFrame | None,
    service_quality_df: pd.DataFrame | None,
    route_geometries_df: pd.DataFrame | None,
    anomalies_df: pd.DataFrame | None,
    lta_df: pd.DataFrame | None,
) -> dict:
    """Build stats for one of the 9 misc-module sections.

    Args:
        section_id: One of the 9 covered section IDs.
        region: Active region filter ("all" or an ONS region code) — used to
            decide whether to surface "worst region"/"largest region" keys
            (only meaningful at national scope) and to filter route_geometries
            by primary_region for c1/c2.
        region_name: Human-readable region name resolved via REGION_NAMES
            (e.g. "London" for code "E12000007"), or "all". Used to filter
            route_geometries_df.primary_region, which stores full region
            names rather than ONS codes — analogous to how precompute.py
            resolves region_name before filtering policy_df.
        urban_rural: Active area-type filter — unused for value computation
            (kept for signature symmetry with other builders), except for
            bsa3 where it flags an LAD-level "not subdivided" caveat.
        policy_df: lsoa_policy_synthesis rows for the active filter scope.
        service_levels_df: lsoa_service_levels rows for the active scope
            (joined to policy_df via lsoa_cd where needed). Required for
            a5/b3, otherwise None.
        service_quality_df: lsoa_service_quality rows for the active scope.
            Required for b2, otherwise None.
        route_geometries_df: route_geometries rows for the active scope.
            Required for c1/c2, otherwise None.
        anomalies_df: anomalies rows for the active scope. Required for g2,
            otherwise None.
        lta_df: lta_franchising_readiness rows for the active scope. Required
            for bsa3, otherwise None.

    Returns:
        Dict matching the relevant template's contract, or {} when required
        source data is missing/empty.
    """
    if section_id == "a3_walking_distance":
        return _build_walking_distance(policy_df, region)
    if section_id == "a5_service_deserts":
        return _build_service_deserts(policy_df, service_levels_df, region)
    if section_id == "b2_operating_hours":
        return _build_operating_hours(service_quality_df)
    if section_id == "b3_weekend_penalty":
        return _build_weekend_penalty(service_quality_df)
    if section_id == "c1_route_length":
        return _build_distribution_section(route_geometries_df, region, region_name, "length_km", "route length", "km")
    if section_id == "c2_stops_per_route":
        return _build_distribution_section(route_geometries_df, region, region_name, "stop_count", "stops per route", "stops")
    if section_id == "d7_deprivation_urban_rural":
        return _build_deprivation_heatmap(policy_df)
    if section_id == "g2_anomalies":
        return _build_anomalies(anomalies_df)
    if section_id == "bsa3_tier_distribution":
        return _build_tier_distribution(lta_df, urban_rural)
    return {}
