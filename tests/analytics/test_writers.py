"""Stage 3 writers must produce equity Parquet, not only check audit files."""

from pathlib import Path

import pandas as pd

from aequitas.analytics.writers import write_equity_metrics
from aequitas.core.config import PipelineConfig


def test_write_equity_metrics_computes_gini(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    audit = tmp_path / "audit"
    processed.mkdir()
    audit.mkdir()

    n = 40
    master = pd.DataFrame(
        {
            "lsoa_code": [f"E{i:08d}" for i in range(n)],
            "population": [1000] * n,
            "imd_score": list(range(n)),
            "imd_rank": list(range(1, n + 1)),
            "imd_decile": [(i % 10) + 1 for i in range(n)],
            "nocar_pct": [10.0] * n,
            "elderly_pct": [15.0] * n,
            "disability_pct": [8.0] * n,
            "unemployment_rate": [5.0] * n,
        }
    )
    sq = pd.DataFrame(
        {
            "lsoa_code": master["lsoa_code"],
            "trips_per_capita": [float(i) for i in range(n)],
        }
    )
    master.to_parquet(processed / "master_lsoa_table.parquet", index=False)
    sq.to_parquet(processed / "lsoa_service_quality.parquet", index=False)

    cfg = PipelineConfig(processed_dir=processed, audit_dir=audit)
    paths = write_equity_metrics(cfg)
    assert any(p.name == "lsoa_equity_metrics.parquet" for p in paths)

    out = pd.read_parquet(processed / "lsoa_equity_metrics.parquet")
    assert len(out) == n
    gini = float(out["gini"].iloc[0])
    assert 0.0 < gini < 1.0
    assert (audit / "lsoa_equity_metrics.parquet").exists()
