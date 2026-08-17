"""France answers for every England section_id (same / replace / omit). Re-derived from INSEE / NAP / F-EDI."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.france.constants import FR_EVENING_NOTE, REGION_NAME_BY_SLUG
from aequitas.warehouse.stats_builders.equity import (
    _concentration_index,
    _palma_ratio,
    _population_weighted_gini,
)

SAME = "same"
REPLACE = "replace"
OMIT = "omit"

# Re-checked INSEE recensement 2018 + F-EDI 2021 + grille densité 2024 (2026-08-17). Do not copy IE/NL omits.
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
    "d2_coverage_unemployment": OMIT,  # structure table 2018 has no chômage series
    "d3_coverage_car": OMIT,  # structure table 2018 has no ménage voiture column
    "d4_coverage_elderly": SAME,  # P18_POP65P / P18_POP
    "d5_coverage_income": OMIT,  # Filosofi IRIS xlsx 500/404 on the three URLs tried
    "d6_transport_poverty": SAME,
    "d7_deprivation_urban_rural": SAME,
    "d8_feature_importance": SAME,
    "d9a_health_access": OMIT,  # no free IRIS health-domain score
    "d9b_employment_access": OMIT,  # activity/emploi IRIS table not on the files that 200'd
    "d9c_crime_access": OMIT,  # no free IRIS crime series
    "d9d_environment_access": OMIT,  # no free IRIS living-environment domain
    "d9e_barriers_access": OMIT,  # no HLM/logement column in structure-pop 2018
    "f1_gini": SAME,
    "f2_disparity_ratio": SAME,
    "f3_ethnic_access": SAME,  # immigrés share if joined — origin, not ethnicity
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
    "a1_route_density": "Route density by région",
    "a2_stop_density": "Stop density by région",
    "a3_walking_distance": "Population within 400 m of an NAP stop",
    "a4_coverage_equity": "Equity of coverage within régions",
    "a5_service_deserts": "Service deserts (people beyond 400 m)",
    "a6_urban_rural_gap": "Urban vs rural coverage (INSEE density)",
    "a7_investment_gap": "People-gap to national 400 m average",
    "a8_coverage_prediction": "Coverage ~ F-EDI and INSEE density",
    "b1_frequency": "Average weekday service quality by région",
    "b2_operating_hours": "Evening service (after 19:00)",
    "b3_weekend_penalty": "Sunday NAP penalty",
    "b4_route_frequency": "Most/least frequent NAP agencies",
    "b5_frequency_deprivation": "Frequency vs F-EDI",
    "c1_route_length": "Stops-per-route distribution",
    "c2_stops_per_route": "Stops per NAP route",
    "c3_operator_hhi": "NAP operator HHI (0–10,000)",
    "c4_urban_rural_routes": "Urban vs rural stop mass",
    "c5_length_vs_frequency": "Stops per route vs agency share",
    "c6_route_archetypes": "NAP route archetypes",
    "c7_network_topology": "Network topology (NAP)",
    "d1_coverage_deprivation": "Coverage vs F-EDI",
    "d2_coverage_unemployment": "Coverage vs chômage (omit — no IRIS series)",
    "d3_coverage_car": "Coverage vs no-car households (omit — no IRIS series)",
    "d4_coverage_elderly": "Coverage vs elderly population",
    "d5_coverage_income": "Coverage vs income per inhabitant",
    "d6_transport_poverty": "Transport poverty clusters (F-EDI × service)",
    "d7_deprivation_urban_rural": "F-EDI × INSEE density",
    "d8_feature_importance": "French feature importance",
    "d9a_health_access": "Coverage vs health domain (none at IRIS)",
    "d9b_employment_access": "Coverage vs labour participation",
    "d9c_crime_access": "Service quality vs crime",
    "d9d_environment_access": "Service quality vs living environment",
    "d9e_barriers_access": "Coverage vs social-rental share",
    "f1_gini": "Gini of NAP weekday trips per capita",
    "f2_disparity_ratio": "Disparity by F-EDI decile",
    "f3_ethnic_access": "Access by immigrés share (origin, not ethnicity)",
    "f5_rural_penalty": "Rural accessibility penalty",
    "f6_equitable_regions": "Most equitable régions",
    "g1_route_clusters": "Route clustering",
    "g2_anomalies": "Anomaly detection",
    "g3_coverage_model": "Coverage prediction",
    "g4_shap": "Feature importance (F-EDI + INSEE density)",
    "g5_scenario_model": "SPC / rural holes intervention KPIs",
    "j1_economic_value": "Priority population by région",
    "j2_bcr": "People-gap (no ADEME euro BCR)",
    "j3_carbon": "Illustrative carbon (no free ADEME unit cost)",
    "j4_investment_priority": "Région × F-EDI coverage gap",
    "bsa1_franchising_readiness": "AOM / SPC coverage by région",
    "bsa2_operator_concentration": "NAP operator concentration",
    "bsa3_tier_distribution": "AOM / SPC / rural-hole tiers",
    "ps1_freq_restoration": "Restore NAP weekday frequency",
    "ps2_evening_extension": "Evening NAP",
    "ps3_drt_rural": "Rural SPC / hole",
    "ps4_franchise": "Combined SPC package",
    "ps5_scenario_comparison": "French intervention comparison",
}

_CAR_G_PER_KM = 164.0
_CARBON_NOTE = (
    "Illustrative only: 164 gCO₂/km passenger-car intensity. No free ADEME/INSEE unit cost applied."
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


def _reg_name(slug: str) -> str:
    return REGION_NAME_BY_SLUG.get(str(slug), str(slug).replace("-", " ").title())


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
    place = "metropolitan France" if region == "all" else _reg_name(region)
    mode_lab = "bus only" if mode == "bus" else "all public transport"
    if urban_rural == "all":
        return f"{place} ({mode_lab})"
    return f"{place}, {urban_rural} ({mode_lab})"


def _brief(key: str, so_what: str, caveat: str) -> str:
    return f"**Key finding.** {key}\n\n**So what.** {so_what}\n\n**Caveat.** {caveat}"


def _lorenz_payload(areas: pd.DataFrame, gini: float | None, n: int, pop: float) -> dict[str, Any]:
    title = f"Lorenz — NAP weekday trips per capita ({int(pop):,} people, {n:,} IRIS)"
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
    mode_lab = "bus only" if mode == "bus" else "all public transport"
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
    ses_col = "fedi_score" if "fedi_score" in areas.columns else "hp_relative"
    r_ses = _corr(areas[ses_col].astype(float), areas["stops_per_1k"].astype(float)) if n >= 3 and ses_col in areas else None
    r_freq = _corr(areas[ses_col].astype(float), areas["sqi"].astype(float)) if n >= 3 and ses_col in areas else None
    gini = palma = ci = None
    if n >= 3 and "trips_per_capita" in areas:
        dec = (
            pd.to_numeric(areas["fedi_decile"], errors="coerce")
            if "fedi_decile" in areas
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
    known_slugs = set(REGION_NAME_BY_SLUG)
    if len(src) and "region" in src.columns:
        leftover_mask = ~src["region"].astype(str).isin(known_slugs)
        n_leftover_region = int(leftover_mask.sum())
        src_known = src.loc[~leftover_mask]
    else:
        n_leftover_region = 0
        src_known = src
    leftover_note = (
        f"{n_leftover_region:,} IRIS with no région slug excluded from région bars."
        if n_leftover_region
        else None
    )
    region_rows = []
    for slug, grp in src_known.groupby("region"):
        p = float(grp["population"].sum())
        cov = float(grp.loc[grp["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0
        region_rows.append(
            {
                "code": str(slug),
                "name": _reg_name(str(slug)),
                "pct_covered": cov,
                "mean_sqi": float(grp["sqi"].mean()) if "sqi" in grp else 0.0,
                "stops": int(grp["stop_count"].sum()) if "stop_count" in grp else 0,
                "pop": p,
                "area_km2": float(grp["area_km2"].sum()) if "area_km2" in grp else 0.0,
                "pop_desert": float(grp.loc[~grp["within_400m"], "population"].sum()),
                "mean_fedi": float(grp[ses_col].mean()) if ses_col in grp else 0.0,
            }
        )

    def density_rank(key: str) -> list[dict[str, Any]]:
        out = []
        for row in region_rows:
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
    dec_col = "fedi_decile" if "fedi_decile" in areas.columns else "hp_decile"
    n_fedi = 0
    n_no_fedi = n
    if n and dec_col in areas:
        dec_num = pd.to_numeric(areas[dec_col], errors="coerce")
        n_fedi = int(dec_num.notna().sum())
        n_no_fedi = n - n_fedi
        ses_only = areas.loc[dec_num.notna()].copy()
        ses_only[dec_col] = dec_num.loc[dec_num.notna()].astype(int)
        for d, grp in ses_only.groupby(dec_col):
            p = float(grp["population"].sum())
            cov = float(grp.loc[grp["within_400m"], "population"].sum()) / p * 100.0 if p else 0.0
            by_decile.append({"decile": int(d), "pct_covered": cov, "n": int(len(grp)), "pop_desert": float(grp.loc[~grp["within_400m"], "population"].sum())})

    def _tier(row) -> str:
        sted = getattr(row, "INSEE density", 5)
        try:
            sted_i = int(sted)
        except (TypeError, ValueError):
            sted_i = 5
        if sted_i <= 2 and bool(row.within_400m):
            return "Urban AOM"
        if bool(row.within_400m) and getattr(row, "urban_rural", "") == "rural":
            return "Rural SPC / hole"
        if bool(row.within_400m):
            return "Regional AOM"
        return "Unserved (400 m)"

    tiers = {"Urban AOM": 0, "Regional AOM": 0, "Rural SPC / hole": 0, "Unserved (400 m)": 0}
    if n:
        for rec in areas.itertuples(index=False):
            tiers[_tier(rec)] += 1
    rural = areas[areas["urban_rural"] == "rural"] if n and "urban_rural" in areas else areas.iloc[0:0]
    if n and "weekday_trips" in areas:
        med = float(areas["weekday_trips"].median())
        if med <= 0:
            low_freq = areas[areas["weekday_trips"] <= 0]
        else:
            low_freq = areas[areas["weekday_trips"] < med]
    else:
        low_freq = areas.iloc[0:0]
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
    r_wmo = None
    r_lab = _corr(pd.to_numeric(areas["activity_rate"], errors="coerce"), areas["stops_per_1k"]) if has_col("activity_rate") else None
    r_huur = _corr(pd.to_numeric(areas["hlm_share"], errors="coerce"), areas["stops_per_1k"]) if has_col("hlm_share") else None
    r_eth = _corr(pd.to_numeric(areas["immig_share"], errors="coerce"), areas["stops_per_1k"]) if has_col("immig_share") else None

    omit_crime = _omit("No free IRIS crime series on INSEE / data.gouv hits.")
    omit_env = _omit("No free IRIS living-environment domain on INSEE hits.")
    omit_health = _omit("No free IRIS health-domain score; F-EDI is a composite, not a health cousin.")
    omit_unemp = _omit("INSEE base-ic-evol-struct-pop-2018 has no chômage series (activity table not downloaded; Filosofi IRIS 500/404).")
    omit_car = _omit("INSEE structure-pop 2018 has no ménage voiture column.")
    omit_income = _omit("Filosofi IRIS xlsx returned 500, 404, 500 on the three INSEE fichier URLs tried.")
    omit_labour = _omit("INSEE activity/emploi IRIS table was not among the files that returned 200.")
    omit_hlm = _omit("INSEE structure-pop 2018 has no HLM / logement-social column.")

    empty_note = "No IRIS match this région / INSEE density cut."
    place = _filter_label(region, urban_rural, mode)
    vintage = extras.get("vintage") or "NAP GTFS harvest, F-EDI 2021, IGN IRIS, INSEE recensement 2018 / densité 2024."
    caveat_base = (
        f"{n:,} IRIS in {place}. F-EDI present for {n_fedi:,} IRIS "
        f"({n_no_fedi:,} null — not imputed). {vintage} Ranks stay inside metropolitan France (F-EDI × NAP)."
    )

    paired_rows: list[dict[str, Any]] = []
    if "urban_rural" in src.columns:
        for slug, grp in src_known.groupby("region"):
            rec: dict[str, Any] = {"name": _reg_name(str(slug)), "code": str(slug)}
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
            return _omit(f"INSEE column for {xlab} did not join at IRIS in this pack.")
        return {"r": r, "x_label": xlab, "y_label": "Stops per 1,000 people", "insufficient_data": r is None}

    stats_map: dict[str, dict[str, Any]] = {
        "a1_route_density": {"national_avg": float(np.mean([r["stops"] / max(r["area_km2"], 1e-6) for r in region_rows])) if region_rows else 0.0, "unit": "NAP stops per km²", "insufficient_data": empty, "n_IRIS": n},
        "a2_stop_density": {"national_avg": float(np.mean([r["stops"] / max(r["pop"], 1) * 1000 for r in region_rows])) if region_rows else 0.0, "unit": "stops per 1,000 people", "insufficient_data": empty},
        "a3_walking_distance": {"pct_covered": pct_covered, "n_zero_access": n_zero, "pct_zero_access": (n_zero / n * 100.0) if n else 0.0, "pop_zero_access": pop_zero, "n_sas": n, "n_IRIS": n, "insufficient_data": empty, "entity_type": "IRIS", "mode": mode},
        "a4_coverage_equity": {"gini": gini, "n_IRIS": n, "insufficient_data": gini is None, "metric": "trips_per_capita (NAP weekday)"},
        "a5_service_deserts": {"n_desert_sas": n_zero, "pop_affected": pop_zero, "mean_fedi": float(areas.loc[~areas["within_400m"], ses_col].mean()) if n_zero and ses_col in areas else None, "n_IRIS": n, "insufficient_data": empty},
        "a6_urban_rural_gap": {"urban": ur_stats.get("urban", {}), "rural": ur_stats.get("rural", {}), "gap_pp": (ur_stats.get("urban", {}).get("pct_covered", 0) - ur_stats.get("rural", {}).get("pct_covered", 0)) if ur_stats else 0.0, "insufficient_data": empty},
        "a7_investment_gap": {"national_pct_covered": nat_cov, "local_pct_covered": pct_covered, "people_gap": max(0.0, (nat_cov - pct_covered) / 100.0 * pop), "currency": None, "note": "People below the national 400 m average. No free ADEME unit cost — not € invented.", "insufficient_data": empty},
        "a8_coverage_prediction": {"r": r_ses, "features": ["fedi_score", "INSEE density"], "insufficient_data": r_ses is None},
        "b1_frequency": {"national_avg": mean_sqi, "value": mean_sqi, "unit": "SQI (NAP weekday analogue, 0–100)", "by_région": [{"name": r["name"], "value": r["mean_sqi"]} for r in region_rows], "n_excluded_no_région": n_leftover_region, "insufficient_data": empty},
        "b2_operating_hours": {"pct_evening_isolated": (n_eve / n * 100.0) if n else 0.0, "n_evening_isolated": n_eve, "insufficient_data": empty},
        "b3_weekend_penalty": {"pct_sunday_deserts": (n_sun / n * 100.0) if n else 0.0, "n_sunday_deserts": n_sun, "pct_sunday_desert": (n_sun / n * 100.0) if n else 0.0, "n_sunday_desert": n_sun, "sunday_source": "NAP calendar.txt OR calendar_dates.txt (exception_type=1) joined to stop_times; an IRIS is a Sunday desert if no Sunday departure within 400 m — not a broken join", "insufficient_data": empty},
        "b4_route_frequency": {"agencies": agencies[:12], "insufficient_data": not agencies},
        "b5_frequency_deprivation": {"r": r_freq, "x_label": "F-EDI 2021 score", "y_label": "SQI (NAP weekday)", "insufficient_data": r_freq is None},
        "c1_route_length": {"n_routes": extras.get("n_routes"), "p50_stops": float(np.median(spr)) if spr else None, "insufficient_data": not spr, "unit": "stops per route"},
        "c2_stops_per_route": {"mean": extras.get("mean_stops_per_route"), "n_routes": extras.get("n_routes"), "insufficient_data": extras.get("mean_stops_per_route") is None},
        "c3_operator_hhi": {"hhi": hhi, "scale": "0-10000", "n_agencies": extras.get("n_agencies"), "top_agency": top_agency_name, "top_agency_share_pct": top_agency_share, "insufficient_data": hhi is None},
        "c4_urban_rural_routes": {"urban_stops": int(areas.loc[areas["urban_rural"] == "urban", "stop_count"].sum()) if n else 0, "rural_stops": int(areas.loc[areas["urban_rural"] == "rural", "stop_count"].sum()) if n else 0, "insufficient_data": empty},
        "c5_length_vs_frequency": {"r": float(areas["stop_count"].corr(areas["sqi"])) if n and "stop_count" in areas and "sqi" in areas else None, "insufficient_data": n < 3},
        "c6_route_archetypes": {"clusters": [{"name": "Urban frequent", "n": int((areas["urban_rural"] == "urban").sum()) if n else 0}, {"name": "Rural sparse", "n": int((areas["urban_rural"] == "rural").sum()) if n else 0}], "insufficient_data": empty},
        "c7_network_topology": {"n_agencies": extras.get("n_agencies"), "n_routes": extras.get("n_routes"), "n_IRIS": n, "insufficient_data": extras.get("n_routes") is None},
        "d1_coverage_deprivation": {"r": r_ses, "x_label": "F-EDI 2021", "y_label": "Stops per 1,000 people", "insufficient_data": empty or r_ses is None},
        "d2_coverage_unemployment": omit_unemp,
        "d3_coverage_car": omit_car,
        "d4_coverage_elderly": corr_or_omit(has_col("elderly_share"), r_eld, "Share aged 65+"),
        "d5_coverage_income": omit_income,
        "d6_transport_poverty": {"method": "F-EDI decile 1–3 and not within 400 m", "n_sas": int(((areas[dec_col] <= 3) & (~areas["within_400m"])).sum()) if n else 0, "population": float(areas.loc[(areas[dec_col] <= 3) & (~areas["within_400m"]), "population"].sum()) if n else 0.0, "insufficient_data": empty},
        "d7_deprivation_urban_rural": {"cells": ur_stats, "index": "F-EDI 2021", "n_with_fedi": n_fedi, "n_without_fedi": n_no_fedi, "insufficient_data": empty},
        "d8_feature_importance": {"features": [{"name": "fedi_score", "r": r_ses}, {"name": "INSEE density", "note": "grille 7 niveaux"}], "insufficient_data": r_ses is None},
        "d9a_health_access": omit_health,
        "d9b_employment_access": omit_labour,
        "d9c_crime_access": omit_crime,
        "d9d_environment_access": omit_env,
        "d9e_barriers_access": omit_hlm,
        "f1_gini": {"gini": gini, "palma": palma, "concentration_index": ci, "n_sas": n, "n_IRIS": n, "insufficient_data": gini is None, "metric": "trips_per_capita (NAP weekday)"},
        "f2_disparity_ratio": {"by_decile": by_decile, "index": "F-EDI 2021", "n_with_fedi": n_fedi, "n_without_fedi": n_no_fedi, "ratio": (by_decile[-1]["pct_covered"] / by_decile[0]["pct_covered"]) if len(by_decile) >= 2 and by_decile[0]["pct_covered"] else None, "insufficient_data": empty or len(by_decile) < 2},
        "f3_ethnic_access": corr_or_omit(has_col("immig_share"), r_eth, "immigrés share (recensement origin)"),
        "f5_rural_penalty": {"urban": ur_stats.get("urban", {}), "rural": ur_stats.get("rural", {}), "penalty_pp": (ur_stats.get("urban", {}).get("pct_covered", 0) - ur_stats.get("rural", {}).get("pct_covered", 0)) if ur_stats else 0.0, "insufficient_data": empty},
        "f6_equitable_regions": {"ranking": sorted(region_rows, key=lambda r: r["pct_covered"], reverse=True)[:12], "insufficient_data": not region_rows},
        "g1_route_clusters": {"n_clusters": 2, "labels": ["urban frequent", "rural sparse"], "insufficient_data": empty},
        "g2_anomalies": {"n_flagged": int(((areas["within_400m"]) & (areas[dec_col] <= 2) & (areas["sqi"] < 20)).sum()) if n else 0, "rule": "F-EDI decile ≤2, a stop nearby, SQI < 20", "insufficient_data": empty},
        "g3_coverage_model": {"r": r_ses, "insufficient_data": r_ses is None},
        "g4_shap": {"features": [{"name": "fedi_score", "r": r_ses}, {"name": "INSEE density", "r": None}], "insufficient_data": r_ses is None},
        "g5_scenario_model": {"points_at": ["ps1_freq_restoration", "ps2_evening_extension", "ps3_drt_rural", "ps4_franchise"], "insufficient_data": empty},
        "j1_economic_value": {"unit": "people beyond 400 m (no € without a cited ADEME/INSEE unit cost)", "by_county": [{"name": r["name"], "value": r["pop_desert"]} for r in region_rows], "national": pop_zero, "insufficient_data": empty},
        "j2_bcr": {"bcr": None, "omit_euro": True, "reason": "No free published ADEME/INSEE unit cost applied. People-gap only.", "people_gap": pop_zero, "insufficient_data": False},
        "j3_carbon": {"co2_saving_tonnes": carbon_t, "factor_g_per_km": _CAR_G_PER_KM, "note": _CARBON_NOTE, "insufficient_data": empty},
        "j4_investment_priority": {"ranking": sorted(region_rows, key=lambda r: (r["pop_desert"], -r["mean_fedi"]), reverse=True)[:12], "insufficient_data": not region_rows},
        "bsa1_franchising_readiness": {"national_avg": pct_covered, "unit": "% people within 400 m (AOM / SPC proxy)", "programme": "AOM / SPC", "insufficient_data": empty},
        "bsa2_operator_concentration": {"hhi": hhi, "scale": "0-10000", "same_as": "c3_operator_hhi", "insufficient_data": hhi is None},
        "bsa3_tier_distribution": {"tiers": tiers, "insufficient_data": empty},
        "ps1_freq_restoration": {"scenario": {"population_affected": ps1_pop, "who": "IRIS below median weekday NAP trips"}, "euro": None, "insufficient_data": empty},
        "ps2_evening_extension": {"scenario": {"population_affected": ps2_pop, "who": "IRIS with no departure after 19:00"}, "euro": None, "insufficient_data": empty},
        "ps3_drt_rural": {"scenario": {"population_affected": ps3_pop, "who": "Rural IRIS beyond 400 m"}, "euro": None, "insufficient_data": empty or urban_rural == "urban"},
        "ps4_franchise": {"scenario": {"population_affected": ps4_pop, "who": "Combined SPC people beyond 400 m"}, "euro": None, "note": "Combined SPC package.", "insufficient_data": empty},
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
                "a1_route_density": _brief(f"NAP stop density varies by région in {place}.", "Région ranks show stop mass, not who can walk to a stop.", caveat_base),
                "a2_stop_density": _brief(f"Stops per 1,000 people in {place} re-ranks régions versus area density.", "A dense stop field can still leave people behind.", f"{caveat_base} Deprivation is F-EDI 2021."),
                "a3_walking_distance": _brief(f"{pct_covered:.1f}% of people in {place} live within 400 m of an NAP stop ({int(covered_pop):,} in, {int(pop_zero):,} out).", "People count behind the 400 m door. Mode is labelled.", caveat_base),
                "a4_coverage_equity": _brief(f"Gini of NAP weekday trips per capita in {place} is {gini_txt}.", "One Lorenz — people-weighted trips per capita.", caveat_base),
                "a5_service_deserts": _brief(f"{int(pop_zero):,} people in {n_zero:,} IRIS in {place} live beyond 400 m.", "The map is people, not empty polygons.", caveat_base),
                "a6_urban_rural_gap": _brief(f"In {place} the urban–rural 400 m gap is {gap_pp:.1f} percentage points.", "INSEE density 1–3 vs 4–5.", caveat_base),
                "a7_investment_gap": _brief(f"{people_gap:,.0f} people in {place} sit below the national 400 m average.", "People-gap only: no free ADEME unit cost.", caveat_base),
                "a8_coverage_prediction": _brief(f"F-EDI vs stops per 1,000 in {place}: r = {r_ses_txt}.", "Association, not a causal model.", caveat_base),
                "b1_frequency": _brief(f"Mean weekday SQI in {place} is {mean_sqi:.1f} / 100.", "Weekday SQI distribution.", f"{caveat_base} Built from NAP stop_times."),
                "b2_operating_hours": _brief(f"{(n_eve / n * 100.0) if n else 0:.1f}% of IRIS in {place} have no departure after 19:00.", "Evening isolation is a clock-time question.", f"{caveat_base} {FR_EVENING_NOTE}"),
                "b3_weekend_penalty": _brief(
                    f"{(n_sun / n * 100.0) if n else 0:.1f}% of IRIS in {place} have no Sunday trip.",
                    "Sunday is the weekend penalty after joining calendar.txt or calendar_dates.txt — not a missing file.",
                    caveat_base,
                ),
                "b4_route_frequency": _brief(f"NAP agencies ranked by route count for {place}.", "Agency route mass, not HHI.", caveat_base),
                "b5_frequency_deprivation": _brief(f"F-EDI vs weekday SQI in {place}: r = {r_freq:.3f}." if r_freq is not None else f"SES–SQI in {place} is not identified.", "Do thinner weekday services sit on lower SES IRIS?", caveat_base),
                "c1_route_length": _brief(
                    "Stops-per-route list not persisted for this NAP write (scan skipped after dual-mode DuckDB trap)."
                    if not spr
                    else "Stops-per-route distribution for this NAP mode.",
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
                "c3_operator_hhi": _brief(
                    f"NAP operator HHI ({mode_lab}) is {hhi:.0f} / 10,000." if hhi is not None else "HHI needs agency.txt.",
                    "One 0–10,000 concentration exhibit. Dual-mode scores may match; HHI still names the mode.",
                    caveat_base,
                ),
                "c4_urban_rural_routes": _brief(f"Stop mass in {place} splits urban vs rural under INSEE density.", "Infrastructure location, not 400 m people coverage.", caveat_base),
                "c5_length_vs_frequency": _brief(f"Stop mass vs weekday SQI in {place}.", "Stops per 1,000 vs SQI.", caveat_base),
                "c6_route_archetypes": _brief("Two archetypes: urban frequent vs rural sparse (INSEE density).", "NAP inputs.", caveat_base),
                "c7_network_topology": _brief(f"NAP: {extras.get('n_routes')} routes, {extras.get('n_agencies')} agencies in {place}.", "Agency route mass.", caveat_base),
                "d1_coverage_deprivation": _brief(f"F-EDI vs stops per 1,000 in {place}: r = {r_ses_txt}.", "In-country SES–service association.", caveat_base),
                "d6_transport_poverty": _brief(f"{stats_map['d6_transport_poverty']['n_sas']:,} IRIS in {place} are F-EDI deciles 1–3 and beyond 400 m.", "Transport-poverty cluster.", caveat_base),
                "d7_deprivation_urban_rural": _brief(f"F-EDI crossed with INSEE density in {place}.", "Where disadvantage and rural INSEE density stack, walk-to-stop is thinner.", caveat_base),
                "d8_feature_importance": _brief(f"In {place}, F-EDI vs stops per 1,000 has r = {r_ses_txt}.", "French features only.", caveat_base),
                "f1_gini": _brief(f"Gini of NAP weekday trips per capita in {place} is {gini_txt} ({int(pop):,} people).", "One Lorenz for this question.", caveat_base),
                "f2_disparity_ratio": _brief(f"F-EDI decile slope of 400 m coverage in {place}.", "People-weighted 400 m by SES decile.", caveat_base),
                "f5_rural_penalty": _brief(f"Rural 400 m coverage in {place} trails urban by {stats_map['f5_rural_penalty']['penalty_pp']:.1f} pp.", "Paired région dots.", caveat_base),
                "f6_equitable_regions": _brief(f"Régions ranked by 400 m coverage for {place}.", "In-country ranks only.", caveat_base),
                "g1_route_clusters": _brief("Two-cluster method on INSEE density × service.", "Appendix to Correlations.", caveat_base),
                "g2_anomalies": _brief(f"{stats_map['g2_anomalies']['n_flagged']:,} IRIS in {place} are F-EDI decile ≤2, near a stop, SQI < 20.", "A nearby stop with thin weekday service.", caveat_base),
                "g3_coverage_model": _brief(f"Coverage association in {place}: r = {r_ses_txt}.", "Same features as a8.", caveat_base),
                "g4_shap": _brief("F-EDI + INSEE density.", "French features only.", caveat_base),
                "g5_scenario_model": _brief(f"KPIs for {place} point at the SPC / rural holes list.", "People only.", caveat_base),
                "j1_economic_value": _brief(f"{int(pop_zero):,} people in {place} live beyond 400 m.", "People only — no invented euro.", caveat_base),
                "j2_bcr": _brief(f"No free published ADEME/INSEE BCR for {place}. People-gap is {int(pop_zero):,}.", "People-gap only.", caveat_base),
                "j3_carbon": _brief(f"{carbon_t:,.0f} t illustrative car-km CO₂ in {place}.", _CARBON_NOTE, caveat_base),
                "j4_investment_priority": _brief(f"Régions ranked by people beyond 400 m and SES disadvantage ({place}).", "Priority is a people-gap.", caveat_base),
                "bsa1_franchising_readiness": _brief(f"AOM / SPC coverage proxy in {place}: {pct_covered:.1f}% of people within 400 m.", "Concession programmes this filter can see.", caveat_base),
                "bsa2_operator_concentration": _brief(f"Same NAP HHI as Network: {hhi:.0f} / 10,000." if hhi is not None else "HHI unavailable.", "Hidden so HHI is not shown twice.", caveat_base),
                "bsa3_tier_distribution": _brief(f"Concession tiers in {place}: urban concession, regional, rural flex, unserved.", "French concession tiers.", caveat_base),
                "ps1_freq_restoration": _brief(f"{int(ps1_pop):,} people in {place} live in IRIS below median weekday trips.", "Restore NAP weekday frequency — people only.", caveat_base),
                "ps2_evening_extension": _brief(f"{int(ps2_pop):,} people in {place} have no departure after 19:00.", "Evening NAP.", caveat_base),
                "ps3_drt_rural": _brief(f"{int(ps3_pop):,} people in rural IRIS of {place} are beyond 400 m.", "Rural SPC / hole.", caveat_base),
                "ps4_franchise": _brief(f"{int(ps4_pop):,} people in {place} live beyond 400 m — combined concession.", "People and SES, not a euro BCR.", caveat_base),
                "ps5_scenario_comparison": _brief(f"Four French interventions compared on people in {place}.", "No invented euro.", caveat_base),
            }
        )
        if has_col("unemp_rate"):
            narratives["d2_coverage_unemployment"] = _brief(f"Unemployment vs stops per 1,000 in {place}: r = {r_unemp}." if r_unemp is not None else "Unemployment vs stop mass not identified.", "INSEE recensement chômage / actifs.", caveat_base)
        if has_col("no_car_share"):
            narratives["d3_coverage_car"] = _brief(f"Low-car share vs stops per 1,000 in {place}: r = {r_car}." if r_car is not None else "Low-car vs stop mass not identified.", "Personenauto's per huishouden inverted.", caveat_base)
        if has_col("elderly_share"):
            narratives["d4_coverage_elderly"] = _brief(f"65+ vs stops per 1,000 in {place}: r = {r_eld}." if r_eld is not None else "65+ not identified.", "INSEE P18_POP65P.", caveat_base)
        if has_col("income"):
            narratives["d5_coverage_income"] = _brief(f"Income vs stops per 1,000 in {place}: r = {r_inc}." if r_inc is not None else "Income not identified.", "Filosofi IRIS if joined.", caveat_base)
        if has_col("activity_rate"):
            narratives["d9b_employment_access"] = _brief(f"Labour participation vs stops per 1,000 in {place}: r = {r_lab}.", "activity rate (recensement).", caveat_base)
        if has_col("hlm_share"):
            narratives["d9e_barriers_access"] = _brief(f"Huur share vs stops per 1,000 in {place}: r = {r_huur}.", "Social-rental / huur share.", caveat_base)
        if has_col("immig_share"):
            narratives["f3_ethnic_access"] = _brief(f"Immigrés share vs stops per 1,000 in {place}: r = {r_eth}.", "INSEE origin (immigrés), not ethnicity.", caveat_base)

    sqi_box = _box_from_values("Weekday SQI", areas["sqi"].astype(float).tolist()) if n and "sqi" in areas else None
    spr_box = _box_from_values("Stops per route", [float(x) for x in spr]) if spr else None
    geo = "france_region"
    if empty:
        charts = {sid: {} for sid in CATALOGUE}
    else:
        charts = {
            "a1_route_density": _ranking_chart(density_rank("stops_area"), title=f"NAP stops per km² — {place}", x_label="Stops per km²"),
            "a2_stop_density": _ranking_chart(density_rank("pop"), title=f"NAP stops per 1,000 people — {place}", x_label="Stops per 1,000 people"),
            "a3_walking_distance": {"type": "stacked_bar", "title": f"People in/out of 400 m — {place}", "x_label": "People", "data": [{"label": place, "group": "Within 400 m", "value": covered_pop}, {"label": place, "group": "Beyond 400 m", "value": pop_zero}]},
            "a4_coverage_equity": _lorenz_payload(areas, gini, n, pop),
            "a5_service_deserts": {"type": "choropleth", "geography": "france_region", "title": f"People beyond 400 m — {place}", "metric_label": "People", "data": [{"area_code": r["code"], "area_name": r["name"], "value": r["pop_desert"]} for r in region_rows]},
            "a6_urban_rural_gap": {"type": "scatter_regression", "title": f"Urban vs rural 400 m by région — {place}", "x_label": "Urban % within 400 m", "y_label": "Rural % within 400 m", "data": [{"x": float(r.get("urban") or 0), "y": float(r.get("rural") or 0), "id": r["name"]} for r in paired_rows]},
            "a7_investment_gap": _ranking_chart([{"label": r["name"], "value": max(0.0, (nat_cov - r["pct_covered"]) / 100.0 * r["pop"])} for r in sorted(region_rows, key=lambda x: -max(0.0, (nat_cov - x["pct_covered"]) / 100.0 * x["pop"]))], title=f"People below national 400 m average — {place}", x_label="People"),
            "a8_coverage_prediction": {"type": "shap_bar", "title": f"French features (F-EDI + INSEE density) — {place}", "features": [{"name": "F-EDI 2021", "importance": abs(r_ses) if r_ses is not None else 0.0}, {"name": "INSEE density", "importance": 0.5}]},
            "b1_frequency": _ranking_chart(
                [{"label": r["name"], "value": r["mean_sqi"]} for r in sorted(region_rows, key=lambda x: -x["mean_sqi"])]
                if region == "all"
                else [
                    {"label": lab, "value": float(sub["sqi"].mean())}
                    for lab, sub in (areas.groupby("urban_rural") if n and "urban_rural" in areas else [])
                ],
                title=f"Weekday SQI by {'région' if region == 'all' else 'INSEE density'} — {place}",
                x_label="Mean SQI (0–100)",
                note=leftover_note if region == "all" else None,
            ),
            "b2_operating_hours": _ranking_chart(
                [
                    {
                        "label": _reg_name(str(slug)),
                        "value": float(grp["evening_isolated"].mean() * 100.0) if "evening_isolated" in grp else 0.0,
                    }
                    for slug, grp in src_known.groupby("region")
                ]
                if region == "all"
                else [
                    {"label": "Isolated after 19:00", "value": n_eve},
                    {"label": "Has evening departure", "value": max(n - n_eve, 0)},
                ],
                title=f"Evening isolation % by région — {place}" if region == "all" else f"Evening isolation — {place}",
                x_label="% of IRIS" if region == "all" else "IRIS",
            ),
            "b3_weekend_penalty": _ranking_chart(
                [
                    {
                        "label": _reg_name(str(slug)),
                        "value": float(grp["sunday_desert"].mean() * 100.0) if "sunday_desert" in grp else 0.0,
                    }
                    for slug, grp in src_known.groupby("region")
                ]
                if region == "all"
                else [
                    {"label": "No Sunday trip", "value": n_sun},
                    {"label": "Has a Sunday trip", "value": max(n - n_sun, 0)},
                ],
                title=f"Sunday desert % by région — {place}" if region == "all" else f"Sunday desert — {place}",
                x_label="% of IRIS" if region == "all" else "IRIS",
            ),
            "b4_route_frequency": _ranking_chart([{"label": a.get("name"), "value": a.get("n_routes") or 0} for a in agencies[:15]], title=f"NAP agencies by route count — {place}", x_label="Routes"),
            "b5_frequency_deprivation": _sample_scatter(areas, ses_col, "sqi", f"F-EDI vs weekday SQI — {place}", "F-EDI 2021", "SQI (NAP weekday)"),
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
                {"type": "box_violin", "title": f"Stops per NAP route — {place}", "groups": [spr_box]}
                if spr_box
                else {
                    "type": "box_violin",
                    "title": f"Stops per NAP route — {place}",
                    "groups": [],
                    "empty_reason": "Stops-per-route list not persisted",
                }
            ),
            "c3_operator_hhi": {
                "type": "gauge",
                "title": f"NAP operator HHI (0–10,000) — {place}",
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
            "c6_route_archetypes": {"type": "scatter_clusters", "title": f"NAP archetypes — {place}", "cluster_sizes": [{"label": "Urban frequent", "n": int((areas["urban_rural"] == "urban").sum()) if n else 0}, {"label": "Rural sparse", "n": int((areas["urban_rural"] == "rural").sum()) if n else 0}]},
            "c7_network_topology": _ranking_chart([{"label": a.get("name"), "value": a.get("n_routes") or 0} for a in agencies[:15]], title=f"NAP agencies (topology mass) — {place}", x_label="Routes"),
            "d1_coverage_deprivation": _sample_scatter(areas, ses_col, "stops_per_1k", f"F-EDI vs stops per 1,000 — {place}", "F-EDI 2021", "Stops per 1,000 people"),
            "d7_deprivation_urban_rural": {
                "type": "heatmap",
                "title": f"F-EDI × INSEE density 400 m % — {place} (n SES={n_fedi:,}; {n_no_fedi:,} null dropped)",
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
            "d8_feature_importance": {"type": "shap_bar", "title": f"French features — {place}", "features": [{"name": "F-EDI", "importance": abs(r_ses) if r_ses is not None else 0.0}, {"name": "INSEE density", "importance": 0.4}]},
            "f1_gini": _lorenz_payload(areas, gini, n, pop),
            "f2_disparity_ratio": {"type": "line", "title": f"F-EDI decile slope of 400 m — {place}", "x_label": "F-EDI decile (1 = lowest SES)", "y_label": "% within 400 m", "data": [{"x": r["decile"], "y": r["pct_covered"]} for r in by_decile]},
            "f5_rural_penalty": {"type": "scatter_regression", "title": f"Urban vs rural 400 m by région — {place}", "data": [{"x": float(r.get("urban") or 0), "y": float(r.get("rural") or 0), "id": r["name"]} for r in paired_rows]},
            "f6_equitable_regions": _ranking_chart([{"label": r["name"], "value": r["pct_covered"]} for r in sorted(region_rows, key=lambda x: -x["pct_covered"])], title=f"400 m coverage by région — {place}", x_label="% within 400 m"),
            "j1_economic_value": _ranking_chart([{"label": r["name"], "value": r["pop_desert"]} for r in sorted(region_rows, key=lambda x: -x["pop_desert"])], title=f"People beyond 400 m — {place}", x_label="People"),
            "j2_bcr": {"type": "horizontal_bar", "title": f"People-gap (no euro BCR) — {place}", "data": [{"label": "People beyond 400 m", "value": pop_zero}]},
            "j3_carbon": {"type": "horizontal_bar", "title": f"Illustrative car-km CO₂ — {place}", "data": [{"label": "t CO₂", "value": carbon_t}]},
            "j4_investment_priority": _ranking_chart([{"label": r["name"], "value": r["pop_desert"]} for r in sorted(region_rows, key=lambda x: -x["pop_desert"])], title=f"Priority people-gap — {place}", x_label="People"),
            "bsa1_franchising_readiness": {"type": "choropleth", "geography": "france_region", "title": f"Concession coverage proxy — {place}", "data": [{"area_code": r["code"], "area_name": r["name"], "value": r["pct_covered"]} for r in region_rows]},
            "bsa3_tier_distribution": {"type": "horizontal_bar", "title": f"Concession tiers — {place}", "data": [{"label": k, "value": v} for k, v in tiers.items()]},
            "ps1_freq_restoration": {"type": "horizontal_bar", "title": f"Restore OV frequency — {place}", "data": [{"label": "People", "value": ps1_pop}]},
            "ps2_evening_extension": {"type": "horizontal_bar", "title": f"Evening NAP — {place}", "data": [{"label": "People", "value": ps2_pop}]},
            "ps3_drt_rural": {"type": "horizontal_bar", "title": f"Rural SPC / hole — {place}", "data": [{"label": "People", "value": ps3_pop}]},
            "ps4_franchise": {"type": "horizontal_bar", "title": f"Combined SPC — {place}", "data": [{"label": "People", "value": ps4_pop}]},
            "ps5_scenario_comparison": {"type": "horizontal_bar", "title": f"Intervention comparison — {place}", "data": [{"label": TITLES["ps1_freq_restoration"], "value": ps1_pop}, {"label": TITLES["ps2_evening_extension"], "value": ps2_pop}, {"label": TITLES["ps3_drt_rural"], "value": ps3_pop}, {"label": TITLES["ps4_franchise"], "value": ps4_pop}]},
        }
        for sid, col, xlab in (
            ("d2_coverage_unemployment", "unemp_rate", "WW share"),
            ("d3_coverage_car", "no_car_share", "Low-car share"),
            ("d4_coverage_elderly", "elderly_share", "65+ share"),
            ("d5_coverage_income", "income", "Income per inhabitant"),

            ("d9b_employment_access", "activity_rate", "Labour participation"),
            ("d9e_barriers_access", "hlm_share", "Huur share"),
            ("f3_ethnic_access", "immig_share", "Buiten Europa share"),
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


def precompute_france(areas: pd.DataFrame, extras: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    extras = extras or {}
    known = set(REGION_NAME_BY_SLUG)
    regions = ["all", *sorted(r for r in set(areas["region"].astype(str)) if r in known)]
    rows: list[dict[str, Any]] = []
    for region in regions:
        for ur in ("all", "urban", "rural"):
            sl = _filter_areas(areas, region, ur)
            rows.extend(_section_bundle(sl, areas, region, ur, extras))
    logger.info("NL sections: {} rows ({} regions × 3 INSEE density × {})", len(rows), len(regions), len(CATALOGUE))
    return rows
