"""Tests for Census table ingestion."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.census import (
    load_population,
    load_age_structure,
    load_car_ownership,
    load_ethnicity,
    load_unemployment,
    load_disability,
)


@pytest.fixture(scope="module")
def cfg():
    return PipelineConfig()


def test_population_total(cfg, ground_truth):
    df = load_population(cfg.raw_dir)
    total = df["population"].sum()
    assert abs(total - ground_truth["census"]["total_population_sum"]) < 100


def test_population_lsoa_count(cfg, ground_truth):
    df = load_population(cfg.raw_dir)
    assert len(df) == ground_truth["census"]["total_lsoas_england"]


def test_unemployment_no_nulls(cfg):
    df = load_unemployment(cfg.raw_dir)
    assert df["unemployment_rate"].notna().all()


def test_disability_loads(cfg):
    df = load_disability(cfg.raw_dir)
    assert "disability_pct" in df.columns
    assert len(df) >= 33_000  # England LSOAs
