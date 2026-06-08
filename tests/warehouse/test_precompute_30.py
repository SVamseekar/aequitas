"""Verify precompute generates all 30 filter combinations and skips none."""
import pytest
from aequitas.warehouse.precompute import _REGIONS, _AREA_TYPES


def test_filter_combo_count():
    """30 combos = 10 regions (all + 9 ONS codes) × 3 area_types."""
    combos = [(r, a) for r in _REGIONS for a in _AREA_TYPES]
    assert len(combos) == 30


def test_no_combos_skipped_in_source():
    """The 'continue' skip for region+urban_rural combos must be removed."""
    import inspect
    from aequitas.warehouse import precompute
    source = inspect.getsource(precompute.precompute_all_sections)
    assert "continue" not in source, (
        "precompute_all_sections must not skip any region × urban_rural combo"
    )


@pytest.mark.slow
def test_previously_dead_combos_now_present():
    """North East + Urban and London + Rural must both be processed (were skipped before)."""
    from aequitas.core.config import PipelineConfig
    from aequitas.warehouse.precompute import precompute_all_sections

    cfg = PipelineConfig()
    results = precompute_all_sections(cfg)
    combos_seen = {(r["region"], r["urban_rural"]) for r in results}
    assert ("E12000001", "urban") in combos_seen
    assert ("E12000007", "rural") in combos_seen
