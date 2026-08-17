"""End-to-end France pack: download → process → warehouse.

Never touches data/aequitas.duckdb, aequitas_ireland.duckdb, or aequitas_netherlands.duckdb.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.analytics.score import compute_score
from aequitas.core.config import PipelineConfig
from aequitas.france.constants import (
    DENSITY_NOTE,
    MAINLAND_DEPS,
    region_from_insee_reg,
    slug_region,
    iris_text,
)
from aequitas.france.download import (
    download_fedi_iris,
    download_filosofi_iris,
    download_insee_density,
    download_insee_iris_pop,
    download_iris_wfs,
    download_nap_gtfs,
    download_region_geojson,
    write_download_manifest,
)
from aequitas.france.network import load_nap_network
from aequitas.france.process import (
    build_fr_areas,
    fedi_decile_from_score,
    merge_nap_feeds,
    write_processed,
)
from aequitas.france.warehouse import build_france_warehouse, france_warehouse_path


def _load_fedi(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="EDI2021_IRIS", dtype={"IRIS": str, "REG": str, "DEP": str, "COM": str})
    out = pd.DataFrame(
        {
            "iris_code": df["IRIS"].map(iris_text),
            "reg": df["REG"].astype(str).str.replace(".0", "", regex=False).str.zfill(2),
            "dep": df["DEP"].astype(str).str.replace(".0", "", regex=False),
            "com": df["COM"].astype(str).str.replace(".0", "", regex=False).str.zfill(5),
            "fedi_score": pd.to_numeric(df["EDI2021"], errors="coerce"),
        }
    )
    out["region"] = out["reg"].map(region_from_insee_reg)
    return out.drop_duplicates("iris_code")


def _load_density(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["com", "density_level"])
    xl = pd.ExcelFile(path)
    sheet = xl.sheet_names[0]
    for s in xl.sheet_names:
        if "2024" in s or "dens" in s.lower() or "commune" in s.lower():
            sheet = s
            break
    header = 0
    peek = pd.read_excel(path, sheet_name=sheet, header=None, nrows=8)
    for i in range(len(peek)):
        vals = [str(v).strip().upper() for v in peek.iloc[i].tolist()]
        if "CODGEO" in vals or "DENS" in vals:
            header = i
            break
    df = pd.read_excel(path, sheet_name=sheet, header=header, dtype=str)
    cols = {c.lower(): c for c in df.columns}

    def pick(*names: str) -> str | None:
        for n in names:
            if n.lower() in cols:
                return cols[n.lower()]
        for key, orig in cols.items():
            if any(n in key for n in names):
                return orig
        return None

    com = pick("codgeo", "com", "code", "depcom")
    dens = pick("dens", "densite", "p-densite", "d7", "grille", "typologie")
    if com is None:
        logger.warning("Density file columns: {}", list(df.columns))
        return pd.DataFrame(columns=["com", "density_level"])
    out = pd.DataFrame({"com": df[com].astype(str).str.replace(".0", "", regex=False).str.zfill(5)})
    if dens:
        out["density_level"] = pd.to_numeric(df[dens], errors="coerce")
    else:
        # last numeric-looking column
        for c in df.columns[::-1]:
            num = pd.to_numeric(df[c], errors="coerce")
            if num.notna().mean() > 0.5:
                out["density_level"] = num
                break
    return out.dropna(subset=["com"]).drop_duplicates("com")


def _load_iris_pop(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    extract = path.parent / "iris_pop_extract"
    extract.mkdir(parents=True, exist_ok=True)
    if not any(extract.glob("*")):
        with ZipFile(path) as zf:
            zf.extractall(extract)
    csvs = [p for p in extract.rglob("*") if p.suffix.lower() == ".csv"]
    if not csvs:
        logger.warning("No CSV in {}", path)
        return pd.DataFrame()
    # Prefer the IRIS table, not the meta dictionary
    iris_csvs = [p for p in csvs if "meta" not in p.name.lower()]
    use = iris_csvs[0] if iris_csvs else csvs[0]
    df = pd.read_csv(use, sep=";", dtype=str, low_memory=False)
    if df.shape[1] == 1:
        df = pd.read_csv(use, dtype=str, low_memory=False)
    cols = {c.upper(): c for c in df.columns}

    def col(*cands: str) -> str | None:
        for c in cands:
            if c.upper() in cols:
                return cols[c.upper()]
        for key, orig in cols.items():
            if any(c.upper() in key for c in cands):
                return orig
        return None

    iris = col("IRIS", "CODE_IRIS", "COMIRIS")
    if iris is None:
        logger.warning("IRIS pop columns: {}", list(df.columns)[:30])
        return pd.DataFrame()
    out = pd.DataFrame({"iris_code": df[iris].map(iris_text)})
    pop = col("P18_POP", "P17_POP", "P16_POP", "POP")
    if pop:
        out["population"] = pd.to_numeric(df[pop], errors="coerce")
    eld = col("P18_POP65P", "P18_POP65P_PLUS", "P17_POP65P")
    if eld and pop:
        out["elderly_share"] = pd.to_numeric(df[eld], errors="coerce") / out["population"].replace(0, np.nan)
    chom = col("P18_CHOM1564", "P18_CHOM15P", "C18_POP15P_CS8")
    act = col("P18_ACT1564", "P18_ACT15P")
    if chom and act:
        out["unemp_rate"] = pd.to_numeric(df[chom], errors="coerce") / pd.to_numeric(df[act], errors="coerce").replace(
            0, np.nan
        )
    if act and pop:
        out["activity_rate"] = pd.to_numeric(df[act], errors="coerce") / out["population"].replace(0, np.nan)
    men0 = col("C18_MEN_VOIT0", "P18_RP_VOIT0", "C18_MENVOIT0")
    men = col("C18_MEN", "P18_MEN")
    if men0 and men:
        out["no_car_share"] = pd.to_numeric(df[men0], errors="coerce") / pd.to_numeric(df[men], errors="coerce").replace(
            0, np.nan
        )
    imm = col("P18_POP_IMM", "P18_POPIMM", "P18_IMMI")
    if imm and pop:
        out["immig_share"] = pd.to_numeric(df[imm], errors="coerce") / out["population"].replace(0, np.nan)
    hlm = col("P18_RP_LOCHLMV", "P18_RP_HLM")
    rp = col("P18_RP")
    if hlm and rp:
        out["hlm_share"] = pd.to_numeric(df[hlm], errors="coerce") / pd.to_numeric(df[rp], errors="coerce").replace(
            0, np.nan
        )
    logger.info("INSEE IRIS pop {} rows from {}", len(out), use.name)
    return out.drop_duplicates("iris_code")


def _load_filosofi(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    df = pd.read_excel(path, dtype=str)
    cols = {c.upper(): c for c in df.columns}
    iris = next((cols[k] for k in cols if "IRIS" in k), None)
    inc = next((cols[k] for k in cols if "DISP" in k or "MED" in k or "NIVVIE" in k), None)
    if iris is None or inc is None:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "iris_code": df[iris].map(iris_text),
            "income": pd.to_numeric(df[inc], errors="coerce"),
        }
    ).drop_duplicates("iris_code")


def _score_terms(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    pop = float(df["population"].sum()) or 1.0
    cov = float(df.loc[df["within_400m"], "population"].sum()) / pop
    eve = float(df.loc[~df["evening_isolated"], "population"].sum()) / pop
    freq = float(df["sqi"].mean()) / 100.0 if "sqi" in df else None
    r = None
    work = df.dropna(subset=["fedi_score"]) if "fedi_score" in df.columns else df.iloc[0:0]
    if len(work) > 5 and "stops_per_1k" in work:
        r = float(work["fedi_score"].corr(work["stops_per_1k"]))
        if r != r:
            r = None
    gap = abs(r) if r is not None else None
    return {
        "pop_within_400m": cov,
        "evening_served": eve,
        "weekday_frequency": freq,
        "deprivation_service": gap,
    }


def _missing_deps(stops: pd.DataFrame, areas: pd.DataFrame) -> list[str]:
    """Départements with IRIS but no stop in bbox."""
    if stops.empty or "lon" not in areas:
        return list(MAINLAND_DEPS)
    # IRIS code: 2-digit dep (or 2A/2B)
    have = set()
    for code in areas.loc[areas["stop_count"] > 0, "iris_code"].astype(str):
        if code.startswith("97"):
            continue
        if code[:2] in {"2A", "2B"} or (len(code) >= 2 and code[0] == "2" and code[1] in "AB"):
            have.add(code[:2])
        else:
            have.add(code[:2])
    return [d for d in MAINLAND_DEPS if d not in have]


def _rebuild_from_processed(cfg: PipelineConfig, dest: Path) -> Path | None:
    """Write warehouse from processed IRIS tables without re-reading 441 GTFS zips."""
    bus_p = cfg.processed_dir / "france" / "iris_table_bus.parquet"
    all_p = cfg.processed_dir / "france" / "iris_table_all.parquet"
    if not bus_p.exists():
        return None
    bus = pd.read_parquet(bus_p)
    areas_by_mode = {"bus": bus}
    extras_by_mode: dict[str, dict] = {}
    gtfs_dir = cfg.raw_dir / "france" / "nap_gtfs"
    extras_by_mode["bus"] = load_nap_network(gtfs_dir, mode="bus")
    if all_p.exists():
        areas_by_mode["all"] = pd.read_parquet(all_p)
        extras_by_mode["all"] = load_nap_network(gtfs_dir, mode="all")
    terms_idf = _score_terms(bus[bus["region"] == "ile-de-france"])
    terms_occ = _score_terms(bus[bus["region"] == "occitanie"])
    score_idf = compute_score(terms_idf).score
    score_occ = compute_score(terms_occ).score
    harvest_log = cfg.raw_dir / "france" / "nap_harvest_log.json"
    merged = skipped = 0
    if harvest_log.exists():
        payload = json.loads(harvest_log.read_text(encoding="utf-8"))
        merged = int((payload.get("summary") or {}).get("merged") or 0)
        skipped = int((payload.get("summary") or {}).get("skipped") or 0)
    n_with = int(bus["fedi_score"].notna().sum()) if "fedi_score" in bus else 0
    vintages = {
        "gtfs": f"NAP merged={merged} skipped={skipped}",
        "small_areas": f"IGN WFS CONTOURS-IRIS n={len(bus)}",
        "join_rate": f"{(n_with / len(bus)):.4f}" if len(bus) else "0",
        "score_idf": str(score_idf),
        "score_occ": str(score_occ),
        "nap_merged": str(merged),
        "nap_skipped": str(skipped),
        "harvest_note": f"NAP merged={merged} skipped={skipped}",
        "n_with_index": str(n_with),
        "n_without_index": str(len(bus) - n_with),
    }
    return build_france_warehouse(areas_by_mode, dest, extras_by_mode=extras_by_mode, vintages=vintages, stops_by_mode=None)


def run_france_pack(cfg: PipelineConfig | None = None, *, skip_download: bool = False) -> Path:
    cfg = cfg or PipelineConfig()
    raw = cfg.raw_dir
    dest = france_warehouse_path(cfg.project_root)
    nap_limit = None  # full harvest; set via env if needed

    if skip_download:
        rebuilt = _rebuild_from_processed(cfg, dest)
        if rebuilt is not None:
            return rebuilt

    if not skip_download:
        download_fedi_iris(raw)
        download_insee_density(raw)
        download_insee_iris_pop(raw)
        download_filosofi_iris(raw)
        download_iris_wfs(raw)
        download_region_geojson(
            raw,
            public_boundaries=cfg.project_root / "frontend" / "public" / "boundaries" / "france_regions.geojson",
        )
        download_nap_gtfs(raw, limit=nap_limit)

    fedi_path = raw / "france" / "EDI2021_IRIS_FM.xlsx"
    # also accept data/france/raw copy
    alt_fedi = cfg.project_root / "data" / "france" / "raw" / "EDI2021_IRIS_FM.xlsx"
    if not fedi_path.exists() and alt_fedi.exists():
        fedi_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy2(alt_fedi, fedi_path)

    iris_cent = raw / "france" / "iris_centroids.parquet"
    areas = pd.read_parquet(iris_cent)
    areas["iris_code"] = areas["iris_code"].map(iris_text)
    # drop DOM
    areas = areas[~areas["com"].astype(str).str.startswith("97")].copy()
    areas = areas[~areas["iris_code"].astype(str).str.startswith("97")].copy()
    fedi = _load_fedi(fedi_path)
    areas = areas.merge(fedi, on="iris_code", how="left", suffixes=("", "_fedi"))
    if "com_fedi" in areas.columns:
        areas["com"] = areas["com"].fillna(areas["com_fedi"])
    if "region" not in areas.columns or areas["region"].isna().all():
        areas["region"] = areas.get("reg", pd.Series(index=areas.index)).map(region_from_insee_reg)
    else:
        areas["region"] = areas["region"].fillna(areas.get("reg", pd.Series(index=areas.index)).map(region_from_insee_reg))
    join_rate = float(areas["fedi_score"].notna().mean()) if "fedi_score" in areas else 0.0
    n_with = int(areas["fedi_score"].notna().sum()) if "fedi_score" in areas else 0
    n_without = int(len(areas) - n_with)
    logger.info("F-EDI join rate {:.2%} ({} with / {} without)", join_rate, n_with, n_without)

    dens = _load_density(raw / "france" / "grille_densite_7_niveaux_2024.xlsx")
    if not dens.empty:
        areas["com"] = areas["com"].astype(str).str.zfill(5)
        areas = areas.merge(dens, on="com", how="left")

    pop = _load_iris_pop(raw / "france" / "base-ic-evol-struct-pop-2018_csv.zip")
    if not pop.empty:
        areas = areas.merge(pop, on="iris_code", how="left")
    if "population" not in areas.columns:
        areas["population"] = np.nan
    # residual: keep IRIS with geometry even if pop missing — fill 0 only after documenting
    miss_pop = int(areas["population"].isna().sum())
    logger.info("IRIS missing population: {} / {}", miss_pop, len(areas))
    areas["population"] = pd.to_numeric(areas["population"], errors="coerce").fillna(0)

    filo = _load_filosofi(next((raw / "france").glob("BASE_TD_FILO*.xlsx"), None) if (raw / "france").exists() else None)
    if not filo.empty:
        areas = areas.merge(filo, on="iris_code", how="left")

    if areas["fedi_score"].notna().sum() >= 10:
        areas["fedi_decile"] = fedi_decile_from_score(areas["fedi_score"])
    else:
        areas["fedi_decile"] = np.nan

    gtfs_dir = raw / "france" / "nap_gtfs"
    modes = ("bus", "all")
    areas_by_mode: dict[str, pd.DataFrame] = {}
    extras_by_mode: dict[str, dict] = {}
    stops_by_mode: dict[str, pd.DataFrame] = {}
    missing_by_mode: dict[str, list[str]] = {}
    for mode in modes:
        logger.info("Building FR areas for mode={}", mode)
        stops, stop_times, _merge_meta = merge_nap_feeds(gtfs_dir, mode=mode)
        built = build_fr_areas(areas=areas, stops=stops, stop_times=stop_times)
        write_processed(built, cfg.processed_dir, mode=mode)
        extras = load_nap_network(gtfs_dir, mode=mode)
        extras["missing_deps"] = _missing_deps(stops, built)
        missing_by_mode[mode] = extras["missing_deps"]
        areas_by_mode[mode] = built
        extras_by_mode[mode] = extras
        stops_by_mode[mode] = stops

    bus = areas_by_mode["bus"]
    n = len(bus)
    terms_idf = _score_terms(bus[bus["region"] == "ile-de-france"])
    terms_occ = _score_terms(bus[bus["region"] == "occitanie"])
    score_idf = compute_score(terms_idf).score
    score_occ = compute_score(terms_occ).score
    differ = (
        score_idf is not None
        and score_occ is not None
        and abs(float(score_idf) - float(score_occ)) > 0.5
    )
    logger.info("FR n={} Île-de-France={} Occitanie={} differ={}", n, score_idf, score_occ, differ)
    if n < 20_000:
        raise RuntimeError(f"France warehouse is not IRIS-scale (n={n}). Not writing packReady warehouse.")
    if not differ:
        raise RuntimeError("Île-de-France and Occitanie scores do not differ — still a seed. Not writing.")

    harvest_log = raw / "france" / "nap_harvest_log.json"
    merged = skipped = 0
    if harvest_log.exists():
        payload = json.loads(harvest_log.read_text(encoding="utf-8"))
        merged = int((payload.get("summary") or {}).get("merged") or 0)
        skipped = int((payload.get("summary") or {}).get("skipped") or 0)
    miss = missing_by_mode.get("bus") or []
    harvest_note = f"NAP merged={merged} skipped={skipped}; missing départements={len(miss)} ({','.join(miss[:20])})"
    logger.info(harvest_note)

    vintages = {
        "gtfs": harvest_note,
        "small_areas": f"IGN WFS CONTOURS-IRIS n={n} (numberMatched logged at download)",
        "join_rate": f"{join_rate:.4f}",
        "score_idf": str(score_idf),
        "score_occ": str(score_occ),
        "nap_merged": str(merged),
        "nap_skipped": str(skipped),
        "harvest_note": harvest_note,
        "n_with_index": str(n_with),
        "n_without_index": str(n_without),
        "urban_rural": DENSITY_NOTE,
    }
    write_download_manifest(
        raw,
        {
            "iris_n": n,
            "ign_wfs_target": 49386,
            "fedi_n": 48577,
            "join_rate": join_rate,
            "n_with_index": n_with,
            "n_without_index": n_without,
            "nap_merged": merged,
            "nap_skipped": skipped,
            "missing_deps": miss,
            "score_idf": score_idf,
            "score_occ": score_occ,
            "density": DENSITY_NOTE,
        },
    )
    written = build_france_warehouse(
        areas_by_mode,
        dest,
        extras_by_mode=extras_by_mode,
        vintages=vintages,
        stops_by_mode=stops_by_mode,
    )
    return written
