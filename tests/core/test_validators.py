"""Tests for reusable field validators."""

import pytest
from aequitas.core.validators import (
    validate_atco_code,
    validate_lsoa_code,
    validate_uk_latitude,
    validate_uk_longitude,
    is_england_atco,
)


def test_valid_atco_code():
    assert validate_atco_code("0100BRP90310") == "0100BRP90310"


def test_invalid_atco_code_too_short():
    with pytest.raises(ValueError, match="ATCO code"):
        validate_atco_code("ABC")


def test_valid_lsoa_code():
    assert validate_lsoa_code("E01000001") == "E01000001"


def test_invalid_lsoa_code():
    with pytest.raises(ValueError, match="LSOA code"):
        validate_lsoa_code("W01000001")  # Wales


def test_uk_latitude_valid():
    assert validate_uk_latitude(51.5) == 51.5


def test_uk_latitude_out_of_range():
    with pytest.raises(ValueError, match="latitude"):
        validate_uk_latitude(70.0)


def test_uk_longitude_valid():
    assert validate_uk_longitude(-0.12) == -0.12


def test_uk_longitude_out_of_range():
    with pytest.raises(ValueError, match="longitude"):
        validate_uk_longitude(10.0)


def test_england_atco_true():
    assert is_england_atco("0100BRP90310") is True
    assert is_england_atco("4990ABC12345") is True


def test_england_atco_false():
    assert is_england_atco("5000SCO00001") is False
    assert is_england_atco("6100WAL00001") is False
