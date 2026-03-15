"""Tests for POI data ingestion."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.poi import load_hospitals, load_gp_surgeries, load_schools, load_employment_proxy


@pytest.fixture(scope="module")
def cfg():
    return PipelineConfig()


def test_hospitals_count(cfg):
    df = load_hospitals(cfg.audit_dir / "hospitals_geocoded.parquet")
    # Phase 0: 3,714 geocoded hospitals (filter to rows with lat/lon)
    assert len(df) == 3714


def test_gp_surgeries_count(cfg):
    df = load_gp_surgeries(cfg.audit_dir / "gp_surgeries_geocoded.parquet")
    assert len(df) == 12059


def test_schools_secondary_count(cfg):
    df = load_schools(cfg.audit_dir / "schools_secondary_geocoded.parquet")
    assert len(df) == 3336


def test_employment_proxy(cfg):
    df = load_employment_proxy(cfg.audit_dir / "lsoa_employment_proxy.parquet")
    assert len(df) >= 32_000
    assert "employment_proxy" in df.columns
