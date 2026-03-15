"""Tests for core type definitions."""

from aequitas.core.types import RegionCode, StopType, UrbanRural, IMDDecile


def test_region_codes_count():
    assert len(RegionCode) == 9


def test_region_code_values():
    assert RegionCode.NORTH_EAST.value == "E12000001"
    assert RegionCode.LONDON.value == "E12000007"


def test_stop_types():
    assert StopType.BCT.value == "BCT"
    assert StopType.BCS.value == "BCS"
    assert StopType.BCE.value == "BCE"


def test_urban_rural():
    assert UrbanRural.URBAN.value == "urban"
    assert UrbanRural.RURAL.value == "rural"


def test_imd_decile_range():
    assert IMDDecile(1).value == 1
    assert IMDDecile(10).value == 10


def test_england_atco_prefixes():
    from aequitas.core.types import ENGLAND_ATCO_PREFIXES
    assert "010" in ENGLAND_ATCO_PREFIXES  # North East
    assert "400" in ENGLAND_ATCO_PREFIXES  # West Midlands
    assert "500" not in ENGLAND_ATCO_PREFIXES  # Scotland
