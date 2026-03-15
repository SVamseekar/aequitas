"""Tests for NaPTAN ingestion."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.naptan import load_naptan


@pytest.fixture
def naptan_df():
    cfg = PipelineConfig()
    return load_naptan(cfg.raw_dir / "naptan" / "Stops.csv")


def test_naptan_count(naptan_df, ground_truth):
    assert len(naptan_df) == ground_truth["naptan"]["england_active_bus_stops"]


def test_naptan_unique_ids(naptan_df):
    assert naptan_df["ATCOCode"].nunique() == len(naptan_df)


def test_naptan_stop_types(naptan_df):
    allowed = {"BCT", "BCS", "BCE"}
    assert set(naptan_df["StopType"].unique()).issubset(allowed)


def test_naptan_status(naptan_df):
    assert (naptan_df["Status"] == "active").all()


def test_naptan_england_only(naptan_df):
    prefixes = naptan_df["ATCOCode"].str[:3].astype(int)
    assert (prefixes < 500).all()


def test_naptan_has_coordinates(naptan_df):
    assert naptan_df["Latitude"].notna().sum() > 0.95 * len(naptan_df)
