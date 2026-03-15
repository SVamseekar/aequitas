"""Tests for ground truth validation."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.validation.ground_truth import validate_against_ground_truth
from aequitas.validation.report import generate_report


@pytest.mark.slow
def test_ground_truth_all_pass():
    """End-to-end: Phase 0 audit Parquets match Phase 0 locked values."""
    cfg = PipelineConfig()
    report = validate_against_ground_truth(cfg)
    failed = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert len(failed) == 0, f"Failed checks: {failed}"


@pytest.mark.slow
def test_ground_truth_produces_checks():
    cfg = PipelineConfig()
    report = validate_against_ground_truth(cfg)
    assert len(report["checks"]) > 0


def test_report_generator():
    fake_result = {
        "checks": [
            {"name": "gini", "status": "PASS", "expected": 0.5741, "actual": 0.5741, "tolerance": "within_pct_5"},
            {"name": "q1_lsoas", "status": "FAIL", "expected": 6091, "actual": 5000, "tolerance": "within_50"},
        ],
        "n_pass": 1,
        "n_warn": 0,
        "n_fail": 1,
        "all_pass": False,
    }
    report = generate_report(fake_result)
    assert "PASS" in report
    assert "FAIL" in report
    assert "gini" in report
