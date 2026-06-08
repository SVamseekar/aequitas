"""Tests for section_results precomputation."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.warehouse.precompute import precompute_all_sections
from aequitas.warehouse.provenance import ProvenanceEntry, build_equity_provenance


@pytest.mark.slow
def test_precompute_produces_results():
    cfg = PipelineConfig()
    results = precompute_all_sections(cfg)
    # At least some filter combos × sections
    assert len(results) > 0
    # Each result has required fields
    for r in results[:5]:
        assert "region" in r
        assert "urban_rural" in r
        assert "section_id" in r
        assert "stats" in r
        assert "narrative" in r


def test_provenance_entry_serialises():
    entry = ProvenanceEntry(
        metric_id="gini_coefficient",
        value=0.5741,
        formula="1 - 2 * trapezoid(cum_service, cum_pop)",
        inputs={"gini": 0.5741},
        source_files=["lsoa_service_quality.parquet"],
    )
    d = entry.to_dict()
    assert d["metric_id"] == "gini_coefficient"
    assert d["value"] == 0.5741
    assert "formula" in d
    assert isinstance(d["source_files"], list)


def test_build_equity_provenance():
    entries = build_equity_provenance(gini=0.5741, palma=5.702, ci=0.1358)
    assert len(entries) == 3
    metric_ids = {e.metric_id for e in entries}
    assert "gini_coefficient" in metric_ids
    assert "palma_ratio" in metric_ids
    assert "concentration_index" in metric_ids


def test_region_filter_matches_full_names():
    """REGION_NAMES must map ONS codes to the full names present in the data."""
    from aequitas.warehouse.precompute import REGION_NAMES
    from aequitas.core.types import RegionCode

    assert REGION_NAMES[RegionCode.NORTH_EAST.value] == "North East"
    assert REGION_NAMES[RegionCode.LONDON.value] == "London"
    assert REGION_NAMES[RegionCode.YORKSHIRE.value] == "Yorkshire and The Humber"
    assert len(REGION_NAMES) == 9


@pytest.mark.slow
def test_region_filter_produces_nonempty_subset():
    """Filtering lsoa_policy_synthesis by ONS code (via REGION_NAMES) must match rows."""
    import pandas as pd
    from aequitas.core.config import PipelineConfig
    from aequitas.warehouse.precompute import REGION_NAMES

    cfg = PipelineConfig()
    df = pd.read_parquet(cfg.audit_dir / "lsoa_policy_synthesis.parquet")
    mask = df["region"] == REGION_NAMES["E12000001"]
    assert mask.sum() > 0, "North East region filter must match rows in the data"
