"""Tests for pipeline configuration."""

from pathlib import Path
from aequitas.core.config import PipelineConfig


def test_default_config_paths_exist():
    cfg = PipelineConfig()
    assert cfg.raw_dir.exists()
    assert cfg.audit_dir.exists()


def test_filter_space():
    cfg = PipelineConfig()
    combos = cfg.filter_combinations()
    # 10 regions (all + 9) × 3 area types = 30
    assert len(combos) == 30
