"""IMD 2025 ingestion — scores, ranks, deciles for all England LSOAs.

Source: data/raw/imd/imd2025_all_ranks_scores_deciles.csv
Ground truth: 33,755 LSOAs, zero missing IMD scores.
"""

from pathlib import Path

import pandas as pd
from loguru import logger


def load_imd(path: Path) -> pd.DataFrame:
    """Load IMD 2025 scores, ranks, and deciles for all England LSOAs.

    Returns DataFrame with columns: lsoa_code, lsoa_name, lad_code, lad_name,
    imd_score, imd_rank, imd_decile, income_score, employment_score, health_score,
    crime_score, barriers_score, living_env_score.
    """
    logger.info("Loading IMD 2025 from {}", path)
    df = pd.read_csv(path)
    logger.info("IMD raw rows: {}", len(df))

    result = pd.DataFrame({
        "lsoa_code": df["LSOA code (2021)"],
        "lsoa_name": df["LSOA name (2021)"],
        "lad_code": df["Local Authority District code (2024)"],
        "lad_name": df["Local Authority District name (2024)"],
        "imd_score": df["Index of Multiple Deprivation (IMD) Score"],
        "imd_rank": df["Index of Multiple Deprivation (IMD) Rank (where 1 is most deprived)"],
        "imd_decile": df["Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOAs)"],
        "income_score": df["Income Score (rate)"],
    })

    # Add subdomain scores if present
    for col_name, out_name in [
        ("Employment Score (rate)", "employment_score"),
        ("Health Deprivation and Disability Score", "health_score"),
        ("Crime Score", "crime_score"),
        ("Barriers to Housing and Services Score", "barriers_score"),
        ("Living Environment Score", "living_env_score"),
    ]:
        if col_name in df.columns:
            result[out_name] = df[col_name]

    logger.info("IMD loaded: {} LSOAs", len(result))
    return result.reset_index(drop=True)
