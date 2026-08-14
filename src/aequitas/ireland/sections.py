"""Ireland answers for every England section_id (same / replace / omit)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.ireland.constants import COUNTY_NAME_BY_SLUG, IRELAND_EVENING_NOTE
from aequitas.warehouse.stats_builders.equity import (
    _concentration_index,
    _palma_ratio,
    _population_weighted_gini,
)

# Catalogue actions — keep in sync with docs/guidelines/country-sections.md
SAME = "same"
REPLACE = "replace"
OMIT = "omit"

CATALOGUE: dict[str, str] = {
    "a1_route_density": SAME,
    "a2_stop_density": SAME,
    "a3_walking_distance": SAME,
    "a4_coverage_equity": SAME,
    "a5_service_deserts": SAME,
    "a6_urban_rural_gap": SAME,
    "a7_investment_gap": SAME,
    "a8_coverage_prediction": SAME,
    "b1_frequency": SAME,
    "b2_operating_hours": SAME,
    "b3_weekend_penalty": SAME,
    "b4_route_frequency": SAME,
    "b5_frequency_deprivation": SAME,
    "c1_route_length": SAME,
    "c2_stops_per_route": SAME,
    "c3_operator_hhi": SAME,
    "c4_urban_rural_routes": SAME,
    "c5_length_vs_frequency": SAME,
    "c6_route_archetypes": SAME,
    "c7_network_topology": SAME,
    "d1_coverage_deprivation": SAME,
    "d2_coverage_unemployment": SAME,  # CSO SAPS T8_1_ST + T8_1_LTUT / T8_1_TT
    "d3_coverage_car": SAME,  # CSO SAPS T15_1_NC / T15_1_TC
    "d4_coverage_elderly": SAME,  # CSO SAPS 65+ / T1_1AGETT
    "d5_coverage_income": OMIT,  # HP is relative affluence, not income
    "d6_transport_poverty": SAME,
    "d7_deprivation_urban_rural": SAME,
    "d8_feature_importance": SAME,
    "d9a_health_access": OMIT,
    "d9b_employment_access": OMIT,
    "d9c_crime_access": OMIT,
    "d9d_environment_access": OMIT,
    "d9e_barriers_access": OMIT,
    "f1_gini": SAME,
    "f2_disparity_ratio": SAME,
    "f3_ethnic_access": OMIT,
    "f5_rural_penalty": SAME,
    "f6_equitable_regions": SAME,
    "g1_route_clusters": SAME,
    "g2_anomalies": SAME,
    "g3_coverage_model": SAME,
    "g4_shap": SAME,
    "g5_scenario_model": REPLACE,
    "j1_economic_value": REPLACE,
    "j2_bcr": REPLACE,
    "j3_carbon": REPLACE,
    "j4_investment_priority": REPLACE,
    "bsa1_franchising_readiness": REPLACE,
    "bsa2_operator_concentration": SAME,
    "bsa3_tier_distribution": REPLACE,
    "ps1_freq_restoration": REPLACE,
    "ps2_evening_extension": REPLACE,
    "ps3_drt_rural": REPLACE,
    "ps4_franchise": REPLACE,
    "ps5_scenario_comparison": REPLACE,
}

TITLES: dict[str, str] = {
    "a1_route_density": "Route density by county",
    "a2_stop_density": "Stop density by county",
    "a3_walking_distance": "Population within 400m of a TFI stop",
    "a4_coverage_equity": "Equity of coverage within counties",
    "a5_service_deserts": "Service deserts (people beyond 400 m)",
    "a6_urban_rural_gap": "Urban vs rural coverage gap",
    "a7_investment_gap": "People-gap to national 400 m average",
    "a8_coverage_prediction": "Coverage ~ HP and density",
    "b1_frequency": "Average weekday service quality by county",
    "b2_operating_hours": "Evening service (after 19:00)",
    "b3_weekend_penalty": "Sunday TFI penalty",
    "b4_route_frequency": "Most/least frequent TFI agencies",
    "b5_frequency_deprivation": "Frequency vs Pobal HP 2022",
    "c1_route_length": "Stops-per-route distribution",
    "c2_stops_per_route": "Stops per TFI route",
    "c3_operator_hhi": "TFI operator HHI (0–10,000)",
    "c4_urban_rural_routes": "Urban vs rural stop mass",
    "c5_length_vs_frequency": "Stops per route vs agency share",
    "c6_route_archetypes": "TFI route archetypes",
    "c7_network_topology": "Network topology (TFI)",
    "d1_coverage_deprivation": "Coverage vs Pobal HP 2022",
    "d2_coverage_unemployment": "Coverage vs unemployment",
    "d3_coverage_car": "Coverage vs no-car households",
    "d4_coverage_elderly": "Coverage vs elderly population",
    "d5_coverage_income": "Coverage vs income",
    "d6_transport_poverty": "Transport poverty clusters (HP × service)",
    "d7_deprivation_urban_rural": "HP × urban/rural",
    "d8_feature_importance": "Irish feature importance",
    "d9a_health_access": "Coverage vs health domain",
    "d9b_employment_access": "Coverage vs employment domain",
    "d9c_crime_access": "Service quality vs crime",
    "d9d_environment_access": "Service quality vs living environment",
    "d9e_barriers_access": "Coverage vs housing/services barriers",
    "f1_gini": "Gini of TFI weekday trips per capita",
    "f2_disparity_ratio": "Disparity by Pobal HP decile",
    "f3_ethnic_access": "Bus access by ethnicity",
    "f5_rural_penalty": "Rural accessibility penalty",
    "f6_equitable_regions": "Most equitable counties",
    "g1_route_clusters": "Route clustering",
    "g2_anomalies": "Anomaly detection",
    "g3_coverage_model": "Coverage prediction",
    "g4_shap": "Feature importance (HP + density)",
    "g5_scenario_model": "Irish intervention KPIs",
    "j1_economic_value": "Priority population by county (CAF/PAG scope)",
    "j2_bcr": "CAF/PAG BCR",
    "j3_carbon": "Illustrative carbon (EPA Ireland / SEAI factors)",
    "j4_investment_priority": "County × HP coverage gap",
    "bsa1_franchising_readiness": "NTA programme coverage by county",
    "bsa2_operator_concentration": "TFI operator concentration",
    "bsa3_tier_distribution": "Local Link / BusConnects / Connecting Ireland tiers",
    "ps1_freq_restoration": "Restore TFI / Local Link weekday frequency",
    "ps2_evening_extension": "Evening Local Link / urban TFI",
    "ps3_drt_rural": "Connecting Ireland / rural RTP",
    "ps4_franchise": "Combined Connecting Ireland + BusConnects package",
    "ps5_scenario_comparison": "Irish intervention comparison",
}

# SEAI Energy in Ireland / EPA inventory: petrol car ~164 gCO2/km (tank-to-wheel).
# Used only as a labelled illustration — not a statutory CAF appraisal.
_EPA_CAR_G_PER_KM = 164.0
_EPA_FACTOR_NOTE = (
    "Illustrative only: SEAI/EPA Ireland passenger-car intensity ~164 gCO₂/km. "
    "Not a statutory CAF appraisal."
)


def catalogue_counts() -> dict[str, int]:
    from collections import Counter

    c = Counter(CATALOGUE.values())
    return {"same": c[SAME], "replace": c[REPLACE], "omit": c[OMIT], "answers": len(CATALOGUE)}


def _filter_areas(df: pd.DataFrame, region: str, urban_rural: str) -> pd.DataFrame:
    out = df
    if region and region != "all":
        out = out[out["region"].astype(str) == region]
    if urban_rural and urban_rural != "all":
        out = out[out["urban_rural"].astype(str) == urban_rural]
    return out


def _corr(x: pd.Series, y: pd.Series) -> float | None:
    if len(x) < 3 or float(x.std() or 0) == 0 or float(y.std() or 0) == 0:
        return None
    r = float(x.corr(y))
    return None if r != r else r


def _omit(reason: str) -> dict[str, Any]:
    return {"omit": True, "reason": reason, "insufficient_data": True}


def _county_name(slug: str) -> str:
    return COUNTY_NAME_BY_SLUG.get(str(slug), str(slug).replace("-", " ").title())


def _spr_bins(spr: list[float]) -> list[dict[str, Any]]:
    edges = [0, 5, 10, 20, 40, 80, 10_000]
    labels = ["1–4", "5–9", "10–19", "20–39", "40–79", "80+"]
    counts = [0] * len(labels)
    for raw in spr:
        v = float(raw)
        for i, hi in enumerate(edges[1:]):
            if v < hi:
                counts[i] += 1
                break
    return [{"label": lab, "value": n} for lab, n in zip(labels, counts)]


def _ranking_chart(rows: list[dict[str, Any]], *, title: str = "", x_label: str = "Value") -> dict[str, Any]:
    data = []
    for row in rows:
        label = row.get("label") or row.get("name")
        data.append({"label": label, "value": row["value"]})
    return {"type": "horizontal_bar", "title": title, "x_label": x_label, "data": data}


def _filter_label(region: str, urban_rural: str) -> str:
    place = "the Republic" if region == "all" else _county_name(region)
    if urban_rural == "all":
        return place
    return f"{place}, {urban_rural}"


def _brief(key: str, so_what: str, caveat: str) -> str:
    return f"**Key finding.** {key}\n\n**So what.** {so_what}\n\n**Caveat.** {caveat}"


def _lorenz_payload(areas: pd.DataFrame, gini: float | None, n: int, pop: float) -> dict[str, Any]:
    title = f"Lorenz — TFI weekday trips per capita ({int(pop):,} people, {n:,} Small Areas)"
    if n < 3 or "trips_per_capita" not in areas or "population" not in areas:
        return {"type": "lorenz_curve", "title": title, "gini": gini, "curve_points": []}
    ranked = areas[["trips_per_capita", "population"]].dropna().copy()
    ranked = ranked.sort_values("trips_per_capita")
    w = ranked["population"].to_numpy(dtype=float)
    v = ranked["trips_per_capita"].to_numpy(dtype=float)
    if w.sum() <= 0:
        return {"type": "lorenz_curve", "title": title, "gini": gini, "curve_points": []}
    cum_w = np.cumsum(w)
    cum_vw = np.cumsum(v * w)
    total_w = float(cum_w[-1])
    total_vw = float(cum_vw[-1])
    if total_vw <= 0:
        xs = np.concatenate([[0.0], cum_w / total_w])
        ys = np.zeros_like(xs)
    else:
        xs = np.concatenate([[0.0], cum_w / total_w])
        ys = np.concatenate([[0.0], cum_vw / total_vw])
    step = max(1, len(xs) // 80)
    idx = list(range(0, len(xs), step))
    if idx[-1] != len(xs) - 1:
        idx.append(len(xs) - 1)
    points = [{"cum_pop": float(xs[i]), "cum_service": float(ys[i])} for i in idx]
    return {"type": "lorenz_curve", "title": title, "gini": gini, "curve_points": points}


def _sample_scatter(
    areas: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    x_label: str,
    y_label: str,
    *,
    max_points: int = 800,
) -> dict[str, Any]:
    if x_col not in areas or y_col not in areas or len(areas) < 3:
        return {"type": "scatter_regression", "title": title, "data": []}
    id_col = "sa_code" if "sa_code" in areas.columns else ("lsoa_code" if "lsoa_code" in areas.columns else None)
    cols = [x_col, y_col] + ([id_col] if id_col else [])
    work = areas[cols].copy()
    work[x_col] = pd.to_numeric(work[x_col], errors="coerce")
    work[y_col] = pd.to_numeric(work[y_col], errors="coerce")
    clean = work.dropna()
    if len(clean) < 3:
        return {"type": "scatter_regression", "title": title, "data": []}
    r = float(clean[x_col].corr(clean[y_col]))
    sample = clean.sample(n=min(max_points, len(clean)), random_state=42) if len(clean) > max_points else clean
    slope = intercept = None
    if float(clean[x_col].std() or 0) > 0:
        coef = np.polyfit(clean[x_col].astype(float), clean[y_col].astype(float), 1)
        slope, intercept = float(coef[0]), float(coef[1])
    points = []
    for rec in sample.itertuples(index=False):
        rid = getattr(rec, id_col, "") if id_col else ""
        points.append({"x": float(getattr(rec, x_col)), "y": float(getattr(rec, y_col)), "id": str(rid)})
    out: dict[str, Any] = {
        "type": "scatter_regression",
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "r": None if r != r else r,
        "data": points,
    }
    if slope is not None:
        out["regression_line"] = {"slope": slope, "intercept": intercept}
    return out


def _box_from_values(label: str, values: list[float]) -> dict[str, Any] | None:
    if len(values) < 4:
        return None
    arr = np.array(values, dtype=float)
    return {
        "label": label,
        "min": float(np.min(arr)),
        "q1": float(np.percentile(arr, 25)),
        "median": float(np.median(arr)),
        "q3": float(np.percentile(arr, 75)),
        "max": float(np.max(arr)),
    }


def _hp_urban_matrix(areas: pd.DataFrame) -> list[list[float]]:
    grid: list[list[float]] = []
    if "hp_decile" not in areas or "urban_rural" not in areas:
        return [[0.0, 0.0] for _ in range(10)]
    for d in range(1, 11):
        row = []
        for ur in ("urban", "rural"):
            sub = areas[(areas["hp_decile"] == d) & (areas["urban_rural"] == ur)]
            p = float(sub["population"].sum()) if len(sub) else 0.0
            cov = float(sub.loc[sub["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0
            row.append(cov)
        grid.append(row)
    return grid


def _section_bundle(
    areas: pd.DataFrame,
    all_areas: pd.DataFrame,
    region: str,
    urban_rural: str,
    extras: dict[str, Any],
) -> list[dict[str, Any]]:
    n = len(areas)
    empty = n == 0
    pop = float(areas["population"].sum()) if n else 0.0
    nat_pop = float(all_areas["population"].sum()) if len(all_areas) else 0.0
    covered_pop = float(areas.loc[areas["within_400m"], "population"].sum()) if n else 0.0
    pct_covered = (covered_pop / pop * 100.0) if pop else 0.0
    nat_cov = (
        float(all_areas.loc[all_areas["within_400m"], "population"].sum()) / nat_pop * 100.0
        if nat_pop
        else 0.0
    )
    n_zero = int((~areas["within_400m"]).sum()) if n else 0
    pop_zero = float(areas.loc[~areas["within_400m"], "population"].sum()) if n else 0.0
    mean_sqi = float(areas["sqi"].mean()) if n and "sqi" in areas else 0.0
    n_eve = int(areas["evening_isolated"].sum()) if n and "evening_isolated" in areas else 0
    n_sun = int(areas["sunday_desert"].sum()) if n and "sunday_desert" in areas else 0
    hhi = extras.get("hhi")
    agencies = extras.get("agencies") or []
    spr = extras.get("stops_per_route") or []

    r_hp = None
    if n >= 3 and "hp_relative" in areas and "stops_per_1k" in areas:
        r_hp = _corr(areas["hp_relative"].astype(float), areas["stops_per_1k"].astype(float))
    r_freq = None
    if n >= 3 and "hp_relative" in areas and "sqi" in areas:
        r_freq = _corr(areas["hp_relative"].astype(float), areas["sqi"].astype(float))

    gini = palma = ci = None
    if n >= 3 and "trips_per_capita" in areas:
        slice_df = pd.DataFrame(
            {
                "trips_per_capita": areas["trips_per_capita"].astype(float),
                "population": areas["population"].astype(float),
                "imd_decile": areas["hp_decile"].astype(int) if "hp_decile" in areas else 5,
            }
        )
        try:
            gini = _population_weighted_gini(slice_df["trips_per_capita"], slice_df["population"])
            palma = _palma_ratio(slice_df, "trips_per_capita")
            ci = _concentration_index(slice_df, "trips_per_capita")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ireland Gini failed: {}", exc)

    # County rankings from the unfiltered pack (national view) or this cut.
    src = all_areas if region == "all" else areas
    county_rows = []
    for slug, grp in src.groupby("region"):
        p = float(grp["population"].sum())
        cov = float(grp.loc[grp["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0
        county_rows.append(
            {
                "code": str(slug),
                "name": _county_name(str(slug)),
                "pct_covered": cov,
                "mean_sqi": float(grp["sqi"].mean()) if "sqi" in grp else 0.0,
                "stops": int(grp["stop_count"].sum()) if "stop_count" in grp else 0,
                "pop": p,
                "area_km2": float(grp["area_km2"].sum()) if "area_km2" in grp else 0.0,
                "pop_desert": float(grp.loc[~grp["within_400m"], "population"].sum()),
                "mean_hp": float(grp["hp_relative"].mean()) if "hp_relative" in grp else 0.0,
            }
        )

    def density_rank(key: str) -> list[dict[str, Any]]:
        out = []
        for row in county_rows:
            area = row["area_km2"] or 1.0
            val = (row["stops"] / area) if key == "stops" else (row["stops"] / max(row["pop"], 1) * 1000)
            out.append({"name": row["name"], "value": val, "code": row["code"]})
        return sorted(out, key=lambda x: x["value"], reverse=True)

    # Urban / rural
    ur_stats = {}
    if n and "urban_rural" in areas:
        for label, grp in areas.groupby("urban_rural"):
            p = float(grp["population"].sum())
            ur_stats[str(label)] = {
                "n": int(len(grp)),
                "pop": p,
                "pct_covered": float(grp.loc[grp["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0,
                "mean_sqi": float(grp["sqi"].mean()) if "sqi" in grp else 0.0,
            }

    # HP decile slope
    by_decile = []
    if n and "hp_decile" in areas:
        for d, grp in areas.groupby("hp_decile"):
            p = float(grp["population"].sum())
            cov = float(grp.loc[grp["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0
            desert_pop = float(grp.loc[~grp["within_400m"], "population"].sum()) if p else 0.0
            by_decile.append(
                {
                    "decile": int(d),
                    "pct_covered": cov,
                    "n": int(len(grp)),
                    "pop_desert": desert_pop,
                }
            )

    # Tiers: Dublin urban high coverage → BusConnects; rural served → Connecting Ireland / Local Link; else desert
    def _tier(row) -> str:
        if str(row.region) == "dublin" and row.urban_rural == "urban" and bool(row.within_400m):
            return "BusConnects"
        if bool(row.within_400m) and row.urban_rural == "rural":
            return "Connecting Ireland / Local Link"
        if bool(row.within_400m):
            return "PSO / urban TFI"
        return "Unserved (400 m)"

    tiers = {"BusConnects": 0, "PSO / urban TFI": 0, "Connecting Ireland / Local Link": 0, "Unserved (400 m)": 0}
    if n:
        for rec in areas.itertuples(index=False):
            tiers[_tier(rec)] += 1

    # Scenarios (people, no invented €)
    rural = areas[areas["urban_rural"] == "rural"] if n and "urban_rural" in areas else areas.iloc[0:0]
    low_freq = areas[areas["weekday_trips"] < areas["weekday_trips"].median()] if n else areas.iloc[0:0]
    eve = areas[areas["evening_isolated"]] if n else areas.iloc[0:0]
    rural_desert = rural[~rural["within_400m"]] if len(rural) else rural
    ps1_pop = float(low_freq["population"].sum()) if len(low_freq) else 0.0
    ps2_pop = float(eve["population"].sum()) if len(eve) else 0.0
    ps3_pop = float(rural_desert["population"].sum()) if len(rural_desert) else 0.0
    ps4_pop = float(areas.loc[~areas["within_400m"], "population"].sum()) if n else 0.0

    # Illustrative carbon: desert people × 3 km × 220 days × 164 g / 1e6
    carbon_t = pop_zero * 3.0 * 220.0 * _EPA_CAR_G_PER_KM / 1e6 if pop_zero else 0.0

    has_unemp = n and "unemp_rate" in areas and areas["unemp_rate"].notna().sum() >= 3
    has_car = n and "no_car_share" in areas and areas["no_car_share"].notna().sum() >= 3
    has_elderly = n and "elderly_share" in areas and areas["elderly_share"].notna().sum() >= 3
    r_unemp = (
        _corr(pd.to_numeric(areas["unemp_rate"], errors="coerce"), pd.to_numeric(areas["stops_per_1k"], errors="coerce"))
        if has_unemp and "stops_per_1k" in areas
        else None
    )
    r_car = (
        _corr(pd.to_numeric(areas["no_car_share"], errors="coerce"), pd.to_numeric(areas["stops_per_1k"], errors="coerce"))
        if has_car and "stops_per_1k" in areas
        else None
    )
    r_eld = (
        _corr(pd.to_numeric(areas["elderly_share"], errors="coerce"), pd.to_numeric(areas["stops_per_1k"], errors="coerce"))
        if has_elderly and "stops_per_1k" in areas
        else None
    )
    omit_unemp = _omit("No free CSO SAPS unemployment column joined at Small Area in this pack.")
    omit_car = _omit("No free CSO no-car household share at Small Area in this pack.")
    omit_elderly = _omit("No free CSO elderly share at Small Area in this pack.")
    omit_income = _omit("Pobal HP is a relative affluence index, not household income. No free SA income.")
    omit_health = _omit("Pobal HP 2022 file in this pack has no health domain at Small Area.")
    omit_emp = _omit("Pobal HP 2022 file in this pack has no employment domain at Small Area.")
    omit_crime = _omit("No free Republic Small Area crime series.")
    omit_env = _omit("No free HP living-environment domain at Small Area.")
    omit_barr = _omit("No free HP barriers-to-housing/services domain at Small Area.")
    omit_eth = _omit("No free CSO ethnicity × Small Area table in this pack.")

    empty_note = "No Small Areas match this county / urban-rural cut."
    place = _filter_label(region, urban_rural)
    vintage = "TFI GTFS_All.zip, Pobal HP 2022 (ED join), CSO Small Areas 2022."
    caveat_base = (
        f"{n:,} Small Areas in {place}. {vintage} "
        "Ranks stay inside the Republic (Pobal HP 2022 × TFI)."
    )

    # Per-county urban vs rural coverage (paired exhibit)
    paired_rows: list[dict[str, Any]] = []
    src_ur = src if "urban_rural" in src.columns else src.iloc[0:0]
    if len(src_ur):
        for slug, grp in src_ur.groupby("region"):
            rec: dict[str, Any] = {"name": _county_name(str(slug)), "code": str(slug)}
            for label, sub in grp.groupby("urban_rural"):
                p = float(sub["population"].sum())
                rec[str(label)] = float(sub.loc[sub["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0
            paired_rows.append(rec)

    top_agency_share = None
    top_agency_name = None
    if agencies:
        total_r = sum(float(a.get("n_routes") or 0) for a in agencies) or 1.0
        top = max(agencies, key=lambda a: float(a.get("n_routes") or 0))
        top_agency_name = top.get("name")
        top_agency_share = float(top.get("n_routes") or 0) / total_r * 100.0

    palma_explain = (
        "Palma is 0.000 here because the bottom 40% of people (ranked by weekday trips per capita) "
        "have zero TFI weekday trips — the ratio is undefined as a share, not locked to a seed."
        if palma == 0.0
        else None
    )

    stats_map: dict[str, dict[str, Any]] = {
        "a1_route_density": {
            "national_avg": float(np.mean([r["stops"] / max(r["area_km2"], 1e-6) for r in county_rows])) if county_rows else 0.0,
            "unit": "TFI stops per km²",
            "insufficient_data": empty,
            "n_sas": n,
        },
        "a2_stop_density": {
            "national_avg": float(np.mean([r["stops"] / max(r["pop"], 1) * 1000 for r in county_rows])) if county_rows else 0.0,
            "unit": "stops per 1,000 people",
            "insufficient_data": empty,
        },
        "a3_walking_distance": {
            "pct_covered": pct_covered,
            "n_zero_access": n_zero,
            "pct_zero_access": (n_zero / n * 100.0) if n else 0.0,
            "pop_zero_access": pop_zero,
            "n_sas": n,
            "insufficient_data": empty,
            "entity_type": "small_area",
        },
        "a4_coverage_equity": {
            "gini": gini,
            "n_sas": n,
            "insufficient_data": gini is None,
            "metric": "trips_per_capita (TFI weekday)",
        },
        "a5_service_deserts": {
            "n_desert_sas": n_zero,
            "pop_affected": pop_zero,
            "mean_hp_relative": float(areas.loc[~areas["within_400m"], "hp_relative"].mean()) if n_zero else None,
            "n_sas": n,
            "insufficient_data": empty,
        },
        "a6_urban_rural_gap": {
            "urban": ur_stats.get("urban", {}),
            "rural": ur_stats.get("rural", {}),
            "gap_pp": (
                ur_stats.get("urban", {}).get("pct_covered", 0) - ur_stats.get("rural", {}).get("pct_covered", 0)
            )
            if ur_stats
            else 0.0,
            "insufficient_data": empty,
        },
        "a7_investment_gap": {
            "national_pct_covered": nat_cov,
            "local_pct_covered": pct_covered,
            "people_gap": max(0.0, (nat_cov - pct_covered) / 100.0 * pop),
            "currency": None,
            "note": "People below the Republic 400 m average. No free NTA unit cost applied — not € invented.",
            "insufficient_data": empty,
        },
        "a8_coverage_prediction": {
            "r": r_hp,
            "features": ["hp_relative", "density"],
            "insufficient_data": r_hp is None,
        },
        "b1_frequency": {
            "national_avg": mean_sqi,
            "value": mean_sqi,
            "unit": "SQI (TFI weekday analogue, 0–100)",
            "insufficient_data": empty,
        },
        "b2_operating_hours": {
            "pct_evening_isolated": (n_eve / n * 100.0) if n else 0.0,
            "n_evening_isolated": n_eve,
            "insufficient_data": empty,
        },
        "b3_weekend_penalty": {
            "pct_sunday_deserts": (n_sun / n * 100.0) if n else 0.0,
            "n_sunday_deserts": n_sun,
            "pct_sunday_desert": (n_sun / n * 100.0) if n else 0.0,
            "n_sunday_desert": n_sun,
            "insufficient_data": empty,
        },
        "b4_route_frequency": {
            "agencies": agencies[:12],
            "insufficient_data": not agencies,
        },
        "b5_frequency_deprivation": {
            "r": r_freq,
            "x_label": "Pobal HP relative index 2022",
            "y_label": "SQI (TFI weekday)",
            "insufficient_data": r_freq is None,
        },
        "c1_route_length": {
            "n_routes": extras.get("n_routes"),
            "p50_stops": float(np.median(spr)) if spr else None,
            "insufficient_data": not spr,
            "unit": "stops per route (TFI shapes not required)",
        },
        "c2_stops_per_route": {
            "mean": extras.get("mean_stops_per_route"),
            "n_routes": extras.get("n_routes"),
            "insufficient_data": extras.get("mean_stops_per_route") is None,
        },
        "c3_operator_hhi": {
            "hhi": hhi,
            "scale": "0-10000",
            "n_agencies": extras.get("n_agencies"),
            "top_agency": top_agency_name,
            "top_agency_share_pct": top_agency_share,
            "insufficient_data": hhi is None,
        },
        "c4_urban_rural_routes": {
            "urban_stops": int(areas.loc[areas["urban_rural"] == "urban", "stop_count"].sum()) if n else 0,
            "rural_stops": int(areas.loc[areas["urban_rural"] == "rural", "stop_count"].sum()) if n else 0,
            "insufficient_data": empty,
        },
        "c5_length_vs_frequency": {
            "r": (
                float(areas["stop_count"].corr(areas["sqi"]))
                if n and "stop_count" in areas and "sqi" in areas
                else None
            ),
            "note": "Stops per 1,000 people vs weekday SQI (length/frequency proxy).",
            "insufficient_data": n < 3,
        },
        "c6_route_archetypes": {
            "clusters": [
                {"name": "Urban frequent", "n": int((areas["urban_rural"] == "urban").sum()) if n else 0},
                {"name": "Rural sparse", "n": int((areas["urban_rural"] == "rural").sum()) if n else 0},
            ],
            "insufficient_data": empty,
        },
        "c7_network_topology": {
            "n_agencies": extras.get("n_agencies"),
            "n_routes": extras.get("n_routes"),
            "n_sas": n,
            "insufficient_data": extras.get("n_routes") is None,
        },
        "d1_coverage_deprivation": {
            "r": r_hp,
            "x_label": "Pobal HP relative index 2022",
            "y_label": "Stops per 1,000 people",
            "insufficient_data": empty or r_hp is None,
        },
        "d2_coverage_unemployment": (
            omit_unemp
            if not has_unemp
            else {
                "r": r_unemp,
                "x_label": "CSO SAPS unemployment share (ST+LTU / Theme 8)",
                "y_label": "Stops per 1,000 people",
                "insufficient_data": r_unemp is None,
            }
        ),
        "d3_coverage_car": (
            omit_car
            if not has_car
            else {
                "r": r_car,
                "x_label": "CSO SAPS no-car household share (T15_1_NC)",
                "y_label": "Stops per 1,000 people",
                "insufficient_data": r_car is None,
            }
        ),
        "d4_coverage_elderly": (
            omit_elderly
            if not has_elderly
            else {
                "r": r_eld,
                "x_label": "CSO SAPS share aged 65+ (T1)",
                "y_label": "Stops per 1,000 people",
                "insufficient_data": r_eld is None,
            }
        ),
        "d5_coverage_income": omit_income,
        "d6_transport_poverty": {
            "method": "HP decile 1–3 and not within 400 m",
            "n_sas": int(((areas["hp_decile"] <= 3) & (~areas["within_400m"])).sum()) if n else 0,
            "population": float(areas.loc[(areas["hp_decile"] <= 3) & (~areas["within_400m"]), "population"].sum())
            if n
            else 0.0,
            "insufficient_data": empty,
        },
        "d7_deprivation_urban_rural": {
            "cells": ur_stats,
            "index": "Pobal HP 2022",
            "insufficient_data": empty,
        },
        "d8_feature_importance": {
            "features": [
                {"name": "hp_relative", "r": r_hp},
                {"name": "urban", "note": "density rule ≥150 people/km²"},
            ],
            "insufficient_data": r_hp is None,
        },
        "d9a_health_access": omit_health,
        "d9b_employment_access": omit_emp,
        "d9c_crime_access": omit_crime,
        "d9d_environment_access": omit_env,
        "d9e_barriers_access": omit_barr,
        "f1_gini": {
            "gini": gini,
            "palma": palma,
            "concentration_index": ci,
            "n_sas": n,
            "insufficient_data": gini is None,
            "metric": "trips_per_capita (TFI weekday)",
            "palma_note": (
                "Palma is 0.000 because the poorest 40% of people (by trips per capita) "
                "have zero weekday TFI trips in this cut — not a seed lock."
                if palma == 0.0
                else None
            ),
        },
        "f2_disparity_ratio": {
            "by_decile": by_decile,
            "index": "Pobal HP 2022",
            "ratio": (
                (by_decile[-1]["pct_covered"] / by_decile[0]["pct_covered"])
                if len(by_decile) >= 2 and by_decile[0]["pct_covered"]
                else None
            ),
            "insufficient_data": empty,
        },
        "f3_ethnic_access": omit_eth,
        "f5_rural_penalty": {
            "urban": ur_stats.get("urban", {}),
            "rural": ur_stats.get("rural", {}),
            "penalty_pp": (
                ur_stats.get("urban", {}).get("pct_covered", 0) - ur_stats.get("rural", {}).get("pct_covered", 0)
            )
            if ur_stats
            else 0.0,
            "insufficient_data": empty,
        },
        "f6_equitable_regions": {
            "ranking": sorted(county_rows, key=lambda r: r["pct_covered"], reverse=True)[:10],
            "insufficient_data": not county_rows,
        },
        "g1_route_clusters": {
            "n_clusters": 2,
            "labels": ["urban frequent", "rural sparse"],
            "insufficient_data": empty,
        },
        "g2_anomalies": {
            "n_flagged": int(((areas["within_400m"]) & (areas["hp_decile"] <= 2) & (areas["sqi"] < 20)).sum())
            if n
            else 0,
            "rule": "HP decile ≤2, a stop nearby, SQI < 20",
            "insufficient_data": empty,
        },
        "g3_coverage_model": {
            "r": r_hp,
            "insufficient_data": r_hp is None,
        },
        "g4_shap": {
            "features": [{"name": "hp_relative", "r": r_hp}, {"name": "density_rule", "r": None}],
            "insufficient_data": r_hp is None,
        },
        "g5_scenario_model": {
            "points_at": ["ps1_freq_restoration", "ps2_evening_extension", "ps3_drt_rural", "ps4_franchise"],
            "insufficient_data": empty,
        },
        "j1_economic_value": {
            "unit": "people beyond 400 m (CAF/PAG scope — no € without a cited NTA unit cost)",
            "by_county": [{"name": r["name"], "value": r["pop_desert"]} for r in county_rows],
            "national": pop_zero,
            "insufficient_data": empty,
        },
        "j2_bcr": {
            "bcr": None,
            "omit_euro": True,
            "reason": "No free published CAF/PAG unit cost applied. People-gap only.",
            "people_gap": pop_zero,
            "insufficient_data": False,
        },
        "j3_carbon": {
            "co2_saving_tonnes": carbon_t,
            "factor_g_per_km": _EPA_CAR_G_PER_KM,
            "note": _EPA_FACTOR_NOTE,
            "insufficient_data": empty,
        },
        "j4_investment_priority": {
            "ranking": sorted(county_rows, key=lambda r: (r["pop_desert"], -r["mean_hp"]), reverse=True)[:12],
            "insufficient_data": not county_rows,
        },
        "bsa1_franchising_readiness": {
            "national_avg": pct_covered,
            "unit": "% people within 400 m (NTA programme coverage proxy)",
            "programme": "Connecting Ireland, BusConnects, Local Link, PSO",
            "insufficient_data": empty,
        },
        "bsa2_operator_concentration": {
            "hhi": hhi,
            "scale": "0-10000",
            "same_as": "c3_operator_hhi",
            "insufficient_data": hhi is None,
        },
        "bsa3_tier_distribution": {
            "tiers": tiers,
            "insufficient_data": empty,
        },
        "ps1_freq_restoration": {
            "scenario": {"population_affected": ps1_pop, "who": "SAs below median weekday TFI trips"},
            "euro": None,
            "insufficient_data": empty,
        },
        "ps2_evening_extension": {
            "scenario": {"population_affected": ps2_pop, "who": "SAs with no TFI departure after 19:00"},
            "euro": None,
            "insufficient_data": empty,
        },
        "ps3_drt_rural": {
            "scenario": {"population_affected": ps3_pop, "who": "Rural SAs beyond 400 m (Connecting Ireland / RTP)"},
            "euro": None,
            "insufficient_data": empty or urban_rural == "urban",
        },
        "ps4_franchise": {
            "scenario": {
                "population_affected": ps4_pop,
                "who": "Combined Connecting Ireland + BusConnects people beyond 400 m",
            },
            "euro": None,
            "note": "Combined Connecting Ireland + BusConnects package.",
            "insufficient_data": empty,
        },
        "ps5_scenario_comparison": {
            "rows": [
                {"id": "ps1", "title": TITLES["ps1_freq_restoration"], "people": ps1_pop},
                {"id": "ps2", "title": TITLES["ps2_evening_extension"], "people": ps2_pop},
                {"id": "ps3", "title": TITLES["ps3_drt_rural"], "people": ps3_pop},
                {"id": "ps4", "title": TITLES["ps4_franchise"], "people": ps4_pop},
            ],
            "insufficient_data": empty,
        },
    }

    if empty:
        stats_map["a3_walking_distance"]["empty_reason"] = empty_note

    narratives: dict[str, str] = {}
    for sid, action in CATALOGUE.items():
        if action == OMIT or stats_map[sid].get("omit"):
            narratives[sid] = stats_map[sid].get("reason") or empty_note
        elif empty and sid not in ("j2_bcr",):
            narratives[sid] = empty_note

    if not empty:
        gap_pp = stats_map["a6_urban_rural_gap"]["gap_pp"]
        people_gap = stats_map["a7_investment_gap"]["people_gap"]
        eve_pct = stats_map["b2_operating_hours"]["pct_evening_isolated"]
        sun_pct = stats_map["b3_weekend_penalty"]["pct_sunday_deserts"]
        gini_txt = f"{gini:.3f}" if gini is not None else "not computed"
        r_hp_txt = f"{r_hp:.3f}" if r_hp is not None else "n/a"
        r_freq_txt = f"{r_freq:.3f}" if r_freq is not None else "n/a"
        narratives.update(
            {
                "a1_route_density": _brief(
                    f"TFI stop density varies by county in {place}.",
                    "County ranks show where physical stop mass is concentrated, not how many people can walk to a stop.",
                    caveat_base,
                ),
                "a2_stop_density": _brief(
                    f"Stops per 1,000 people in {place} re-ranks counties versus area density.",
                    "A dense stop field on a map can still leave people behind if it sits away from population.",
                    f"{caveat_base} Deprivation is Pobal HP 2022.",
                ),
                "a3_walking_distance": _brief(
                    f"{pct_covered:.1f}% of people in {place} live within 400 m of a TFI stop "
                    f"({int(covered_pop):,} in, {int(pop_zero):,} out).",
                    "This is the people count behind the 400 m access door — not another county ranking.",
                    caveat_base,
                ),
                "a4_coverage_equity": _brief(
                    f"Gini of TFI weekday trips per capita in {place} is {gini_txt}.",
                    "The Lorenz is people-weighted trips per capita — not a 26-county bar.",
                    caveat_base,
                ),
                "a5_service_deserts": _brief(
                    f"{int(pop_zero):,} people in {n_zero:,} Small Areas in {place} live beyond 400 m of a TFI stop.",
                    "The map is people, not a count of empty polygons.",
                    caveat_base,
                ),
                "a6_urban_rural_gap": _brief(
                    f"In {place} the urban–rural 400 m gap is {gap_pp:.1f} percentage points.",
                    "Each county is a pair of urban and rural coverage — not a third ranking bar.",
                    f"{caveat_base} Urban/rural is the ≥150 people/km² density rule.",
                ),
                "a7_investment_gap": _brief(
                    f"{people_gap:,.0f} people in {place} sit below the Republic 400 m average.",
                    "People-gap only: no free NTA/CAF unit cost, so no invented euro.",
                    caveat_base,
                ),
                "a8_coverage_prediction": _brief(
                    f"HP relative vs stops per 1,000 in {place}: r = {r_hp_txt}.",
                    "This is an association, not a causal coverage model.",
                    caveat_base,
                ),
                "b1_frequency": _brief(
                    f"Mean weekday service-quality analogue in {place} is {mean_sqi:.1f} / 100.",
                    "The box is the weekday SQI distribution — not evening or Sunday.",
                    f"{caveat_base} Built from TFI stop_times.",
                ),
                "b2_operating_hours": _brief(
                    f"{eve_pct:.1f}% of Small Areas in {place} have no departure after 19:00 "
                    f"({n_eve:,} SAs).",
                    "Evening isolation is a clock-time question, distinct from weekday frequency.",
                    f"{caveat_base} {IRELAND_EVENING_NOTE}",
                ),
                "b3_weekend_penalty": _brief(
                    f"{sun_pct:.1f}% of Small Areas in {place} have no Sunday TFI trip ({n_sun:,} SAs).",
                    "Sunday is the weekend penalty — not a third county ranking of weekday SQI.",
                    caveat_base,
                ),
                "b4_route_frequency": _brief(
                    f"TFI agencies ranked by route count for {place}.",
                    "This is agency route mass, not operator HHI.",
                    f"{caveat_base} Agency names come from TFI agency.txt.",
                ),
                "b5_frequency_deprivation": _brief(
                    f"Pobal HP 2022 vs weekday SQI in {place}: r = {r_freq_txt}.",
                    "The scatter asks whether poorer Small Areas get thinner weekday service.",
                    caveat_base,
                ),
                "c1_route_length": _brief(
                    f"Stops-per-route distribution for TFI in {place} (median {extras.get('p50_stops') or stats_map['c1_route_length'].get('p50_stops')}).",
                    "Length is a stop-count proxy because TFI shapes are not required.",
                    caveat_base,
                ),
                "c2_stops_per_route": _brief(
                    f"Mean stops per TFI route is {extras.get('mean_stops_per_route')} in this pack.",
                    "The box is the route-stop distribution — not a tile of the mean.",
                    caveat_base,
                ),
                "c3_operator_hhi": _brief(
                    (
                        f"TFI operator HHI is {hhi:.0f} / 10,000"
                        + (f"; {top_agency_name} has {top_agency_share:.1f}% of routes." if top_agency_share is not None else ".")
                    )
                    if hhi is not None
                    else "HHI needs agency.txt in TFI.",
                    "One 0–10,000 concentration exhibit — not routes-per-agency labelled as HHI.",
                    caveat_base,
                ),
                "c4_urban_rural_routes": _brief(
                    f"Stop mass in {place} splits urban vs rural under the density rule.",
                    "This is infrastructure location, not 400 m people coverage.",
                    caveat_base,
                ),
                "c5_length_vs_frequency": _brief(
                    f"Stop mass vs weekday SQI in {place}: r = {r_freq_txt}.",
                    "Stops per 1,000 is the length/mass proxy; SQI is weekday frequency.",
                    caveat_base,
                ),
                "c6_route_archetypes": _brief(
                    "Two archetypes: urban frequent vs rural sparse (density rule).",
                    "Clusters are Irish TFI inputs (urban frequent vs rural sparse).",
                    caveat_base,
                ),
                "c7_network_topology": _brief(
                    f"TFI network: {extras.get('n_routes')} routes, {extras.get('n_agencies')} agencies in {place}.",
                    "Agency route mass is the topology exhibit — not a tile of three counts.",
                    caveat_base,
                ),
                "d1_coverage_deprivation": _brief(
                    f"Pobal HP 2022 vs stops per 1,000 in {place}: r = {r_hp_txt}.",
                    f"A weak HP–stop mass link in {place} means disadvantaged Small Areas are not systematically starved of nearby TFI stops.",
                    caveat_base,
                ),
                **(
                    {
                        "d2_coverage_unemployment": _brief(
                            f"CSO SAPS unemployment (short + long term) vs stops per 1,000 in {place}: r = {r_unemp:.3f}."
                            if r_unemp is not None
                            else f"Unemployment share vs stop mass in {place} is not identified.",
                            f"SAPS Theme 8 in {place} — not an IMD employment domain.",
                            caveat_base,
                        )
                    }
                    if has_unemp
                    else {}
                ),
                **(
                    {
                        "d3_coverage_car": _brief(
                            f"CSO no-car household share vs stops per 1,000 in {place}: r = {r_car:.3f}."
                            if r_car is not None
                            else f"No-car share vs stop mass in {place} is not identified.",
                            f"T15_1_NC / T15_1_TC in {place}. Households without a car are the demand-side counterpart to 400 m TFI.",
                            caveat_base,
                        )
                    }
                    if has_car
                    else {}
                ),
                **(
                    {
                        "d4_coverage_elderly": _brief(
                            f"CSO share aged 65+ vs stops per 1,000 in {place}: r = {r_eld:.3f}."
                            if r_eld is not None
                            else f"65+ share vs stop mass in {place} is not identified.",
                            f"Age 65+ from T1 in {place} — not an England older-people domain.",
                            caveat_base,
                        )
                    }
                    if has_elderly
                    else {}
                ),
                "d6_transport_poverty": _brief(
                    f"{stats_map['d6_transport_poverty']['n_sas']:,} Small Areas in {place} are HP deciles 1–3 and beyond 400 m "
                    f"({int(stats_map['d6_transport_poverty']['population']):,} people).",
                    "Transport-poverty cluster, Republic only.",
                    caveat_base,
                ),
                "d7_deprivation_urban_rural": _brief(
                    (
                        f"In {place}, urban 400 m coverage is {ur_stats.get('urban', {}).get('pct_covered', 0):.1f}% "
                        f"({int(ur_stats.get('urban', {}).get('pop') or 0):,} people) vs "
                        f"rural {ur_stats.get('rural', {}).get('pct_covered', 0):.1f}% "
                        f"({int(ur_stats.get('rural', {}).get('pop') or 0):,} people), crossed with Pobal HP 2022."
                    ),
                    f"Where HP disadvantage and rural density stack in {place}, walk-to-stop coverage is thinner — a Local Link / Connecting Ireland hole, not a missing matrix.",
                    caveat_base,
                ),
                "d8_feature_importance": _brief(
                    f"In {place}, HP relative vs stops per 1,000 has r = {r_hp_txt} (density class is the other Irish feature).",
                    f"Coverage in {place} tracks density and Pobal HP together — not a second scatter of the same r.",
                    caveat_base,
                ),
                "f1_gini": _brief(
                    f"Gini of TFI weekday trips per capita in {place} is {gini_txt} "
                    f"({int(pop):,} people).",
                    palma_explain
                    or "One Lorenz curve for this question. Palma and CI sit in the chips.",
                    caveat_base,
                ),
                "f2_disparity_ratio": _brief(
                    (
                        f"HP 2022 decile slope of 400 m coverage in {place}"
                        + (
                            f": decile 1 {by_decile[0]['pct_covered']:.1f}% vs decile 10 {by_decile[-1]['pct_covered']:.1f}%."
                            if len(by_decile) >= 2
                            else "."
                        )
                    ),
                    f"People-weighted 400 m coverage by HP decile in {place} is the equity slope — who can walk to TFI.",
                    caveat_base,
                ),
                "f5_rural_penalty": _brief(
                    f"Rural 400 m coverage in {place} trails urban by {stats_map['f5_rural_penalty']['penalty_pp']:.1f} pp.",
                    "Paired county dots, distinct from the Access urban–rural scatter.",
                    caveat_base,
                ),
                "f6_equitable_regions": _brief(
                    f"Counties ranked by 400 m coverage for {place} (in-country ranks only).",
                    "This is the equity ranking question — not Gini and not the HP slope.",
                    caveat_base,
                ),
                "g1_route_clusters": _brief(
                    "Two-cluster method on Irish urban/rural service.",
                    "Appendix to Correlations.",
                    caveat_base,
                ),
                "g2_anomalies": _brief(
                    f"{stats_map['g2_anomalies']['n_flagged']:,} Small Areas in {place} are HP ≤2, near a stop, SQI < 20.",
                    "A nearby stop with thin weekday service is a different hole from a desert.",
                    caveat_base,
                ),
                "g3_coverage_model": _brief(
                    f"Coverage association in {place}: r = {r_hp_txt}.",
                    "Same Irish features as a8; shown as a KPI, not a third scatter.",
                    caveat_base,
                ),
                "g4_shap": _brief(
                    "HP + density — Irish features.",
                    "Irish features only.",
                    caveat_base,
                ),
                "g5_scenario_model": _brief(
                    f"KPIs for {place} point at the Irish intervention list.",
                    "Combined Connecting Ireland + BusConnects — people only.",
                    caveat_base,
                ),
                "j1_economic_value": _brief(
                    f"{int(pop_zero):,} people in {place} live beyond 400 m.",
                    "CAF/PAG scope. People only — no invented euro.",
                    caveat_base,
                ),
                "j2_bcr": _brief(
                    f"No free published CAF/PAG BCR for {place}. People-gap is {int(pop_zero):,}.",
                    "People-gap only — no invented euro BCR.",
                    caveat_base,
                ),
                "j3_carbon": _brief(
                    f"{carbon_t:,.0f} t illustrative car-km CO₂ in {place} if desert residents drove 3 km × 220 days.",
                    _EPA_FACTOR_NOTE,
                    caveat_base,
                ),
                "j4_investment_priority": _brief(
                    f"Counties ranked by people beyond 400 m and HP disadvantage ({place}).",
                    "Priority is a people-gap, not a BCR.",
                    caveat_base,
                ),
                "bsa1_franchising_readiness": _brief(
                    f"NTA programme coverage proxy in {place}: {pct_covered:.1f}% of people within 400 m.",
                    "Connecting Ireland, BusConnects, Local Link, and PSO are the Republic programmes this filter can see.",
                    caveat_base,
                ),
                "bsa2_operator_concentration": _brief(
                    f"Same TFI HHI as Network: {hhi:.0f} / 10,000." if hhi is not None else "HHI unavailable.",
                    "Hidden on the Policy door so HHI is not shown twice.",
                    caveat_base,
                ),
                "bsa3_tier_distribution": _brief(
                    f"Programme tiers in {place}: BusConnects, PSO urban TFI, Connecting Ireland / Local Link, unserved.",
                    "Tiers are Irish programmes (BusConnects / PSO / Local Link / unserved).",
                    caveat_base,
                ),
                "ps1_freq_restoration": _brief(
                    f"{int(ps1_pop):,} people in {place} live in Small Areas below median weekday TFI trips.",
                    "Restore TFI / Local Link weekday frequency — people only.",
                    caveat_base,
                ),
                "ps2_evening_extension": _brief(
                    f"{int(ps2_pop):,} people in {place} live in Small Areas with no TFI departure after 19:00.",
                    "Evening Local Link / urban TFI — not the weekday-frequency card.",
                    caveat_base,
                ),
                "ps3_drt_rural": _brief(
                    f"{int(ps3_pop):,} people in rural Small Areas of {place} are beyond 400 m.",
                    "Connecting Ireland / rural RTP. Hidden on an urban-only filter.",
                    caveat_base,
                ),
                "ps4_franchise": _brief(
                    f"{int(ps4_pop):,} people in {place} live beyond 400 m — combined Connecting Ireland + BusConnects.",
                    "Combined Connecting Ireland + BusConnects on people and HP, not a euro BCR.",
                    caveat_base,
                ),
                "ps5_scenario_comparison": _brief(
                    f"Four Irish interventions compared on people in {place}.",
                    "No invented euro. Rows are TFI / Local Link / Connecting Ireland / BusConnects.",
                    caveat_base,
                ),
            }
        )

    sqi_box = _box_from_values("Weekday SQI", areas["sqi"].astype(float).tolist()) if n and "sqi" in areas else None
    spr_box = _box_from_values("Stops per route", [float(x) for x in spr]) if spr else None
    omit_ids = {sid for sid, action in CATALOGUE.items() if action == OMIT}

    charts: dict[str, dict[str, Any]] = {}
    if empty:
        for sid in CATALOGUE:
            charts[sid] = {}
    else:
        charts = {
            "a1_route_density": _ranking_chart(
                density_rank("area"),
                title=f"TFI stops per km² — {place}",
                x_label="Stops per km²",
            ),
            "a2_stop_density": _ranking_chart(
                density_rank("stops"),
                title=f"TFI stops per 1,000 people — {place}",
                x_label="Stops per 1,000 people",
            ),
            "a3_walking_distance": {
                "type": "stacked_bar",
                "title": f"People in/out of 400 m — {place}",
                "x_label": "People",
                "data": [
                    {"label": place, "group": "Within 400 m", "value": covered_pop},
                    {"label": place, "group": "Beyond 400 m", "value": pop_zero},
                ],
            },
            "a4_coverage_equity": _lorenz_payload(areas, gini, n, pop),
            "a5_service_deserts": {
                "type": "choropleth",
                "geography": "ireland_county",
                "title": f"People beyond 400 m of a TFI stop — {place}",
                "metric_label": "People",
                "data": [
                    {
                        "area_code": r["code"],
                        "area_name": r["name"],
                        "value": r["pop_desert"],
                    }
                    for r in county_rows
                ],
            },
            "a6_urban_rural_gap": {
                "type": "scatter_regression",
                "title": f"Urban vs rural 400 m coverage by county — {place}",
                "x_label": "Urban % within 400 m",
                "y_label": "Rural % within 400 m",
                "data": [
                    {
                        "x": float(r.get("urban") or 0),
                        "y": float(r.get("rural") or 0),
                        "id": r["name"],
                    }
                    for r in paired_rows
                    if "urban" in r or "rural" in r
                ],
            },
            "a7_investment_gap": _ranking_chart(
                [
                    {
                        "label": r["name"],
                        "value": max(0.0, (nat_cov - r["pct_covered"]) / 100.0 * r["pop"]),
                    }
                    for r in sorted(county_rows, key=lambda x: -max(0.0, (nat_cov - x["pct_covered"]) / 100.0 * x["pop"]))
                ],
                title=f"People below Republic 400 m average — {place}",
                x_label="People",
            ),
            "a8_coverage_prediction": {
                "type": "shap_bar",
                "title": f"Irish features (HP + density) — {place}",
                "features": [
                    {"name": "Pobal HP relative 2022", "importance": abs(r_hp) if r_hp is not None else 0.0},
                    {"name": "Density class (≥150/km²)", "importance": 0.5},
                ],
            },
            "b1_frequency": {
                "type": "box_violin",
                "title": f"Weekday SQI distribution — {place}",
                "groups": [sqi_box] if sqi_box else [],
            },
            "b2_operating_hours": {
                "type": "stacked_bar",
                "title": f"Evening isolation (after 19:00) — {place}",
                "x_label": "Small Areas",
                "data": [
                    {"label": "Evening", "group": "Isolated", "value": n_eve},
                    {"label": "Evening", "group": "Has a departure after 19:00", "value": max(n - n_eve, 0)},
                ],
            },
            "b3_weekend_penalty": {
                "type": "stacked_bar",
                "title": f"Sunday TFI desert — {place}",
                "x_label": "Small Areas",
                "data": [
                    {"label": "Sunday", "group": "No Sunday trip", "value": n_sun},
                    {"label": "Sunday", "group": "Has a Sunday trip", "value": max(n - n_sun, 0)},
                ],
            },
            "b4_route_frequency": _ranking_chart(
                [{"label": a.get("name"), "value": a.get("n_routes") or 0} for a in agencies[:15]],
                title=f"TFI agencies by route count — {place}",
                x_label="Routes",
            ),
            "b5_frequency_deprivation": _sample_scatter(
                areas,
                "hp_relative",
                "sqi",
                f"HP 2022 vs weekday SQI — {place}",
                "Pobal HP relative index 2022",
                "SQI (TFI weekday)",
            ),
            "c1_route_length": (
                {
                    "type": "horizontal_bar",
                    "title": f"Stops-per-route bins (TFI) — {place}",
                    "x_label": "Routes",
                    "data": _spr_bins(spr),
                }
                if spr
                else {
                    "type": "horizontal_bar",
                    "title": f"Stops-per-route bins (TFI) — {place} (list not persisted)",
                    "x_label": "Routes",
                    "data": [],
                }
            ),
            "c2_stops_per_route": {
                "type": "box_violin",
                "title": f"Stops per TFI route — {place}",
                "groups": [spr_box] if spr_box else [],
            },
            "c3_operator_hhi": {
                "type": "gauge",
                "title": f"TFI operator HHI (0–10,000) — {place}",
                "value": hhi,
                "min": 0,
                "max": 10000,
                "unit": "/ 10,000",
                "bands": [
                    {"label": "Low", "min": 0.0, "max": 1500.0, "color_hint": "green"},
                    {"label": "Moderate", "min": 1500.0, "max": 2500.0, "color_hint": "yellow"},
                    {"label": "High", "min": 2500.0, "max": None, "color_hint": "red"},
                ],
                "markers": (
                    [{"label": f"{top_agency_name} {top_agency_share:.1f}% of routes", "value": hhi}]
                    if hhi is not None and top_agency_share is not None
                    else []
                ),
            },
            "c4_urban_rural_routes": {
                "type": "stacked_bar",
                "title": f"Stop mass urban vs rural — {place}",
                "x_label": "Stops",
                "data": [
                    {"label": "Stops", "group": "Urban", "value": stats_map["c4_urban_rural_routes"]["urban_stops"]},
                    {"label": "Stops", "group": "Rural", "value": stats_map["c4_urban_rural_routes"]["rural_stops"]},
                ],
            },
            "c5_length_vs_frequency": _sample_scatter(
                areas,
                "stops_per_1k",
                "sqi",
                f"Stop mass vs weekday SQI — {place}",
                "Stops per 1,000 people",
                "SQI (TFI weekday)",
            ),
            "c6_route_archetypes": {
                "type": "scatter_clusters",
                "title": f"TFI archetypes — {place}",
                "x_label": "Stops per 1,000",
                "y_label": "Weekday SQI",
                "scatter_suppressed": True,
                "cluster_sizes": [
                    {"label": "Urban frequent", "n": int((areas["urban_rural"] == "urban").sum()) if n else 0},
                    {"label": "Rural sparse", "n": int((areas["urban_rural"] == "rural").sum()) if n else 0},
                ],
            },
            "c7_network_topology": _ranking_chart(
                [{"label": a.get("name"), "value": a.get("n_routes") or 0} for a in agencies[:15]],
                title=f"TFI agencies by route count (topology mass) — {place}",
                x_label="Routes",
            ),
            "d1_coverage_deprivation": _sample_scatter(
                areas,
                "hp_relative",
                "stops_per_1k",
                f"Pobal HP 2022 vs stops per 1,000 — {place}",
                "Pobal HP relative index 2022",
                "Stops per 1,000 people",
            ),
            **(
                {
                    "d2_coverage_unemployment": _sample_scatter(
                        areas,
                        "unemp_rate",
                        "stops_per_1k",
                        f"CSO unemployment vs TFI stop mass — {place}",
                        "SAPS unemployment share (ST+LTU)",
                        "Stops per 1,000 people",
                    )
                }
                if has_unemp
                else {}
            ),
            **(
                {
                    "d3_coverage_car": _sample_scatter(
                        areas,
                        "no_car_share",
                        "stops_per_1k",
                        f"CSO no-car households vs TFI stop mass — {place}",
                        "SAPS no-car household share",
                        "Stops per 1,000 people",
                    )
                }
                if has_car
                else {}
            ),
            **(
                {
                    "d4_coverage_elderly": _sample_scatter(
                        areas,
                        "elderly_share",
                        "stops_per_1k",
                        f"CSO 65+ share vs TFI stop mass — {place}",
                        "SAPS share aged 65+",
                        "Stops per 1,000 people",
                    )
                }
                if has_elderly
                else {}
            ),
            "d6_transport_poverty": {
                "type": "scatter_clusters",
                "title": f"Transport-poverty cluster — {place}",
                "x_label": "HP relative",
                "y_label": "Stops per 1,000",
                "scatter_suppressed": True,
                "cluster_sizes": [
                    {
                        "label": "HP 1–3 beyond 400 m",
                        "n": int(stats_map["d6_transport_poverty"]["n_sas"]),
                    },
                    {"label": "Other Small Areas", "n": max(n - int(stats_map["d6_transport_poverty"]["n_sas"]), 0)},
                ],
            },
            "d7_deprivation_urban_rural": {
                "type": "heatmap",
                "title": f"HP decile × urban/rural coverage % — {place}",
                "x_labels": ["urban", "rural"],
                "y_labels": [f"HP {d}" for d in range(1, 11)],
                "values": _hp_urban_matrix(areas),
            },
            "d8_feature_importance": {
                "type": "shap_bar",
                "title": "Irish feature importance",
                "features": [
                    {"name": "hp_relative", "importance": abs(r_hp) if r_hp is not None else 0.0},
                    {"name": "density_rule", "importance": 0.4},
                ],
            },
            "f1_gini": _lorenz_payload(areas, gini, n, pop),
            "f2_disparity_ratio": {
                "type": "scatter_regression",
                "title": f"HP decile slope of 400 m coverage — {place}",
                "x_label": "Pobal HP decile (1 = most disadvantaged)",
                "y_label": "% people within 400 m",
                "data": [
                    {"x": d["decile"], "y": d["pct_covered"], "id": f"HP {d['decile']}"}
                    for d in by_decile
                ],
            },
            "f5_rural_penalty": {
                "type": "grouped_bar",
                "title": f"Urban vs rural 400 m by county — {place}",
                "x_label": "% people within 400 m",
                "data": [
                    item
                    for r in paired_rows
                    for item in (
                        {"label": r["name"], "group": "Urban", "value": float(r.get("urban") or 0)},
                        {"label": r["name"], "group": "Rural", "value": float(r.get("rural") or 0)},
                    )
                ],
            },
            "f6_equitable_regions": _ranking_chart(
                [{"label": r["name"], "value": r["pct_covered"]} for r in stats_map["f6_equitable_regions"]["ranking"]],
                title=f"Most equitable counties (400 m) — {place}",
                x_label="% people within 400 m",
            ),
            "g1_route_clusters": {
                "type": "scatter_clusters",
                "title": "Urban frequent vs rural sparse",
                "scatter_suppressed": True,
                "cluster_sizes": [
                    {"label": "urban frequent", "n": int((areas["urban_rural"] == "urban").sum()) if n else 0},
                    {"label": "rural sparse", "n": int((areas["urban_rural"] == "rural").sum()) if n else 0},
                ],
            },
            "g2_anomalies": _sample_scatter(
                areas,
                "hp_relative",
                "sqi",
                f"Anomaly scan (HP vs SQI) — {place}",
                "Pobal HP relative",
                "SQI",
            )
            if n
            else {},
            "g3_coverage_model": _sample_scatter(
                areas,
                "hp_relative",
                "stops_per_1k",
                f"Coverage model — HP vs stop mass — {place}",
                "Pobal HP relative 2022",
                "Stops per 1,000 people",
            ),
            "g4_shap": {
                "type": "shap_bar",
                "title": "HP + density",
                "features": [
                    {"name": "hp_relative", "importance": abs(r_hp) if r_hp is not None else 0.0},
                    {"name": "density_rule", "importance": 0.4},
                ],
            },
            "g5_scenario_model": {
                "type": "kpi_tiles",
                "title": "Irish intervention people",
                "tiles": [
                    {"label": "Below-median weekday trips", "value": ps1_pop, "unit": "people"},
                    {"label": "No evening after 19:00", "value": ps2_pop, "unit": "people"},
                    {"label": "Rural beyond 400 m", "value": ps3_pop, "unit": "people"},
                    {"label": "Combined beyond 400 m", "value": ps4_pop, "unit": "people"},
                ],
            },
            "j1_economic_value": _ranking_chart(
                [
                    {"label": r["name"], "value": r["pop_desert"]}
                    for r in sorted(county_rows, key=lambda x: -x["pop_desert"])
                ],
                title=f"People beyond 400 m by county — {place}",
                x_label="People",
            ),
            "j2_bcr": {
                "type": "horizontal_bar",
                "title": f"People beyond 400 m by Pobal HP decile — {place}",
                "x_label": "People (no published CAF/PAG unit cost)",
                "data": [
                    {
                        "label": f"HP {row['decile']}",
                        "value": row.get("pop_desert") or 0.0,
                    }
                    for row in sorted(by_decile, key=lambda x: x["decile"])
                ],
            },
            "j3_carbon": {
                "type": "horizontal_bar",
                "title": f"Illustrative car-km CO₂ by county (EPA { _EPA_CAR_G_PER_KM:g} g/km) — {place}",
                "x_label": "Tonnes (illustrative)",
                "data": [
                    {
                        "label": r["name"],
                        "value": r["pop_desert"] * 3.0 * 220.0 * _EPA_CAR_G_PER_KM / 1e6,
                    }
                    for r in sorted(county_rows, key=lambda x: -x["pop_desert"])
                ],
            },
            "j4_investment_priority": {
                "type": "scatter_regression",
                "title": f"Priority: people beyond 400 m vs HP — {place}",
                "x_label": "Mean HP relative (lower = more disadvantaged)",
                "y_label": "People beyond 400 m",
                "data": [
                    {"x": r["mean_hp"], "y": r["pop_desert"], "id": r["name"]}
                    for r in county_rows
                ],
            },
            "bsa1_franchising_readiness": {
                "type": "choropleth",
                "geography": "ireland_county",
                "title": f"NTA coverage proxy (% people within 400 m) — {place}",
                "metric_label": "% people",
                "data": [
                    {"area_code": r["code"], "area_name": r["name"], "value": r["pct_covered"]}
                    for r in county_rows
                ],
            },
            "bsa2_operator_concentration": {
                "type": "gauge",
                "title": f"TFI operator HHI (0–10,000) — {place}",
                "value": hhi,
                "min": 0,
                "max": 10000,
                "unit": "/ 10,000",
                "bands": [
                    {"label": "Low", "min": 0.0, "max": 1500.0, "color_hint": "green"},
                    {"label": "Moderate", "min": 1500.0, "max": 2500.0, "color_hint": "yellow"},
                    {"label": "High", "min": 2500.0, "max": None, "color_hint": "red"},
                ],
                "markers": (
                    [{"label": f"{top_agency_name} {top_agency_share:.1f}% of routes", "value": hhi}]
                    if hhi is not None and top_agency_share is not None
                    else []
                ),
            },
            "bsa3_tier_distribution": {
                "type": "grouped_bar",
                "title": f"NTA programme tiers — {place}",
                "x_label": "Small Areas",
                "data": [{"label": k, "group": "SAs", "value": v} for k, v in tiers.items()],
            },
            "ps1_freq_restoration": {
                "type": "kpi_tiles",
                "title": f"Restore weekday frequency — {place}",
                "tiles": [{"label": "People below median weekday trips", "value": ps1_pop, "unit": "people"}],
            },
            "ps2_evening_extension": {
                "type": "kpi_tiles",
                "title": f"Evening extension — {place}",
                "tiles": [{"label": "People with no departure after 19:00", "value": ps2_pop, "unit": "people"}],
            },
            "ps3_drt_rural": {
                "type": "kpi_tiles",
                "title": f"Connecting Ireland / rural RTP — {place}",
                "tiles": [{"label": "Rural people beyond 400 m", "value": ps3_pop, "unit": "people"}],
            }
            if urban_rural != "urban"
            else {},
            "ps4_franchise": {
                "type": "kpi_tiles",
                "title": f"Combined Connecting Ireland + BusConnects — {place}",
                "tiles": [{"label": "People beyond 400 m", "value": ps4_pop, "unit": "people"}],
            },
            "ps5_scenario_comparison": {
                "type": "table",
                "title": f"Irish intervention comparison — {place}",
                "data": [
                    {
                        "Intervention": row["title"],
                        "People": int(row["people"]),
                    }
                    for row in stats_map["ps5_scenario_comparison"]["rows"]
                ],
            },
        }
        for sid in omit_ids:
            charts[sid] = {}

    out = []
    for sid in CATALOGUE:
        st = dict(stats_map[sid])
        st["title"] = TITLES[sid]
        st["catalogue"] = CATALOGUE[sid]
        raw_chart = charts.get(sid) or {}
        if CATALOGUE[sid] == OMIT or empty or st.get("omit"):
            raw_chart = {}
        out.append(
            {
                "region": region,
                "urban_rural": urban_rural,
                "section_id": sid,
                "stats": st,
                "chart_data": raw_chart,
                "narrative": narratives.get(sid, ""),
            }
        )
    return out


def precompute_ireland(areas: pd.DataFrame, extras: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    extras = extras or {}
    regions = ["all"] + sorted({str(r) for r in areas["region"].dropna().unique()})
    area_types = ["all", "urban", "rural"]
    out: list[dict[str, Any]] = []
    for region in regions:
        for ur in area_types:
            sl = _filter_areas(areas, region, ur)
            out.extend(_section_bundle(sl, areas, region, ur, extras))
    return out
