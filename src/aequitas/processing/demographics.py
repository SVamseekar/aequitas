"""Master LSOA table assembly — joins all 9 socio-economic factors.

Builds the canonical master_lsoa_table used by all analytics stages.
Ground truth: 33,755 England LSOAs, population 56,490,056.
"""

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.ingestion.census import (
    load_age_structure,
    load_car_ownership,
    load_disability,
    load_ethnicity,
    load_population,
    load_unemployment,
)
from aequitas.ingestion.imd import load_imd
from aequitas.ingestion.ruc import load_ruc


def build_master_lsoa_table(cfg: PipelineConfig) -> pd.DataFrame:
    """Build master LSOA table by joining all 9 socio-economic factors.

    Factors:
    1. Deprivation (IMD score/decile/subdomains)
    2. Unemployment rate (TS066)
    3. Car ownership (% no-car households, TS045)
    4. Elderly population share (% aged 65+, TS007a)
    5. Income levels (IMD income sub-domain)
    6. Ethnic composition (% non-white-British, TS021)
    7. Geo barriers score (IMD barriers_score as accessibility proxy)
    8. Urban/rural classification (RUC 2021)
    9. Disability (% disabled under Equality Act, TS038)

    Returns DataFrame with lsoa_code as join key, 33,755 rows.
    """
    logger.info("Building master LSOA table")

    # Load all sources
    pop = load_population(cfg.raw_dir)
    imd = load_imd(cfg.raw_dir / "imd" / "imd2025_all_ranks_scores_deciles.csv")
    age = load_age_structure(cfg.raw_dir)
    cars = load_car_ownership(cfg.raw_dir)
    eth = load_ethnicity(cfg.raw_dir)
    unemp = load_unemployment(cfg.raw_dir)
    disability = load_disability(cfg.raw_dir)
    ruc = load_ruc(cfg.raw_dir)

    # Start from population (all 33,755 England LSOAs)
    df = pop.rename(columns={"lsoa_name": "lsoa_nm"}).rename(columns={"lsoa_code": "lsoa_cd"})
    # Use standardised lsoa_code throughout
    df = df.rename(columns={"lsoa_cd": "lsoa_code"})

    # Join IMD
    df = df.merge(
        imd[["lsoa_code", "lad_code", "lad_name", "imd_score", "imd_rank", "imd_decile",
             "income_score"]].rename(columns={"lad_code": "lad_cd", "lad_name": "lad_nm"}),
        on="lsoa_code", how="left",
    )
    # Add subdomain scores if available
    for col in ["employment_score", "health_score", "crime_score", "barriers_score", "living_env_score"]:
        if col in imd.columns:
            df = df.merge(imd[["lsoa_code", col]], on="lsoa_code", how="left")

    # Geo barriers score — use IMD barriers_score as proximity proxy (Factor 7)
    if "barriers_score" not in df.columns:
        df["barriers_score"] = 0.0
    df["geo_barriers_score"] = df["barriers_score"]

    # Join age structure
    df = df.merge(age[["lsoa_code", "elderly_pct", "elderly_65plus"]], on="lsoa_code", how="left")

    # Join car ownership
    df = df.merge(
        cars[["lsoa_code", "total_households", "no_car_households", "nocar_pct"]],
        on="lsoa_code", how="left",
    )

    # Join ethnicity
    df = df.merge(eth[["lsoa_code", "nonwhite_pct"]], on="lsoa_code", how="left")

    # Join unemployment
    df = df.merge(
        unemp[["lsoa_code", "econ_active", "unemployed", "unemployment_rate"]],
        on="lsoa_code", how="left",
    )

    # Join disability
    df = df.merge(
        disability[["lsoa_code", "disability_pct"]],
        on="lsoa_code", how="left",
    )

    # Join urban/rural
    df = df.merge(ruc[["lsoa_code", "ruc_code", "ruc_name", "urban_rural"]], on="lsoa_code", how="left")

    logger.info(
        "Master LSOA table: {} rows, {} columns",
        len(df), len(df.columns)
    )
    return df.reset_index(drop=True)
