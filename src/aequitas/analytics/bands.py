"""Aequitas access / service bands.

Not TfL PTAL. Not labelled official PTAL.

Two schemes, one integer scale 1–6:

* **service** — 400 m stop presence + weekday SQI / evening / Sunday.
  Allowed when r5py times are missing. Must never be called 45-minute jobs.
* **travel_time** — destination counts at 15/30/45 from the reach parquet.
  Only assigned when that LSOA has reach rows. Not Hansen.

Hansen needs origin–destination *minutes*. The Wave 2 parquet stores
destination *counts* (`t_15`/`t_30`/`t_45`). We do not invent Hansen from counts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from aequitas.analytics.reach import DEST_TYPES, ITL1_NAMES, reach_output_path

BANDS_NAME = "lsoa_access_bands.parquet"
BANDS_META = "lsoa_access_bands.meta.json"

ITL1_NAME_TO_CODE = {v: k for k, v in ITL1_NAMES.items()}

# One-LSOA authorities that never inherit a neighbour in the same LAD.
_LAD_ITL1_FALLBACK: dict[str, tuple[str, str]] = {
    "E06000053": ("South West", "E12000009"),  # Isles of Scilly
}

SERVICE_SCHEME = "service"
TRAVEL_SCHEME = "travel_time"

BAND_LABELS: dict[int, str] = {
    1: "1 — no nearby stop or no weekday service",
    2: "2 — stop nearby, evening and Sunday isolated",
    3: "3 — thin weekday service",
    4: "4 — moderate weekday service",
    5: "5 — good weekday service",
    6: "6 — high weekday quality",
}

TRAVEL_BAND_LABELS: dict[int, str] = {
    1: "1 — no destinations in 45 minutes",
    2: "2 — destinations only beyond 30 minutes",
    3: "3 — few destinations in 30 minutes",
    4: "4 — moderate 30-minute catchment",
    5: "5 — strong 30-minute, limited 15-minute",
    6: "6 — many destinations in 15 minutes",
}

FORMULA_SERVICE = (
    "service band (no travel-time model): "
    "band 1 if stop_count = 0 or no_service; "
    "band 2 if a stop exists and evening_isolated and sunday_desert; "
    "else SQI < 30 → 3, < 50 → 4, < 70 → 5, else 6. "
    "Not TfL PTAL. Not 45-minute job access."
)

FORMULA_TRAVEL = (
    "travel-time band (jobs counts from r5py): "
    "band 1 if t_45 = 0; band 2 if t_30 = 0; "
    "band 3 if t_30 < 10; band 4 if t_30 < 50; "
    "band 5 if t_15 < 20; else 6. "
    "Not TfL PTAL. Not Hansen."
)

HANSEN_BETA = 0.05  # documented; used only with minutes, never with counts


def assign_service_band(
    *,
    stop_count: float | int | None,
    no_service: bool | int | None = False,
    evening_isolated: bool | int | None = False,
    sunday_desert: bool | int | None = False,
    sqi: float | None = None,
) -> tuple[int, str]:
    """Exact band from known inputs — used by tests and the writer."""
    stops = 0 if stop_count is None or pd.isna(stop_count) else float(stop_count)
    if stops <= 0 or bool(no_service):
        return 1, "No stop within 400 m or no weekday service."
    if bool(evening_isolated) and bool(sunday_desert):
        return 2, "A stop is nearby but evening and Sunday service are isolated."
    score = 0.0 if sqi is None or pd.isna(sqi) else float(sqi)
    if score < 30:
        return 3, f"Weekday service quality index {score:.0f} (thin)."
    if score < 50:
        return 4, f"Weekday service quality index {score:.0f} (moderate)."
    if score < 70:
        return 5, f"Weekday service quality index {score:.0f} (good)."
    return 6, f"Weekday service quality index {score:.0f} (high)."


def assign_travel_band(
    *,
    t_15: float | int | None,
    t_30: float | int | None,
    t_45: float | int | None,
) -> tuple[int, str]:
    """Band from destination *counts* at 15/30/45. Not Hansen."""
    a = 0 if t_15 is None or pd.isna(t_15) else int(t_15)
    b = 0 if t_30 is None or pd.isna(t_30) else int(t_30)
    c = 0 if t_45 is None or pd.isna(t_45) else int(t_45)
    if c <= 0:
        return 1, "No jobs (or chosen destinations) reachable in 45 minutes."
    if b <= 0:
        return 2, "Destinations reachable only between 30 and 45 minutes."
    if b < 10:
        return 3, f"{b} destinations in 30 minutes (few)."
    if b < 50:
        return 4, f"{b} destinations in 30 minutes (moderate)."
    if a < 20:
        return 5, f"{a} destinations in 15 minutes; {b} in 30."
    return 6, f"{a} destinations in 15 minutes (many)."


def hansen_from_minutes(minutes: pd.Series, weights: pd.Series | None = None, *, beta: float = HANSEN_BETA) -> float:
    """sum dest_weight × exp(−βt). Only for real travel times in minutes."""
    import math

    t = pd.to_numeric(minutes, errors="coerce")
    w = pd.Series(1.0, index=t.index) if weights is None else pd.to_numeric(weights, errors="coerce").fillna(0.0)
    mask = t.notna() & (t >= 0)
    if not mask.any():
        return 0.0
    return float((w[mask] * t[mask].map(lambda m: math.exp(-beta * float(m)))).sum())


def bands_output_path(processed_dir: Path) -> Path:
    return processed_dir / "reach" / BANDS_NAME


def _truthy(val: Any) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    if isinstance(val, str):
        return val.strip().lower() in {"1", "true", "yes", "t"}
    return bool(val)


def _norm_urban(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def _region_code_series(names: pd.Series) -> pd.Series:
    return names.astype(str).map(lambda n: ITL1_NAME_TO_CODE.get(n, n))


def _is_unknown_region(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    return s.isin({"Unknown", "nan", "None", ""}) | series.isna()


def repair_region_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Fill Unknown ITL1 from the same LAD's known name, then a tiny LAD fallback.

    Remaining Unknown rows stay in people totals but never become a map feature.
    """
    if df.empty or "region" not in df.columns:
        return df
    work = df.copy()
    work["region"] = work["region"].astype(str)
    unk = _is_unknown_region(work["region"])
    if "lad_cd" in work.columns:
        known = work.loc[~unk]
        if not known.empty:
            mode_nm = known.groupby("lad_cd")["region"].agg(
                lambda s: s.mode().iloc[0] if not s.mode().empty else pd.NA
            )
            work.loc[unk, "region"] = work.loc[unk, "lad_cd"].map(mode_nm)
        for lad, (name, _code) in _LAD_ITL1_FALLBACK.items():
            work.loc[work["lad_cd"].astype(str).eq(lad), "region"] = name
    still = _is_unknown_region(work["region"])
    work.loc[still, "region"] = "Unknown"
    work["region_code"] = _region_code_series(work["region"])
    return work


def load_service_quality(cfg) -> pd.DataFrame:
    for cand in (
        cfg.processed_dir / "lsoa_service_quality.parquet",
        cfg.audit_dir / "lsoa_service_quality.parquet",
    ):
        if cand.exists():
            df = pd.read_parquet(cand)
            if "LSOA21CD" in df.columns and "lsoa" not in df.columns:
                df = df.rename(columns={"LSOA21CD": "lsoa"})
            if "lsoa_cd" in df.columns and "lsoa" not in df.columns:
                df = df.rename(columns={"lsoa_cd": "lsoa"})
            return df
    return pd.DataFrame()


def load_demographics(cfg) -> pd.DataFrame:
    df = pd.DataFrame()
    warehouse = cfg.warehouse_path
    if warehouse.exists():
        import duckdb

        con = duckdb.connect(str(warehouse), read_only=True)
        try:
            tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
            if "lsoa_demographics" in tables:
                df = con.execute("SELECT * FROM lsoa_demographics").df()
        finally:
            con.close()
    if df.empty or ("region" in df.columns and df["region"].astype(str).eq("Unknown").all()):
        for cand in (
            cfg.processed_dir / "master_lsoa_table.parquet",
            cfg.audit_dir / "master_lsoa_table.parquet",
        ):
            if cand.exists():
                alt = pd.read_parquet(cand)
                if df.empty:
                    df = alt
                elif "region" in alt.columns and not alt["region"].astype(str).eq("Unknown").all():
                    df = alt
                break
    if df.empty:
        return df
    if "lsoa_cd" in df.columns and "lsoa" not in df.columns:
        df = df.rename(columns={"lsoa_cd": "lsoa"})
    return df


def write_access_bands(cfg, reach_df: pd.DataFrame | None = None) -> Path | None:
    """Write processed/reach/lsoa_access_bands.parquet for every LSOA we can join."""
    demo = load_demographics(cfg)
    if demo.empty:
        logger.warning("No demographics — cannot write access bands")
        return None
    sq = load_service_quality(cfg)
    work = demo.copy()
    if "lsoa" not in work.columns:
        logger.warning("Demographics missing lsoa column")
        return None
    work["lsoa"] = work["lsoa"].astype(str)
    if not sq.empty:
        keep = [
            c
            for c in (
                "lsoa",
                "no_service",
                "evening_isolated",
                "sunday_desert",
                "service_quality_index",
            )
            if c in sq.columns
        ]
        work = work.merge(sq[keep], on="lsoa", how="left")
    for col in ("no_service", "evening_isolated", "sunday_desert"):
        if col not in work.columns:
            work[col] = False
    if "service_quality_index" not in work.columns:
        work["service_quality_index"] = None
    if "stop_count" not in work.columns:
        work["stop_count"] = work["has_bus"].map(lambda x: 1 if _truthy(x) else 0) if "has_bus" in work.columns else 0

    svc = work.apply(
        lambda r: assign_service_band(
            stop_count=r.get("stop_count"),
            no_service=_truthy(r.get("no_service")),
            evening_isolated=_truthy(r.get("evening_isolated")),
            sunday_desert=_truthy(r.get("sunday_desert")),
            sqi=r.get("service_quality_index"),
        ),
        axis=1,
    )
    work["service_band"] = [t[0] for t in svc]
    work["service_why"] = [t[1] for t in svc]

    reach = reach_df
    if reach is None:
        rpath = reach_output_path(cfg.processed_dir)
        if rpath.exists():
            reach = pd.read_parquet(rpath)
    jobs = pd.DataFrame()
    if reach is not None and not reach.empty and "dest_type" in reach.columns:
        jobs = reach[reach["dest_type"] == "jobs"].copy()
        jobs["lsoa"] = jobs["lsoa"].astype(str)
    work = work.merge(
        jobs[["lsoa", "t_15", "t_30", "t_45"]] if not jobs.empty else pd.DataFrame(columns=["lsoa", "t_15", "t_30", "t_45"]),
        on="lsoa",
        how="left",
    )
    has_tt = work["t_45"].notna() if "t_45" in work.columns else pd.Series(False, index=work.index)
    travel = work.apply(
        lambda r: assign_travel_band(t_15=r.get("t_15"), t_30=r.get("t_30"), t_45=r.get("t_45"))
        if pd.notna(r.get("t_45"))
        else (None, None),
        axis=1,
    )
    work["travel_band"] = [t[0] for t in travel]
    work["travel_why"] = [t[1] for t in travel]
    work["scheme"] = [TRAVEL_SCHEME if ok else SERVICE_SCHEME for ok in has_tt]
    work["band"] = work["travel_band"].where(has_tt, work["service_band"]).astype(int)
    work["why"] = work["travel_why"].where(has_tt, work["service_why"])
    if "region" in work.columns:
        work = repair_region_labels(work)
    else:
        work["region_code"] = None
    work["urban_rural_norm"] = _norm_urban(work["urban_rural"]) if "urban_rural" in work.columns else "all"

    out_cols = [
        "lsoa",
        "lsoa_nm" if "lsoa_nm" in work.columns else None,
        "lad_cd" if "lad_cd" in work.columns else None,
        "lad_nm" if "lad_nm" in work.columns else None,
        "region" if "region" in work.columns else None,
        "region_code",
        "urban_rural" if "urban_rural" in work.columns else None,
        "urban_rural_norm",
        "population" if "population" in work.columns else None,
        "imd_decile" if "imd_decile" in work.columns else None,
        "stop_count",
        "band",
        "scheme",
        "why",
        "service_band",
        "travel_band",
    ]
    cols = [c for c in out_cols if c]
    frame = work[cols].copy()
    out = bands_output_path(cfg.processed_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, index=False)
    meta = {
        "written_at": datetime.now(timezone.utc).isoformat(),
        "rows": int(len(frame)),
        "n_travel_time": int((frame["scheme"] == TRAVEL_SCHEME).sum()),
        "n_service": int((frame["scheme"] == SERVICE_SCHEME).sum()),
        "formula_service": FORMULA_SERVICE,
        "formula_travel": FORMULA_TRAVEL,
        "hansen": "not computed — parquet stores destination counts, not minutes",
        "not_tfl_ptal": True,
    }
    (out.parent / BANDS_META).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Wrote {} ({} rows, {} travel-time)", out, len(frame), meta["n_travel_time"])
    return out


def filter_bands(
    df: pd.DataFrame,
    *,
    region: str = "all",
    urban_rural: str = "all",
) -> pd.DataFrame:
    work = df
    if region and region != "all":
        if "region_code" in work.columns:
            work = work[work["region_code"] == region]
        elif "region" in work.columns:
            name = ITL1_NAMES.get(region, region)
            work = work[work["region"].isin([region, name])]
    if urban_rural and urban_rural != "all" and "urban_rural_norm" in work.columns:
        work = work[work["urban_rural_norm"] == urban_rural.lower()]
    elif urban_rural and urban_rural != "all" and "urban_rural" in work.columns:
        work = work[_norm_urban(work["urban_rural"]) == urban_rural.lower()]
    return work


def summarise_bands(
    df: pd.DataFrame,
    *,
    region: str = "all",
    urban_rural: str = "all",
) -> dict[str, Any]:
    """Filter-sensitive exhibit: map + people × IMD decile."""
    if region == "E12000007" and urban_rural == "rural":
        return {
            "empty": True,
            "empty_reason": "London has no rural LSOAs under the official classification.",
            "mode": SERVICE_SCHEME,
            "not_tfl_ptal": True,
            "hansen_available": False,
            "map": {"geography": "region", "data": []},
            "people_by_band_decile": [],
            "band_totals": [],
            "n_areas": 0,
            "people": 0,
            "pct_worst_two": None,
            "narrative": "London has no rural LSOAs under the official classification.",
            "formula": FORMULA_SERVICE,
            "geographies_with_times": [],
        }
    work = filter_bands(repair_region_labels(df), region=region, urban_rural=urban_rural)
    if work.empty:
        return {
            "empty": True,
            "empty_reason": "No areas match this filter.",
            "mode": SERVICE_SCHEME,
            "not_tfl_ptal": True,
            "hansen_available": False,
            "map": {"geography": "region", "data": []},
            "people_by_band_decile": [],
            "band_totals": [],
            "n_areas": 0,
            "people": 0,
            "pct_worst_two": None,
            "narrative": "No areas match this filter.",
            "formula": FORMULA_SERVICE,
            "geographies_with_times": [],
        }

    n_tt = int((work["scheme"] == TRAVEL_SCHEME).sum()) if "scheme" in work.columns else 0
    mode = TRAVEL_SCHEME if n_tt == len(work) else SERVICE_SCHEME if n_tt == 0 else "mixed"
    pop = pd.to_numeric(work.get("population", pd.Series(0, index=work.index)), errors="coerce").fillna(0)
    worst = work["band"].isin([1, 2])
    people_total = float(pop.sum())
    people_worst = float(pop[worst].sum())
    pct_worst = (100.0 * people_worst / people_total) if people_total else None

    by = (
        work.assign(_pop=pop, _dec=pd.to_numeric(work.get("imd_decile", 0), errors="coerce").fillna(0).astype(int))
        .groupby(["band", "_dec"], dropna=False)
        .agg(people=("_pop", "sum"), n_areas=("lsoa", "nunique"))
        .reset_index()
        .rename(columns={"_dec": "imd_decile"})
    )
    people_by = [
        {
            "band": int(r.band),
            "imd_decile": int(r.imd_decile),
            "people": int(r.people),
            "n_areas": int(r.n_areas),
        }
        for r in by.itertuples(index=False)
    ]
    totals = (
        work.assign(_pop=pop)
        .groupby("band")
        .agg(people=("_pop", "sum"), n_areas=("lsoa", "nunique"))
        .reset_index()
    )
    band_totals = [
        {
            "band": int(r.band),
            "label": (TRAVEL_BAND_LABELS if mode == TRAVEL_SCHEME else BAND_LABELS).get(int(r.band), str(r.band)),
            "people": int(r.people),
            "n_areas": int(r.n_areas),
        }
        for r in totals.itertuples(index=False)
    ]

    map_payload = _band_map(work, region)
    unmatched_mask = _is_unknown_region(work["region"]) if "region" in work.columns else pd.Series(False, index=work.index)
    unmatched_people = int(pop[unmatched_mask].sum()) if unmatched_mask.any() else 0
    unmatched_areas = int(work.loc[unmatched_mask, "lsoa"].nunique()) if unmatched_mask.any() else 0
    unmatched_note = None
    if unmatched_people:
        unmatched_note = (
            f"{unmatched_people:,} people in {unmatched_areas:,} LSOAs have no ITL1 "
            "after the LAD backfill — unmatched (excluded from the map)."
        )
    geographies = []
    if "region_code" in work.columns:
        geographies = sorted({str(c) for c in work.loc[work.get("scheme") == TRAVEL_SCHEME, "region_code"].dropna().unique()})

    place = ITL1_NAMES.get(region, "England") if region != "all" else "England"
    if urban_rural and urban_rural != "all":
        place = f"{place} {urban_rural}"
    n = int(work["lsoa"].nunique())
    narrative = (
        f"In {place}, {n:,} LSOAs are assigned an Aequitas "
        f"{'access' if mode == TRAVEL_SCHEME else 'service'} band. "
        f"{people_worst:,.0f} people ({pct_worst:.1f}% of {people_total:,.0f}) live in the worst two bands."
        if pct_worst is not None
        else f"In {place}, {n:,} LSOAs are assigned a band."
    )
    if mode == SERVICE_SCHEME:
        narrative += " This is a service band (no travel-time model) — not 45-minute job access, not official PTAL."
    elif mode == "mixed":
        narrative += f" {n_tt:,} LSOAs use r5py travel-time bands; the rest use the service band."
    else:
        narrative += " Bands use r5py destination counts. Not official PTAL. Not Hansen."

    return {
        "empty": False,
        "empty_reason": None,
        "mode": mode,
        "label": (
            "Aequitas service band (no travel-time model)"
            if mode == SERVICE_SCHEME
            else "Aequitas access band"
        ),
        "not_tfl_ptal": True,
        "hansen_available": False,
        "hansen_note": (
            "Hansen-style index needs origin–destination minutes (sum dest × exp(−βt), β="
            f"{HANSEN_BETA}). This pack stores destination counts, not minutes."
        ),
        "map": map_payload,
        "map_aggregation": map_payload.get("aggregation"),
        "unmatched_people": unmatched_people,
        "unmatched_areas": unmatched_areas,
        "unmatched_note": unmatched_note,
        "people_by_band_decile": people_by,
        "band_totals": band_totals,
        "n_areas": n,
        "people": int(people_total),
        "pct_worst_two": pct_worst,
        "narrative": narrative,
        "formula": FORMULA_TRAVEL if mode == TRAVEL_SCHEME else FORMULA_SERVICE,
        "geographies_with_times": geographies,
        "coverage_400m_share": _coverage_share(work),
    }


def _coverage_share(work: pd.DataFrame) -> float | None:
    if "stop_count" not in work.columns or "population" not in work.columns:
        return None
    pop = pd.to_numeric(work["population"], errors="coerce").fillna(0)
    if float(pop.sum()) <= 0:
        return None
    covered = pop[pd.to_numeric(work["stop_count"], errors="coerce").fillna(0) > 0]
    return float(covered.sum() / pop.sum())


def _band_map(work: pd.DataFrame, region: str) -> dict[str, Any]:
    pop = pd.to_numeric(work.get("population", 0), errors="coerce").fillna(0)
    work = work.assign(_pop=pop)
    national = region == "all" or "lad_cd" not in work.columns
    if national:
        grp_col, name_col, geo = "region_code", "region", "region"
        if "region_code" not in work.columns:
            return {"geography": "region", "metric_label": "Aequitas band", "data": []}
    else:
        grp_col, name_col, geo = "lad_cd", "lad_nm" if "lad_nm" in work.columns else "lad_cd", "lad"

    rows = []
    for key, g in work.groupby(grp_col):
        if key is None or (isinstance(key, float) and pd.isna(key)):
            continue
        code = str(key)
        if code in {"Unknown", "nan", "None", ""} or not code.startswith("E"):
            continue
        people = int(g["_pop"].sum())
        worst = float(g.loc[g["band"].isin([1, 2]), "_pop"].sum())
        pct_worst = round(100.0 * worst / people, 1) if people else 0.0
        weighted = g.groupby("band")["_pop"].sum()
        band = int(weighted.idxmax()) if not weighted.empty else int(g["band"].mode().iloc[0])
        why = str(g.loc[g["band"] == band, "why"].mode().iloc[0]) if (g["band"] == band).any() else ""
        dec = pd.to_numeric(g.get("imd_decile", 0), errors="coerce")
        name = str(g[name_col].iloc[0]) if name_col in g.columns else code
        if national:
            hover = (
                f"{name}: {pct_worst:.1f}% of {people:,} people in bands 1–2 "
                f"(modal band {band}). National map is share in 1–2, not mean SQI."
            )
            rows.append(
                {
                    "area_code": code,
                    "area_name": name,
                    "value": pct_worst,
                    "people": people,
                    "pct_worst_two": pct_worst,
                    "modal_band": band,
                    "imd_decile": int(dec.median()) if dec.notna().any() else None,
                    "why": why,
                    "hover": hover,
                }
            )
        else:
            hover = f"{name}: band {band}; {people:,} people; {why}"
            rows.append(
                {
                    "area_code": code,
                    "area_name": name,
                    "value": band,
                    "people": people,
                    "imd_decile": int(dec.median()) if dec.notna().any() else None,
                    "why": why,
                    "hover": hover,
                }
            )
    if national:
        return {
            "geography": geo,
            "metric_label": "% of people in bands 1–2",
            "data": rows,
            "color_mode": "continuous",
            "aggregation": (
                "ITL1 choropleth is the share of people in service bands 1–2 "
                "(not modal SQI, not mean SQI). Unmatched LSOAs are excluded from the map."
            ),
        }
    return {
        "geography": geo,
        "metric_label": "Aequitas band (1 worst – 6 best)",
        "data": rows,
        "color_mode": "band",
        "aggregation": "LAD map is the population-weighted modal service band.",
    }
