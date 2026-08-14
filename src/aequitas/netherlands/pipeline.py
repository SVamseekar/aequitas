"""End-to-end Netherlands pack: download → process → warehouse.

Never touches data/aequitas.duckdb or data/aequitas_ireland.duckdb.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.analytics.score import compute_score
from aequitas.core.config import PipelineConfig
from aequitas.netherlands.constants import slug_province
from aequitas.netherlands.download import (
    download_kerncijfers,
    download_ovapi_gtfs,
    download_provincie_geojson,
    download_ses_woa,
    download_wijkbuurtkaart,
    ovapi_gtfs_path,
    write_download_manifest,
)
from aequitas.netherlands.network import load_ovapi_network
from aequitas.netherlands.process import build_nl_areas, load_ovapi_stop_times, load_ovapi_stops, write_processed
from aequitas.netherlands.warehouse import build_netherlands_warehouse, netherlands_warehouse_path

_GM_TO_PROV = {
    # filled from gemeente layer when present
}


def _norm_buurt(raw: object) -> str:
    s = str(raw or "").strip().replace(" ", "")
    if s.startswith("BU") and len(s) >= 10:
        return s[:10]
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) >= 8:
        return "BU" + digits[-8:]
    return s


def _load_buurt_geometry(zip_path: Path) -> pd.DataFrame:
    """Centroids + area + provincie from Wijk- en Buurtkaart (gpkg or shp)."""
    extract = zip_path.parent / "wijkbuurt_extract"
    extract.mkdir(parents=True, exist_ok=True)
    if not any(extract.iterdir()):
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract)
    gpkg = list(extract.rglob("*.gpkg"))
    shps = list(extract.rglob("*buurt*.shp")) + list(extract.rglob("*Buurt*.shp"))
    try:
        import geopandas as gpd
    except ImportError:
        gpd = None  # type: ignore[assignment]
    if gpd is not None and gpkg:
        layers = []
        try:
            import pyogrio

            names = pyogrio.list_layers(gpkg[0])
            layers = names["name"].tolist() if hasattr(names, "columns") else [r[0] for r in names]
        except Exception:  # noqa: BLE001
            layers = ["buurten", "gemeenten"]
        buurt_layer = next((n for n in layers if n.lower() == "buurten" or ("buurt" in n.lower() and "wijk" not in n.lower())), layers[0] if layers else None)
        gdf = gpd.read_file(gpkg[0], layer=buurt_layer)
        gdf = gdf.to_crs(4326)
    elif gpd is not None and shps:
        gdf = gpd.read_file(shps[0]).to_crs(4326)
    else:
        raise FileNotFoundError(f"No buurt geometry in {zip_path} (need geopandas + gpkg/shp)")

    cols = {c.lower(): c for c in gdf.columns}

    def pick(*names: str) -> str | None:
        for n in names:
            if n in cols:
                return cols[n]
        for key, orig in cols.items():
            if any(n in key for n in names):
                return orig
        return None

    code_col = pick("bu_code", "buurtcode", "statcode", "code")
    name_col = pick("bu_naam", "buurtnaam", "statnaam", "naam")
    gm_col = pick("gm_code", "gemeentecode")
    gm_name = pick("gm_naam", "gemeentenaam")
    pv_col = pick("pv_naam", "provincienaam", "prov_naam", "water")
    sted_col = pick("sted", "stedelijkheid", "mate_van_stedelijkheid")
    pop_col = pick("aant_inw", "aantalinwoners", "inwoners")
    opp_col = pick("opp_land", "oppervlakte_land", "opp_tot")
    water_col = pick("water")
    if water_col and water_col in gdf.columns:
        water = gdf[water_col].astype(str).str.upper()
        gdf = gdf[~water.isin({"JA", "J", "1", "TRUE", "B", "WATER"})]
    if code_col is None:
        raise ValueError(f"buurt layer has no code: {list(gdf.columns)}")
    cents = gdf.geometry.centroid
    # area in km2 from projected
    try:
        area = gdf.to_crs(28992).geometry.area / 1e6
    except Exception:  # noqa: BLE001
        area = pd.Series(np.nan, index=gdf.index)
    out = pd.DataFrame(
        {
            "buurt_code": gdf[code_col].map(_norm_buurt),
            "name": gdf[name_col].astype(str) if name_col else gdf[code_col].astype(str),
            "lat": cents.y.astype(float),
            "lon": cents.x.astype(float),
            "area_km2": pd.to_numeric(area, errors="coerce"),
        }
    )
    if sted_col:
        out["stedelijkheid"] = pd.to_numeric(gdf[sted_col], errors="coerce")
    if pop_col:
        out["population"] = pd.to_numeric(gdf[pop_col], errors="coerce")
    if gm_col:
        out["gm_code"] = gdf[gm_col].astype(str).str.strip()
    if gm_name:
        out["gm_name"] = gdf[gm_name].astype(str)
    if pv_col and "water" not in str(pv_col).lower():
        out["region"] = gdf[pv_col].astype(str).map(slug_province)
    elif opp_col:
        out["area_km2"] = pd.to_numeric(gdf[opp_col], errors="coerce") / 100.0  # ha → km² if ha
    # Assign provincie by centroid-in-polygon (gpkg gemeenten has no provincie name).
    prov_path = zip_path.parent / "provincies.geojson"
    if prov_path.exists() and gpd is not None:
        try:
            prov = gpd.read_file(prov_path).to_crs(4326)
            cents_g = gpd.GeoDataFrame(out, geometry=gpd.points_from_xy(out["lon"], out["lat"]), crs=4326)
            joined = gpd.sjoin(cents_g, prov, how="left", predicate="within")
            name_col = next((c for c in ("statnaam", "PV_NAAM", "prov_naam") if c in joined.columns), None)
            if name_col:
                first = joined.groupby(level=0)[name_col].first()
                out = out.copy()
                out["region"] = first.reindex(out.index).map(slug_province)
                logger.info("Provincie spatial join: {} / {} assigned", out["region"].notna().sum(), len(out))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Provincie spatial join failed: {}", exc)
            raise
    logger.info("Buurt geometry: {} rows from {}", len(out), zip_path.name)
    return out.dropna(subset=["lat", "lon"])


def _fill_gm_prov(gem: pd.DataFrame) -> None:
    cols = {c.lower(): c for c in gem.columns}
    gm = cols.get("gm_code") or cols.get("statcode")
    pv = cols.get("pv_naam") or cols.get("provincienaam")
    if gm and pv:
        for a, b in zip(gem[gm].astype(str).str.strip(), gem[pv].astype(str)):
            _GM_TO_PROV[a] = slug_province(b)


def _attach_provincie(areas: pd.DataFrame) -> pd.DataFrame:
    out = areas.copy()
    if "region" not in out.columns or out["region"].isna().all():
        if "gm_code" in out.columns:
            out["region"] = out["gm_code"].map(_GM_TO_PROV)
    # Gemeente-name fallbacks for missing provincie
    if "region" not in out.columns:
        out["region"] = "utrecht"
    out["region"] = out["region"].fillna("unknown")
    return out


def _load_ses(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    cols = {c.lower(): c for c in df.columns}
    geo = cols.get("wijkenenbuurten") or cols.get("regiocodegemeentewijkbuurt_1")
    score = cols.get("gemiddeldescore_29")
    if score is None:
        for c in df.columns:
            if "gemiddeldescore" in c.lower() and "29" in c:
                score = c
                break
    if geo is None or score is None:
        raise ValueError(f"SES-WOA columns not recognised: {list(df.columns)[:20]}")
    out = pd.DataFrame(
        {
            "buurt_code": df[geo].map(_norm_buurt),
            "ses_score": pd.to_numeric(df[score], errors="coerce"),
        }
    )
    out = out[out["buurt_code"].str.startswith("BU", na=False)]
    return out.dropna(subset=["ses_score"]).drop_duplicates("buurt_code")


def _load_kerncijfers(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    cols = {c.lower(): c for c in df.columns}

    def col(*names: str) -> str | None:
        for n in names:
            if n.lower() in cols:
                return cols[n.lower()]
        return None

    geo = col("WijkenEnBuurten", "Codering_3")
    if geo is None:
        raise ValueError(f"Kerncijfers has no geo: {list(df.columns)[:15]}")
    out = pd.DataFrame({"buurt_code": df[geo].map(_norm_buurt)})
    mapping = {
        "population": col("AantalInwoners_5"),
        "elderly_n": col("k_65JaarOfOuder_12"),
        "ww": col("PersonenPerSoortUitkeringWW_89"),
        "cars_per_hh": col("PersonenautoSPerHuishouden_107"),
        "income": col("GemiddeldInkomenPerInwoner_78"),
        "wmo_rel": col("WmoClientenRelatief_94"),
        "labour_part": col("Nettoarbeidsparticipatie_71"),
        "hh": col("HuishoudensTotaal_29"),
        "huur": col("HuurwoningenTotaal_48"),
        "woningen": col("Woningvoorraad_35"),
        "buiten_eu": col("BuitenEuropa_19"),
        "stedelijkheid": col("MateVanStedelijkheid_120"),
        "soort": col("SoortRegio_2"),
        "pv": col("Naam_1"),
    }
    for key, c in mapping.items():
        if c:
            out[key] = df[c]
    if "soort" in out.columns:
        soort = out["soort"].astype(str).str.lower()
        out = out[soort.str.contains("buurt") | out["buurt_code"].str.startswith("BU")]
    else:
        out = out[out["buurt_code"].str.startswith("BU", na=False)]
    for c in out.columns:
        if c != "buurt_code" and c != "soort" and c != "pv":
            out[c] = pd.to_numeric(out[c], errors="coerce")
    pop = out.get("population")
    if pop is not None:
        out["elderly_share"] = out["elderly_n"] / pop.replace(0, np.nan) if "elderly_n" in out else np.nan
        out["unemp_rate"] = out["ww"] / pop.replace(0, np.nan) if "ww" in out else np.nan
        out["buiten_europa_share"] = out["buiten_eu"] / pop.replace(0, np.nan) if "buiten_eu" in out else np.nan
    if "cars_per_hh" in out.columns:
        out["no_car_share"] = (1.0 - out["cars_per_hh"].clip(lower=0, upper=1)).clip(0, 1)
    if "huur" in out.columns and "woningen" in out.columns:
        out["huur_share"] = out["huur"] / out["woningen"].replace(0, np.nan)
    if "wmo_rel" in out.columns:
        out["wmo_share"] = out["wmo_rel"] / 1000.0  # typically per 1000
    return out.drop_duplicates("buurt_code")


def run_netherlands_pack(cfg: PipelineConfig | None = None, *, skip_download: bool = False) -> Path:
    cfg = cfg or PipelineConfig()
    raw = cfg.raw_dir
    dest = netherlands_warehouse_path(cfg.project_root)

    if not skip_download:
        download_ovapi_gtfs(raw)
        download_ses_woa(raw)
        download_kerncijfers(raw)
        download_wijkbuurtkaart(raw)
        download_provincie_geojson(
            raw,
            public_boundaries=cfg.project_root / "frontend" / "public" / "boundaries" / "netherlands_provincies.geojson",
        )

    gtfs = ovapi_gtfs_path(raw)
    if gtfs is None:
        raise FileNotFoundError("OVapi GTFS missing — place data/raw/ovapi/gtfs-nl.zip")
    ses_path = raw / "netherlands" / "ses_woa_86092NED_2023.parquet"
    kern_path = raw / "netherlands" / "kerncijfers_85984NED.parquet"
    wb = raw / "netherlands" / "WijkBuurtkaart_2024_v2.zip"
    if not wb.exists():
        alt = raw / "netherlands" / "WijkBuurtkaart_2025_v1.zip"
        wb = alt if alt.exists() else wb

    areas = _load_buurt_geometry(wb)
    areas = _attach_provincie(areas)
    if ses_path.exists():
        ses = _load_ses(ses_path)
        areas = areas.merge(ses, on="buurt_code", how="left")
        join_rate = float(areas["ses_score"].notna().mean())
        logger.info("SES-WOA join rate: {:.2%}", join_rate)
    else:
        join_rate = 0.0
        areas["ses_score"] = np.nan
    if kern_path.exists():
        kern = _load_kerncijfers(kern_path)
        areas = areas.merge(kern, on="buurt_code", how="left", suffixes=("", "_k"))
        if "population_k" in areas.columns:
            areas["population"] = areas["population"].fillna(areas["population_k"])
        if "stedelijkheid_k" in areas.columns:
            areas["stedelijkheid"] = areas["stedelijkheid"].fillna(areas["stedelijkheid_k"])
    if "population" not in areas.columns:
        areas["population"] = 500.0
    areas["population"] = pd.to_numeric(areas["population"], errors="coerce").fillna(0)
    # drop water / empty
    areas = areas[areas["population"] > 0].copy()
    if areas["ses_score"].notna().sum() >= 10:
        from aequitas.netherlands.process import ses_decile_from_score

        areas["ses_decile"] = ses_decile_from_score(areas["ses_score"])
    else:
        areas["ses_decile"] = np.nan
    # Do not invent SES-WOA scores or deciles for the unmatched share.

    modes = ("bus", "all")
    areas_by_mode: dict[str, pd.DataFrame] = {}
    extras_by_mode: dict[str, dict] = {}
    stops_by_mode: dict[str, pd.DataFrame] = {}
    for mode in modes:
        logger.info("Building NL areas for mode={}", mode)
        stops = load_ovapi_stops(gtfs, mode=mode)
        stop_times = load_ovapi_stop_times(gtfs, mode=mode)
        built = build_nl_areas(areas=areas, stops=stops, stop_times=stop_times)
        write_processed(built, cfg.processed_dir, mode=mode)
        extras = load_ovapi_network(gtfs, mode=mode)
        areas_by_mode[mode] = built
        extras_by_mode[mode] = extras
        stops_by_mode[mode] = stops

    # PackReady gate: census-scale + two provincies differ
    bus = areas_by_mode["bus"]
    n = len(bus)
    terms_nh = _score_terms(bus[bus["region"] == "noord-holland"])
    terms_gr = _score_terms(bus[bus["region"] == "groningen"])
    score_nh = compute_score(terms_nh).score
    score_gr = compute_score(terms_gr).score
    differ = (
        score_nh is not None
        and score_gr is not None
        and abs(float(score_nh) - float(score_gr)) > 0.5
    )
    logger.info("NL n={} Noord-Holland={} Groningen={} differ={}", n, score_nh, score_gr, differ)
    if n < 5_000:
        raise RuntimeError(f"Netherlands warehouse is not census-scale (n={n}). Not writing packReady warehouse.")
    if not differ:
        raise RuntimeError("Noord-Holland and Groningen scores do not differ — still a seed. Not writing.")

    gtfs_mtime = datetime.fromtimestamp(gtfs.stat().st_mtime, tz=timezone.utc).date().isoformat()
    vintages = {
        "gtfs": f"OVapi {gtfs.name} Last-Modified~{gtfs_mtime} ({gtfs.stat().st_size} B)",
        "small_areas": f"CBS Wijk- en Buurtkaart {wb.name} n={n}",
        "join_rate": f"{join_rate:.4f}",
        "stedelijkheid": "MateVanStedelijkheid_120 / STED (1–5)",
        "score_nh": str(score_nh),
        "score_gr": str(score_gr),
    }
    write_download_manifest(
        raw,
        {
            "ses_table": "86092NED",
            "ses_year": "2023",
            "ses_join_rate": join_rate,
            "n_buurten": n,
            "ovapi": vintages["gtfs"],
            "geometry": wb.name,
            "stedelijkheid": vintages["stedelijkheid"],
            "score_noord_holland": score_nh,
            "score_groningen": score_gr,
        },
    )
    built_path = build_netherlands_warehouse(
        areas_by_mode,
        dest,
        extras_by_mode=extras_by_mode,
        vintages=vintages,
        stops_by_mode=stops_by_mode,
    )
    from aequitas.warehouse.packs import ensure_current_registered

    ensure_current_registered("netherlands", built_path, pack_id=datetime.now(timezone.utc).date().isoformat())
    return built_path


def _score_terms(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    pop = float(df["population"].sum()) or 1.0
    cov = float(df.loc[df["within_400m"], "population"].sum()) / pop
    eve = float(df.loc[~df["evening_isolated"], "population"].sum()) / pop
    freq = float(df["sqi"].mean()) / 100.0 if "sqi" in df else None
    r = None
    if "ses_score" in df and "stops_per_1k" in df and df["ses_score"].notna().sum() > 5:
        r = float(df["ses_score"].corr(df["stops_per_1k"]))
        if r != r:
            r = None
    gap = abs(r) if r is not None else None
    return {
        "pop_within_400m": cov,
        "evening_served": eve,
        "weekday_frequency": freq,
        "deprivation_service": gap,
    }
