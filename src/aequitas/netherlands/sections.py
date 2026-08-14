"""Netherlands answers for every England section_id (same / replace / omit). Re-derived from CBS."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.netherlands.constants import NL_EVENING_NOTE, PROVINCE_NAME_BY_SLUG
from aequitas.warehouse.stats_builders.equity import (
    _concentration_index,
    _palma_ratio,
    _population_weighted_gini,
)

SAME = "same"
REPLACE = "replace"
OMIT = "omit"

# Re-checked CBS 85984NED + 86092NED (2026-08-13). Do not copy Ireland omits.
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
    "d2_coverage_unemployment": SAME,  # WW / inwoners (85984NED)
    "d3_coverage_car": SAME,  # 1 − clip(personenauto's per huishouden)
    "d4_coverage_elderly": SAME,  # 65+ / inwoners
    "d5_coverage_income": SAME,  # gemiddeld inkomen per inwoner
    "d6_transport_poverty": SAME,
    "d7_deprivation_urban_rural": SAME,
    "d8_feature_importance": SAME,
    "d9a_health_access": SAME,  # Wmo-cliënten relatief (care use cousin)
    "d9b_employment_access": SAME,  # nettoarbeidsparticipatie
    "d9c_crime_access": OMIT,  # no buurt crime in 85984NED
    "d9d_environment_access": OMIT,
    "d9e_barriers_access": SAME,  # huurwoningen share
    "f1_gini": SAME,
    "f2_disparity_ratio": SAME,
    "f3_ethnic_access": SAME,  # herkomst buiten Europa / inwoners
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
    "a1_route_density": "Route density by provincie",
    "a2_stop_density": "Stop density by provincie",
    "a3_walking_distance": "Population within 400 m of an OVapi stop",
    "a4_coverage_equity": "Equity of coverage within provincies",
    "a5_service_deserts": "Service deserts (people beyond 400 m)",
    "a6_urban_rural_gap": "Urban vs rural coverage (stedelijkheid)",
    "a7_investment_gap": "People-gap to national 400 m average",
    "a8_coverage_prediction": "Coverage ~ SES-WOA and stedelijkheid",
    "b1_frequency": "Average weekday service quality by provincie",
    "b2_operating_hours": "Evening service (after 19:00)",
    "b3_weekend_penalty": "Sunday OVapi penalty",
    "b4_route_frequency": "Most/least frequent OVapi agencies",
    "b5_frequency_deprivation": "Frequency vs SES-WOA",
    "c1_route_length": "Stops-per-route distribution",
    "c2_stops_per_route": "Stops per OVapi route",
    "c3_operator_hhi": "OVapi operator HHI (0–10,000)",
    "c4_urban_rural_routes": "Urban vs rural stop mass",
    "c5_length_vs_frequency": "Stops per route vs agency share",
    "c6_route_archetypes": "OVapi route archetypes",
    "c7_network_topology": "Network topology (OVapi)",
    "d1_coverage_deprivation": "Coverage vs SES-WOA",
    "d2_coverage_unemployment": "Coverage vs WW benefit share",
    "d3_coverage_car": "Coverage vs low-car households",
    "d4_coverage_elderly": "Coverage vs elderly population",
    "d5_coverage_income": "Coverage vs income per inhabitant",
    "d6_transport_poverty": "Transport poverty clusters (SES × service)",
    "d7_deprivation_urban_rural": "SES-WOA × stedelijkheid",
    "d8_feature_importance": "Dutch feature importance",
    "d9a_health_access": "Coverage vs Wmo client share",
    "d9b_employment_access": "Coverage vs labour participation",
    "d9c_crime_access": "Service quality vs crime",
    "d9d_environment_access": "Service quality vs living environment",
    "d9e_barriers_access": "Coverage vs social-rental share",
    "f1_gini": "Gini of OVapi weekday trips per capita",
    "f2_disparity_ratio": "Disparity by SES-WOA decile",
    "f3_ethnic_access": "Access by herkomst (buiten Europa)",
    "f5_rural_penalty": "Rural accessibility penalty",
    "f6_equitable_regions": "Most equitable provincies",
    "g1_route_clusters": "Route clustering",
    "g2_anomalies": "Anomaly detection",
    "g3_coverage_model": "Coverage prediction",
    "g4_shap": "Feature importance (SES-WOA + stedelijkheid)",
    "g5_scenario_model": "OV / flex intervention KPIs",
    "j1_economic_value": "Priority population by provincie",
    "j2_bcr": "Official OV/welzijn BCR",
    "j3_carbon": "Illustrative carbon (no free PBL unit cost)",
    "j4_investment_priority": "Provincie × SES coverage gap",
    "bsa1_franchising_readiness": "Concession / OV-wet coverage by provincie",
    "bsa2_operator_concentration": "OVapi operator concentration",
    "bsa3_tier_distribution": "Concession / urban OV / rural flex tiers",
    "ps1_freq_restoration": "Restore OV weekday frequency",
    "ps2_evening_extension": "Evening OV",
    "ps3_drt_rural": "Rural OV / flex",
    "ps4_franchise": "Combined concession package",
    "ps5_scenario_comparison": "Dutch intervention comparison",
}

_CAR_G_PER_KM = 164.0
_CARBON_NOTE = (
    "Illustrative only: 164 gCO₂/km passenger-car intensity. No free PBL/CBS unit cost applied."
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


def _prov_name(slug: str) -> str:
    return PROVINCE_NAME_BY_SLUG.get(str(slug), str(slug).replace("-", " ").title())


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


def _ranking_chart(
    rows: list[dict[str, Any]], *, title: str = "", x_label: str = "Value", note: str | None = None
) -> dict[str, Any]:
    data = [{"label": row.get("label") or row.get("name"), "value": row["value"]} for row in rows]
    out: dict[str, Any] = {"type": "horizontal_bar", "title": title, "x_label": x_label, "data": data}
    if note:
        out["note"] = note
    return out


def _filter_label(region: str, urban_rural: str, mode: str) -> str:
    place = "the Netherlands" if region == "all" else _prov_name(region)
    mode_lab = "bus only" if mode == "bus" else "all public transport"
    if urban_rural == "all":
        return f"{place} ({mode_lab})"
    return f"{place}, {urban_rural} ({mode_lab})"


def _brief(key: str, so_what: str, caveat: str) -> str:
    return f"**Key finding.** {key}\n\n**So what.** {so_what}\n\n**Caveat.** {caveat}"


def _lorenz_payload(areas: pd.DataFrame, gini: float | None, n: int, pop: float) -> dict[str, Any]:
    title = f"Lorenz — OVapi weekday trips per capita ({int(pop):,} people, {n:,} buurten)"
    if n < 3 or "trips_per_capita" not in areas or "population" not in areas:
        return {"type": "lorenz_curve", "title": title, "gini": gini, "curve_points": []}
    ranked = areas[["trips_per_capita", "population"]].dropna().copy().sort_values("trips_per_capita")
    w = ranked["population"].to_numpy(dtype=float)
    v = ranked["trips_per_capita"].to_numpy(dtype=float)
    if w.sum() <= 0:
        return {"type": "lorenz_curve", "title": title, "gini": gini, "curve_points": []}
    cum_w = np.cumsum(w)
    cum_vw = np.cumsum(v * w)
    total_w = float(cum_w[-1])
    total_vw = float(cum_vw[-1])
    xs = np.concatenate([[0.0], cum_w / total_w])
    ys = np.zeros_like(xs) if total_vw <= 0 else np.concatenate([[0.0], cum_vw / total_vw])
    step = max(1, len(xs) // 80)
    idx = list(range(0, len(xs), step))
    if idx[-1] != len(xs) - 1:
        idx.append(len(xs) - 1)
    points = [{"cum_pop": float(xs[i]), "cum_service": float(ys[i])} for i in idx]
    return {"type": "lorenz_curve", "title": title, "gini": gini, "curve_points": points}


def _sample_scatter(areas, x_col, y_col, title, x_label, y_label, *, max_points: int = 80) -> dict[str, Any]:
    if x_col not in areas or y_col not in areas or len(areas) < 3:
        return {"type": "scatter_regression", "title": title, "data": []}
    work = areas[[x_col, y_col]].copy()
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
    points = [{"x": float(a), "y": float(b)} for a, b in zip(sample[x_col], sample[y_col])]
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


def _section_bundle(areas, all_areas, region, urban_rural, extras) -> list[dict[str, Any]]:
    mode = str(extras.get("mode") or "bus")
    n = len(areas)
    empty = n == 0
    pop = float(areas["population"].sum()) if n else 0.0
    nat_pop = float(all_areas["population"].sum()) if len(all_areas) else 0.0
    covered_pop = float(areas.loc[areas["within_400m"], "population"].sum()) if n else 0.0
    pct_covered = (covered_pop / pop * 100.0) if pop else 0.0
    nat_cov = (
        float(all_areas.loc[all_areas["within_400m"], "population"].sum()) / nat_pop * 100.0 if nat_pop else 0.0
    )
    n_zero = int((~areas["within_400m"]).sum()) if n else 0
    pop_zero = float(areas.loc[~areas["within_400m"], "population"].sum()) if n else 0.0
    mean_sqi = float(areas["sqi"].mean()) if n and "sqi" in areas else 0.0
    n_eve = int(areas["evening_isolated"].sum()) if n and "evening_isolated" in areas else 0
    n_sun = int(areas["sunday_desert"].sum()) if n and "sunday_desert" in areas else 0
    hhi = extras.get("hhi")
    agencies = extras.get("agencies") or []
    spr = extras.get("stops_per_route") or []
    ses_col = "ses_score" if "ses_score" in areas.columns else "hp_relative"
    r_ses = _corr(areas[ses_col].astype(float), areas["stops_per_1k"].astype(float)) if n >= 3 and ses_col in areas else None
    r_freq = _corr(areas[ses_col].astype(float), areas["sqi"].astype(float)) if n >= 3 and ses_col in areas else None
    gini = palma = ci = None
    if n >= 3 and "trips_per_capita" in areas:
        dec = (
            pd.to_numeric(areas["ses_decile"], errors="coerce")
            if "ses_decile" in areas
            else pd.Series(pd.NA, index=areas.index)
        )
        slice_df = pd.DataFrame(
            {
                "trips_per_capita": areas["trips_per_capita"].astype(float),
                "population": areas["population"].astype(float),
                "imd_decile": dec,
            }
        ).dropna(subset=["imd_decile"])
        if not slice_df.empty:
            slice_df["imd_decile"] = slice_df["imd_decile"].astype(int)
        try:
            gini = _population_weighted_gini(
                areas["trips_per_capita"].astype(float), areas["population"].astype(float)
            )
            if len(slice_df) >= 3:
                palma = _palma_ratio(slice_df, "trips_per_capita")
                ci = _concentration_index(slice_df, "trips_per_capita")
        except Exception as exc:  # noqa: BLE001
            logger.warning("NL Gini failed: {}", exc)
    src = all_areas if region == "all" else areas
    known_slugs = set(PROVINCE_NAME_BY_SLUG)
    if len(src) and "region" in src.columns:
        leftover_mask = ~src["region"].astype(str).isin(known_slugs)
        n_leftover_region = int(leftover_mask.sum())
        src_known = src.loc[~leftover_mask]
    else:
        n_leftover_region = 0
        src_known = src
    leftover_note = (
        f"{n_leftover_region:,} buurten with no provincie slug excluded from provincie bars."
        if n_leftover_region
        else None
    )
    province_rows = []
    for slug, grp in src_known.groupby("region"):
        p = float(grp["population"].sum())
        cov = float(grp.loc[grp["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0
        province_rows.append(
            {
                "code": str(slug),
                "name": _prov_name(str(slug)),
                "pct_covered": cov,
                "mean_sqi": float(grp["sqi"].mean()) if "sqi" in grp else 0.0,
                "stops": int(grp["stop_count"].sum()) if "stop_count" in grp else 0,
                "pop": p,
                "area_km2": float(grp["area_km2"].sum()) if "area_km2" in grp else 0.0,
                "pop_desert": float(grp.loc[~grp["within_400m"], "population"].sum()),
                "mean_ses": float(grp[ses_col].mean()) if ses_col in grp else 0.0,
            }
        )

    def density_rank(key: str) -> list[dict[str, Any]]:
        out = []
        for row in province_rows:
            area = row["area_km2"] or 1.0
            val = (row["stops"] / area) if key == "stops_area" else (row["stops"] / max(row["pop"], 1) * 1000)
            if key == "stops_area":
                val = row["stops"] / area
            out.append({"name": row["name"], "value": val, "code": row["code"]})
        return sorted(out, key=lambda x: x["value"], reverse=True)

    ur_stats: dict[str, Any] = {}
    if n and "urban_rural" in areas:
        for label, grp in areas.groupby("urban_rural"):
            p = float(grp["population"].sum())
            ur_stats[str(label)] = {
                "n": int(len(grp)),
                "pop": p,
                "pct_covered": float(grp.loc[grp["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0,
                "mean_sqi": float(grp["sqi"].mean()) if "sqi" in grp else 0.0,
            }
    by_decile = []
    dec_col = "ses_decile" if "ses_decile" in areas.columns else "hp_decile"
    n_ses = 0
    n_no_ses = n
    if n and dec_col in areas:
        dec_num = pd.to_numeric(areas[dec_col], errors="coerce")
        n_ses = int(dec_num.notna().sum())
        n_no_ses = n - n_ses
        ses_only = areas.loc[dec_num.notna()].copy()
        ses_only[dec_col] = dec_num.loc[dec_num.notna()].astype(int)
        for d, grp in ses_only.groupby(dec_col):
            p = float(grp["population"].sum())
            cov = float(grp.loc[grp["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0
            by_decile.append({"decile": int(d), "pct_covered": cov, "n": int(len(grp)), "pop_desert": float(grp.loc[~grp["within_400m"], "population"].sum())})

    def _tier(row) -> str:
        sted = getattr(row, "stedelijkheid", 5)
        try:
            sted_i = int(sted)
        except (TypeError, ValueError):
            sted_i = 5
        if sted_i <= 2 and bool(row.within_400m):
            return "Urban concession"
        if bool(row.within_400m) and getattr(row, "urban_rural", "") == "rural":
            return "Rural OV / flex"
        if bool(row.within_400m):
            return "Regional concession"
        return "Unserved (400 m)"

    tiers = {"Urban concession": 0, "Regional concession": 0, "Rural OV / flex": 0, "Unserved (400 m)": 0}
    if n:
        for rec in areas.itertuples(index=False):
            tiers[_tier(rec)] += 1
    rural = areas[areas["urban_rural"] == "rural"] if n and "urban_rural" in areas else areas.iloc[0:0]
    low_freq = areas[areas["weekday_trips"] < areas["weekday_trips"].median()] if n else areas.iloc[0:0]
    eve = areas[areas["evening_isolated"]] if n else areas.iloc[0:0]
    rural_desert = rural[~rural["within_400m"]] if len(rural) else rural
    ps1_pop = float(low_freq["population"].sum()) if len(low_freq) else 0.0
    ps2_pop = float(eve["population"].sum()) if len(eve) else 0.0
    ps3_pop = float(rural_desert["population"].sum()) if len(rural_desert) else 0.0
    ps4_pop = float(areas.loc[~areas["within_400m"], "population"].sum()) if n else 0.0
    carbon_t = pop_zero * 3.0 * 220.0 * _CAR_G_PER_KM / 1e6 if pop_zero else 0.0

    def has_col(col: str) -> bool:
        return bool(n and col in areas and areas[col].notna().sum() >= 3)

    r_unemp = _corr(pd.to_numeric(areas["unemp_rate"], errors="coerce"), areas["stops_per_1k"]) if has_col("unemp_rate") else None
    r_car = _corr(pd.to_numeric(areas["no_car_share"], errors="coerce"), areas["stops_per_1k"]) if has_col("no_car_share") else None
    r_eld = _corr(pd.to_numeric(areas["elderly_share"], errors="coerce"), areas["stops_per_1k"]) if has_col("elderly_share") else None
    r_inc = _corr(pd.to_numeric(areas["income"], errors="coerce"), areas["stops_per_1k"]) if has_col("income") else None
    r_wmo = _corr(pd.to_numeric(areas["wmo_share"], errors="coerce"), areas["stops_per_1k"]) if has_col("wmo_share") else None
    r_lab = _corr(pd.to_numeric(areas["labour_part"], errors="coerce"), areas["stops_per_1k"]) if has_col("labour_part") else None
    r_huur = _corr(pd.to_numeric(areas["huur_share"], errors="coerce"), areas["stops_per_1k"]) if has_col("huur_share") else None
    r_eth = _corr(pd.to_numeric(areas["buiten_europa_share"], errors="coerce"), areas["stops_per_1k"]) if has_col("buiten_europa_share") else None

    omit_crime = _omit("CBS Kerncijfers 85984NED has no buurt crime series.")
    omit_env = _omit("CBS Kerncijfers 85984NED has no living-environment domain at buurt.")

    empty_note = "No buurten match this provincie / stedelijkheid cut."
    place = _filter_label(region, urban_rural, mode)
    vintage = extras.get("vintage") or "OVapi gtfs-nl.zip, CBS SES-WOA 86092NED (2023), Kerncijfers 85984NED (2024)."
    caveat_base = (
        f"{n:,} buurten in {place}. SES-WOA present for {n_ses:,} buurten "
        f"({n_no_ses:,} null — not imputed). {vintage} Ranks stay inside the Netherlands (SES-WOA × OVapi)."
    )

    paired_rows: list[dict[str, Any]] = []
    if "urban_rural" in src.columns:
        for slug, grp in src_known.groupby("region"):
            rec: dict[str, Any] = {"name": _prov_name(str(slug)), "code": str(slug)}
            for label, sub in grp.groupby("urban_rural"):
                p = float(sub["population"].sum())
                rec[str(label)] = float(sub.loc[sub["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0
            paired_rows.append(rec)

    top_agency_share = top_agency_name = None
    if agencies:
        total_r = sum(float(a.get("n_routes") or 0) for a in agencies) or 1.0
        top = max(agencies, key=lambda a: float(a.get("n_routes") or 0))
        top_agency_name = top.get("name")
        top_agency_share = float(top.get("n_routes") or 0) / total_r * 100.0

    def corr_or_omit(has: bool, r: float | None, xlab: str) -> dict[str, Any]:
        if not has:
            return _omit(f"CBS column for {xlab} did not join at buurt in this pack.")
        return {"r": r, "x_label": xlab, "y_label": "Stops per 1,000 people", "insufficient_data": r is None}

    stats_map: dict[str, dict[str, Any]] = {
        "a1_route_density": {"national_avg": float(np.mean([r["stops"] / max(r["area_km2"], 1e-6) for r in province_rows])) if province_rows else 0.0, "unit": "OVapi stops per km²", "insufficient_data": empty, "n_buurten": n},
        "a2_stop_density": {"national_avg": float(np.mean([r["stops"] / max(r["pop"], 1) * 1000 for r in province_rows])) if province_rows else 0.0, "unit": "stops per 1,000 people", "insufficient_data": empty},
        "a3_walking_distance": {"pct_covered": pct_covered, "n_zero_access": n_zero, "pct_zero_access": (n_zero / n * 100.0) if n else 0.0, "pop_zero_access": pop_zero, "n_sas": n, "n_buurten": n, "insufficient_data": empty, "entity_type": "buurt", "mode": mode},
        "a4_coverage_equity": {"gini": gini, "n_buurten": n, "insufficient_data": gini is None, "metric": "trips_per_capita (OVapi weekday)"},
        "a5_service_deserts": {"n_desert_sas": n_zero, "pop_affected": pop_zero, "mean_ses": float(areas.loc[~areas["within_400m"], ses_col].mean()) if n_zero and ses_col in areas else None, "n_buurten": n, "insufficient_data": empty},
        "a6_urban_rural_gap": {"urban": ur_stats.get("urban", {}), "rural": ur_stats.get("rural", {}), "gap_pp": (ur_stats.get("urban", {}).get("pct_covered", 0) - ur_stats.get("rural", {}).get("pct_covered", 0)) if ur_stats else 0.0, "insufficient_data": empty},
        "a7_investment_gap": {"national_pct_covered": nat_cov, "local_pct_covered": pct_covered, "people_gap": max(0.0, (nat_cov - pct_covered) / 100.0 * pop), "currency": None, "note": "People below the national 400 m average. No free PBL unit cost — not € invented.", "insufficient_data": empty},
        "a8_coverage_prediction": {"r": r_ses, "features": ["ses_score", "stedelijkheid"], "insufficient_data": r_ses is None},
        "b1_frequency": {"national_avg": mean_sqi, "value": mean_sqi, "unit": "SQI (OVapi weekday analogue, 0–100)", "by_provincie": [{"name": r["name"], "value": r["mean_sqi"]} for r in province_rows], "n_excluded_no_provincie": n_leftover_region, "insufficient_data": empty},
        "b2_operating_hours": {"pct_evening_isolated": (n_eve / n * 100.0) if n else 0.0, "n_evening_isolated": n_eve, "insufficient_data": empty},
        "b3_weekend_penalty": {"pct_sunday_deserts": (n_sun / n * 100.0) if n else 0.0, "n_sunday_deserts": n_sun, "pct_sunday_desert": (n_sun / n * 100.0) if n else 0.0, "n_sunday_desert": n_sun, "sunday_source": "OVapi calendar_dates.txt (exception_type=1) joined to stop_times; a buurt is a Sunday desert if no Sunday departure within 400 m", "insufficient_data": empty},
        "b4_route_frequency": {"agencies": agencies[:12], "insufficient_data": not agencies},
        "b5_frequency_deprivation": {"r": r_freq, "x_label": "SES-WOA 2023 score", "y_label": "SQI (OVapi weekday)", "insufficient_data": r_freq is None},
        "c1_route_length": {"n_routes": extras.get("n_routes"), "p50_stops": float(np.median(spr)) if spr else None, "insufficient_data": not spr, "unit": "stops per route"},
        "c2_stops_per_route": {"mean": extras.get("mean_stops_per_route"), "n_routes": extras.get("n_routes"), "insufficient_data": extras.get("mean_stops_per_route") is None},
        "c3_operator_hhi": {"hhi": hhi, "scale": "0-10000", "n_agencies": extras.get("n_agencies"), "top_agency": top_agency_name, "top_agency_share_pct": top_agency_share, "insufficient_data": hhi is None},
        "c4_urban_rural_routes": {"urban_stops": int(areas.loc[areas["urban_rural"] == "urban", "stop_count"].sum()) if n else 0, "rural_stops": int(areas.loc[areas["urban_rural"] == "rural", "stop_count"].sum()) if n else 0, "insufficient_data": empty},
        "c5_length_vs_frequency": {"r": float(areas["stop_count"].corr(areas["sqi"])) if n and "stop_count" in areas and "sqi" in areas else None, "insufficient_data": n < 3},
        "c6_route_archetypes": {"clusters": [{"name": "Urban frequent", "n": int((areas["urban_rural"] == "urban").sum()) if n else 0}, {"name": "Rural sparse", "n": int((areas["urban_rural"] == "rural").sum()) if n else 0}], "insufficient_data": empty},
        "c7_network_topology": {"n_agencies": extras.get("n_agencies"), "n_routes": extras.get("n_routes"), "n_buurten": n, "insufficient_data": extras.get("n_routes") is None},
        "d1_coverage_deprivation": {"r": r_ses, "x_label": "SES-WOA 2023", "y_label": "Stops per 1,000 people", "insufficient_data": empty or r_ses is None},
        "d2_coverage_unemployment": corr_or_omit(has_col("unemp_rate"), r_unemp, "WW benefit share (85984NED)"),
        "d3_coverage_car": corr_or_omit(has_col("no_car_share"), r_car, "Low-car share (1 − personenauto's per huishouden)"),
        "d4_coverage_elderly": corr_or_omit(has_col("elderly_share"), r_eld, "Share aged 65+"),
        "d5_coverage_income": corr_or_omit(has_col("income"), r_inc, "Gemiddeld inkomen per inwoner"),
        "d6_transport_poverty": {"method": "SES-WOA decile 1–3 and not within 400 m", "n_sas": int(((areas[dec_col] <= 3) & (~areas["within_400m"])).sum()) if n else 0, "population": float(areas.loc[(areas[dec_col] <= 3) & (~areas["within_400m"]), "population"].sum()) if n else 0.0, "insufficient_data": empty},
        "d7_deprivation_urban_rural": {"cells": ur_stats, "index": "SES-WOA 2023", "n_with_ses": n_ses, "n_without_ses": n_no_ses, "insufficient_data": empty},
        "d8_feature_importance": {"features": [{"name": "ses_score", "r": r_ses}, {"name": "stedelijkheid", "note": "CBS 1–5"}], "insufficient_data": r_ses is None},
        "d9a_health_access": corr_or_omit(has_col("wmo_share"), r_wmo, "Wmo client share"),
        "d9b_employment_access": corr_or_omit(has_col("labour_part"), r_lab, "Nettoarbeidsparticipatie"),
        "d9c_crime_access": omit_crime,
        "d9d_environment_access": omit_env,
        "d9e_barriers_access": corr_or_omit(has_col("huur_share"), r_huur, "Huurwoningen share"),
        "f1_gini": {"gini": gini, "palma": palma, "concentration_index": ci, "n_sas": n, "n_buurten": n, "insufficient_data": gini is None, "metric": "trips_per_capita (OVapi weekday)"},
        "f2_disparity_ratio": {"by_decile": by_decile, "index": "SES-WOA 2023", "n_with_ses": n_ses, "n_without_ses": n_no_ses, "ratio": (by_decile[-1]["pct_covered"] / by_decile[0]["pct_covered"]) if len(by_decile) >= 2 and by_decile[0]["pct_covered"] else None, "insufficient_data": empty or len(by_decile) < 2},
        "f3_ethnic_access": corr_or_omit(has_col("buiten_europa_share"), r_eth, "Herkomst buiten Europa share"),
        "f5_rural_penalty": {"urban": ur_stats.get("urban", {}), "rural": ur_stats.get("rural", {}), "penalty_pp": (ur_stats.get("urban", {}).get("pct_covered", 0) - ur_stats.get("rural", {}).get("pct_covered", 0)) if ur_stats else 0.0, "insufficient_data": empty},
        "f6_equitable_regions": {"ranking": sorted(province_rows, key=lambda r: r["pct_covered"], reverse=True)[:12], "insufficient_data": not province_rows},
        "g1_route_clusters": {"n_clusters": 2, "labels": ["urban frequent", "rural sparse"], "insufficient_data": empty},
        "g2_anomalies": {"n_flagged": int(((areas["within_400m"]) & (areas[dec_col] <= 2) & (areas["sqi"] < 20)).sum()) if n else 0, "rule": "SES-WOA decile ≤2, a stop nearby, SQI < 20", "insufficient_data": empty},
        "g3_coverage_model": {"r": r_ses, "insufficient_data": r_ses is None},
        "g4_shap": {"features": [{"name": "ses_score", "r": r_ses}, {"name": "stedelijkheid", "r": None}], "insufficient_data": r_ses is None},
        "g5_scenario_model": {"points_at": ["ps1_freq_restoration", "ps2_evening_extension", "ps3_drt_rural", "ps4_franchise"], "insufficient_data": empty},
        "j1_economic_value": {"unit": "people beyond 400 m (no € without a cited PBL/CBS unit cost)", "by_county": [{"name": r["name"], "value": r["pop_desert"]} for r in province_rows], "national": pop_zero, "insufficient_data": empty},
        "j2_bcr": {"bcr": None, "omit_euro": True, "reason": "No free published PBL/CBS unit cost applied. People-gap only.", "people_gap": pop_zero, "insufficient_data": False},
        "j3_carbon": {"co2_saving_tonnes": carbon_t, "factor_g_per_km": _CAR_G_PER_KM, "note": _CARBON_NOTE, "insufficient_data": empty},
        "j4_investment_priority": {"ranking": sorted(province_rows, key=lambda r: (r["pop_desert"], -r["mean_ses"]), reverse=True)[:12], "insufficient_data": not province_rows},
        "bsa1_franchising_readiness": {"national_avg": pct_covered, "unit": "% people within 400 m (concession / OV-wet proxy)", "programme": "Concession / OV-wet", "insufficient_data": empty},
        "bsa2_operator_concentration": {"hhi": hhi, "scale": "0-10000", "same_as": "c3_operator_hhi", "insufficient_data": hhi is None},
        "bsa3_tier_distribution": {"tiers": tiers, "insufficient_data": empty},
        "ps1_freq_restoration": {"scenario": {"population_affected": ps1_pop, "who": "Buurten below median weekday OVapi trips"}, "euro": None, "insufficient_data": empty},
        "ps2_evening_extension": {"scenario": {"population_affected": ps2_pop, "who": "Buurten with no departure after 19:00"}, "euro": None, "insufficient_data": empty},
        "ps3_drt_rural": {"scenario": {"population_affected": ps3_pop, "who": "Rural buurten beyond 400 m"}, "euro": None, "insufficient_data": empty or urban_rural == "urban"},
        "ps4_franchise": {"scenario": {"population_affected": ps4_pop, "who": "Combined concession people beyond 400 m"}, "euro": None, "note": "Combined concession package.", "insufficient_data": empty},
        "ps5_scenario_comparison": {"rows": [{"id": "ps1", "title": TITLES["ps1_freq_restoration"], "people": ps1_pop}, {"id": "ps2", "title": TITLES["ps2_evening_extension"], "people": ps2_pop}, {"id": "ps3", "title": TITLES["ps3_drt_rural"], "people": ps3_pop}, {"id": "ps4", "title": TITLES["ps4_franchise"], "people": ps4_pop}], "insufficient_data": empty},
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
        r_ses_txt = f"{r_ses:.3f}" if r_ses is not None else "n/a"
        gini_txt = f"{gini:.3f}" if gini is not None else "not computed"
        gap_pp = stats_map["a6_urban_rural_gap"]["gap_pp"]
        people_gap = stats_map["a7_investment_gap"]["people_gap"]
        narratives.update(
            {
                "a1_route_density": _brief(f"OVapi stop density varies by provincie in {place}.", "Provincie ranks show stop mass, not who can walk to a stop.", caveat_base),
                "a2_stop_density": _brief(f"Stops per 1,000 people in {place} re-ranks provincies versus area density.", "A dense stop field can still leave people behind.", f"{caveat_base} Deprivation is SES-WOA 2023."),
                "a3_walking_distance": _brief(f"{pct_covered:.1f}% of people in {place} live within 400 m of an OVapi stop ({int(covered_pop):,} in, {int(pop_zero):,} out).", "People count behind the 400 m door. Mode is labelled.", caveat_base),
                "a4_coverage_equity": _brief(f"Gini of OVapi weekday trips per capita in {place} is {gini_txt}.", "One Lorenz — people-weighted trips per capita.", caveat_base),
                "a5_service_deserts": _brief(f"{int(pop_zero):,} people in {n_zero:,} buurten in {place} live beyond 400 m.", "The map is people, not empty polygons.", caveat_base),
                "a6_urban_rural_gap": _brief(f"In {place} the urban–rural 400 m gap is {gap_pp:.1f} percentage points.", "Stedelijkheid 1–3 vs 4–5.", caveat_base),
                "a7_investment_gap": _brief(f"{people_gap:,.0f} people in {place} sit below the national 400 m average.", "People-gap only: no free PBL unit cost.", caveat_base),
                "a8_coverage_prediction": _brief(f"SES-WOA vs stops per 1,000 in {place}: r = {r_ses_txt}.", "Association, not a causal model.", caveat_base),
                "b1_frequency": _brief(f"Mean weekday SQI in {place} is {mean_sqi:.1f} / 100.", "Weekday SQI distribution.", f"{caveat_base} Built from OVapi stop_times."),
                "b2_operating_hours": _brief(f"{(n_eve / n * 100.0) if n else 0:.1f}% of buurten in {place} have no departure after 19:00.", "Evening isolation is a clock-time question.", f"{caveat_base} {NL_EVENING_NOTE}"),
                "b3_weekend_penalty": _brief(f"{(n_sun / n * 100.0) if n else 0:.1f}% of buurten in {place} have no Sunday trip.", "Sunday is the weekend penalty.", caveat_base),
                "b4_route_frequency": _brief(f"OVapi agencies ranked by route count for {place}.", "Agency route mass, not HHI.", caveat_base),
                "b5_frequency_deprivation": _brief(f"SES-WOA vs weekday SQI in {place}: r = {r_freq:.3f}." if r_freq is not None else f"SES–SQI in {place} is not identified.", "Do thinner weekday services sit on lower SES buurten?", caveat_base),
                "c1_route_length": _brief(
                    "Stops-per-route list not persisted for this OVapi write (scan skipped after dual-mode DuckDB trap)."
                    if not spr
                    else "Stops-per-route distribution for this OVapi mode.",
                    "Stop-count proxy — empty is honest, not a zero bin.",
                    caveat_base,
                ),
                "c2_stops_per_route": _brief(
                    "Stops-per-route list not persisted."
                    if extras.get("mean_stops_per_route") is None
                    else f"Mean stops per route is {extras.get('mean_stops_per_route')}.",
                    "Route-stop distribution.",
                    caveat_base,
                ),
                "c3_operator_hhi": _brief(f"OVapi operator HHI is {hhi:.0f} / 10,000." if hhi is not None else "HHI needs agency.txt.", "One 0–10,000 concentration exhibit.", caveat_base),
                "c4_urban_rural_routes": _brief(f"Stop mass in {place} splits urban vs rural under stedelijkheid.", "Infrastructure location, not 400 m people coverage.", caveat_base),
                "c5_length_vs_frequency": _brief(f"Stop mass vs weekday SQI in {place}.", "Stops per 1,000 vs SQI.", caveat_base),
                "c6_route_archetypes": _brief("Two archetypes: urban frequent vs rural sparse (stedelijkheid).", "OVapi inputs.", caveat_base),
                "c7_network_topology": _brief(f"OVapi: {extras.get('n_routes')} routes, {extras.get('n_agencies')} agencies in {place}.", "Agency route mass.", caveat_base),
                "d1_coverage_deprivation": _brief(f"SES-WOA vs stops per 1,000 in {place}: r = {r_ses_txt}.", "In-country SES–service association.", caveat_base),
                "d6_transport_poverty": _brief(f"{stats_map['d6_transport_poverty']['n_sas']:,} buurten in {place} are SES deciles 1–3 and beyond 400 m.", "Transport-poverty cluster.", caveat_base),
                "d7_deprivation_urban_rural": _brief(f"SES-WOA crossed with stedelijkheid in {place}.", "Where disadvantage and rural stedelijkheid stack, walk-to-stop is thinner.", caveat_base),
                "d8_feature_importance": _brief(f"In {place}, SES-WOA vs stops per 1,000 has r = {r_ses_txt}.", "Dutch features only.", caveat_base),
                "f1_gini": _brief(f"Gini of OVapi weekday trips per capita in {place} is {gini_txt} ({int(pop):,} people).", "One Lorenz for this question.", caveat_base),
                "f2_disparity_ratio": _brief(f"SES-WOA decile slope of 400 m coverage in {place}.", "People-weighted 400 m by SES decile.", caveat_base),
                "f5_rural_penalty": _brief(f"Rural 400 m coverage in {place} trails urban by {stats_map['f5_rural_penalty']['penalty_pp']:.1f} pp.", "Paired provincie dots.", caveat_base),
                "f6_equitable_regions": _brief(f"Provincies ranked by 400 m coverage for {place}.", "In-country ranks only.", caveat_base),
                "g1_route_clusters": _brief("Two-cluster method on stedelijkheid × service.", "Appendix to Correlations.", caveat_base),
                "g2_anomalies": _brief(f"{stats_map['g2_anomalies']['n_flagged']:,} buurten in {place} are SES ≤2, near a stop, SQI < 20.", "A nearby stop with thin weekday service.", caveat_base),
                "g3_coverage_model": _brief(f"Coverage association in {place}: r = {r_ses_txt}.", "Same features as a8.", caveat_base),
                "g4_shap": _brief("SES-WOA + stedelijkheid.", "Dutch features only.", caveat_base),
                "g5_scenario_model": _brief(f"KPIs for {place} point at the OV / flex list.", "People only.", caveat_base),
                "j1_economic_value": _brief(f"{int(pop_zero):,} people in {place} live beyond 400 m.", "People only — no invented euro.", caveat_base),
                "j2_bcr": _brief(f"No free published PBL/CBS BCR for {place}. People-gap is {int(pop_zero):,}.", "People-gap only.", caveat_base),
                "j3_carbon": _brief(f"{carbon_t:,.0f} t illustrative car-km CO₂ in {place}.", _CARBON_NOTE, caveat_base),
                "j4_investment_priority": _brief(f"Provincies ranked by people beyond 400 m and SES disadvantage ({place}).", "Priority is a people-gap.", caveat_base),
                "bsa1_franchising_readiness": _brief(f"Concession / OV-wet coverage proxy in {place}: {pct_covered:.1f}% of people within 400 m.", "Concession programmes this filter can see.", caveat_base),
                "bsa2_operator_concentration": _brief(f"Same OVapi HHI as Network: {hhi:.0f} / 10,000." if hhi is not None else "HHI unavailable.", "Hidden so HHI is not shown twice.", caveat_base),
                "bsa3_tier_distribution": _brief(f"Concession tiers in {place}: urban concession, regional, rural flex, unserved.", "Dutch concession tiers.", caveat_base),
                "ps1_freq_restoration": _brief(f"{int(ps1_pop):,} people in {place} live in buurten below median weekday trips.", "Restore OV weekday frequency — people only.", caveat_base),
                "ps2_evening_extension": _brief(f"{int(ps2_pop):,} people in {place} have no departure after 19:00.", "Evening OV.", caveat_base),
                "ps3_drt_rural": _brief(f"{int(ps3_pop):,} people in rural buurten of {place} are beyond 400 m.", "Rural OV / flex.", caveat_base),
                "ps4_franchise": _brief(f"{int(ps4_pop):,} people in {place} live beyond 400 m — combined concession.", "People and SES, not a euro BCR.", caveat_base),
                "ps5_scenario_comparison": _brief(f"Four Dutch interventions compared on people in {place}.", "No invented euro.", caveat_base),
            }
        )
        if has_col("unemp_rate"):
            narratives["d2_coverage_unemployment"] = _brief(f"WW share vs stops per 1,000 in {place}: r = {r_unemp}." if r_unemp is not None else "WW vs stop mass not identified.", "CBS Kerncijfers WW.", caveat_base)
        if has_col("no_car_share"):
            narratives["d3_coverage_car"] = _brief(f"Low-car share vs stops per 1,000 in {place}: r = {r_car}." if r_car is not None else "Low-car vs stop mass not identified.", "Personenauto's per huishouden inverted.", caveat_base)
        if has_col("elderly_share"):
            narratives["d4_coverage_elderly"] = _brief(f"65+ vs stops per 1,000 in {place}: r = {r_eld}." if r_eld is not None else "65+ not identified.", "CBS 65 jaar of ouder.", caveat_base)
        if has_col("income"):
            narratives["d5_coverage_income"] = _brief(f"Income per inhabitant vs stops per 1,000 in {place}: r = {r_inc}." if r_inc is not None else "Income not identified.", "CBS gemiddeld inkomen per inwoner.", caveat_base)
        if has_col("wmo_share"):
            narratives["d9a_health_access"] = _brief(f"Wmo share vs stops per 1,000 in {place}: r = {r_wmo}.", "Wmo is care use, not a health domain score.", caveat_base)
        if has_col("labour_part"):
            narratives["d9b_employment_access"] = _brief(f"Labour participation vs stops per 1,000 in {place}: r = {r_lab}.", "Nettoarbeidsparticipatie.", caveat_base)
        if has_col("huur_share"):
            narratives["d9e_barriers_access"] = _brief(f"Huur share vs stops per 1,000 in {place}: r = {r_huur}.", "Social-rental / huur share.", caveat_base)
        if has_col("buiten_europa_share"):
            narratives["f3_ethnic_access"] = _brief(f"Herkomst buiten Europa vs stops per 1,000 in {place}: r = {r_eth}.", "CBS herkomstland.", caveat_base)

    sqi_box = _box_from_values("Weekday SQI", areas["sqi"].astype(float).tolist()) if n and "sqi" in areas else None
    spr_box = _box_from_values("Stops per route", [float(x) for x in spr]) if spr else None
    geo = "netherlands_provincie"
    if empty:
        charts = {sid: {} for sid in CATALOGUE}
    else:
        charts = {
            "a1_route_density": _ranking_chart(density_rank("stops_area"), title=f"OVapi stops per km² — {place}", x_label="Stops per km²"),
            "a2_stop_density": _ranking_chart(density_rank("pop"), title=f"OVapi stops per 1,000 people — {place}", x_label="Stops per 1,000 people"),
            "a3_walking_distance": {"type": "stacked_bar", "title": f"People in/out of 400 m — {place}", "x_label": "People", "data": [{"label": place, "group": "Within 400 m", "value": covered_pop}, {"label": place, "group": "Beyond 400 m", "value": pop_zero}]},
            "a4_coverage_equity": _lorenz_payload(areas, gini, n, pop),
            "a5_service_deserts": {"type": "choropleth", "geography": geo, "title": f"People beyond 400 m — {place}", "metric_label": "People", "data": [{"area_code": r["code"], "area_name": r["name"], "value": r["pop_desert"]} for r in province_rows]},
            "a6_urban_rural_gap": {"type": "scatter_regression", "title": f"Urban vs rural 400 m by provincie — {place}", "x_label": "Urban % within 400 m", "y_label": "Rural % within 400 m", "data": [{"x": float(r.get("urban") or 0), "y": float(r.get("rural") or 0), "id": r["name"]} for r in paired_rows]},
            "a7_investment_gap": _ranking_chart([{"label": r["name"], "value": max(0.0, (nat_cov - r["pct_covered"]) / 100.0 * r["pop"])} for r in sorted(province_rows, key=lambda x: -max(0.0, (nat_cov - x["pct_covered"]) / 100.0 * x["pop"]))], title=f"People below national 400 m average — {place}", x_label="People"),
            "a8_coverage_prediction": {"type": "shap_bar", "title": f"Dutch features (SES-WOA + stedelijkheid) — {place}", "features": [{"name": "SES-WOA 2023", "importance": abs(r_ses) if r_ses is not None else 0.0}, {"name": "Stedelijkheid", "importance": 0.5}]},
            "b1_frequency": _ranking_chart(
                [{"label": r["name"], "value": r["mean_sqi"]} for r in sorted(province_rows, key=lambda x: -x["mean_sqi"])]
                if region == "all"
                else [
                    {"label": lab, "value": float(sub["sqi"].mean())}
                    for lab, sub in (areas.groupby("urban_rural") if n and "urban_rural" in areas else [])
                ],
                title=f"Weekday SQI by {'provincie' if region == 'all' else 'stedelijkheid'} — {place}",
                x_label="Mean SQI (0–100)",
                note=leftover_note if region == "all" else None,
            ),
            "b2_operating_hours": _ranking_chart(
                [
                    {
                        "label": _prov_name(str(slug)),
                        "value": float(grp["evening_isolated"].mean() * 100.0) if "evening_isolated" in grp else 0.0,
                    }
                    for slug, grp in src_known.groupby("region")
                ]
                if region == "all"
                else [
                    {"label": "Isolated after 19:00", "value": n_eve},
                    {"label": "Has evening departure", "value": max(n - n_eve, 0)},
                ],
                title=f"Evening isolation % by provincie — {place}" if region == "all" else f"Evening isolation — {place}",
                x_label="% of buurten" if region == "all" else "Buurten",
            ),
            "b3_weekend_penalty": _ranking_chart(
                [
                    {
                        "label": _prov_name(str(slug)),
                        "value": float(grp["sunday_desert"].mean() * 100.0) if "sunday_desert" in grp else 0.0,
                    }
                    for slug, grp in src_known.groupby("region")
                ]
                if region == "all"
                else [
                    {"label": "No Sunday trip", "value": n_sun},
                    {"label": "Has a Sunday trip", "value": max(n - n_sun, 0)},
                ],
                title=f"Sunday desert % by provincie — {place}" if region == "all" else f"Sunday desert — {place}",
                x_label="% of buurten" if region == "all" else "Buurten",
            ),
            "b4_route_frequency": _ranking_chart([{"label": a.get("name"), "value": a.get("n_routes") or 0} for a in agencies[:15]], title=f"OVapi agencies by route count — {place}", x_label="Routes"),
            "b5_frequency_deprivation": _sample_scatter(areas, ses_col, "sqi", f"SES-WOA vs weekday SQI — {place}", "SES-WOA 2023", "SQI (OVapi weekday)"),
            "c1_route_length": (
                {
                    "type": "horizontal_bar",
                    "title": f"Stops-per-route bins — {place}",
                    "data": _spr_bins(spr),
                }
                if spr
                else {
                    "type": "horizontal_bar",
                    "title": f"Stops-per-route bins — {place}",
                    "data": [],
                    "empty_reason": "Stops-per-route list not persisted",
                }
            ),
            "c2_stops_per_route": (
                {"type": "box_violin", "title": f"Stops per OVapi route — {place}", "groups": [spr_box]}
                if spr_box
                else {
                    "type": "box_violin",
                    "title": f"Stops per OVapi route — {place}",
                    "groups": [],
                    "empty_reason": "Stops-per-route list not persisted",
                }
            ),
            "c3_operator_hhi": {
                "type": "gauge",
                "title": f"OVapi operator HHI (0–10,000) — {place}",
                "value": hhi,
                "min": 0,
                "max": 10000,
                "unit": "/ 10,000",
                "markers": [{"label": "HHI", "value": float(hhi) if hhi is not None else 0.0}],
                "bands": [
                    {"label": "Low", "min": 0.0, "max": 1500.0, "color_hint": "green"},
                    {"label": "Moderate", "min": 1500.0, "max": 2500.0, "color_hint": "orange"},
                    {"label": "High", "min": 2500.0, "max": 10000.0, "color_hint": "red"},
                ],
            },
            "c4_urban_rural_routes": {"type": "stacked_bar", "title": f"Stop mass urban vs rural — {place}", "data": [{"label": "Stops", "group": "Urban", "value": stats_map["c4_urban_rural_routes"]["urban_stops"]}, {"label": "Stops", "group": "Rural", "value": stats_map["c4_urban_rural_routes"]["rural_stops"]}]},
            "c5_length_vs_frequency": _sample_scatter(areas, "stops_per_1k", "sqi", f"Stop mass vs weekday SQI — {place}", "Stops per 1,000 people", "SQI"),
            "c6_route_archetypes": {"type": "scatter_clusters", "title": f"OVapi archetypes — {place}", "cluster_sizes": [{"label": "Urban frequent", "n": int((areas["urban_rural"] == "urban").sum()) if n else 0}, {"label": "Rural sparse", "n": int((areas["urban_rural"] == "rural").sum()) if n else 0}]},
            "c7_network_topology": _ranking_chart([{"label": a.get("name"), "value": a.get("n_routes") or 0} for a in agencies[:15]], title=f"OVapi agencies (topology mass) — {place}", x_label="Routes"),
            "d1_coverage_deprivation": _sample_scatter(areas, ses_col, "stops_per_1k", f"SES-WOA vs stops per 1,000 — {place}", "SES-WOA 2023", "Stops per 1,000 people"),
            "d7_deprivation_urban_rural": {
                "type": "heatmap",
                "title": f"SES-WOA × stedelijkheid 400 m % — {place} (n SES={n_ses:,}; {n_no_ses:,} null dropped)",
                "x_labels": ["Urban", "Rural"],
                "y_labels": [f"D{d}" for d in range(1, 11)],
                "z": [
                    [
                        (
                            float(
                                areas.loc[
                                    (pd.to_numeric(areas[dec_col], errors="coerce") == d)
                                    & (areas["urban_rural"] == ur),
                                    "within_400m",
                                ].mean()
                                * 100
                            )
                            if n
                            and dec_col in areas
                            and areas.loc[
                                (pd.to_numeric(areas[dec_col], errors="coerce") == d) & (areas["urban_rural"] == ur)
                            ].shape[0]
                            else None
                        )
                        for ur in ("urban", "rural")
                    ]
                    for d in range(1, 11)
                ],
            },
            "d8_feature_importance": {"type": "shap_bar", "title": f"Dutch features — {place}", "features": [{"name": "SES-WOA", "importance": abs(r_ses) if r_ses is not None else 0.0}, {"name": "Stedelijkheid", "importance": 0.4}]},
            "f1_gini": _lorenz_payload(areas, gini, n, pop),
            "f2_disparity_ratio": {"type": "line", "title": f"SES-WOA decile slope of 400 m — {place}", "x_label": "SES-WOA decile (1 = lowest SES)", "y_label": "% within 400 m", "data": [{"x": r["decile"], "y": r["pct_covered"]} for r in by_decile]},
            "f5_rural_penalty": {"type": "scatter_regression", "title": f"Urban vs rural 400 m by provincie — {place}", "data": [{"x": float(r.get("urban") or 0), "y": float(r.get("rural") or 0), "id": r["name"]} for r in paired_rows]},
            "f6_equitable_regions": _ranking_chart([{"label": r["name"], "value": r["pct_covered"]} for r in sorted(province_rows, key=lambda x: -x["pct_covered"])], title=f"400 m coverage by provincie — {place}", x_label="% within 400 m"),
            "j1_economic_value": _ranking_chart([{"label": r["name"], "value": r["pop_desert"]} for r in sorted(province_rows, key=lambda x: -x["pop_desert"])], title=f"People beyond 400 m — {place}", x_label="People"),
            "j2_bcr": {"type": "horizontal_bar", "title": f"People-gap (no euro BCR) — {place}", "data": [{"label": "People beyond 400 m", "value": pop_zero}]},
            "j3_carbon": {"type": "horizontal_bar", "title": f"Illustrative car-km CO₂ — {place}", "data": [{"label": "t CO₂", "value": carbon_t}]},
            "j4_investment_priority": _ranking_chart([{"label": r["name"], "value": r["pop_desert"]} for r in sorted(province_rows, key=lambda x: -x["pop_desert"])], title=f"Priority people-gap — {place}", x_label="People"),
            "bsa1_franchising_readiness": {"type": "choropleth", "geography": geo, "title": f"Concession coverage proxy — {place}", "data": [{"area_code": r["code"], "area_name": r["name"], "value": r["pct_covered"]} for r in province_rows]},
            "bsa3_tier_distribution": {"type": "horizontal_bar", "title": f"Concession tiers — {place}", "data": [{"label": k, "value": v} for k, v in tiers.items()]},
            "ps1_freq_restoration": {"type": "horizontal_bar", "title": f"Restore OV frequency — {place}", "data": [{"label": "People", "value": ps1_pop}]},
            "ps2_evening_extension": {"type": "horizontal_bar", "title": f"Evening OV — {place}", "data": [{"label": "People", "value": ps2_pop}]},
            "ps3_drt_rural": {"type": "horizontal_bar", "title": f"Rural OV / flex — {place}", "data": [{"label": "People", "value": ps3_pop}]},
            "ps4_franchise": {"type": "horizontal_bar", "title": f"Combined concession — {place}", "data": [{"label": "People", "value": ps4_pop}]},
            "ps5_scenario_comparison": {"type": "horizontal_bar", "title": f"Intervention comparison — {place}", "data": [{"label": TITLES["ps1_freq_restoration"], "value": ps1_pop}, {"label": TITLES["ps2_evening_extension"], "value": ps2_pop}, {"label": TITLES["ps3_drt_rural"], "value": ps3_pop}, {"label": TITLES["ps4_franchise"], "value": ps4_pop}]},
        }
        for sid, col, xlab in (
            ("d2_coverage_unemployment", "unemp_rate", "WW share"),
            ("d3_coverage_car", "no_car_share", "Low-car share"),
            ("d4_coverage_elderly", "elderly_share", "65+ share"),
            ("d5_coverage_income", "income", "Income per inhabitant"),
            ("d9a_health_access", "wmo_share", "Wmo share"),
            ("d9b_employment_access", "labour_part", "Labour participation"),
            ("d9e_barriers_access", "huur_share", "Huur share"),
            ("f3_ethnic_access", "buiten_europa_share", "Buiten Europa share"),
        ):
            if has_col(col):
                charts[sid] = _sample_scatter(areas, col, "stops_per_1k", f"{xlab} vs stops per 1,000 — {place}", xlab, "Stops per 1,000 people")
        d7 = charts.get("d7_deprivation_urban_rural")
        if isinstance(d7, dict) and d7.get("z") is not None:
            d7["values"] = d7["z"]

    rows = []
    for sid in CATALOGUE:
        rows.append(
            {
                "region": region,
                "urban_rural": urban_rural,
                "section_id": sid,
                "stats": {**stats_map[sid], "title": TITLES[sid], "catalogue": CATALOGUE[sid], "mode": mode},
                "chart_data": charts.get(sid) or {},
                "narrative": narratives.get(sid, ""),
            }
        )
    return rows


def precompute_netherlands(areas: pd.DataFrame, extras: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    extras = extras or {}
    known = set(PROVINCE_NAME_BY_SLUG)
    regions = ["all", *sorted(r for r in set(areas["region"].astype(str)) if r in known)]
    rows: list[dict[str, Any]] = []
    for region in regions:
        for ur in ("all", "urban", "rural"):
            sl = _filter_areas(areas, region, ur)
            rows.extend(_section_bundle(sl, areas, region, ur, extras))
    logger.info("NL sections: {} rows ({} regions × 3 stedelijkheid × {})", len(rows), len(regions), len(CATALOGUE))
    return rows
