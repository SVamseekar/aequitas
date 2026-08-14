"""Stage 3 writers — compute analytics Parquets instead of checking audit files.

Writes to processed_dir and mirrors into audit_dir so warehouse precompute
can discover outputs after a real pipeline run.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from aequitas.analytics.equity import (
    compute_concentration_index,
    compute_gini,
    compute_palma_ratio,
    compute_vulnerability_index,
    identify_triple_deprived,
)
from aequitas.core.config import PipelineConfig


def _first_existing(cfg: PipelineConfig, name: str) -> Path | None:
    for folder in (cfg.processed_dir, cfg.audit_dir):
        path = folder / name
        if path.exists():
            return path
    return None


def _write_both(df: pd.DataFrame, cfg: PipelineConfig, name: str) -> list[Path]:
    cfg.processed_dir.mkdir(parents=True, exist_ok=True)
    cfg.audit_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for folder in (cfg.processed_dir, cfg.audit_dir):
        out = folder / name
        df.to_parquet(out, index=False, compression="zstd")
        written.append(out)
    return written


def _resolve_lsoa_col(df: pd.DataFrame) -> str:
    for col in ("lsoa_cd", "lsoa_code"):
        if col in df.columns:
            return col
    raise ValueError("No LSOA code column in source table")


def write_equity_metrics(cfg: PipelineConfig) -> list[Path]:
    """Compute LSOA-level equity metrics and write Parquet.

    Joins master LSOA demographics to service-quality trips when available.
    """
    master_path = _first_existing(cfg, "master_lsoa_table.parquet")
    if master_path is None:
        raise FileNotFoundError("master_lsoa_table.parquet not found in processed/ or audit/")

    master = pd.read_parquet(master_path)
    lsoa_col = _resolve_lsoa_col(master)
    df = master.copy()
    df["lsoa_cd"] = df[lsoa_col].astype(str)

    sq_path = _first_existing(cfg, "lsoa_service_quality.parquet")
    if sq_path is not None:
        sq = pd.read_parquet(sq_path)
        sq_key = _resolve_lsoa_col(sq)
        trip_col = next(
            (c for c in ("trips_per_capita", "annual_trips_per_capita", "trips") if c in sq.columns),
            None,
        )
        if trip_col:
            merged = sq[[sq_key, trip_col]].rename(columns={sq_key: "lsoa_cd", trip_col: "trips_per_capita"})
            df = df.merge(merged, on="lsoa_cd", how="left", suffixes=("", "_sq"))
            if "trips_per_capita_sq" in df.columns:
                df["trips_per_capita"] = df["trips_per_capita_sq"].fillna(df.get("trips_per_capita"))
                df = df.drop(columns=["trips_per_capita_sq"])

    if "trips_per_capita" not in df.columns:
        df["trips_per_capita"] = 0.0
    df["trips_per_capita"] = pd.to_numeric(df["trips_per_capita"], errors="coerce").fillna(0.0)

    if "population" not in df.columns:
        raise ValueError("master LSOA table missing population")

    values = df["trips_per_capita"].to_numpy(dtype=float)
    weights = df["population"].to_numpy(dtype=float)
    gini = compute_gini(values, weights) if weights.sum() > 0 else 0.0
    palma = compute_palma_ratio(values, weights) if weights.sum() > 0 else 0.0
    if "imd_rank" in df.columns:
        ci = compute_concentration_index(
            values,
            df["imd_rank"].to_numpy(dtype=float),
            weights,
        )
    else:
        ci = 0.0

    try:
        df["vulnerability_index"] = compute_vulnerability_index(df)
    except (KeyError, ValueError) as exc:
        logger.warning(f"Vulnerability index skipped: {exc}")
        df["vulnerability_index"] = 0.0
    try:
        df["triple_deprived"] = identify_triple_deprived(df)
    except (KeyError, ValueError) as exc:
        logger.warning(f"Triple-deprived flag skipped: {exc}")
        df["triple_deprived"] = False

    df["gini"] = round(float(gini), 4)
    df["palma_ratio"] = round(float(palma), 3)
    df["concentration_index"] = round(float(ci), 4)

    keep = [
        "lsoa_cd",
        "population",
        "imd_decile",
        "imd_rank",
        "imd_score",
        "trips_per_capita",
        "vulnerability_index",
        "triple_deprived",
        "gini",
        "palma_ratio",
        "concentration_index",
        "region",
        "urban_rural",
    ]
    extra = [c for c in keep if c in df.columns]
    out_df = df[extra].copy()
    paths = _write_both(out_df, cfg, "lsoa_equity_metrics.parquet")
    logger.info(
        f"Wrote equity metrics: n={len(out_df):,} gini={gini:.4f} palma={palma:.3f} ci={ci:.4f}"
    )
    return paths


def _mirror_existing(cfg: PipelineConfig, name: str) -> Path | None:
    src = _first_existing(cfg, name)
    if src is None:
        return None
    df = pd.read_parquet(src)
    _write_both(df, cfg, name)
    return cfg.processed_dir / name


def write_analytics_pack(cfg: PipelineConfig) -> list[Path]:
    """Write equity plus any existing policy / economic / SHAP artefacts."""
    written: list[Path] = []
    written.extend(write_equity_metrics(cfg))

    optional = (
        "lsoa_policy_synthesis.parquet",
        "lta_franchising_readiness.parquet",
        "policy_scenarios.parquet",
        "shap_importance.parquet",
        "lsoa_2sfca.parquet",
        "lsoa_economic_appraisal.parquet",
        "lsoa_service_quality.parquet",
    )
    for name in optional:
        path = _mirror_existing(cfg, name)
        if path is not None:
            written.append(path)
        else:
            logger.warning(f"Optional analytics artefact not found: {name}")

    shap_src = _first_existing(cfg, "master_lsoa_table.parquet")
    shap_out = cfg.processed_dir / "shap_importance.parquet"
    if shap_src is not None and not shap_out.exists():
        try:
            from aequitas.analytics.shap_export import export_shap_importance

            export_shap_importance(cfg, output_dir=cfg.processed_dir)
            if shap_out.exists():
                written.append(shap_out)
                _write_both(pd.read_parquet(shap_out), cfg, "shap_importance.parquet")
        except Exception as exc:
            logger.warning(f"SHAP export skipped: {exc}")

    return written
