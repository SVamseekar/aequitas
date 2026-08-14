"""End-to-end Ireland pack: download → process → warehouse.

Failed builds write a temp file and do not touch data/aequitas.duckdb.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.ireland.constants import IRELAND_EVENING_NOTE
from aequitas.ireland.download import (
    download_cso_sa_geojson,
    download_cso_saps,
    download_pobal_hp,
    download_tfi_gtfs,
    tfi_gtfs_path,
)
from aequitas.ireland.constants import slug_county
from aequitas.ireland.process import (
    build_ireland_areas,
    load_pobal_hp,
    load_tfi_stop_times_sample,
    load_tfi_stops,
    write_processed,
)
from aequitas.ireland.warehouse import build_ireland_warehouse, ireland_warehouse_path


def _norm_ed(raw: object) -> str:
    s = str(raw or "").strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    if digits:
        return digits.zfill(6)
    return s


def _load_sa_geojson(path: Path) -> pd.DataFrame | None:
    """Stream CSO SA polygons — do not load 487 MB into a GeoDataFrame."""
    cache = path.with_suffix(".centroids.parquet")
    if cache.exists() and cache.stat().st_mtime >= path.stat().st_mtime:
        logger.info("Using cached SA centroids {}", cache.name)
        cached = pd.read_parquet(cache)
        if "region" in cached.columns:
            cached["region"] = cached["region"].astype(str).map(slug_county)
        return cached

    try:
        from pyproj import Transformer
        from shapely.geometry import shape
        from shapely.ops import transform as shp_transform
    except ImportError:
        logger.warning("shapely/pyproj missing — cannot read SA polygons")
        return None

    to_itm = Transformer.from_crs("EPSG:4326", "EPSG:2157", always_xy=True).transform
    raw = json.loads(path.read_text(encoding="utf-8"))
    features = raw.get("features") or []
    del raw
    if not features:
        return None
    sample_props = (features[0].get("properties") or {})
    schema_props = {str(k).lower(): k for k in sample_props}

    def pick(*names: str) -> str | None:
        for n in names:
            if n in schema_props:
                return schema_props[n]
        for key, orig in schema_props.items():
            if any(n in key for n in names):
                return orig
        return None

    code_col = pick("sa_guid_2022", "sa_guid", "sa2022", "guid", "small_area", "sa_code")
    if code_col is None:
        logger.warning("SA geojson has no code column: {}", list(schema_props))
        return None
    county_col = pick("county_english", "county", "countyname", "contae", "local_authority")
    name_col = pick("ed_english", "sa_name", "ed_name", "name")
    ed_col = pick("ed_id_str", "ed_id", "ed_official")
    pub_col = pick("sa_pub2022", "sa_geogid_2022")
    nuts1_col = pick("sa_nuts1", "nuts1")

    rows: list[dict] = []
    for feat in features:
        props = feat.get("properties") or {}
        geom = feat.get("geometry")
        if not geom:
            continue
        if nuts1_col:
            nuts = str(props.get(nuts1_col) or "")
            if nuts and ("UKN" in nuts or "Northern" in nuts):
                continue
        try:
            shp = shape(geom)
            if shp.is_empty:
                continue
            itm = shp_transform(to_itm, shp)
            cent = shp.centroid
        except Exception:  # noqa: BLE001
            continue
        row = {
            "sa_code": str(props.get(code_col)),
            "lat": float(cent.y),
            "lon": float(cent.x),
            "area_km2": float(itm.area) / 1e6,
        }
        row["name"] = str(props.get(name_col) or row["sa_code"]) if name_col else row["sa_code"]
        if county_col:
            row["region"] = slug_county(str(props.get(county_col) or ""))
        if ed_col:
            row["ed_code"] = _norm_ed(props.get(ed_col))
        if pub_col:
            row["sa_pub"] = str(props.get(pub_col))
        rows.append(row)
        if len(rows) % 4000 == 0:
            logger.info("Streamed {} SA polygons…", len(rows))
    del features

    if len(rows) < 1000:
        logger.warning("SA geojson yielded only {} rows", len(rows))
        return None
    out = pd.DataFrame(rows)
    out.to_parquet(cache, index=False)
    logger.info("Loaded {} Small Area polygons from {} (cached {})", len(out), path.name, cache.name)
    return out


def _attach_population(areas: pd.DataFrame, saps_path: Path | None) -> pd.DataFrame:
    if saps_path is None or not saps_path.exists():
        if "population" not in areas.columns:
            areas = areas.copy()
            areas["population"] = 120  # typical SA household band midpoint; flagged
            areas.attrs["pop_note"] = "SAPS missing — placeholder 120 per SA (documented hole)"
        return areas
    try:
        sap = pd.read_csv(saps_path, usecols=lambda c: str(c).lower() in {"guid", "sa_guid_2022", "t1_1agett"})
    except Exception as exc:  # noqa: BLE001
        logger.warning("SAPS parse failed: {}", exc)
        areas = areas.copy()
        areas["population"] = areas.get("population", 120)
        return areas
    cols = {c.lower(): c for c in sap.columns}
    code = cols.get("guid") or cols.get("sa_guid_2022")
    if code is None:
        for key in ("guid", "small_area", "cso_sa"):
            for c, orig in cols.items():
                if c == key or c.endswith(key):
                    code = orig
                    break
            if code:
                break
    # Census 2022 usually-resident persons — not T1_1AGE0T (age 0).
    pop_col = cols.get("t1_1agett")
    if pop_col is None:
        for c, orig in cols.items():
            if c in {"t1_1agett", "t1_1age_tt"}:
                pop_col = orig
                break
    if code is None or pop_col is None:
        logger.warning("SAPS columns not recognised: {}", list(sap.columns)[:20])
        areas = areas.copy()
        areas["population"] = 120
        areas.attrs["pop_note"] = "SAPS columns unrecognised — placeholder 120 per SA"
        return areas
    sap = sap[[code, pop_col]].copy()
    sap.columns = ["sa_code", "population"]
    sap["sa_code"] = sap["sa_code"].astype(str)
    sap["population"] = pd.to_numeric(sap["population"], errors="coerce")
    merged = areas.merge(sap, on="sa_code", how="left")
    hole = merged["population"].isna().mean()
    logger.info("SAPS join missing {:.2%} (GUID ↔ SA_GUID_2022, pop=T1_1AGETT)", hole)
    merged["population"] = merged["population"].fillna(120)
    return merged


def _merge_hp(areas: pd.DataFrame, hp: pd.DataFrame) -> pd.DataFrame:
    left = areas.copy()
    hp_cols = ["hp_relative", "hp_decile"] + [c for c in ("region",) if c in hp.columns]

    def _take(merged: pd.DataFrame) -> pd.DataFrame:
        if "region_hp" in merged.columns:
            merged["region"] = merged["region"].fillna(merged["region_hp"])
            merged = merged.drop(columns=["region_hp"])
        return merged

    # Prefer SA code join when the Pobal file is SA-level.
    if "sa_code" in hp.columns and hp["sa_code"].nunique() > 5000:
        hp2 = hp.drop_duplicates("sa_code")
        merged = left.merge(
            hp2[["sa_code", *hp_cols]],
            on="sa_code",
            how="left",
            suffixes=("", "_hp"),
        )
        merged = _take(merged)
        rate = merged["hp_relative"].notna().mean()
        logger.info("HP join on SA code: {:.2%}", rate)
        if rate >= 0.5:
            return merged
    # Official 2022 CKAN file is ED-level (Index22_ED_std_rel_wt × ED_ID_STR).
    if "ed_code" in hp.columns and "ed_code" in left.columns:
        hp2 = hp.dropna(subset=["ed_code"]).drop_duplicates("ed_code")
        merged = left.merge(
            hp2[["ed_code", *hp_cols]],
            on="ed_code",
            how="left",
            suffixes=("", "_hp"),
        )
        merged = _take(merged)
        rate = float(merged["hp_relative"].notna().mean())
        logger.info("HP join on ED_ID_STR: {:.2%}", rate)
        if rate >= 0.5:
            merged.attrs["hp_join"] = (
                "Pobal HP 2022 ED relative index (CKAN datastore 0806f07b…) "
                "joined SA→ED via CSO ED_ID_STR. Not invented SA deciles."
            )
            return merged
    # Fallback: county-level mean HP
    if "region" in hp.columns and "hp_relative" in hp.columns:
        means = hp.groupby("region")["hp_relative"].mean()
        left["hp_relative"] = left["region"].map(means)
        from aequitas.ireland.process import hp_decile_from_relative

        left["hp_decile"] = hp_decile_from_relative(left["hp_relative"].fillna(left["hp_relative"].median()))
        left.attrs["hp_join"] = "county-mean fallback (SA codes did not match Pobal CSV)"
        return left
    left["hp_relative"] = 0.0
    left["hp_decile"] = 5
    left.attrs["hp_join"] = "HP missing"
    return left


def run_ireland_pack(cfg: PipelineConfig | None = None, *, skip_download: bool = False) -> Path:
    cfg = cfg or PipelineConfig()
    raw = cfg.raw_dir
    processed = cfg.processed_dir
    dest = ireland_warehouse_path(cfg.project_root)

    if not skip_download:
        try:
            download_tfi_gtfs(raw)
        except Exception as exc:
            logger.warning("TFI download: {}", exc)
        try:
            download_pobal_hp(raw)
        except Exception as exc:
            logger.warning("Pobal download: {}", exc)
        download_cso_sa_geojson(raw)
        download_cso_saps(raw)
        from aequitas.ireland.download import download_ireland_counties

        download_ireland_counties(
            raw,
            public_boundaries=cfg.project_root / "frontend" / "public" / "boundaries" / "ireland_counties.geojson",
        )

    gtfs = tfi_gtfs_path(raw)
    hp_path = raw / "ireland" / "hp_deprivation_2022.csv"
    sa_path = raw / "ireland" / "sa_2022.geojson"
    saps_path = raw / "ireland" / "saps_2022.csv"

    if gtfs is None:
        raise FileNotFoundError("TFI GTFS missing — run download or place data/raw/tfi/GTFS_All.zip")

    stops = load_tfi_stops(gtfs)
    # Full TFI stop_times (not a row cap).
    logger.info("Reading TFI stop_times (evening / Sunday)…")
    stop_times = load_tfi_stop_times_sample(gtfs)
    extras: dict = {}
    try:
        from aequitas.ireland.network import load_tfi_network

        extras = load_tfi_network(gtfs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("TFI network/HHI: {}", exc)

    if sa_path.exists():
        areas = _load_sa_geojson(sa_path)
    else:
        areas = None
    if areas is None or areas.empty:
        # Honest fallback: one row per HP geography with county centroid-ish from stops
        if hp_path.exists():
            hp = load_pobal_hp(hp_path)
            # Use stop mean per county as a stand-in centroid only if HP has region
            if "region" not in hp.columns:
                raise FileNotFoundError(
                    "CSO SA 2022 GeoJSON missing and Pobal CSV has no county — "
                    "cannot build Small Areas. Place sa_2022.geojson under data/raw/ireland/."
                )
            logger.warning("SA polygons missing — building county-level areas from HP + TFI stops")
            rows = []
            for slug, grp in hp.groupby("region"):
                county_stops = stops
                lat = float(county_stops["stop_lat"].mean()) if len(county_stops) else 53.3
                lon = float(county_stops["stop_lon"].mean()) if len(county_stops) else -8.0
                rows.append(
                    {
                        "sa_code": f"HP-{slug}",
                        "name": slug,
                        "lat": lat,
                        "lon": lon,
                        "region": slug,
                        "population": 4000,
                        "hp_relative": float(grp["hp_relative"].mean()),
                        "hp_decile": int(grp["hp_decile"].median()) if "hp_decile" in grp else 5,
                        "area_km2": 500.0,
                    }
                )
            areas = pd.DataFrame(rows)
            areas.attrs["hole"] = "CSO SA 2022 polygons not downloaded — county aggregates only"
        else:
            raise FileNotFoundError("Need CSO SA GeoJSON or Pobal HP CSV")

    areas = _attach_population(areas, saps_path if saps_path.exists() else None)
    if hp_path.exists():
        areas = _merge_hp(areas, load_pobal_hp(hp_path))
    elif "hp_relative" not in areas.columns:
        areas["hp_relative"] = 0.0
        areas["hp_decile"] = 5

    # CSO Small Areas 2022 file is Republic (SA_NUTS1=IE0, n=18,919).
    # The conservative NI bbox also covers Louth / Monaghan centroids — do not
    # drop official Republic SAs. Only clip TFI stops (clip_republic_stops).
    if areas.attrs.get("nuts1_clipped"):
        pass
    areas["hp_decile"] = pd.to_numeric(areas.get("hp_decile"), errors="coerce")
    areas["hp_relative"] = pd.to_numeric(areas.get("hp_relative"), errors="coerce")
    if areas["hp_decile"].isna().any():
        fill_d = int(areas["hp_decile"].median()) if areas["hp_decile"].notna().any() else 5
        areas["hp_decile"] = areas["hp_decile"].fillna(fill_d).astype(int)
    if areas["hp_relative"].isna().any():
        fill_r = float(areas["hp_relative"].median()) if areas["hp_relative"].notna().any() else 0.0
        areas["hp_relative"] = areas["hp_relative"].fillna(fill_r)

    built = build_ireland_areas(areas=areas, stops=stops, stop_times=stop_times)
    write_processed(built, processed)

    join_rate = float(built["sa_code"].notna().mean())
    n_with_pop = int((built["population"] > 0).sum())
    vintages = {
        "gtfs": f"TFI GTFS_All.zip ({datetime.now(timezone.utc).date().isoformat()})",
        "small_areas": "CSO Small Areas 2022" if sa_path.exists() else "county fallback — SA polygons missing",
        "join_rate": f"{join_rate:.4f}",
        "n_with_pop": str(n_with_pop),
        "hole": str(built.attrs.get("hole") or areas.attrs.get("pop_note") or areas.attrs.get("hp_join") or ""),
        "evening": IRELAND_EVENING_NOTE,
    }
    (processed / "ireland" / "vintages.json").write_text(json.dumps(vintages, indent=2), encoding="utf-8")

    path = build_ireland_warehouse(built, dest, stops=stops, vintages=vintages, extras=extras)
    from aequitas.ireland.bands import write_ireland_bands

    write_ireland_bands(cfg)
    return path
