"""Tests for IMD 2025 ingestion."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.imd import load_imd


def test_imd_lsoa_count(ground_truth):
    cfg = PipelineConfig()
    df = load_imd(cfg.raw_dir / "imd" / "imd2025_all_ranks_scores_deciles.csv")
    assert len(df) == ground_truth["imd"]["total_lsoas"]


def test_imd_no_missing_scores():
    cfg = PipelineConfig()
    df = load_imd(cfg.raw_dir / "imd" / "imd2025_all_ranks_scores_deciles.csv")
    assert df["imd_score"].notna().all()


def test_imd_decile_range():
    cfg = PipelineConfig()
    df = load_imd(cfg.raw_dir / "imd" / "imd2025_all_ranks_scores_deciles.csv")
    assert df["imd_decile"].between(1, 10).all()
