"""Tests for master LSOA table assembly."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.core.constants import LSOA_COUNT_ENGLAND, POPULATION_ENGLAND
from aequitas.processing.demographics import build_master_lsoa_table


def test_master_table_row_count():
    cfg = PipelineConfig()
    df = build_master_lsoa_table(cfg)
    assert len(df) == LSOA_COUNT_ENGLAND


def test_master_table_population_total():
    cfg = PipelineConfig()
    df = build_master_lsoa_table(cfg)
    assert abs(df["population"].sum() - POPULATION_ENGLAND) < 100


def test_master_table_has_all_9_factors():
    cfg = PipelineConfig()
    df = build_master_lsoa_table(cfg)
    required = [
        "imd_score", "imd_decile", "unemployment_rate", "nocar_pct",
        "elderly_pct", "income_score", "nonwhite_pct", "geo_barriers_score",
        "urban_rural", "disability_pct",
    ]
    for col in required:
        assert col in df.columns, f"Missing factor column: {col}"
        assert df[col].notna().mean() > 0.95, f"Too many nulls in {col}"
