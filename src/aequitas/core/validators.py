"""Reusable field validators for Aequitas data models.

Every raw data boundary uses these to catch malformed data early.
"""

import re

_LSOA_PATTERN = re.compile(r"^E0[12]\d{6}$")
_ATCO_MIN_LEN = 8
_ATCO_MAX_LEN = 16
_UK_LAT_RANGE = (49.8, 60.9)
_UK_LON_RANGE = (-8.2, 1.8)


def validate_atco_code(v: str) -> str:
    """Validate NaPTAN ATCO code format (8-16 alphanumeric chars)."""
    if not (_ATCO_MIN_LEN <= len(v) <= _ATCO_MAX_LEN):
        raise ValueError(
            f"ATCO code must be {_ATCO_MIN_LEN}-{_ATCO_MAX_LEN} chars, got {len(v)}: {v!r}"
        )
    return v


def validate_lsoa_code(v: str) -> str:
    """Validate England LSOA code format (E01XXXXXX or E02XXXXXX)."""
    if not _LSOA_PATTERN.match(v):
        raise ValueError(f"LSOA code must match E0[12]XXXXXX pattern, got: {v!r}")
    return v


def validate_uk_latitude(v: float) -> float:
    """Validate latitude is within UK bounds (49.8-60.9)."""
    if not (_UK_LAT_RANGE[0] <= v <= _UK_LAT_RANGE[1]):
        raise ValueError(
            f"UK latitude must be {_UK_LAT_RANGE[0]}-{_UK_LAT_RANGE[1]}, got: {v}"
        )
    return v


def validate_uk_longitude(v: float) -> float:
    """Validate longitude is within UK bounds (-8.2 to 1.8)."""
    if not (_UK_LON_RANGE[0] <= v <= _UK_LON_RANGE[1]):
        raise ValueError(
            f"UK longitude must be {_UK_LON_RANGE[0]}-{_UK_LON_RANGE[1]}, got: {v}"
        )
    return v


def is_england_atco(atco_code: str) -> bool:
    """Check if an ATCO code belongs to an England admin area (prefix 000-499)."""
    try:
        prefix = int(atco_code[:3])
    except (ValueError, IndexError):
        return False
    return 0 <= prefix <= 499
