"""Shared test fixtures for Aequitas test suite."""

import json
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
DATA_AUDIT = PROJECT_ROOT / "data" / "audit"
DATA_RAW = PROJECT_ROOT / "data" / "raw"


@pytest.fixture
def ground_truth() -> dict:
    """Load locked ground truth from Phase 0 audit."""
    with open(DATA_AUDIT / "ground_truth.json") as f:
        return json.load(f)


@pytest.fixture
def tag_constants() -> dict:
    """Load TAG v2.03fc constants."""
    with open(DATA_AUDIT / "tag_constants.json") as f:
        return json.load(f)


@pytest.fixture
def desnz_factors() -> dict:
    """Load DESNZ 2025 carbon factors."""
    with open(DATA_AUDIT / "desnz_carbon_factors.json") as f:
        return json.load(f)


@pytest.fixture
def sample_lsoa_codes() -> list[str]:
    """A handful of known LSOA codes for unit tests."""
    return ["E01000001", "E01000002", "E01000003", "E01033768"]


@pytest.fixture
def master_lsoa_table() -> pd.DataFrame:
    """Load the Phase 0 master LSOA table (33,755 rows)."""
    return pd.read_parquet(DATA_AUDIT / "master_lsoa_table.parquet")
