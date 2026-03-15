"""Census 2021 table ingestion — population, age, car ownership, ethnicity, unemployment, disability.

All tables filtered to England LSOAs (geography code starting with 'E01').
Source files: data/raw/census/ and data/raw/nomis/
"""

from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from loguru import logger

_ENGLAND_LSOA_PREFIX = "E01"


def _read_lsoa_csv_from_zip(zip_path: Path, filename: str) -> pd.DataFrame:
    """Read an LSOA-level CSV from inside a zip archive."""
    with ZipFile(zip_path) as zf:
        with zf.open(filename) as f:
            return pd.read_csv(f)


def _filter_england_lsoa(df: pd.DataFrame, code_col: str = "geography code") -> pd.DataFrame:
    """Filter DataFrame to England LSOAs only (code starts with E01)."""
    return df[df[code_col].str.startswith(_ENGLAND_LSOA_PREFIX)].copy()


def load_population(raw_dir: Path) -> pd.DataFrame:
    """Load Census TS001 population by LSOA.

    Returns DataFrame with columns: lsoa_code, lsoa_name, population.
    Ground truth: 33,755 England LSOAs, total population 56,490,056.
    """
    path = raw_dir / "census" / "census2021_ts001_lsoa_population.csv"
    logger.info("Loading population from {}", path)
    df = pd.read_csv(path)
    df = _filter_england_lsoa(df)
    pop_col = "Residence type: Total; measures: Value"
    result = pd.DataFrame({
        "lsoa_code": df["geography code"],
        "lsoa_name": df["geography"],
        "population": df[pop_col].astype(int),
    })
    logger.info("Population loaded: {} LSOAs, total pop={}", len(result), result["population"].sum())
    return result.reset_index(drop=True)


def load_age_structure(raw_dir: Path) -> pd.DataFrame:
    """Load Census TS007a age structure by LSOA.

    Returns DataFrame with columns: lsoa_code, age_total, elderly_pct (65+).
    """
    zip_path = raw_dir / "census" / "census2021-ts007a.zip"
    logger.info("Loading age structure from {}", zip_path)
    df = _read_lsoa_csv_from_zip(zip_path, "census2021-ts007a-lsoa.csv")
    df = _filter_england_lsoa(df)

    # Sum up 65+ columns
    age_total_col = "Age: Total"
    age_cols = [c for c in df.columns if "Age: Aged" in c]
    elderly_cols = [c for c in age_cols if any(
        f"Aged {a}" in c for a in
        ["65", "66", "67", "68", "69", "70", "71", "72", "73", "74", "75",
         "76", "77", "78", "79", "80", "81", "82", "83", "84", "85"]
    )]

    result = pd.DataFrame({"lsoa_code": df["geography code"]})
    result["age_total"] = df[age_total_col]
    result["elderly_65plus"] = df[elderly_cols].sum(axis=1)
    result["elderly_pct"] = (result["elderly_65plus"] / result["age_total"] * 100).round(2)
    logger.info("Age structure loaded: {} LSOAs", len(result))
    return result.reset_index(drop=True)


def load_car_ownership(raw_dir: Path) -> pd.DataFrame:
    """Load Census TS045 car/van availability by LSOA.

    Returns DataFrame with columns: lsoa_code, total_households, no_car_households, nocar_pct.
    """
    zip_path = raw_dir / "census" / "census2021-ts045.zip"
    logger.info("Loading car ownership from {}", zip_path)
    df = _read_lsoa_csv_from_zip(zip_path, "census2021-ts045-lsoa.csv")
    df = _filter_england_lsoa(df)

    total_col = "Number of cars or vans: Total: All households"
    nocar_col = "Number of cars or vans: No cars or vans in household"
    result = pd.DataFrame({
        "lsoa_code": df["geography code"],
        "total_households": df[total_col].astype(int),
        "no_car_households": df[nocar_col].astype(int),
    })
    result["nocar_pct"] = (result["no_car_households"] / result["total_households"] * 100).round(2)
    logger.info("Car ownership loaded: {} LSOAs", len(result))
    return result.reset_index(drop=True)


def load_ethnicity(raw_dir: Path) -> pd.DataFrame:
    """Load Census TS021 ethnic group by LSOA.

    Returns DataFrame with columns: lsoa_code, total_residents, white_british, nonwhite_pct.
    """
    zip_path = raw_dir / "census" / "census2021-ts021.zip"
    logger.info("Loading ethnicity from {}", zip_path)
    df = _read_lsoa_csv_from_zip(zip_path, "census2021-ts021-lsoa.csv")
    df = _filter_england_lsoa(df)

    total_col = "Ethnic group: Total: All usual residents"
    white_col = "Ethnic group: White: English, Welsh, Scottish, Northern Irish or British"
    result = pd.DataFrame({
        "lsoa_code": df["geography code"],
        "total_residents": df[total_col].astype(int),
        "white_british": df[white_col].astype(int),
    })
    result["nonwhite_pct"] = (
        (result["total_residents"] - result["white_british"]) / result["total_residents"] * 100
    ).round(2)
    logger.info("Ethnicity loaded: {} LSOAs", len(result))
    return result.reset_index(drop=True)


def load_unemployment(raw_dir: Path) -> pd.DataFrame:
    """Load Census TS066 economic activity by LSOA.

    Returns DataFrame with columns: lsoa_code, econ_active, unemployed, unemployment_rate.
    Source: data/raw/nomis/census2021-ts066.zip (TS066 is in nomis dir).
    Ground truth: 33,755 LSOAs, zero null unemployment rates.
    """
    zip_path = raw_dir / "nomis" / "census2021-ts066.zip"
    logger.info("Loading unemployment from {}", zip_path)
    with ZipFile(zip_path) as zf:
        with zf.open("census2021-ts066-lsoa.csv") as f:
            df = pd.read_csv(f)
    df = _filter_england_lsoa(df)

    active_col = "Economic activity status: Economically active (excluding full-time students)"
    unemp_col = (
        "Economic activity status: Economically active (excluding full-time students): Unemployed"
    )
    result = pd.DataFrame({
        "lsoa_code": df["geography code"],
        "econ_active": df[active_col].astype(int),
        "unemployed": df[unemp_col].astype(int),
    })
    result["unemployment_rate"] = (result["unemployed"] / result["econ_active"] * 100).round(4)
    # Zero active population would divide by zero — set to 0
    result.loc[result["econ_active"] == 0, "unemployment_rate"] = 0.0
    logger.info("Unemployment loaded: {} LSOAs", len(result))
    return result.reset_index(drop=True)


def load_disability(raw_dir: Path) -> pd.DataFrame:
    """Load Census TS038 disability by LSOA.

    Returns DataFrame with columns: lsoa_code, total_residents, disabled, disability_pct.
    Source: data/raw/census/census2021-ts038-lsoa.csv (pre-extracted).
    """
    path = raw_dir / "census" / "census2021-ts038-lsoa.csv"
    logger.info("Loading disability from {}", path)
    df = pd.read_csv(path)
    df = _filter_england_lsoa(df)

    total_col = "Disability: Total: All usual residents"
    disabled_col = "Disability: Disabled under the Equality Act"
    result = pd.DataFrame({
        "lsoa_code": df["geography code"],
        "total_residents": df[total_col].astype(int),
        "disabled": df[disabled_col].astype(int),
    })
    result["disability_pct"] = (result["disabled"] / result["total_residents"] * 100).round(2)
    logger.info("Disability loaded: {} LSOAs", len(result))
    return result.reset_index(drop=True)
