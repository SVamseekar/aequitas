"""Rural-Urban Classification 2021 ingestion.

Maps RUC 2021 6-class to binary urban/rural at LSOA level.
Source: data/raw/census/ruc2021_lsoa_ew.csv
"""

from pathlib import Path

import pandas as pd
from loguru import logger

# Urban RUC codes: UN1, UN2, UN3, UF1, UF2, UF3 (Urban)
# Rural RUC codes: R1, R2, R3 (Rural)
_URBAN_RUC_CODES = frozenset({"UN1", "UN2", "UN3", "UF1", "UF2", "UF3"})


def load_ruc(raw_dir: Path) -> pd.DataFrame:
    """Load RUC 2021 classification for England LSOAs.

    Returns DataFrame with columns: lsoa_code, ruc_code, ruc_name, is_urban.
    Filters to England LSOAs only (LSOA21CD starting with 'E').
    """
    path = raw_dir / "census" / "ruc2021_lsoa_ew.csv"
    logger.info("Loading RUC 2021 from {}", path)
    df = pd.read_csv(path)

    # Filter England only
    df = df[df["LSOA21CD"].str.startswith("E")].copy()
    logger.info("RUC England LSOAs: {}", len(df))

    result = pd.DataFrame({
        "lsoa_code": df["LSOA21CD"],
        "ruc_code": df["RUC21CD"],
        "ruc_name": df["RUC21NM"],
        "is_urban": df["RUC21CD"].isin(_URBAN_RUC_CODES),
        "urban_rural": df["RUC21CD"].apply(lambda x: "urban" if x in _URBAN_RUC_CODES else "rural"),
    })
    logger.info("RUC loaded: {} urban, {} rural", result["is_urban"].sum(), (~result["is_urban"]).sum())
    return result.reset_index(drop=True)
