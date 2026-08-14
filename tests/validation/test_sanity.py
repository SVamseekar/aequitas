from aequitas.validation.sanity import validate_sanity
from aequitas.core.config import PipelineConfig
from pathlib import Path

import pandas as pd


def test_sanity_fails_without_master(tmp_path: Path) -> None:
    cfg = PipelineConfig(processed_dir=tmp_path / "p", audit_dir=tmp_path / "a")
    cfg.processed_dir.mkdir()
    cfg.audit_dir.mkdir()
    result = validate_sanity(cfg)
    assert result["all_pass"] is False


def test_sanity_passes_england_counts(tmp_path: Path) -> None:
    processed = tmp_path / "p"
    processed.mkdir()
    df = pd.DataFrame(
        {
            "lsoa_code": [f"E{i:08d}" for i in range(33755)],
            "population": [1674] * 33755,
        }
    )
    # Population will fail unless we use exact 56_490_056
    # 33755 * 1674 = 56_505_870 — fail pop, pass lsoa
    df.to_parquet(processed / "master_lsoa_table.parquet", index=False)
    cfg = PipelineConfig(processed_dir=processed, audit_dir=tmp_path / "a")
    cfg.audit_dir.mkdir()
    result = validate_sanity(cfg)
    names = {c["name"]: c["status"] for c in result["checks"]}
    assert names["lsoa_count"] == "PASS"
    assert names["population_total"] == "FAIL"
