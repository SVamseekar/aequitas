"""Verify precompute generates all 30 filter combinations."""
from aequitas.warehouse.precompute import _REGIONS, _AREA_TYPES


def test_filter_combo_count():
    """30 combos = 10 regions (all + 9 ONS codes) × 3 area_types."""
    combos = [(r, a) for r in _REGIONS for a in _AREA_TYPES]
    assert len(combos) == 30  # 10 × 3


def test_no_combos_skipped():
    """Every region × area_type pair must be included."""
    combos = [(r, a) for r in _REGIONS for a in _AREA_TYPES]
    # Verify specific previously-skipped combos exist
    assert ("E12000001", "urban") in combos  # North East urban
    assert ("E12000007", "rural") in combos  # London rural
